import json
import os
import re

import bpy
import numpy as np

from liberadronecore.formation import fn_parse
from liberadronecore.ledeffects import led_codegen_runtime as le_codegen
from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.system.transition import transition_apply
from liberadronecore.ui.import_sheet import sheetutils
from liberadronecore.util import image_util
from liberadronecore.util import led_eval


PREFIX_MAP_FILENAME = "prefix_map.json"
DEFAULT_FOLDER_DURATION = 480


def _storyboard_name(base_name: str, meta: dict | None = None) -> str:
    meta = meta or {}
    meta_id = meta.get("id")
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
    with open(mapping_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{PREFIX_MAP_FILENAME} must contain a JSON object")

    default_start = None
    if "startframe" in data and not isinstance(data["startframe"], dict):
        default_start = int(data["startframe"])

    default_duration = DEFAULT_FOLDER_DURATION
    if "duration" in data and not isinstance(data["duration"], dict):
        default_duration = int(data["duration"])

    metadata: dict[str, dict] = {}
    for key, value in data.items():
        if key in {"startframe", "duration"}:
            continue
        if not isinstance(value, dict):
            continue
        entry_id = int(value.get("id"))
        start_frame = value.get("startframe", default_start)
        if start_frame is not None:
            start_frame = int(start_frame)
        duration = value.get("duration", default_duration)
        duration = int(duration)
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


def _ordered_candidate_names(base_dir: str, metadata_map: dict[str, dict]) -> list[str]:
    subdirs = [d for d in sorted(os.listdir(base_dir)) if os.path.isdir(os.path.join(base_dir, d))]
    if not metadata_map:
        if subdirs:
            return subdirs
        return [os.path.basename(base_dir)]
    ordered: list[str] = []
    seen: set[str] = set()
    for key, meta in sorted(metadata_map.items(), key=lambda item: item[1]["id"]):
        name = str(key)
        ordered.append(name)
        seen.add(name)
    for name in subdirs:
        if name not in seen:
            ordered.append(name)
    return ordered


def _transition_duration_from_meta(meta: dict | None, default: int | None) -> int:
    meta = meta or {}
    duration = meta.get("transition_duration", meta.get("duration", default))
    if duration is None:
        return int(default or 0)
    return int(duration)


def _is_transition_marker(name: str) -> bool:
    return "_TR" in (name or "")


def _build_compat_candidates(base_dir: str, report, fps: float) -> tuple[list[dict[str, object]], dict[str, int | None]]:
    metadata_map, metadata_defaults = _load_prefix_map(base_dir, report)
    ordered_names = _ordered_candidate_names(base_dir, metadata_map)
    candidates: list[dict[str, object]] = []

    for folder_name in ordered_names:
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.isdir(folder_path):
            folder_path = ""
        base_name, gap_frames = _split_name_and_gap(folder_name, fps)
        meta = metadata_map.get(folder_name, {}) if metadata_map else {}
        display_name = _storyboard_name(base_name, meta)

        pos_img = None
        cat_img = None
        pos_path = None
        if folder_path:
            pos_path, cat_path = sheetutils._find_vat_cat_files(folder_path)
            pos_img = sheetutils._load_image(pos_path) if pos_path else None
            cat_img = sheetutils._load_image(cat_path, colorspace="sRGB") if cat_path else None

        frame_count = 0
        if pos_img is not None and getattr(pos_img, "size", None):
            frame_count = int(pos_img.size[0])
        elif cat_img is not None and getattr(cat_img, "size", None):
            frame_count = int(cat_img.size[0])

        duration = max(0, int(frame_count) - 1) if frame_count > 0 else 0
        has_assets = frame_count > 0
        bounds = (
            sheetutils._parse_bounds_from_name(os.path.basename(pos_path))
            if pos_path
            else None
        )
        pos_min, pos_max = bounds if bounds else ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))

        candidates.append(
            {
                "name": folder_name,
                "folder_path": folder_path,
                "display_name": display_name,
                "base_name": base_name,
                "gap_frames": int(gap_frames),
                "meta": meta,
                "pos_img": pos_img,
                "cat_img": cat_img,
                "pos_min": pos_min,
                "pos_max": pos_max,
                "frame_count": int(frame_count),
                "duration": int(duration),
                "has_assets": bool(has_assets),
                "is_transition_marker": _is_transition_marker(folder_name),
            }
        )

    return candidates, metadata_defaults


def _build_compat_sequence(
    candidates: list[dict[str, object]],
    metadata_defaults: dict[str, int | None],
    *,
    selected_names: set[str] | None = None,
    include_auto_transitions: bool = True,
) -> list[dict[str, object]]:
    if not candidates:
        return []
    show_mask: list[bool] = []
    for entry in candidates:
        name = str(entry.get("name", ""))
        allowed = selected_names is None or name in selected_names
        is_transition = bool(entry.get("is_transition_marker"))
        show_mask.append(bool(entry.get("has_assets")) and allowed and not is_transition)

    prev_show_idx: list[int | None] = [None] * len(candidates)
    last_idx: int | None = None
    for idx, is_show in enumerate(show_mask):
        prev_show_idx[idx] = last_idx
        if is_show:
            last_idx = idx

    next_show_idx: list[int | None] = [None] * len(candidates)
    next_idx: int | None = None
    for idx in range(len(candidates) - 1, -1, -1):
        next_show_idx[idx] = next_idx
        if show_mask[idx]:
            next_idx = idx

    base_sequence: list[dict[str, object]] = []
    for idx, entry in enumerate(candidates):
        name = str(entry.get("name", ""))
        allowed = selected_names is None or name in selected_names
        is_transition = bool(entry.get("is_transition_marker"))
        has_assets = bool(entry.get("has_assets"))
        if is_transition and allowed and has_assets:
            base_sequence.append(
                {
                    "kind": "TRANSITION",
                    "source_name": name,
                    "display_name": entry.get("display_name", name),
                    "meta": entry.get("meta", {}),
                    "transition_duration": _transition_duration_from_meta(
                        entry.get("meta", {}),
                        metadata_defaults.get("transition_duration", 0),
                    ),
                    "duration": entry.get("duration", 0),
                    "frame_count": entry.get("frame_count", 0),
                    "pos_img": entry.get("pos_img"),
                    "pos_min": entry.get("pos_min"),
                    "pos_max": entry.get("pos_max"),
                    "cat_img": entry.get("cat_img"),
                    "has_assets": True,
                    "is_auto": False,
                }
            )
        elif show_mask[idx]:
            base_sequence.append(
                {
                    "kind": "SHOW",
                    "source_name": name,
                    "display_name": entry.get("display_name", name),
                    "meta": entry.get("meta", {}),
                    "gap_frames": entry.get("gap_frames", 0),
                    "duration": entry.get("duration", 0),
                    "frame_count": entry.get("frame_count", 0),
                    "pos_img": entry.get("pos_img"),
                    "pos_min": entry.get("pos_min"),
                    "pos_max": entry.get("pos_max"),
                    "cat_img": entry.get("cat_img"),
                }
            )
        elif (
            allowed
            and is_transition
            and prev_show_idx[idx] is not None
            and next_show_idx[idx] is not None
        ):
            base_sequence.append(
                {
                    "kind": "TRANSITION",
                    "source_name": name,
                    "display_name": entry.get("display_name", name),
                    "meta": entry.get("meta", {}),
                    "transition_duration": _transition_duration_from_meta(
                        entry.get("meta", {}),
                        metadata_defaults.get("transition_duration", 0),
                    ),
                    "has_assets": False,
                    "is_auto": False,
                }
            )

    if not include_auto_transitions:
        return base_sequence

    sequence: list[dict[str, object]] = []
    for idx, entry in enumerate(base_sequence):
        sequence.append(entry)
        if entry.get("kind") != "SHOW":
            continue
        if idx >= len(base_sequence) - 1:
            continue
        next_entry = base_sequence[idx + 1]
        if next_entry.get("kind") != "SHOW":
            continue
        transition_duration = _transition_duration_from_meta(
            next_entry.get("meta", {}),
            metadata_defaults.get("transition_duration", 0),
        )
        sequence.append(
            {
                "kind": "TRANSITION",
                "source_name": f"{entry.get('source_name', '')}__auto",
                "display_name": f"{entry.get('display_name', '')}Transition",
                "meta": next_entry.get("meta", {}),
                "transition_duration": transition_duration,
                "is_auto": True,
            }
        )

    return sequence


def _sanitize_name(name: str) -> str:
    safe = []
    for ch in name or "":
        if ch.isalnum() or ch in {"_", "-"}:
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe).strip("_")
    return result or "render_range"


def _strip_id_prefix(name: str) -> str:
    if not name:
        return ""
    match = re.match(r"^\d+[_-]+(.+)$", name)
    if match:
        return match.group(1)
    return name


def _hide_collection(col: bpy.types.Collection) -> None:
    if col is None:
        return
    for attr in ("hide_viewport", "hide_render", "hide_select"):
        if hasattr(col, attr):
            setattr(col, attr, True)


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


class LD_CompatPreviewItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="")
    source_name: bpy.props.StringProperty(name="Source", default="")
    kind: bpy.props.StringProperty(name="Kind", default="SHOW")
    checked: bpy.props.BoolProperty(name="Use", default=True)
    duration: bpy.props.IntProperty(name="Duration", default=0, min=0)
    has_assets: bpy.props.BoolProperty(name="Has Assets", default=True)


class LD_UL_CompatPreview(bpy.types.UIList):
    bl_idname = "LD_UL_CompatPreview"

    def draw_item(
        self,
        context,
        layout,
        _data,
        item,
        _icon,
        _active_data,
        _active_propname,
        _index,
    ):
        row = layout.row(align=True)
        row.prop(item, "checked", text="")
        label = item.name or item.source_name
        if item.kind == "TRANSITION":
            label = f"{label} (TR)"
        row.label(text=label)
        if item.kind == "TRANSITION" and not item.has_assets:
            sub = row.row(align=True)
            sub.prop(item, "duration", text="Dur")


class LD_OT_compat_preview_vatcat(bpy.types.Operator):
    bl_idname = "liberadrone.compat_preview_vatcat"
    bl_label = "Compatibility Preview (VAT/CAT)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        base_dir = bpy.path.abspath(getattr(scene, "ld_import_vat_dir", "") or "")
        if not base_dir or not os.path.isdir(base_dir):
            self.report({"ERROR"}, "Invalid VAT/CAT folder")
            return {"CANCELLED"}

        items = getattr(scene, "ld_compat_preview_items", None)
        if items is None:
            self.report({"ERROR"}, "Preview list not available")
            return {"CANCELLED"}
        items.clear()

        fps = scene.render.fps
        candidates, metadata_defaults = _build_compat_candidates(base_dir, self.report, fps)
        sequence = _build_compat_sequence(
            candidates,
            metadata_defaults,
            include_auto_transitions=False,
        )
        if not sequence:
            self.report({"WARNING"}, "No preview entries found")
            return {"CANCELLED"}

        for entry in sequence:
            item = items.add()
            item.name = str(entry.get("display_name", ""))
            item.source_name = str(entry.get("source_name", ""))
            item.kind = str(entry.get("kind", "SHOW"))
            item.checked = True
            item.has_assets = bool(entry.get("has_assets", True))
            if item.kind == "TRANSITION" and not item.has_assets:
                item.duration = max(0, int(entry.get("transition_duration", 0)))

        scene.ld_compat_preview_index = 0
        self.report({"INFO"}, "Preview generated")
        return {"FINISHED"}


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

        sheetutils._set_world_surface_black(scene)

        tree = sheetutils._ensure_formation_tree(context)
        if tree is None:
            self.report({"ERROR"}, "Formation tree not available")
            return {"CANCELLED"}

        start_node = next((n for n in tree.nodes if n.bl_idname == "FN_StartNode"), None)
        if start_node is None:
            start_node = tree.nodes.new("FN_StartNode")
            start_node.location = (-300, 0)

        node_map: dict[str, bpy.types.Node] = {}
        for node in tree.nodes:
            key = node.label or node.name
            node_map[key] = node

        fps = scene.render.fps
        candidates, metadata_defaults = _build_compat_candidates(base_dir, self.report, fps)
        selected_names = None
        preview_items = getattr(scene, "ld_compat_preview_items", None)
        if preview_items and len(preview_items) > 0:
            selected_names = {item.source_name for item in preview_items if item.checked}
            if not selected_names:
                self.report({"ERROR"}, "No preview entries selected")
                return {"CANCELLED"}

        duration_overrides: dict[str, int] = {}
        if preview_items:
            for item in preview_items:
                if not item.checked:
                    continue
                if getattr(item, "kind", "") != "TRANSITION":
                    continue
                if bool(getattr(item, "has_assets", True)):
                    continue
                dur = int(getattr(item, "duration", 0))
                if dur > 0:
                    duration_overrides[str(getattr(item, "source_name", ""))] = dur

        sequence = _build_compat_sequence(
            candidates,
            metadata_defaults,
            selected_names=selected_names,
            include_auto_transitions=True,
        )

        next_start = metadata_defaults.get("start_frame")
        if next_start is None:
            next_start = int(scene.frame_start)

        created_shows = 0
        vat_heights: set[int] = set()
        prev_node = start_node
        flow_index = 0
        last_gap_frames = 0

        for entry in sequence:
            kind = entry.get("kind", "SHOW")
            if kind == "SHOW":
                display_name = str(entry.get("display_name", ""))
                meta = entry.get("meta", {}) or {}
                duration = int(entry.get("duration", 0))
                frame_count = int(entry.get("frame_count", 0))
                start_frame = meta.get("start_frame", None)
                if start_frame is None:
                    start_frame = next_start
                start_frame = int(start_frame)
                pos_img = entry.get("pos_img")
                pos_min = entry.get("pos_min")
                pos_max = entry.get("pos_max")
                cat_img = entry.get("cat_img")

                node = node_map.get(display_name)
                if node is None or node.bl_idname != "FN_ShowNode":
                    node = tree.nodes.new("FN_ShowNode")
                    node.label = display_name
                    node.location = (200 * (flow_index + 1), 0)
                    node_map[display_name] = node
                    created_shows += 1
                flow_index += 1

                existed = bpy.data.collections.get(display_name) is not None
                col = sheetutils._ensure_collection(scene, display_name)
                if not existed:
                    _hide_collection(col)
                sheetutils._set_socket_collection(node, "Collection", col)
                sheetutils._set_socket_value(node, "Duration", float(duration))

                if pos_img is not None:
                    vat_count = int(pos_img.size[1]) if getattr(pos_img, "size", None) else 1
                    vat_heights.add(vat_count)
                    obj = sheetutils._create_point_object(f"{display_name}_VAT", vat_count, col)
                    pos_img.colorspace_settings.name = "Non-Color"
                    start_frame_vat = int(start_frame) - 1
                    frame_count_vat = max(1, int(frame_count))
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
                next_start = int(start_frame) + int(duration)
                last_gap_frames = int(entry.get("gap_frames", 0))
            else:
                display_name = str(entry.get("display_name", ""))
                transition_meta = entry.get("meta", {}) or {}
                has_assets = bool(entry.get("has_assets"))
                if has_assets:
                    transition_total = max(0, int(entry.get("duration", 0)))
                    last_gap_frames = 0
                else:
                    transition_duration = _transition_duration_from_meta(
                        transition_meta,
                        metadata_defaults.get("transition_duration", 0),
                    )
                    transition_total = max(0, int(transition_duration)) + max(0, int(last_gap_frames))
                    last_gap_frames = 0
                if not has_assets:
                    override = duration_overrides.get(str(entry.get("source_name", "")))
                    if override and override > 0:
                        transition_total = override

                trans_node = node_map.get(display_name)
                if trans_node is None or trans_node.bl_idname != "FN_TransitionNode":
                    trans_node = tree.nodes.new("FN_TransitionNode")
                    trans_node.label = display_name
                    trans_node.location = (200 * (flow_index + 1), -140)
                    node_map[display_name] = trans_node
                flow_index += 1

                sheetutils._set_socket_value(trans_node, "Duration", float(transition_total))
                if has_assets:
                    existed = bpy.data.collections.get(display_name) is not None
                    col = sheetutils._ensure_collection(scene, display_name)
                    if not existed:
                        _hide_collection(col)
                    if hasattr(trans_node, "collection"):
                        trans_node.collection = col
                    pos_img = entry.get("pos_img")
                    if pos_img is not None:
                        vat_count = int(pos_img.size[1]) if getattr(pos_img, "size", None) else 1
                        obj = sheetutils._create_point_object(f"{display_name}_VAT", vat_count, col)
                        pos_img.colorspace_settings.name = "Non-Color"
                        start_frame_vat = int(next_start) - 1
                        frame_count_vat = max(1, int(entry.get("frame_count", 0)))
                        pos_min = entry.get("pos_min")
                        pos_max = entry.get("pos_max")
                        sheetutils._apply_vat_to_object(
                            obj,
                            pos_img,
                            pos_min=pos_min,
                            pos_max=pos_max,
                            start_frame=start_frame_vat,
                            frame_count=frame_count_vat,
                            drone_count=vat_count,
                        )
                if prev_node:
                    sheetutils._link_flow(tree, prev_node, trans_node)
                prev_node = trans_node
                next_start = int(next_start) + int(transition_total)

        if vat_heights:
            start_node.drone_count = int(next(iter(vat_heights)))

        bpy.ops.liberadrone.setup_all()

        sheetutils._link_tree_to_workspace("Formation", tree, "FN_FormationTree")
        led_tree = sheetutils.led_panel._get_led_tree(context)
        if led_tree is not None:
            sheetutils._link_tree_to_workspace("LED", led_tree, "LD_LedEffectsTree")
        bpy.ops.fn.calculate_schedule()

        if created_shows:
            self.report({"INFO"}, f"Imported {created_shows} folder(s)")
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
        os.makedirs(export_dir, exist_ok=True)

        frame_start = int(scene.frame_start)
        frame_end = int(scene.frame_end)
        if frame_end <= frame_start:
            self.report({"ERROR"}, "Render range is invalid")
            return {"CANCELLED"}

        col = bpy.data.collections.get("Formation")
        if col is None:
            self.report({"ERROR"}, "Formation collection not found")
            return {"CANCELLED"}

        tree = le_codegen.get_active_tree(scene)
        if tree is None:
            self.report({"ERROR"}, "LED effects tree not found")
            return {"CANCELLED"}
        effect_fn = le_codegen.get_compiled_effect(tree)
        if effect_fn is None:
            self.report({"ERROR"}, "LED effects output not available")
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
            positions, pair_ids, formation_ids = transition_apply._collect_positions_for_collection(
                col, frame, depsgraph, collect_form_ids=True
            )
            if not positions:
                scene.frame_set(original_frame)
                if view_layer is not None:
                    view_layer.update()
                self.report({"ERROR"}, f"No positions at frame {frame}")
                return {"CANCELLED"}
            result = led_eval.evaluate_led_colors(effect_fn, positions, pair_ids, formation_ids, frame)
            if result is None:
                scene.frame_set(original_frame)
                if view_layer is not None:
                    view_layer.update()
                self.report({"ERROR"}, "LED effects evaluation failed")
                return {"CANCELLED"}
            colors, mapped_positions = result
            if colors is None or len(colors) != len(mapped_positions):
                scene.frame_set(original_frame)
                if view_layer is not None:
                    view_layer.update()
                self.report({"ERROR"}, "LED effects evaluation failed")
                return {"CANCELLED"}
            ordered_pos = [(float(p.x), float(p.y), float(p.z)) for p in mapped_positions]
            colors_list = [(float(c[0]), float(c[1]), float(c[2]), float(c[3])) for c in colors]
            colors_frames.append(colors_list)
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

        positions_arr = np.concatenate([positions_arr, positions_arr[-1:]], axis=0)
        colors_arr = np.concatenate([colors_arr, colors_arr[-1:]], axis=0)
        frame_count, drone_count, _ = positions_arr.shape

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
        cat_base = f"{name}_Color"
        pos_path = os.path.join(target_dir, f"{vat_base}.exr")
        cat_path = os.path.join(target_dir, f"{cat_base}.png")

        if not image_util.write_exr_rgba(pos_path, pos_pixels):
            self.report({"ERROR"}, f"Failed to write EXR: {pos_path}")
            return {"CANCELLED"}

        image_util.write_png_rgba(cat_path, col_pixels, colorspace="sRGB")

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
        os.makedirs(export_dir, exist_ok=True)

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

        tree = le_codegen.get_active_tree(scene)
        if tree is None:
            self.report({"ERROR"}, "LED effects tree not found")
            return {"CANCELLED"}
        effect_fn = le_codegen.get_compiled_effect(tree)
        if effect_fn is None:
            self.report({"ERROR"}, "LED effects output not available")
            return {"CANCELLED"}

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
                positions, pair_ids, formation_ids = transition_apply._collect_positions_for_collection(
                    entry.collection,
                    frame,
                    depsgraph,
                    collect_form_ids=True,
                )
                if not positions:
                    errors.append(f"{node.name}: No positions at frame {frame}")
                    failed = True
                    break
                result = led_eval.evaluate_led_colors(effect_fn, positions, pair_ids, formation_ids, frame)
                if result is None:
                    errors.append(f"{node.name}: LED effects evaluation failed")
                    failed = True
                    break
                colors, mapped_positions = result
                if colors is None or len(colors) != len(mapped_positions):
                    errors.append(f"{node.name}: LED effects evaluation failed")
                    failed = True
                    break
                ordered_pos = [(float(p.x), float(p.y), float(p.z)) for p in mapped_positions]
                colors_list = [(float(c[0]), float(c[1]), float(c[2]), float(c[3])) for c in colors]
                colors_frames.append(colors_list)
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

            positions_arr = np.concatenate([positions_arr, positions_arr[-1:]], axis=0)
            colors_arr = np.concatenate([colors_arr, colors_arr[-1:]], axis=0)
            frame_count, drone_count, _ = positions_arr.shape

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
            base_label = _strip_id_prefix(base_label)
            safe_name = _sanitize_name(base_label)
            target_dir = os.path.join(export_dir, safe_name)
            os.makedirs(target_dir, exist_ok=True)

            bounds_suffix = _format_bounds_suffix(pos_min, pos_max)
            vat_base = f"{safe_name}_VAT_{bounds_suffix}"
            cat_base = f"{safe_name}_Color"
            pos_path = os.path.join(target_dir, f"{vat_base}.exr")
            cat_path = os.path.join(target_dir, f"{cat_base}.png")

            if not image_util.write_exr_rgba(pos_path, pos_pixels):
                errors.append(f"{node.name}: Failed to write EXR: {pos_path}")
                continue

            image_util.write_png_rgba(cat_path, col_pixels, colorspace="sRGB")

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
        bpy.utils.register_class(LD_CompatPreviewItem)
        bpy.utils.register_class(LD_UL_CompatPreview)
        bpy.utils.register_class(LD_OT_compat_preview_vatcat)
        bpy.utils.register_class(LD_OT_compat_import_vatcat)
        bpy.utils.register_class(LD_OT_export_vatcat_renderrange)
        bpy.utils.register_class(LD_OT_export_vatcat_transitions)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LD_OT_export_vatcat_transitions)
        bpy.utils.unregister_class(LD_OT_export_vatcat_renderrange)
        bpy.utils.unregister_class(LD_OT_compat_import_vatcat)
        bpy.utils.unregister_class(LD_OT_compat_preview_vatcat)
        bpy.utils.unregister_class(LD_UL_CompatPreview)
        bpy.utils.unregister_class(LD_CompatPreviewItem)
