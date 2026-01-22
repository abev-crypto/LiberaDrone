import json
import os
import re

import bpy
import numpy as np

from liberadronecore.formation import fn_parse
from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.system.transition import transition_apply
from liberadronecore.ui.import_sheet import sheetutils
from liberadronecore.util import image_util


PREFIX_MAP_FILENAME = "prefix_map.json"
DEFAULT_FOLDER_DURATION = 480


def _storyboard_name(base_name: str, meta: dict | None = None) -> str:
    meta = meta or {}
    try:
        meta_id = meta.get("id")
    except Exception:
        meta_id = None
    if meta_id is not None:
        return f"{meta_id}_{base_name}"
    return base_name


def _parse_gap_value(value: str | None, fps: float) -> int:
    if not value:
        return 0
    match = re.match(r"(?i)^(?P<amount>\d+(?:\.\d+)?)(?P<unit>[sf]?)$", value.strip())
    if not match:
        return 0
    amount = float(match.group("amount"))
    unit = match.group("unit").lower()
    if unit == "s":
        return int(round(amount * fps))
    return int(round(amount))


def _split_name_and_gap(folder_name: str, fps: float) -> tuple[str, int]:
    match = re.match(r"^(.*)_(\d+(?:\.\d+)?[sf]?)$", folder_name)
    if not match:
        return folder_name, 0
    base_name = match.group(1)
    gap_frames = _parse_gap_value(match.group(2), fps)
    return base_name, gap_frames


def _load_prefix_map(directory: str, report) -> tuple[dict[str, dict], dict[str, int | None]]:
    mapping_path = os.path.join(directory, PREFIX_MAP_FILENAME)
    if not os.path.isfile(mapping_path):
        return {}, {"start_frame": None}
    try:
        with open(mapping_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        report({"WARNING"}, f"Could not read {PREFIX_MAP_FILENAME}: {exc}")
        return {}, {"start_frame": None}
    if not isinstance(data, dict):
        report({"WARNING"}, f"{PREFIX_MAP_FILENAME} must contain a JSON object")
        return {}, {"start_frame": None}

    default_start = None
    if "startframe" in data and not isinstance(data["startframe"], dict):
        try:
            default_start = int(data["startframe"])
        except Exception:
            report({"WARNING"}, "Invalid top-level startframe in prefix_map.json")

    default_duration = DEFAULT_FOLDER_DURATION
    if "duration" in data and not isinstance(data["duration"], dict):
        try:
            default_duration = int(data["duration"])
        except Exception:
            report({"WARNING"}, "Invalid top-level duration in prefix_map.json")

    metadata: dict[str, dict] = {}
    for key, value in data.items():
        if key in {"startframe", "duration"}:
            continue
        if not isinstance(value, dict):
            continue
        try:
            entry_id = int(value.get("id"))
        except Exception:
            report({"WARNING"}, f"Missing or invalid id for '{key}' in {PREFIX_MAP_FILENAME}")
            continue
        start_frame = value.get("startframe", default_start)
        if start_frame is not None:
            try:
                start_frame = int(start_frame)
            except Exception:
                start_frame = default_start
        duration = value.get("duration", default_duration)
        try:
            duration = int(duration)
        except Exception:
            duration = default_duration
        metadata[str(key)] = {
            "id": entry_id,
            "start_frame": start_frame,
            "transition_duration": duration,
        }
    return metadata, {"start_frame": default_start, "transition_duration": default_duration}


def _ordered_subdirs(base_dir: str, metadata_map: dict[str, dict]) -> list[str]:
    subdirs = [d for d in sorted(os.listdir(base_dir)) if os.path.isdir(os.path.join(base_dir, d))]
    if not metadata_map:
        return subdirs
    ordered: list[str] = []
    subdir_set = set(subdirs)
    for key, meta in sorted(metadata_map.items(), key=lambda item: item[1]["id"]):
        if key in subdir_set:
            ordered.append(key)
    for name in subdirs:
        if name not in metadata_map:
            ordered.append(name)
    return ordered


def _sanitize_name(name: str) -> str:
    safe = []
    for ch in name or "":
        if ch.isalnum() or ch in {"_", "-"}:
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe).strip("_")
    return result or "render_range"


def _read_color_verts() -> tuple[list[tuple[float, float, float, float]], list[int] | None] | None:
    obj = bpy.data.objects.get("ColorVerts")
    if obj is None or obj.type != 'MESH':
        return None
    mesh = obj.data
    attr = None
    if hasattr(mesh, "color_attributes"):
        attr = mesh.color_attributes.get("color")
    if attr is None and hasattr(mesh, "attributes"):
        attr = mesh.attributes.get("color")
    if attr is None or len(attr.data) != len(mesh.vertices):
        return None
    flat = [0.0] * (len(attr.data) * 4)
    try:
        attr.data.foreach_get("color", flat)
    except Exception:
        return None
    colors = [tuple(flat[i:i + 4]) for i in range(0, len(flat), 4)]
    pair_ids = None
    if hasattr(mesh, "attributes"):
        pair_attr = mesh.attributes.get("pair_id")
        if (
            pair_attr is not None
            and pair_attr.data_type == 'INT'
            and pair_attr.domain == 'POINT'
            and len(pair_attr.data) == len(mesh.vertices)
        ):
            vals = [0] * len(mesh.vertices)
            pair_attr.data.foreach_get("value", vals)
            pair_ids = vals
    return colors, pair_ids


def _order_by_pair_id(items, pair_ids):
    if pair_ids is None or len(items) != len(pair_ids):
        return items
    count = len(items)
    ordered = [None] * count
    for idx, pid in enumerate(pair_ids):
        if pid is None or pid < 0 or pid >= count:
            return items
        if ordered[pid] is not None:
            return items
        ordered[pid] = items[idx]
    if any(entry is None for entry in ordered):
        return items
    return ordered


def _format_bounds_suffix(pos_min, pos_max) -> str:
    def _fmt(value: float) -> str:
        text = f"{value:.3f}".rstrip("0").rstrip(".")
        return "0" if text == "-0" else text

    return "S_{0}_{1}_{2}_E_{3}_{4}_{5}".format(
        _fmt(pos_min[0]),
        _fmt(pos_min[1]),
        _fmt(pos_min[2]),
        _fmt(pos_max[0]),
        _fmt(pos_max[1]),
        _fmt(pos_max[2]),
    )


class LD_OT_compat_import_vatcat(bpy.types.Operator):
    bl_idname = "liberadrone.compat_import_vatcat"
    bl_label = "Compatibility Import (VAT/CAT)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        base_dir = bpy.path.abspath(getattr(scene, "ld_import_vat_dir", "") or "")
        if not base_dir or not os.path.isdir(base_dir):
            self.report({"ERROR"}, "Invalid VAT/CAT folder")
            return {"CANCELLED"}

        try:
            sheetutils._set_world_surface_black(scene)
        except Exception:
            pass

        tree = sheetutils._ensure_formation_tree(context)
        if tree is None:
            self.report({"ERROR"}, "Formation tree not available")
            return {"CANCELLED"}

        metadata_map, metadata_defaults = _load_prefix_map(base_dir, self.report)
        ordered_subdirs = _ordered_subdirs(base_dir, metadata_map)
        if ordered_subdirs:
            target_folders = [(name, os.path.join(base_dir, name)) for name in ordered_subdirs]
        else:
            target_folders = [(os.path.basename(base_dir), base_dir)]

        start_node = next((n for n in tree.nodes if n.bl_idname == "FN_StartNode"), None)
        if start_node is None:
            start_node = tree.nodes.new("FN_StartNode")
            start_node.location = (-300, 0)

        node_map: dict[str, bpy.types.Node] = {}
        for node in tree.nodes:
            key = node.label or node.name
            node_map[key] = node

        fps = scene.render.fps
        next_start = metadata_defaults.get("start_frame")
        if next_start is None:
            next_start = int(scene.frame_start)

        created = 0
        vat_heights: set[int] = set()
        entries: list[dict[str, object]] = []

        for idx, (folder_name, folder_path) in enumerate(target_folders):
            if not os.path.isdir(folder_path):
                continue
            base_name, gap_frames = _split_name_and_gap(folder_name, fps)
            meta = metadata_map.get(folder_name, {}) if metadata_map else {}
            display_name = _storyboard_name(base_name, meta)
            start_frame = meta.get("start_frame", None)
            if start_frame is None:
                start_frame = next_start
            next_meta = (
                metadata_map.get(target_folders[idx + 1][0], {})
                if metadata_map and idx < len(target_folders) - 1
                else {}
            )

            pos_path, cat_path = sheetutils._find_vat_cat_files(folder_path)
            pos_img = sheetutils._load_image(pos_path) if pos_path else None
            cat_img = sheetutils._load_image(cat_path) if cat_path else None

            if pos_img is None and cat_img is None:
                continue

            frame_count = 0
            if pos_img is not None and getattr(pos_img, "size", None):
                frame_count = int(pos_img.size[0])
                vat_heights.add(int(pos_img.size[1]))
            elif cat_img is not None and getattr(cat_img, "size", None):
                frame_count = int(cat_img.size[0])

            if frame_count <= 0:
                continue

            duration = max(1, int(frame_count) - 1)
            bounds = (
                sheetutils._parse_bounds_from_name(os.path.basename(pos_path))
                if pos_path
                else None
            )
            pos_min, pos_max = bounds if bounds else ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
            transition_duration = next_meta.get(
                "transition_duration",
                metadata_defaults.get("transition_duration", 0),
            )
            try:
                transition_duration = int(transition_duration)
            except Exception:
                transition_duration = 0
            transition_total = max(0, int(gap_frames) + int(transition_duration))

            entries.append(
                {
                    "display_name": display_name,
                    "start_frame": int(start_frame),
                    "duration": int(duration),
                    "frame_count": int(frame_count),
                    "gap_frames": int(gap_frames),
                    "transition_duration": int(transition_total),
                    "pos_img": pos_img,
                    "pos_min": pos_min,
                    "pos_max": pos_max,
                    "cat_img": cat_img,
                }
            )
            next_start = int(start_frame) + int(duration) + int(transition_total)

        prev_node = start_node
        flow_index = 0
        for entry_idx, entry in enumerate(entries):
            display_name = str(entry["display_name"])
            duration = int(entry["duration"])
            frame_count = int(entry["frame_count"])
            start_frame = int(entry["start_frame"])
            transition_total = int(entry.get("transition_duration", 0))
            pos_img = entry["pos_img"]
            pos_min = entry["pos_min"]
            pos_max = entry["pos_max"]
            cat_img = entry["cat_img"]

            node = node_map.get(display_name)
            if node is None or node.bl_idname != "FN_ShowNode":
                node = tree.nodes.new("FN_ShowNode")
                node.label = display_name
                node.location = (200 * (flow_index + 1), 0)
                node_map[display_name] = node
                created += 1
            flow_index += 1

            col = sheetutils._ensure_collection(scene, display_name)
            sheetutils._set_socket_collection(node, "Collection", col)
            sheetutils._set_socket_value(node, "Duration", float(duration))

            if pos_img is not None:
                vat_count = int(pos_img.size[1]) if getattr(pos_img, "size", None) else 1
                obj = sheetutils._create_point_object(f"{display_name}_VAT", vat_count, col)
                try:
                    pos_img.colorspace_settings.name = "Non-Color"
                except Exception:
                    pass
                start_frame_vat = int(start_frame) - 1
                frame_count_vat = max(1, int(frame_count) - 1)
                sheetutils._apply_vat_to_object(
                    obj,
                    pos_img,
                    pos_min=pos_min,
                    pos_max=pos_max,
                    start_frame=start_frame_vat,
                    frame_count=frame_count_vat,
                    drone_count=vat_count,
                )

            if cat_img is not None:
                start_frame_led = int(start_frame) - 1
                sheetutils._build_cat_led_graph(
                    context,
                    cut_name=display_name,
                    cat_image=cat_img,
                    start_frame=start_frame_led,
                    duration=int(duration),
                )

            if prev_node:
                sheetutils._link_flow(tree, prev_node, node)
            prev_node = node

            if entry_idx < len(entries) - 1:
                trans_name = f"{display_name}Transition"
                trans_node = node_map.get(trans_name)
                if trans_node is None or trans_node.bl_idname != "FN_TransitionNode":
                    trans_node = tree.nodes.new("FN_TransitionNode")
                    trans_node.label = trans_name
                    trans_node.location = (200 * (flow_index + 1), -140)
                    node_map[trans_name] = trans_node
                flow_index += 1
                sheetutils._set_socket_value(trans_node, "Duration", float(transition_total))
                if prev_node:
                    sheetutils._link_flow(tree, prev_node, trans_node)
                prev_node = trans_node

        if vat_heights:
            try:
                start_node.drone_count = int(next(iter(vat_heights)))
            except Exception:
                pass

        try:
            bpy.ops.liberadrone.setup_all()
        except Exception:
            pass

        try:
            sheetutils._link_tree_to_workspace("Formation", tree, "FN_FormationTree")
        except Exception:
            pass
        led_tree = sheetutils.led_panel._get_led_tree(context)
        if led_tree is not None:
            try:
                sheetutils._link_tree_to_workspace("LED", led_tree, "LD_LedEffectsTree")
            except Exception:
                pass
        try:
            bpy.ops.fn.calculate_schedule()
        except Exception:
            pass

        if created:
            self.report({"INFO"}, f"Imported {created} folder(s)")
        else:
            self.report({"WARNING"}, "No VAT/CAT folders found")
        return {"FINISHED"}


class LD_OT_export_vatcat_renderrange(bpy.types.Operator):
    bl_idname = "liberadrone.export_vatcat_renderrange"
    bl_label = "Export VAT/CAT (Render Range)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        export_dir = bpy.path.abspath(getattr(scene, "ld_import_vat_dir", "") or "")
        if not export_dir:
            self.report({"ERROR"}, "Set VAT/CAT folder")
            return {"CANCELLED"}
        try:
            os.makedirs(export_dir, exist_ok=True)
        except Exception as exc:
            self.report({"ERROR"}, f"Export folder error: {exc}")
            return {"CANCELLED"}

        frame_start = int(scene.frame_start)
        frame_end = int(scene.frame_end)
        if frame_end <= frame_start:
            self.report({"ERROR"}, "Render range is invalid")
            return {"CANCELLED"}

        col = bpy.data.collections.get("Formation")
        if col is None:
            self.report({"ERROR"}, "Formation collection not found")
            return {"CANCELLED"}

        original_frame = scene.frame_current
        view_layer = context.view_layer
        depsgraph = context.evaluated_depsgraph_get()

        positions_frames: list[list[tuple[float, float, float]]] = []
        colors_frames: list[list[tuple[float, float, float, float]]] = []

        for frame in range(frame_start, frame_end + 1):
            scene.frame_set(frame)
            if view_layer is not None:
                view_layer.update()
            positions, pair_ids, _ = transition_apply._collect_positions_for_collection(
                col, frame, depsgraph
            )
            if not positions:
                scene.frame_set(original_frame)
                if view_layer is not None:
                    view_layer.update()
                self.report({"ERROR"}, f"No positions at frame {frame}")
                return {"CANCELLED"}
            mapped_positions = _order_by_pair_id(positions, pair_ids)
            ordered_pos = [(float(p.x), float(p.y), float(p.z)) for p in mapped_positions]

            color_data = _read_color_verts()
            if color_data is None:
                scene.frame_set(original_frame)
                if view_layer is not None:
                    view_layer.update()
                self.report({"ERROR"}, "ColorVerts not available")
                return {"CANCELLED"}
            colors, color_pair_ids = color_data
            if len(colors) != len(ordered_pos):
                scene.frame_set(original_frame)
                if view_layer is not None:
                    view_layer.update()
                self.report({"ERROR"}, "ColorVerts count mismatch")
                return {"CANCELLED"}
            mapped_colors = _order_by_pair_id(colors, color_pair_ids)
            colors_frames.append(
                [(float(c[0]), float(c[1]), float(c[2]), float(c[3])) for c in mapped_colors]
            )
            positions_frames.append(ordered_pos)

        scene.frame_set(original_frame)
        if view_layer is not None:
            view_layer.update()

        positions_arr = np.asarray(positions_frames, dtype=np.float32)
        colors_arr = np.asarray(colors_frames, dtype=np.float32)
        if positions_arr.ndim != 3 or positions_arr.shape[2] != 3:
            self.report({"ERROR"}, "Invalid position data")
            return {"CANCELLED"}

        frame_count, drone_count, _ = positions_arr.shape
        if colors_arr.shape[0] != frame_count or colors_arr.shape[1] != drone_count:
            self.report({"ERROR"}, "Invalid color data")
            return {"CANCELLED"}

        pos_min = positions_arr.min(axis=(0, 1))
        pos_max = positions_arr.max(axis=(0, 1))
        rx = float(pos_max[0] - pos_min[0]) or 1.0
        ry = float(pos_max[1] - pos_min[1]) or 1.0
        rz = float(pos_max[2] - pos_min[2]) or 1.0

        pos_pixels = np.empty((drone_count, frame_count, 4), dtype=np.float32)
        pos_pixels[:, :, 3] = 1.0
        pos_pixels[:, :, 0] = (positions_arr[:, :, 0].T - pos_min[0]) / rx
        pos_pixels[:, :, 1] = (positions_arr[:, :, 1].T - pos_min[1]) / ry
        pos_pixels[:, :, 2] = (positions_arr[:, :, 2].T - pos_min[2]) / rz

        col_pixels = np.empty((drone_count, frame_count, 4), dtype=np.float32)
        col_pixels[:, :, :] = colors_arr.transpose((1, 0, 2))

        name = _sanitize_name(scene.name or "RenderRange")
        folder_name = f"{name}_RenderRange"
        target_dir = os.path.join(export_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        bounds_suffix = _format_bounds_suffix(pos_min, pos_max)
        vat_base = f"{name}_VAT_{bounds_suffix}"
        cat_base = f"{name}_CAT"
        pos_path = os.path.join(target_dir, f"{vat_base}.exr")
        cat_path = os.path.join(target_dir, f"{cat_base}.png")

        if not image_util.write_exr_rgba(pos_path, pos_pixels):
            pos_img = bpy.data.images.new(
                name=vat_base,
                width=frame_count,
                height=drone_count,
                alpha=True,
                float_buffer=True,
            )
            pos_img.pixels[:] = pos_pixels.ravel()
            image_util.save_image(pos_img, pos_path, "OPEN_EXR", use_float=True, colorspace="Non-Color")

        if not image_util.write_png_rgba(cat_path, col_pixels):
            col_img = bpy.data.images.new(
                name=cat_base,
                width=frame_count,
                height=drone_count,
                alpha=True,
                float_buffer=False,
            )
            col_img.pixels[:] = col_pixels.ravel()
            image_util.save_image(col_img, cat_path, "PNG")

        self.report({"INFO"}, f"Exported VAT/CAT to {target_dir}")
        return {"FINISHED"}


class LD_OT_export_vatcat_transitions(bpy.types.Operator):
    bl_idname = "liberadrone.export_vatcat_transitions"
    bl_label = "Export VAT/CAT (Transitions)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        export_dir = bpy.path.abspath(getattr(scene, "ld_import_vat_dir", "") or "")
        if not export_dir:
            self.report({"ERROR"}, "Set VAT/CAT folder")
            return {"CANCELLED"}
        try:
            os.makedirs(export_dir, exist_ok=True)
        except Exception as exc:
            self.report({"ERROR"}, f"Export folder error: {exc}")
            return {"CANCELLED"}

        schedule = fn_parse.compute_schedule(context, assign_pairs=False)
        tree_map = {
            tree.name: tree
            for tree in bpy.data.node_groups
            if getattr(tree, "bl_idname", "") == "FN_FormationTree"
        }
        transition_types = {
            "FN_TransitionNode",
            "FN_SplitTransitionNode",
            "FN_MergeTransitionNode",
        }
        transition_entries: list[tuple[fn_parse.ScheduleEntry, bpy.types.Node]] = []
        for entry in schedule:
            tree = tree_map.get(entry.tree_name)
            if tree is None:
                continue
            node = tree.nodes.get(entry.node_name)
            if node is None or getattr(node, "bl_idname", "") not in transition_types:
                continue
            if entry.collection is None:
                continue
            transition_entries.append((entry, node))

        if not transition_entries:
            self.report({"WARNING"}, "No transition entries found")
            return {"CANCELLED"}

        original_frame = scene.frame_current
        view_layer = context.view_layer
        depsgraph = context.evaluated_depsgraph_get()

        transitions_dir = os.path.join(export_dir, "Transitions")
        os.makedirs(transitions_dir, exist_ok=True)

        exported = 0
        errors: list[str] = []
        for entry, node in transition_entries:
            start = int(entry.start)
            end = int(entry.end)
            duration = max(0, end - start)
            if duration <= 0:
                continue
            positions_frames: list[list[tuple[float, float, float]]] = []
            colors_frames: list[list[tuple[float, float, float, float]]] = []
            failed = False
            for frame in range(start, end):
                scene.frame_set(frame)
                if view_layer is not None:
                    view_layer.update()
                positions, pair_ids, _ = transition_apply._collect_positions_for_collection(
                    entry.collection,
                    frame,
                    depsgraph,
                )
                if not positions:
                    errors.append(f"{node.name}: No positions at frame {frame}")
                    failed = True
                    break
                mapped_positions = _order_by_pair_id(positions, pair_ids)
                ordered_pos = [(float(p.x), float(p.y), float(p.z)) for p in mapped_positions]

                color_data = _read_color_verts()
                if color_data is None:
                    errors.append(f"{node.name}: ColorVerts not available")
                    failed = True
                    break
                colors, color_pair_ids = color_data
                if len(colors) != len(ordered_pos):
                    errors.append(f"{node.name}: ColorVerts count mismatch")
                    failed = True
                    break
                mapped_colors = _order_by_pair_id(colors, color_pair_ids)
                colors_frames.append(
                    [(float(c[0]), float(c[1]), float(c[2]), float(c[3])) for c in mapped_colors]
                )
                positions_frames.append(ordered_pos)

            if failed:
                continue

            positions_arr = np.asarray(positions_frames, dtype=np.float32)
            colors_arr = np.asarray(colors_frames, dtype=np.float32)
            if positions_arr.ndim != 3 or positions_arr.shape[2] != 3:
                errors.append(f"{node.name}: Invalid position data")
                continue

            frame_count, drone_count, _ = positions_arr.shape
            if colors_arr.shape[0] != frame_count or colors_arr.shape[1] != drone_count:
                errors.append(f"{node.name}: Invalid color data")
                continue

            pos_min = positions_arr.min(axis=(0, 1))
            pos_max = positions_arr.max(axis=(0, 1))
            rx = float(pos_max[0] - pos_min[0]) or 1.0
            ry = float(pos_max[1] - pos_min[1]) or 1.0
            rz = float(pos_max[2] - pos_min[2]) or 1.0

            pos_pixels = np.empty((drone_count, frame_count, 4), dtype=np.float32)
            pos_pixels[:, :, 3] = 1.0
            pos_pixels[:, :, 0] = (positions_arr[:, :, 0].T - pos_min[0]) / rx
            pos_pixels[:, :, 1] = (positions_arr[:, :, 1].T - pos_min[1]) / ry
            pos_pixels[:, :, 2] = (positions_arr[:, :, 2].T - pos_min[2]) / rz

            col_pixels = np.empty((drone_count, frame_count, 4), dtype=np.float32)
            col_pixels[:, :, :] = colors_arr.transpose((1, 0, 2))

            base_label = getattr(node, "label", "") or node.name
            safe_name = _sanitize_name(base_label)
            target_dir = os.path.join(transitions_dir, safe_name)
            os.makedirs(target_dir, exist_ok=True)

            bounds_suffix = _format_bounds_suffix(pos_min, pos_max)
            vat_base = f"{safe_name}_VAT_{bounds_suffix}"
            cat_base = f"{safe_name}_CAT"
            pos_path = os.path.join(target_dir, f"{vat_base}.exr")
            cat_path = os.path.join(target_dir, f"{cat_base}.png")

            if not image_util.write_exr_rgba(pos_path, pos_pixels):
                pos_img = bpy.data.images.new(
                    name=vat_base,
                    width=frame_count,
                    height=drone_count,
                    alpha=True,
                    float_buffer=True,
                )
                pos_img.pixels[:] = pos_pixels.ravel()
                image_util.save_image(pos_img, pos_path, "OPEN_EXR", use_float=True, colorspace="Non-Color")

            if not image_util.write_png_rgba(cat_path, col_pixels):
                col_img = bpy.data.images.new(
                    name=cat_base,
                    width=frame_count,
                    height=drone_count,
                    alpha=True,
                    float_buffer=False,
                )
                col_img.pixels[:] = col_pixels.ravel()
                image_util.save_image(col_img, cat_path, "PNG")

            exported += 1

        scene.frame_set(original_frame)
        if view_layer is not None:
            view_layer.update()

        if exported == 0:
            message = errors[0] if errors else "No transitions exported"
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        if errors:
            self.report({"WARNING"}, f"Exported {exported} transition(s); first error: {errors[0]}")
        else:
            self.report({"INFO"}, f"Exported {exported} transition(s)")
        return {"FINISHED"}


class CompatibilityOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LD_OT_compat_import_vatcat)
        bpy.utils.register_class(LD_OT_export_vatcat_renderrange)
        bpy.utils.register_class(LD_OT_export_vatcat_transitions)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LD_OT_export_vatcat_transitions)
        bpy.utils.unregister_class(LD_OT_export_vatcat_renderrange)
        bpy.utils.unregister_class(LD_OT_compat_import_vatcat)
