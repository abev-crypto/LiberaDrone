import os
import struct
import zlib

import bpy
import numpy as np
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects import led_codegen_runtime
from liberadronecore.reg.base_reg import RegisterBase


class LDLEDCatCacheNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Bake LED colors into a CAT image for reuse."""

    bl_idname = "LDLEDCatCacheNode"
    bl_label = "CAT Cache"
    bl_icon = "FILE_CACHE"

    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def code_inputs(self):
        if not hasattr(self, "inputs"):
            return []
        if self.image:
            return [sock.name for sock in self.inputs if sock.name != "Color"]
        return [sock.name for sock in self.inputs]

    def draw_buttons(self, context, layout):
        layout.prop(self, "image")
        op = layout.operator("ldled.cat_cache_bake", text="Cache")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        color_in = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_color = self.output_var("Color")
        image_name = self.image.name if self.image else ""
        cat_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        if not image_name:
            return f"{out_color} = {color_in}"
        return "\n".join(
            [
                f"_progress_{cat_id} = _entry_progress({entry}, frame)",
                f"_img_{cat_id} = {image_name!r}",
                f"_v_{cat_id} = 0.0",
                f"if _img_{cat_id}:",
                f"    _im_{cat_id} = bpy.data.images.get(_img_{cat_id})",
                f"    if _im_{cat_id} and _im_{cat_id}.size[1] > 1:",
                f"        _v_{cat_id} = _clamp(idx / float(_im_{cat_id}.size[1] - 1), 0.0, 1.0)",
                f"{out_color} = _sample_image(_img_{cat_id}, (_progress_{cat_id}, _v_{cat_id})) if _progress_{cat_id} > 0.0 else (0.0, 0.0, 0.0, 1.0)",
            ]
        )


def _pack_cat_image(img: bpy.types.Image) -> None:
    if img is None:
        return
    if getattr(img, "packed_file", None) is not None:
        return

    packed = False
    try:
        img.pack(as_png=True)
        packed = getattr(img, "packed_file", None) is not None
    except Exception:
        pass
    if not packed:
        try:
            img.pack()
            packed = getattr(img, "packed_file", None) is not None
        except Exception:
            pass

    if not packed:
        try:
            if getattr(bpy.data, "is_saved", False):
                img.filepath_raw = f"//{img.name}"
                img.file_format = 'PNG'
                img.save()
                img.pack()
                packed = getattr(img, "packed_file", None) is not None
        except Exception:
            pass

    if not packed:
        print(f"[CATCache] Warning: failed to pack image {img.name}")


def _sanitize_filename(name: str) -> str:
    safe = []
    for ch in name or "":
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch in {"_", "-"}:
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe).strip("_")
    return result or "cat_cache"


def _cat_cache_png_path(scene, node) -> str | None:
    filepath = getattr(bpy.data, "filepath", "")
    if not filepath:
        return None
    dirpath = os.path.dirname(filepath)
    if not dirpath:
        return None
    name = _sanitize_filename(getattr(node, "name", "") or "cat_cache")
    return os.path.join(dirpath, f"{name}_CAT.png")


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _write_png_rgba(path: str, pixels: np.ndarray) -> bool:
    try:
        height, width, channels = pixels.shape
    except Exception:
        return False
    if width <= 0 or height <= 0:
        return False
    data = np.clip(pixels, 0.0, 1.0)
    if channels < 4:
        pad = np.zeros((height, width, 4 - channels), dtype=data.dtype)
        data = np.concatenate([data, pad], axis=2)
    elif channels > 4:
        data = data[:, :, :4]
    data = (data * 255.0 + 0.5).astype(np.uint8)
    data = np.flipud(data)  # PNG is top-down; Blender pixels are bottom-up.
    row = data.reshape(height, width * 4)
    raw = np.zeros((height, width * 4 + 1), dtype=np.uint8)
    raw[:, 1:] = row
    compressed = zlib.compress(raw.tobytes(), level=6)
    try:
        with open(path, "wb") as handle:
            handle.write(b"\x89PNG\r\n\x1a\n")
            handle.write(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)))
            handle.write(_png_chunk(b"IDAT", compressed))
            handle.write(_png_chunk(b"IEND", b""))
    except Exception:
        return False
    return True


def _first_entry_span(entry) -> tuple[float, float] | None:
    if not entry:
        return None
    spans: list[tuple[float, float]] = []
    for items in entry.values():
        for start, end in items:
            spans.append((float(start), float(end)))
    if not spans:
        return None
    spans.sort(key=lambda item: (item[0], item[1]))
    return spans[0]


def _resolve_positions(scene, frame: int):
    try:
        from liberadronecore.tasks import ledeffects_task
    except Exception:
        return [], None
    scene.frame_set(frame)
    view_layer = bpy.context.view_layer
    if view_layer is not None:
        view_layer.update()
    positions, pair_ids = ledeffects_task._collect_formation_positions(scene)
    return positions, pair_ids


class LDLED_OT_cat_cache_bake(bpy.types.Operator):
    bl_idname = "ldled.cat_cache_bake"
    bl_label = "Bake CAT Cache"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, LDLEDCatCacheNode):
            self.report({'ERROR'}, "CAT Cache node not found")
            return {'CANCELLED'}

        scene = context.scene
        if scene is None:
            self.report({'ERROR'}, "No active scene")
            return {'CANCELLED'}

        color_fn = led_codegen_runtime.compile_led_socket(tree, node, "Color", force_inputs=True)
        entry_fn = led_codegen_runtime.compile_led_socket(tree, node, "Entry", force_inputs=True)
        if color_fn is None or entry_fn is None:
            self.report({'ERROR'}, "Failed to compile CAT inputs")
            return {'CANCELLED'}

        entry = entry_fn(0, (0.0, 0.0, 0.0), scene.frame_current)
        span = _first_entry_span(entry)
        if span is None:
            self.report({'ERROR'}, "Entry span not found")
            return {'CANCELLED'}

        start, end = span
        start_frame = int(start)
        end_frame = int(end)
        if end_frame <= start_frame:
            self.report({'ERROR'}, "Entry duration is 0")
            return {'CANCELLED'}

        width = max(1, end_frame - start_frame)
        original_frame = scene.frame_current
        span_items: list[tuple[float, float, str]] = []
        if entry:
            for key, items in entry.items():
                for s, e in items:
                    span_items.append((float(s), float(e), str(key)))
        span_items.sort(key=lambda item: (item[0], item[1], item[2]))
        span_preview = span_items[:3]
        print(
            f"[CATCache] Bake node={node.name} start={start_frame} end={end_frame} "
            f"size={width}x{max(0, len(_resolve_positions(scene, start_frame)[0]))} "
            f"spans={len(span_items)} preview={span_preview}"
        )

        suspend = None
        try:
            from liberadronecore.tasks import ledeffects_task
            suspend = getattr(ledeffects_task, "suspend_led_effects", None)
        except Exception:
            suspend = None

        if suspend is not None:
            suspend(True)

        positions, pair_ids = _resolve_positions(scene, start_frame)
        height = len(positions)
        if height <= 0:
            self.report({'ERROR'}, "No formation vertices")
            return {'CANCELLED'}

        pixels = np.zeros((height, width, 4), dtype=np.float32)

        for col_idx, frame in enumerate(range(start_frame, end_frame)):
            positions, pair_ids = _resolve_positions(scene, frame)
            if not positions:
                continue
            if len(positions) != height:
                continue
            frame_logs: list[str] = []
            for idx, pos in enumerate(positions):
                runtime_idx = idx
                if pair_ids is not None:
                    pid = pair_ids[idx]
                    if pid is not None:
                        try:
                            runtime_idx = int(pid)
                        except (TypeError, ValueError):
                            runtime_idx = idx
                if runtime_idx < 0 or runtime_idx >= height:
                    continue
                color = color_fn(runtime_idx, pos, frame)
                if not color:
                    continue
                rgba = [0.0, 0.0, 0.0, 1.0]
                for chan in range(min(4, len(color))):
                    rgba[chan] = float(color[chan])
                pixels[runtime_idx, col_idx] = rgba
                frame_logs.append(
                    f"[CATCache] frame={frame} idx={idx} runtime_idx={runtime_idx} color={rgba}"
                )
            if frame_logs:
                print("\n".join(frame_logs))
        try:
            min_val = float(pixels.min())
            max_val = float(pixels.max())
            nonzero = int(np.count_nonzero(pixels))
            print(f"[CATCache] pixels stats min={min_val} max={max_val} nonzero={nonzero}")
        except Exception:
            pass
        img = None
        png_path = _cat_cache_png_path(scene, node)
        if png_path and _write_png_rgba(png_path, pixels):
            abs_path = bpy.path.abspath(png_path)
            img = node.image
            if img is not None:
                try:
                    img_path = bpy.path.abspath(img.filepath)
                except Exception:
                    img_path = ""
                if img_path and os.path.normpath(img_path) == os.path.normpath(abs_path):
                    try:
                        img.reload()
                    except Exception:
                        pass
                else:
                    img = None
            if img is None:
                try:
                    img = bpy.data.images.load(abs_path, check_existing=True)
                except Exception:
                    img = None

        if img is None:
            img = node.image
            if img is None or img.size[0] != width or img.size[1] != height:
                name = f"{node.name}_CAT"
                img = bpy.data.images.new(name=name, width=width, height=height, alpha=True, float_buffer=True)
            img.pixels.foreach_set(pixels.reshape(-1).tolist())
            try:
                if hasattr(img, "update"):
                    img.update()
                if hasattr(img, "update_tag"):
                    img.update_tag()
            except Exception:
                pass
        if img is not None:
            try:
                led_codegen_runtime._IMAGE_CACHE.pop(int(img.as_pointer()), None)
            except Exception:
                pass
        try:
            img.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
        try:
            img.use_fake_user = True
        except Exception:
            pass
        _pack_cat_image(img)
        node.image = img
        scene.frame_set(original_frame)
        if suspend is not None:
            suspend(False)

        return {'FINISHED'}


class LDLED_CatCacheOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LDLED_OT_cat_cache_bake)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LDLED_OT_cat_cache_bake)
