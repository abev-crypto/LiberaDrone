import csv
import io
import os
import re
import sys
import urllib.parse
import urllib.request

import bpy
from PySide6 import QtCore, QtWidgets
import numpy as np

from liberadronecore.system.transition import vat_gn
from liberadronecore.formation import fn_parse
from liberadronecore.system.transition import transition_apply
from liberadronecore.ui import ledeffects_panel as led_panel

SHEET_URL_DEFAULT = (
    "https://docs.google.com/spreadsheets/d/"
    "1EbPM3lqhiVnR1ZgmwEZoooDo7JqmlJyqLl51QKSAZhI/edit?gid=0#gid=0"
)

HEADERS = ("Use", "Name", "Attr", "Start(F)", "Duration(F)", "States", "FileCheck")
EXPORT_HEADERS = ("Use", "Name", "Duration(F)", "Computed(F)", "Status")


def _ensure_qapp():
    _install_qt_message_handler()
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


_QT_HANDLER_INSTALLED = False
_QT_PREV_HANDLER = None


def _install_qt_message_handler() -> None:
    global _QT_HANDLER_INSTALLED, _QT_PREV_HANDLER
    if _QT_HANDLER_INSTALLED:
        return

    def _handler(mode, context, message):
        if "SetProcessDpiAwarenessContext() failed" in message:
            return
        if _QT_PREV_HANDLER is not None:
            _QT_PREV_HANDLER(mode, context, message)
            return
        try:
            sys.stderr.write(message + "\n")
        except Exception:
            pass

    _QT_PREV_HANDLER = QtCore.qInstallMessageHandler(_handler)
    _QT_HANDLER_INSTALLED = True


def _parse_sheet_url(url: str) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    sheet_id = match.group(1) if match else None

    gid = None
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query or "")
    if "gid" in query and query["gid"]:
        gid = query["gid"][0]
    if gid is None and parsed.fragment:
        frag = urllib.parse.parse_qs(parsed.fragment)
        if "gid" in frag and frag["gid"]:
            gid = frag["gid"][0]
    return sheet_id, gid


def _sheet_export_url(url: str) -> str | None:
    sheet_id, gid = _parse_sheet_url(url)
    if not sheet_id:
        return None
    gid = gid or "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _fetch_csv(url: str) -> str:
    export_url = _sheet_export_url(url) or url
    return _fetch_csv_url(export_url)


def _fetch_csv_url(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace")


def _sheet_named_export_url(sheet_id: str, sheet_name: str) -> str:
    safe = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={safe}"


def _parse_rows(text: str) -> list[dict[str, str]]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    header_row = None
    header_idx = None
    for idx, row in enumerate(rows[:6]):
        if not row:
            continue
        has_name = any((cell or "").strip().lower() == "name" for cell in row)
        has_attr = any((cell or "").strip().lower() == "attr" for cell in row)
        if has_name and has_attr:
            header_row = row
            header_idx = idx
            break

    if header_row is not None:
        def _norm(label: str) -> str:
            return re.sub(r"[^a-z0-9]", "", label.lower())

        col_map = {_norm(cell): i for i, cell in enumerate(header_row) if cell}
        name_idx = col_map.get("name", 0)
        attr_idx = col_map.get("attr", 1)
        start_idx = col_map.get("startf", 3)
        duration_idx = col_map.get("durationf", 5)
        states_idx = col_map.get("states", 6)
        data_rows = rows[header_idx + 1:]
    else:
        name_idx, attr_idx, start_idx, duration_idx, states_idx = 0, 1, 3, 5, 6
        data_rows = rows[3:]
    parsed: list[dict[str, str]] = []
    for row in data_rows:
        padded = list(row)
        max_idx = max(name_idx, attr_idx, start_idx, duration_idx, states_idx)
        if len(padded) <= max_idx:
            padded += [""] * (max_idx + 1 - len(padded))
        name = (padded[name_idx] or "").strip()
        attr = (padded[attr_idx] or "").strip()
        start_frame = (padded[start_idx] or "").strip()
        duration_frame = (padded[duration_idx] or "").strip()
        states = (padded[states_idx] or "").strip()
        if not (name or attr or start_frame or duration_frame or states):
            continue
        parsed.append(
            {
                "name": name,
                "attr": attr,
                "start_frame": start_frame,
                "duration_frame": duration_frame,
                "states": states,
            }
        )
    for idx, row in enumerate(parsed):
        if row.get("attr") != "Transition":
            continue
        if row.get("name"):
            continue
        prev_name = ""
        for prev in range(idx - 1, -1, -1):
            prev_name = parsed[prev].get("name", "")
            if prev_name:
                break
        if prev_name:
            row["name"] = f"{prev_name}Transition"
    return parsed


def _parse_settings_rows(text: str) -> dict[str, str]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return {}
    settings: dict[str, str] = {}
    for row in rows:
        if not row:
            continue
        key = (row[0] or "").strip()
        if not key:
            continue
        value = (row[1] if len(row) > 1 else "").strip()
        if not value:
            continue
        norm = re.sub(r"[^a-z0-9]", "", key.lower())
        if not norm:
            continue
        settings[norm] = value
    return settings


def _read_sheet_settings(sheet_url: str) -> tuple[dict[str, str], str | None, str | None]:
    sheet_id, _gid = _parse_sheet_url(sheet_url)
    if not sheet_id:
        return {}, None, "Invalid sheet URL."
    url = _sheet_named_export_url(sheet_id, "シート2")
    text = _fetch_csv_url(url)
    settings = _parse_settings_rows(text)
    if settings:
        return settings, "sheet: シート2", None
    return {}, None, "Settings not found."


def _apply_import_settings(scene: bpy.types.Scene, settings: dict[str, str], start_node=None) -> None:
    drone_num = _to_int(settings.get("dronenum"))
    if start_node is not None and drone_num and drone_num > 0:
        start_node.drone_count = drone_num
    area_width = _to_float(settings.get("areawidth"))
    if area_width is not None and area_width > 0 and hasattr(scene, "ld_checker_range_width"):
        scene.ld_checker_range_width = area_width
    area_height = _to_float(settings.get("areaheight"))
    if area_height is not None and area_height > 0 and hasattr(scene, "ld_checker_range_height"):
        scene.ld_checker_range_height = area_height
    area_depth = _to_float(settings.get("areadepth"))
    if area_depth is not None and area_depth > 0 and hasattr(scene, "ld_checker_range_depth"):
        scene.ld_checker_range_depth = area_depth
    model = settings.get("dronemodel", "")
    if model:
        norm = re.sub(r"[^a-z0-9]", "", model.lower())
        if norm == "modelx" and hasattr(scene, "ld_limit_profile"):
            scene.ld_limit_profile = "MODEL_X"
        elif norm == "custom" and hasattr(scene, "ld_limit_profile"):
            scene.ld_limit_profile = "CUSTOM"


def _set_world_surface_black(scene: bpy.types.Scene) -> None:
    if scene is None:
        return
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass

    nt = getattr(world, "node_tree", None)
    if nt is None:
        return
    nodes = nt.nodes
    links = nt.links

    output = next((n for n in nodes if n.type == "OUTPUT_WORLD"), None)
    if output is None:
        output = nodes.new("ShaderNodeOutputWorld")
        output.location = (300, 0)

    bg_node = None
    for link in links:
        if link.to_node == output and link.to_socket.name == "Surface":
            if link.from_node and link.from_node.type == "BACKGROUND":
                bg_node = link.from_node
                break
    if bg_node is None:
        bg_node = next((n for n in nodes if n.type == "BACKGROUND"), None)
    if bg_node is None:
        bg_node = nodes.new("ShaderNodeBackground")
        bg_node.location = (0, 0)

    if output and not output.inputs["Surface"].is_linked:
        try:
            links.new(bg_node.outputs["Background"], output.inputs["Surface"])
        except Exception:
            pass

    try:
        color_input = bg_node.inputs.get("Color")
        if color_input is not None:
            color_input.default_value = (0.0, 0.0, 0.0, 1.0)
    except Exception:
        pass


def _link_camera_blend_assets(
    scene: bpy.types.Scene,
    base_dir: str,
) -> tuple[list[bpy.types.Object], bpy.types.Object | None]:
    if scene is None or not base_dir:
        return [], None
    blend_path = os.path.join(base_dir, "Camera.blend")
    if not os.path.isfile(blend_path):
        return [], None

    before_names = {s.name for s in bpy.data.scenes}
    scene_name = None
    try:
        with bpy.data.libraries.load(blend_path, link=True) as (data_from, data_to):
            if not data_from.scenes:
                return [], None
            scene_name = "Scene" if "Scene" in data_from.scenes else data_from.scenes[0]
            data_to.scenes = [scene_name]
    except Exception:
        return [], None

    after_names = {s.name for s in bpy.data.scenes}
    new_names = [name for name in after_names if name not in before_names]
    linked_scene = bpy.data.scenes.get(new_names[0]) if new_names else bpy.data.scenes.get(scene_name or "")
    if linked_scene is None:
        return [], None

    cameras: list[bpy.types.Object] = []
    area_obj = None
    for obj in linked_scene.objects:
        if obj.type == 'CAMERA':
            if scene.objects.get(obj.name) is None:
                scene.collection.objects.link(obj)
            cameras.append(obj)
        elif obj.name == "AreaObject":
            if scene.objects.get(obj.name) is None:
                scene.collection.objects.link(obj)
            area_obj = obj
    return cameras, area_obj


def _get_formation_tree(context) -> bpy.types.NodeTree | None:
    space = getattr(context, "space_data", None)
    if space and getattr(space, "edit_tree", None) and getattr(space, "tree_type", "") == "FN_FormationTree":
        return space.edit_tree
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", "") == "FN_FormationTree":
            return tree
    return None


def _cut_display_name(node: bpy.types.Node) -> str:
    return (getattr(node, "label", "") or node.name or "").strip()


def _collect_cut_map(context, *, assign_pairs: bool) -> dict[str, dict[str, object]]:
    tree = _get_formation_tree(context)
    if tree is None:
        return {}
    schedule = fn_parse.compute_schedule(context, assign_pairs=assign_pairs)
    entries = [entry for entry in schedule if entry.tree_name == tree.name]
    entry_map = {entry.node_name: entry for entry in entries}

    cuts: dict[str, dict[str, object]] = {}
    used_nodes: set[str] = set()

    frames = [n for n in tree.nodes if getattr(n, "bl_idname", "") == "NodeFrame"]
    for frame in frames:
        child_nodes = [n for n in tree.nodes if getattr(n, "parent", None) == frame and n.name in entry_map]
        if not child_nodes:
            continue
        used_nodes.update(n.name for n in child_nodes)
        frame_entries = [entry_map[n.name] for n in child_nodes]
        start = min(entry.start for entry in frame_entries)
        end = max(entry.end for entry in frame_entries)
        name = (frame.label or frame.name or "").strip()
        if not name:
            continue
        cuts[name] = {
            "name": name,
            "start": int(start),
            "end": int(end),
            "duration": int(end - start),
            "entries": frame_entries,
            "node_names": [n.name for n in child_nodes],
            "tree_name": tree.name,
        }

    for entry in entries:
        if entry.node_name in used_nodes:
            continue
        node = tree.nodes.get(entry.node_name)
        if node is None:
            continue
        name = _cut_display_name(node)
        if not name:
            continue
        cuts[name] = {
            "name": name,
            "start": int(entry.start),
            "end": int(entry.end),
            "duration": int(entry.end - entry.start),
            "entries": [entry],
            "node_names": [entry.node_name],
            "tree_name": tree.name,
        }
    return cuts


def _active_entry_for_frame(entries, frame: int):
    for entry in entries:
        if entry.start <= frame < entry.end:
            return entry
    return None


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


def _map_by_pair_id(items, pair_ids):
    if pair_ids is None or len(items) != len(pair_ids):
        return items
    count = len(items)
    mapped = [None] * count
    for dst_idx, pid in enumerate(pair_ids):
        if pid is None or pid < 0 or pid >= count:
            return items
        mapped[dst_idx] = items[pid]
    if any(entry is None for entry in mapped):
        return items
    return mapped


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


def _sanitize_name(name: str) -> str:
    safe = []
    for ch in name or "":
        if ch.isalnum() or ch in {"_", "-"}:
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe).strip("_")
    return result or "cut"


def _format_bound(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    return text


def _format_bounds_suffix(pos_min, pos_max) -> str:
    return "S_{0}_{1}_{2}_E_{3}_{4}_{5}".format(
        _format_bound(pos_min[0]),
        _format_bound(pos_min[1]),
        _format_bound(pos_min[2]),
        _format_bound(pos_max[0]),
        _format_bound(pos_max[1]),
        _format_bound(pos_max[2]),
    )


def _save_image(img: bpy.types.Image, path: str, file_format: str) -> None:
    try:
        img.filepath_raw = path
        img.file_format = file_format
        if file_format == "OPEN_EXR":
            try:
                img.colorspace_settings.name = "Non-Color"
            except Exception:
                pass
            if hasattr(img, "use_float"):
                img.use_float = True
        img.save()
    except Exception:
        pass


def _export_cut_to_vat_cat(context, cut: dict[str, object], export_dir: str) -> tuple[bool, str]:
    scene = context.scene
    view_layer = context.view_layer
    depsgraph = context.evaluated_depsgraph_get()

    entries = list(cut.get("entries") or [])
    if not entries:
        return False, "No schedule entries."

    start = int(cut.get("start", 0))
    end = int(cut.get("end", 0))
    duration = max(0, end - start)
    if duration <= 0:
        return False, "Invalid duration."

    original_frame = scene.frame_current
    positions_frames: list[list[tuple[float, float, float]]] = []
    colors_frames: list[list[tuple[float, float, float, float]]] = []

    for frame in range(start, end):
        scene.frame_set(frame)
        if view_layer is not None:
            view_layer.update()

        entry = _active_entry_for_frame(entries, frame)
        if entry is None or entry.collection is None:
            scene.frame_set(original_frame)
            if view_layer is not None:
                view_layer.update()
            return False, f"Missing collection at frame {frame}."

        positions, pair_ids = transition_apply._collect_positions_for_collection(
            entry.collection, frame, depsgraph
        )
        if not positions:
            scene.frame_set(original_frame)
            if view_layer is not None:
                view_layer.update()
            return False, f"No positions at frame {frame}."

        mapped_positions = _map_by_pair_id(positions, pair_ids)
        ordered_pos = [(float(p.x), float(p.y), float(p.z)) for p in mapped_positions]

        color_data = _read_color_verts()
        if color_data is None:
            scene.frame_set(original_frame)
            if view_layer is not None:
                view_layer.update()
            return False, "ColorVerts not available."
        colors, color_pair_ids = color_data
        if len(colors) != len(ordered_pos):
            scene.frame_set(original_frame)
            if view_layer is not None:
                view_layer.update()
            return False, "ColorVerts count mismatch."
        mapped_colors = _map_by_pair_id(colors, color_pair_ids)
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
        return False, "Invalid position data."

    frame_count, drone_count, _ = positions_arr.shape
    if colors_arr.shape[0] != frame_count or colors_arr.shape[1] != drone_count:
        return False, "Invalid color data."

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

    name = str(cut.get("name") or "cut")
    folder_name = name.replace(os.sep, "_")
    if os.altsep:
        folder_name = folder_name.replace(os.altsep, "_")
    target_dir = os.path.join(export_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    safe_name = _sanitize_name(name)
    bounds_suffix = _format_bounds_suffix(pos_min, pos_max)
    vat_base = f"{safe_name}_VAT_{bounds_suffix}"
    cat_base = f"{safe_name}_CAT"

    pos_img = bpy.data.images.new(
        name=vat_base,
        width=frame_count,
        height=drone_count,
        alpha=True,
        float_buffer=True,
    )
    pos_img.pixels[:] = pos_pixels.ravel()
    col_img = bpy.data.images.new(
        name=cat_base,
        width=frame_count,
        height=drone_count,
        alpha=True,
        float_buffer=False,
    )
    col_img.pixels[:] = col_pixels.ravel()

    pos_path = os.path.join(target_dir, f"{vat_base}.exr")
    cat_path = os.path.join(target_dir, f"{cat_base}.png")
    _save_image(pos_img, pos_path, "OPEN_EXR")
    _save_image(col_img, cat_path, "PNG")

    return True, f"Exported: {name}"


def _map_show_neighbors(rows: list[dict[str, str]]) -> None:
    prev_show_idx = None
    for idx, row in enumerate(rows):
        if row.get("attr") == "Show":
            prev_show_idx = idx
        row["prev_show_idx"] = prev_show_idx
    next_show_idx = None
    for idx in range(len(rows) - 1, -1, -1):
        if rows[idx].get("attr") == "Show":
            next_show_idx = idx
        rows[idx]["next_show_idx"] = next_show_idx


def _filter_transition_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    _map_show_neighbors(rows)
    display_rows: list[dict[str, str]] = []
    for idx, row in enumerate(rows):
        attr = row.get("attr")
        if attr == "Show":
            row["row_index"] = idx
            display_rows.append(row)
            continue
        if attr != "Transition":
            continue
        prev_idx = row.get("prev_show_idx")
        next_idx = row.get("next_show_idx")
        if prev_idx is None or next_idx is None:
            continue
        prev_show = rows[prev_idx]
        next_show = rows[next_idx]
        if prev_show.get("states") != "完了" or next_show.get("states") != "完了":
            continue
        row["row_index"] = idx
        display_rows.append(row)
    return display_rows


def _ensure_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
    elif col.name not in scene.collection.children:
        scene.collection.children.link(col)
    return col


def _load_image(path: str) -> bpy.types.Image | None:
    if not path or not os.path.isfile(path):
        return None
    abs_path = os.path.abspath(path)
    for img in bpy.data.images:
        try:
            if os.path.abspath(bpy.path.abspath(img.filepath)) == abs_path:
                return img
        except Exception:
            continue
    try:
        return bpy.data.images.load(abs_path)
    except Exception:
        return None


def _parse_bounds_from_name(filename: str) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    pattern = r"S_(-?\\d+(?:\\.\\d+)?)_(-?\\d+(?:\\.\\d+)?)_(-?\\d+(?:\\.\\d+)?)_E_(-?\\d+(?:\\.\\d+)?)_(-?\\d+(?:\\.\\d+)?)_(-?\\d+(?:\\.\\d+)?)"
    match = re.search(pattern, filename)
    if not match:
        return None
    values = [float(match.group(i)) for i in range(1, 7)]
    return (values[0], values[1], values[2]), (values[3], values[4], values[5])


def _find_vat_cat_files(folder: str) -> tuple[str | None, str | None]:
    if not folder or not os.path.isdir(folder):
        return None, None
    pos_path = None
    color_path = None
    fallback_png = None
    for entry in os.listdir(folder):
        path = os.path.join(folder, entry)
        if not os.path.isfile(path):
            continue
        low = entry.lower()
        if pos_path is None and low.endswith(".exr") and "vat" in low:
            pos_path = path
            continue
        if low.endswith(".png"):
            if color_path is None and ("color" in low or "cat" in low):
                color_path = path
                continue
            if fallback_png is None:
                fallback_png = path
                continue
    if color_path is None and fallback_png is not None:
        color_path = fallback_png
    return pos_path, color_path


def _get_image_width(path: str | None) -> int | None:
    if not path:
        return None
    img = _load_image(path)
    if img is None or not getattr(img, "size", None):
        return None
    return int(img.size[0])


def _calc_asset_status(base_dir: str, row: dict[str, str]) -> str:
    if not base_dir or not row.get("name"):
        return ""
    folder = os.path.join(base_dir, row.get("name", ""))
    pos_path, color_path = _find_vat_cat_files(folder)
    vat_width = _get_image_width(pos_path)
    cat_width = _get_image_width(color_path)
    vat_exists = vat_width is not None
    cat_exists = cat_width is not None
    if not vat_exists and not cat_exists:
        return "Missing"
    if not vat_exists:
        return "MissingVAT"
    if not cat_exists:
        return "MissingCAT"
    duration = _to_int(row.get("duration_frame"))
    if duration is None or duration <= 0:
        return "DurError"
    if vat_width != duration or cat_width != duration:
        return "DurError"
    return "OK"


def _create_point_object(name: str, count: int, collection: bpy.types.Collection) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    mesh = None
    if obj is None:
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
    else:
        mesh = obj.data
        if obj.name not in collection.objects:
            collection.objects.link(obj)
    if mesh is None:
        return obj
    count = max(1, int(count))
    mesh.clear_geometry()
    mesh.vertices.add(count)
    mesh.update()
    return obj


def _apply_vat_to_object(
    obj: bpy.types.Object,
    pos_img: bpy.types.Image,
    *,
    pos_min: tuple[float, float, float],
    pos_max: tuple[float, float, float],
    start_frame: int | None,
    frame_count: int | None = None,
    drone_count: int | None = None,
) -> None:
    if pos_img is None:
        return
    if frame_count is None or frame_count <= 0:
        frame_count = max(1, int(pos_img.size[0]))
    if drone_count is None or drone_count <= 0:
        drone_count = max(1, int(pos_img.size[1]))
    group = vat_gn._create_gn_vat_group(
        pos_img,
        pos_min,
        pos_max,
        frame_count,
        drone_count,
        start_frame=start_frame,
        base_name=obj.name,
    )
    vat_gn._apply_gn_to_object(obj, group)


def _ensure_formation_tree(context) -> bpy.types.NodeTree | None:
    tree = None
    space = getattr(context, "space_data", None)
    if space and getattr(space, "edit_tree", None):
        tree = space.edit_tree
    if tree is None or getattr(tree, "bl_idname", "") != "FN_FormationTree":
        tree = next((ng for ng in bpy.data.node_groups if getattr(ng, "bl_idname", "") == "FN_FormationTree"), None)
    if tree is None:
        tree = bpy.data.node_groups.new("FormationTree", "FN_FormationTree")
        if space and getattr(space, "type", "") == "NODE_EDITOR":
            try:
                space.tree_type = "FN_FormationTree"
                space.node_tree = tree
            except Exception:
                pass
    return tree


def _cat_template_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "ledeffects", "sample", "CAT.json")
    )


def _build_cat_led_graph(
    context,
    *,
    cut_name: str,
    cat_image: bpy.types.Image | None,
    start_frame: int,
    duration: int,
):

    tree = led_panel._ensure_led_tree(context)
    if tree is None:
        return None
    payload = led_panel._load_template_file(_cat_template_path())
    if not payload:
        return None
    root = led_panel._build_led_graph(tree, payload)
    if root is None:
        return None
    try:
        root.name = cut_name
        root.label = cut_name
    except Exception:
        pass
    frame = getattr(root, "parent", None)
    if frame is not None:
        try:
            frame.label = cut_name
        except Exception:
            pass
        frame_nodes = [n for n in tree.nodes if getattr(n, "parent", None) == frame]
    else:
        frame_nodes = [root]
    for node in frame_nodes:
        if getattr(node, "bl_idname", "") == "LDLEDFrameEntryNode":
            try:
                node.start = int(start_frame)
                node.duration = int(duration)
            except Exception:
                pass
        elif getattr(node, "bl_idname", "") == "LDLEDCatSamplerNode":
            try:
                node.image = cat_image
            except Exception:
                pass
    led_panel._sync_output_items(context.scene, tree)
    return root


def _first_flow_out(node):
    for sock in getattr(node, "outputs", []):
        if getattr(sock, "bl_idname", "") == "FN_SocketFlow":
            return sock
    return None


def _first_flow_in(node):
    for sock in getattr(node, "inputs", []):
        if getattr(sock, "bl_idname", "") == "FN_SocketFlow":
            return sock
    return None


def _link_flow(tree, from_node, to_node):
    out_sock = _first_flow_out(from_node)
    in_sock = _first_flow_in(to_node)
    if out_sock and in_sock and not in_sock.is_linked:
        try:
            tree.links.new(out_sock, in_sock)
        except Exception:
            pass


def _set_socket_value(node, name: str, value) -> None:
    sock = node.inputs.get(name) if hasattr(node, "inputs") else None
    if sock is None:
        return
    if hasattr(sock, "value"):
        try:
            sock.value = value
        except Exception:
            pass


def _set_socket_collection(node, name: str, collection: bpy.types.Collection) -> None:
    sock = node.inputs.get(name) if hasattr(node, "inputs") else None
    if sock is None:
        return
    if hasattr(sock, "collection"):
        try:
            sock.collection = collection
        except Exception:
            pass


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


class SheetImportWindow(QtWidgets.QMainWindow):
    _instance = None

    def __init__(self, sheet_url: str, vat_dir: str = ""):
        super().__init__()
        self._sheet_url = sheet_url
        self._vat_dir = vat_dir
        self._rows_all: list[dict[str, str]] = []
        self._rows: list[dict[str, str]] = []
        self.setWindowTitle("LiberaDrone Import Sheet")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        top_row = QtWidgets.QHBoxLayout()
        root.addLayout(top_row)
        top_row.addWidget(QtWidgets.QLabel("Sheet URL"))
        self.url_edit = QtWidgets.QLineEdit(self._sheet_url)
        top_row.addWidget(self.url_edit, 1)
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        top_row.addWidget(self.btn_refresh)

        folder_row = QtWidgets.QHBoxLayout()
        root.addLayout(folder_row)
        folder_row.addWidget(QtWidgets.QLabel("VAT/CAT Folder"))
        self.folder_edit = QtWidgets.QLineEdit(self._vat_dir)
        folder_row.addWidget(self.folder_edit, 1)

        self.status_label = QtWidgets.QLabel("")
        root.addWidget(self.status_label)

        self.table = QtWidgets.QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        root.addWidget(self.table)

        bottom_row = QtWidgets.QHBoxLayout()
        root.addLayout(bottom_row)
        bottom_row.addStretch(1)
        self.btn_import = QtWidgets.QPushButton("Import Selected")
        bottom_row.addWidget(self.btn_import)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_import.clicked.connect(self.import_selected)
        self.refresh()

    def refresh(self):
        url = self.url_edit.text().strip()
        if not url:
            self.status_label.setText("Missing URL.")
            return
        base_dir = self.folder_edit.text().strip()
        try:
            text = _fetch_csv(url)
            rows = _parse_rows(text)
            self._rows_all = rows
            display_rows = _filter_transition_rows(rows)
        except Exception as exc:
            self.status_label.setText(f"Failed to load: {exc}")
            QtWidgets.QMessageBox.warning(self, "Import Error", str(exc))
            return

        self._rows = display_rows
        self.table.setRowCount(len(display_rows))
        for row_idx, row in enumerate(display_rows):
            check_item = QtWidgets.QTableWidgetItem()
            check_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            check_item.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row_idx, 0, check_item)
            status = _calc_asset_status(base_dir, row)
            values = (
                row.get("name", ""),
                row.get("attr", ""),
                row.get("start_frame", ""),
                row.get("duration_frame", ""),
                row.get("states", ""),
                status,
            )
            for col_idx, value in enumerate(values, start=1):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                self.table.setItem(row_idx, col_idx, item)
        self.status_label.setText(f"Loaded: {len(display_rows)} rows")

    def _checked_rows(self) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        for row_idx, row in enumerate(self._rows):
            item = self.table.item(row_idx, 0)
            if item is None:
                continue
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(row)
        return selected

    def import_selected(self):
        selected = self._checked_rows()
        if not selected:
            self.status_label.setText("No rows selected.")
            return

        scene = getattr(bpy.context, "scene", None)
        if scene is None:
            self.status_label.setText("No active scene.")
            return
        _set_world_surface_black(scene)

        base_dir = self.folder_edit.text().strip()
        if not base_dir:
            self.status_label.setText("Missing VAT/CAT folder.")
            return

        linked_area_obj = None
        try:
            _linked_cameras, linked_area_obj = _link_camera_blend_assets(scene, base_dir)
        except Exception:
            linked_area_obj = None
        if linked_area_obj is not None:
            try:
                scene.ld_checker_range_object = linked_area_obj
            except Exception:
                pass

        tree = _ensure_formation_tree(bpy.context)
        if tree is None:
            self.status_label.setText("Formation tree not available.")
            return

        import_indices: set[int] = set()
        for row in selected:
            idx = row.get("row_index")
            if idx is None:
                continue
            import_indices.add(idx)
            if row.get("attr") == "Transition":
                prev_idx = self._rows_all[idx].get("prev_show_idx")
                next_idx = self._rows_all[idx].get("next_show_idx")
                if prev_idx is not None:
                    import_indices.add(prev_idx)
                if next_idx is not None:
                    import_indices.add(next_idx)

        if not import_indices:
            self.status_label.setText("No rows selected.")
            return

        rows_to_import: list[dict[str, str]] = []
        for idx in sorted(import_indices):
            row = dict(self._rows_all[idx])
            row["row_index"] = idx
            rows_to_import.append(row)

        status_map: dict[int, str] = {}
        for row in rows_to_import:
            status = _calc_asset_status(base_dir, row)
            status_map[row["row_index"]] = status
            if status == "DurError":
                name = row.get("name", "")
                self.status_label.setText(f"DurError: {name}")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Import Error",
                    f"Duration mismatch: {name}",
                )
                return

        def _should_create_vat(row, status: str, pos_img) -> bool:
            if pos_img is None:
                return False
            if status in ("Missing", "MissingVAT"):
                return False
            if row.get("attr") == "Transition" and status != "OK":
                return False
            return True

        assets: dict[int, dict[str, object]] = {}
        vat_heights: set[int] = set()
        for row in rows_to_import:
            idx = row["row_index"]
            name = row.get("name", "")
            pos_img = None
            pos_min, pos_max = (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
            if name:
                folder = os.path.join(base_dir, name)
                pos_path, _color_path = _find_vat_cat_files(folder)
                pos_img = _load_image(pos_path) if pos_path else None
                bounds = _parse_bounds_from_name(os.path.basename(pos_path)) if pos_path else None
                if bounds:
                    pos_min, pos_max = bounds
            assets[idx] = {
                "pos_img": pos_img,
                "pos_min": pos_min,
                "pos_max": pos_max,
            }
            status = status_map.get(idx, "")
            if _should_create_vat(row, status, pos_img):
                vat_heights.add(int(pos_img.size[1]))

        settings, settings_source, settings_error = _read_sheet_settings(self.url_edit.text().strip())
        drone_num_setting = _to_int(settings.get("dronenum")) if settings else None
        glare_threshold = _to_float(settings.get("glarethreshold")) if settings else None

        if drone_num_setting and vat_heights:
            if any(height != drone_num_setting for height in vat_heights):
                self.status_label.setText("Error: Drone count mismatch.")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Import Error",
                    "Drone count mismatch between VAT images and sheet settings.",
                )
                return
        elif len(vat_heights) > 1:
            self.status_label.setText("Error: Drone count mismatch.")
            QtWidgets.QMessageBox.warning(
                self,
                "Import Error",
                "Drone count mismatch between VAT images.",
            )
            return

        node_map: dict[str, bpy.types.Node] = {}
        for node in tree.nodes:
            key = node.label or node.name
            node_map[key] = node

        start_node = next((n for n in tree.nodes if n.bl_idname == "FN_StartNode"), None)
        if start_node is None:
            start_node = tree.nodes.new("FN_StartNode")
            start_node.location = (-300, 0)
        if settings:
            _apply_import_settings(scene, settings, start_node=start_node)
        if linked_area_obj is None and getattr(scene, "ld_checker_range_object", None) is None:
            try:
                bpy.ops.liberadrone.create_range_object()
            except Exception:
                pass
        settings_note = ""
        if settings:
            parts = []
            for key in ("dronenum", "areawidth", "areaheight", "areadepth", "dronemodel"):
                if key in settings:
                    parts.append(f"{key}={settings[key]}")
            detail = ", ".join(parts) if parts else "loaded"
            src = settings_source or "sheet2"
            settings_note = f" (Settings {src}: {detail})"
        elif settings_error:
            settings_note = f" (Settings error: {settings_error})"
        if vat_heights and not (drone_num_setting and drone_num_setting > 0):
            start_node.drone_count = int(next(iter(vat_heights)))

        created = 0
        prev_node = start_node
        for order_idx, row in enumerate(rows_to_import):
            idx = row["row_index"]
            name = row.get("name", "")
            if not name:
                continue
            status = status_map.get(idx, "")
            attr = row.get("attr")
            pos_img = assets[idx]["pos_img"]
            pos_min = assets[idx]["pos_min"]
            pos_max = assets[idx]["pos_max"]
            duration = _to_float(row.get("duration_frame"))
            duration_int = _to_int(row.get("duration_frame"))
            start_frame = _to_int(row.get("start_frame")) or 0

            if attr == "Transition" and status == "OK":
                bl_idname = "FN_ShowNode"
            elif attr == "Transition":
                bl_idname = "FN_TransitionNode"
            else:
                bl_idname = "FN_ShowNode"

            node = node_map.get(name)
            if node is None or node.bl_idname != bl_idname:
                node = tree.nodes.new(bl_idname)
                node.label = name
                node.location = (200 * (order_idx + 1), 0)
                node_map[name] = node
                created += 1

            col = _ensure_collection(scene, name)
            if bl_idname == "FN_ShowNode":
                _set_socket_collection(node, "Collection", col)
            else:
                if hasattr(node, "collection"):
                    try:
                        node.collection = col
                    except Exception:
                        pass

            if duration is not None:
                _set_socket_value(node, "Duration", duration)

            if _should_create_vat(row, status, pos_img):
                vat_count = drone_num_setting or (pos_img.size[1] if pos_img else 1)
                obj = _create_point_object(f"{name}_VAT", vat_count, col)
                if pos_img is not None:
                    try:
                        pos_img.colorspace_settings.name = "Non-Color"
                    except Exception:
                        pass
                    _apply_vat_to_object(
                        obj,
                        pos_img,
                        pos_min=pos_min,
                        pos_max=pos_max,
                        start_frame=start_frame,
                        frame_count=duration_int,
                        drone_count=vat_count,
                    )

            cat_img = None
            if name:
                folder = os.path.join(base_dir, name)
                _pos_path, cat_path = _find_vat_cat_files(folder)
                cat_img = _load_image(cat_path) if cat_path else None
            if cat_img is not None:
                _build_cat_led_graph(
                    bpy.context,
                    cut_name=name,
                    cat_image=cat_img,
                    start_frame=start_frame,
                    duration=duration_int or 0,
                )

            if prev_node:
                _link_flow(tree, prev_node, node)
            prev_node = node

        if created:
            self.status_label.setText(f"Imported: {created} nodes{settings_note}")
        else:
            self.status_label.setText(f"No nodes created.{settings_note}")
        try:
            bpy.ops.liberadrone.setup_all()
        except Exception:
            pass
        try:
            from liberadronecore.util import view_setup
            view_setup.setup_glare_compositor(scene, glare_threshold=glare_threshold)
        except Exception:
            pass
        try:
            SheetImportWindow._instance = None
            self.close()
        except Exception:
            pass

    @staticmethod
    def show_window(sheet_url: str, vat_dir: str = ""):
        _ensure_qapp()
        if SheetImportWindow._instance is not None:
            try:
                SheetImportWindow._instance.close()
            except Exception:
                pass
        SheetImportWindow._instance = SheetImportWindow(sheet_url, vat_dir)
        SheetImportWindow._instance.resize(900, 500)
        SheetImportWindow._instance.show()
        return SheetImportWindow._instance


class SheetExportWindow(QtWidgets.QMainWindow):
    _instance = None

    def __init__(self, sheet_url: str, export_dir: str = ""):
        super().__init__()
        self._sheet_url = sheet_url
        self._export_dir = export_dir
        self._rows: list[dict[str, object]] = []
        self.setWindowTitle("LiberaDrone Export Sheet")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        top_row = QtWidgets.QHBoxLayout()
        root.addLayout(top_row)
        top_row.addWidget(QtWidgets.QLabel("Sheet URL"))
        self.url_edit = QtWidgets.QLineEdit(self._sheet_url)
        top_row.addWidget(self.url_edit, 1)
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        top_row.addWidget(self.btn_refresh)

        folder_row = QtWidgets.QHBoxLayout()
        root.addLayout(folder_row)
        folder_row.addWidget(QtWidgets.QLabel("Export Folder"))
        self.folder_edit = QtWidgets.QLineEdit(self._export_dir)
        folder_row.addWidget(self.folder_edit, 1)

        self.status_label = QtWidgets.QLabel("")
        root.addWidget(self.status_label)

        self.table = QtWidgets.QTableWidget(0, len(EXPORT_HEADERS))
        self.table.setHorizontalHeaderLabels(EXPORT_HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        root.addWidget(self.table)

        bottom_row = QtWidgets.QHBoxLayout()
        root.addLayout(bottom_row)
        bottom_row.addStretch(1)
        self.btn_export = QtWidgets.QPushButton("Export Selected")
        bottom_row.addWidget(self.btn_export)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_export.clicked.connect(self.export_selected)
        self.refresh()

    def refresh(self):
        url = self.url_edit.text().strip()
        if not url:
            self.status_label.setText("Missing URL.")
            return
        try:
            text = _fetch_csv(url)
            rows = _parse_rows(text)
        except Exception as exc:
            self.status_label.setText(f"Failed to load: {exc}")
            QtWidgets.QMessageBox.warning(self, "Export Error", str(exc))
            return

        cuts = _collect_cut_map(bpy.context, assign_pairs=False)
        if not cuts:
            self.status_label.setText("Formation nodes not available.")
            return

        display_rows: list[dict[str, object]] = []
        for row in rows:
            name = (row.get("name") or "").strip()
            if not name or name not in cuts:
                continue
            cut = cuts[name]
            duration_sheet = _to_int(row.get("duration_frame"))
            duration_calc = int(cut.get("duration", 0))
            status = "OK" if duration_sheet is not None and duration_sheet == duration_calc else "DurError"
            display_rows.append(
                {
                    "name": name,
                    "duration_sheet": duration_sheet,
                    "duration_calc": duration_calc,
                    "status": status,
                    "cut": cut,
                }
            )

        self._rows = display_rows
        self.table.setRowCount(len(display_rows))
        for row_idx, row in enumerate(display_rows):
            check_item = QtWidgets.QTableWidgetItem()
            check_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            check_item.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row_idx, 0, check_item)
            values = (
                row.get("name", ""),
                str(row.get("duration_sheet") or ""),
                str(row.get("duration_calc") or ""),
                row.get("status", ""),
            )
            for col_idx, value in enumerate(values, start=1):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                self.table.setItem(row_idx, col_idx, item)
        self.status_label.setText(f"Loaded: {len(display_rows)} rows")

    def _checked_rows(self) -> list[dict[str, object]]:
        selected: list[dict[str, object]] = []
        for row_idx, row in enumerate(self._rows):
            item = self.table.item(row_idx, 0)
            if item is None:
                continue
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(row)
        return selected

    def export_selected(self):
        selected = self._checked_rows()
        if not selected:
            self.status_label.setText("No rows selected.")
            return

        export_dir = self.folder_edit.text().strip()
        if not export_dir:
            self.status_label.setText("Missing export folder.")
            return

        for row in selected:
            if row.get("status") != "OK":
                self.status_label.setText("Duration mismatch found.")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Export Error",
                    "Duration mismatch detected in selected rows.",
                )
                return

        export_cuts = _collect_cut_map(bpy.context, assign_pairs=True)
        for row in selected:
            name = row.get("name", "")
            cut = export_cuts.get(name) or row.get("cut") or {}
            ok, message = _export_cut_to_vat_cat(bpy.context, cut, export_dir)
            if not ok:
                self.status_label.setText(message)
                QtWidgets.QMessageBox.warning(self, "Export Error", message)
                return

        self.status_label.setText(f"Exported: {len(selected)} cuts")

    @staticmethod
    def show_window(sheet_url: str, export_dir: str = ""):
        _ensure_qapp()
        if SheetExportWindow._instance is not None:
            try:
                SheetExportWindow._instance.close()
            except Exception:
                pass
        SheetExportWindow._instance = SheetExportWindow(sheet_url, export_dir)
        SheetExportWindow._instance.resize(900, 500)
        SheetExportWindow._instance.show()
        return SheetExportWindow._instance


