import bpy
import os
import numpy as np
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects import led_codegen_runtime
from liberadronecore.util import image_util


_CAT_CACHE: dict[str, tuple[tuple[float, float, float, float], float]] = {}


@register_runtime_function
def _cat_cache_write(name: str, color: tuple[float, float, float, float], intensity: float) -> None:
    _CAT_CACHE[str(name)] = (tuple(color), float(intensity))


@register_runtime_function
def _cat_cache_read(name: str) -> tuple[tuple[float, float, float, float], float]:
    return _CAT_CACHE.get(str(name), ((0.0, 0.0, 0.0, 1.0), 0.0))


class LDLEDCatCacheNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Bake LED colors into a CAT image for reuse."""

    bl_idname = "LDLEDCatCacheNode"
    bl_label = "CAT Cache"
    bl_icon = "FILE_CACHE"

    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
        options={'LIBRARY_EDITABLE'},
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
                f"_active_{cat_id} = _entry_active_count({entry}, frame)",
                f"if _entry_is_empty({entry}):",
                f"    _active_{cat_id} = 1",
                f"_progress_{cat_id} = _entry_progress({entry}, frame)",
                f"_img_{cat_id} = {image_name!r}",
                f"_v_{cat_id} = 0.0",
                f"if _img_{cat_id}:",
                f"    _im_{cat_id} = bpy.data.images.get(_img_{cat_id})",
                f"    if _im_{cat_id} and _im_{cat_id}.size[1] > 1:",
                f"        _v_{cat_id} = _clamp(idx / float(_im_{cat_id}.size[1] - 1), 0.0, 1.0)",
                f"{out_color} = _sample_image(_img_{cat_id}, (_progress_{cat_id}, _v_{cat_id})) if _active_{cat_id} > 0 else (0.0, 0.0, 0.0, 1.0)",
            ]
        )


def _pack_cat_image(img: bpy.types.Image) -> None:
    if img is None:
        raise ValueError("CAT image is missing")
    if getattr(img, "packed_file", None) is not None:
        return

    img.pack(as_png=True)
    if getattr(img, "packed_file", None) is not None:
        return
    img.pack()
    if getattr(img, "packed_file", None) is not None:
        return
    if getattr(bpy.data, "is_saved", False):
        img.filepath_raw = f"//{img.name}"
        img.file_format = 'PNG'
        img.save()
        img.pack()
    if getattr(img, "packed_file", None) is None:
        raise RuntimeError(f"[CATCache] Failed to pack image {img.name}")


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
    from liberadronecore.tasks import ledeffects_task
    scene.frame_set(frame)
    view_layer = bpy.context.view_layer
    view_layer.update()
    positions, pair_ids, formation_ids = ledeffects_task._collect_formation_positions(scene)
    return positions, pair_ids, formation_ids


