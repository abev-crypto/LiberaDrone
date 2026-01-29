"""
Viewport overlay for checker status derived from formation meshes.
"""

import bpy
import blf
import gpu
import numpy as np
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from mathutils.kdtree import KDTree

from liberadronecore.util import formation_positions
from liberadronecore.formation import fn_parse_pairing

FORMATION_ROOT = "Formation"
ATTR_COLORS = {
    "speed": (1.0, 1.0, 0.2, 1.0),
    "acc": (1.0, 0.2, 1.0, 1.0),
    "distance": (1.0, 0.2, 0.2, 1.0),
    "range": (0.2, 0.8, 1.0, 1.0),
}

_handler = None
_text_handler = None
_CHECK_CACHE = {
    "scene_name": None,
    "frame": None,
    "prev_frame": None,
    "signature": None,
    "collection_signature": None,
    "positions": [],
    "positions_np": None,
    "prev_positions": [],
    "prev_positions_np": None,
    "prev_vel": [],
    "prev_vel_np": None,
    "speed_vert": [],
    "speed_horiz": [],
    "speed_all": [],
    "acc": [],
    "min_distance": [],
    "form_order": False,
}

_FLOW_CACHE = {
    "scene_name": None,
    "frame": None,
    "signature": None,
    "positions_np": None,
    "prev_positions_np": None,
    "speed": [],
    "direction": [],
    "pair_id_map": {},
}

def _get_fps(scene: bpy.types.Scene) -> float:
    fps = float(getattr(scene.render, "fps", 0.0))
    base = float(getattr(scene.render, "fps_base", 1.0) or 1.0)
    if base <= 0.0:
        base = 1.0
    if fps <= 0.0:
        fps = 24.0
    return fps / base


def _collection_signature(collection_name: str) -> tuple[int, ...]:
    col = bpy.data.collections.get(collection_name)
    if col is None:
        return ()
    meshes = fn_parse_pairing._collect_mesh_objects(col)
    keys: list[int] = []
    for obj in meshes:
        try:
            key = int(obj.as_pointer())
        except Exception:
            key = id(obj)
        keys.append(key)
    return tuple(keys)


def _collect_formation_positions(
    scene: bpy.types.Scene,
    depsgraph,
) -> tuple[list[Vector], list[int] | None, list[int] | None, tuple[tuple[str, int | str], ...], tuple[int, ...]]:
    positions, pair_ids, form_ids, signature = formation_positions.collect_formation_positions_with_form_ids(
        scene,
        depsgraph,
        collection_name=FORMATION_ROOT,
        sort_by_pair_id=False,
        include_signature=True,
        as_numpy=False,
    )
    return positions, pair_ids, form_ids, signature or (), _collection_signature(FORMATION_ROOT)


def _order_indices_by_ids(ids: list[int] | None):
    if not ids:
        return [], False
    paired = []
    fallback = []
    for idx, val in enumerate(ids):
        try:
            key = int(val)
        except (TypeError, ValueError):
            key = None
        if key is None:
            fallback.append(idx)
        else:
            paired.append((key, idx))
    if not paired:
        return [], False
    paired.sort(key=lambda item: (item[0], item[1]))
    return [idx for _key, idx in paired] + fallback, True


def _valid_id_map(ids: list[int] | None, count: int) -> bool:
    if not ids or count <= 0 or len(ids) != len(set(ids)):
        return False
    for val in ids:
        try:
            key = int(val)
        except (TypeError, ValueError):
            return False
        if key < 0 or key >= count:
            return False
    return True


def _positions_to_numpy(positions: list[Vector]) -> np.ndarray:
    if not positions:
        return np.zeros((0, 3), dtype=np.float64)
    return np.asarray([[p.x, p.y, p.z] for p in positions], dtype=np.float64)


def _compute_min_distances(positions: list[Vector]) -> list[float]:
    count = len(positions)
    if count < 2:
        return [0.0] * count
    kd = KDTree(count)
    for idx, pos in enumerate(positions):
        kd.insert(pos, idx)
    kd.balance()
    distances = [0.0] * count
    for idx, pos in enumerate(positions):
        nearest = None
        for _co, other_idx, dist in kd.find_n(pos, 2):
            if other_idx == idx:
                continue
            nearest = dist
            break
        distances[idx] = float(nearest) if nearest is not None else 0.0
    return distances


def _build_pair_id_map(pair_ids: list[int] | None) -> dict[int, int]:
    mapping: dict[int, int] = {}
    if not pair_ids:
        return mapping
    for idx, pid in enumerate(pair_ids):
        try:
            key = int(pid)
        except (TypeError, ValueError):
            continue
        if key not in mapping:
            mapping[key] = idx
    return mapping


def _collect_flow_positions(
    scene: bpy.types.Scene,
    depsgraph,
) -> tuple[np.ndarray, list[int] | None, tuple[tuple[str, int | str], ...]]:
    positions, pair_ids, _form_ids, signature = formation_positions.collect_formation_positions_with_form_ids(
        scene,
        depsgraph,
        collection_name=FORMATION_ROOT,
        sort_by_pair_id=True,
        include_signature=True,
        as_numpy=True,
    )
    if positions is None or len(positions) == 0:
        return np.zeros((0, 3), dtype=np.float64), None, signature or ()
    if not isinstance(positions, np.ndarray):
        positions = _positions_to_numpy(positions)
    return positions, pair_ids, signature or ()


def _update_flow_cache(scene: bpy.types.Scene) -> dict | None:
    cache = _FLOW_CACHE
    if scene is None:
        return None

    scene_name = scene.name if scene else None
    frame = int(getattr(scene, "frame_current", 0))
    if cache["scene_name"] == scene_name and cache["frame"] == frame and cache["speed"]:
        return cache

    depsgraph = bpy.context.evaluated_depsgraph_get()
    positions_np, pair_ids, signature = _collect_flow_positions(scene, depsgraph)
    count = int(positions_np.shape[0]) if positions_np is not None else 0
    if count <= 0:
        cache.update(
            {
                "scene_name": scene_name,
                "frame": frame,
                "signature": signature,
                "positions_np": None,
                "prev_positions_np": None,
                "speed": [],
                "direction": [],
                "pair_id_map": {},
            }
        )
        return cache

    prev_positions_np = cache.get("prev_positions_np")
    prev_frame = cache.get("frame")

    reset = (
        prev_positions_np is None
        or prev_positions_np.shape[0] != positions_np.shape[0]
        or prev_frame is None
        or cache.get("signature") != signature
    )
    pair_id_map = _build_pair_id_map(pair_ids)
    if reset:
        zeros = [0.0] * count
        dir_zeros = [(0.0, 0.0, 0.0)] * count
        cache.update(
            {
                "scene_name": scene_name,
                "frame": frame,
                "signature": signature,
                "positions_np": positions_np,
                "prev_positions_np": positions_np.copy(),
                "speed": list(zeros),
                "direction": list(dir_zeros),
                "pair_id_map": pair_id_map,
            }
        )
        return cache

    fps = _get_fps(scene)
    frame_delta = frame - prev_frame
    if frame_delta == 0:
        frame_delta = 1
    dt = (frame_delta / fps) if fps > 0.0 else 1.0

    vel = (positions_np - prev_positions_np) / dt
    speed = np.linalg.norm(vel, axis=1)
    direction = np.zeros_like(vel)
    mask = speed > 1.0e-8
    if np.any(mask):
        direction[mask] = vel[mask] / speed[mask, None]

    cache.update(
        {
            "scene_name": scene_name,
            "frame": frame,
            "signature": signature,
            "positions_np": positions_np,
            "prev_positions_np": positions_np.copy(),
            "speed": speed.tolist(),
            "direction": [tuple(row) for row in direction.tolist()],
            "pair_id_map": pair_id_map,
        }
    )
    return cache


def get_flow_values(idx: int, frame: float) -> float:
    scene = getattr(bpy.context, "scene", None)
    cache = _update_flow_cache(scene)
    if not cache:
        return 0.0
    try:
        idx_i = int(idx)
    except (TypeError, ValueError):
        idx_i = -1
    pair_id_map = cache.get("pair_id_map") or {}
    if idx_i in pair_id_map:
        idx_i = pair_id_map[idx_i]
    speed = cache.get("speed", [])
    if idx_i < 0 or idx_i >= len(speed):
        return 0.0
    return float(speed[idx_i])


def get_flow_direction(idx: int, frame: float) -> tuple[float, float, float]:
    scene = getattr(bpy.context, "scene", None)
    cache = _update_flow_cache(scene)
    if not cache:
        return 0.0, 0.0, 0.0
    try:
        idx_i = int(idx)
    except (TypeError, ValueError):
        idx_i = -1
    pair_id_map = cache.get("pair_id_map") or {}
    if idx_i in pair_id_map:
        idx_i = pair_id_map[idx_i]
    direction = cache.get("direction", [])
    if idx_i < 0 or idx_i >= len(direction):
        return 0.0, 0.0, 0.0
    vec = direction[idx_i]
    if not vec or len(vec) < 3:
        return 0.0, 0.0, 0.0
    return float(vec[0]), float(vec[1]), float(vec[2])


def _update_checker_cache(scene: bpy.types.Scene, *, need_distance: bool) -> dict | None:
    cache = _CHECK_CACHE
    if scene is None:
        return None

    scene_name = scene.name if scene else None
    frame = int(getattr(scene, "frame_current", 0))
    if cache["scene_name"] == scene_name and cache["frame"] == frame and cache["positions"]:
        if need_distance and not cache["min_distance"]:
            cache["min_distance"] = _compute_min_distances(cache["positions"])
        return cache

    depsgraph = bpy.context.evaluated_depsgraph_get()
    positions, pair_ids, form_ids, signature, col_sig = _collect_formation_positions(scene, depsgraph)
    if not positions:
        cache.update(
            {
                "scene_name": scene_name,
                "frame": frame,
                "prev_frame": None,
                "signature": signature,
                "collection_signature": col_sig,
                "positions": [],
                "positions_np": None,
                "prev_positions": [],
                "prev_positions_np": None,
                "prev_vel": [],
                "prev_vel_np": None,
                "speed_vert": [],
                "speed_horiz": [],
                "speed_all": [],
                "acc": [],
                "min_distance": [],
                "form_order": False,
            }
        )
        return None

    collection_changed = cache.get("collection_signature") != col_sig
    positions_np = _positions_to_numpy(positions)
    form_indices, form_ok = _order_indices_by_ids(form_ids)
    if form_ok and len(form_indices) == len(positions):
        cache_indices = form_indices
    else:
        cache_indices = list(range(len(positions)))
        form_ok = False
    if cache_indices != list(range(len(positions))):
        positions_cache = [positions[idx] for idx in cache_indices]
        positions_cache_np = positions_np[np.asarray(cache_indices, dtype=np.int64)]
    else:
        positions_cache = list(positions)
        positions_cache_np = positions_np

    prev_positions_np = cache.get("prev_positions_np")
    prev_vel_np = cache.get("prev_vel_np")
    prev_frame = cache.get("frame")
    prev_form_order = bool(cache.get("form_order", False))
    can_pair_map = (
        collection_changed
        and prev_form_order
        and prev_positions_np is not None
        and _valid_id_map(pair_ids, int(prev_positions_np.shape[0]))
    )

    if (
        prev_positions_np is None
        or prev_positions_np.shape[0] != positions_cache_np.shape[0]
        or prev_frame is None
        or (collection_changed and not can_pair_map)
    ):
        zeros = [0.0] * len(positions_cache)
        cache.update(
            {
                "scene_name": scene_name,
                "frame": frame,
                "prev_frame": None,
                "signature": signature,
                "collection_signature": col_sig,
                "positions": positions_cache,
                "positions_np": positions_cache_np,
                "prev_positions": positions_cache,
                "prev_positions_np": positions_cache_np.copy(),
                "prev_vel": [],
                "prev_vel_np": np.zeros_like(positions_cache_np),
                "speed_vert": list(zeros),
                "speed_horiz": list(zeros),
                "speed_all": list(zeros),
                "acc": list(zeros),
                "min_distance": _compute_min_distances(positions_cache) if need_distance else [],
                "form_order": form_ok,
            }
        )
        return cache

    if cache["frame"] == frame and cache["positions"]:
        if need_distance and not cache["min_distance"]:
            cache["min_distance"] = _compute_min_distances(cache["positions"])
        return cache

    fps = _get_fps(scene)
    frame_delta = frame - prev_frame if prev_frame is not None else 1
    if frame_delta == 0:
        frame_delta = 1
    dt = (frame_delta / fps) if fps > 0.0 else 1.0

    if can_pair_map:
        pair_ids_np = np.asarray(pair_ids, dtype=np.int64)
        prev_match = prev_positions_np[pair_ids_np]
        vel_orig = (positions_np - prev_match) / dt
        vel = vel_orig[cache_indices] if cache_indices else vel_orig
    else:
        vel = (positions_cache_np - prev_positions_np) / dt
    if prev_vel_np is None or prev_vel_np.shape[0] != positions_np.shape[0]:
        prev_vel_np = np.zeros_like(vel)

    speed_vert = vel[:, 2].tolist()
    speed_horiz = np.linalg.norm(vel[:, :2], axis=1).tolist()
    speed_all = np.linalg.norm(vel, axis=1).tolist()
    acc_vec = (vel - prev_vel_np) / dt
    acc = np.linalg.norm(acc_vec, axis=1).tolist()

    cache.update(
        {
            "scene_name": scene_name,
            "frame": frame,
            "prev_frame": prev_frame,
            "signature": signature,
            "collection_signature": col_sig,
            "positions": positions_cache,
            "positions_np": positions_cache_np,
            "prev_positions": positions_cache,
            "prev_positions_np": positions_cache_np.copy(),
            "prev_vel": [],
            "prev_vel_np": vel,
            "speed_vert": speed_vert,
            "speed_horiz": speed_horiz,
            "speed_all": speed_all,
            "acc": acc,
            "min_distance": _compute_min_distances(positions_cache) if need_distance else [],
            "form_order": form_ok,
        }
    )
    return cache


def _draw_points_2d(coords, color, size):
    if not coords:
        return
    coords_3d = [(co[0], co[1], 0.0) for co in coords]
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": coords_3d})
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    gpu.state.depth_mask_set(False)
    gpu.state.point_size_set(size)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.depth_mask_set(True)
    gpu.state.depth_test_set('LESS_EQUAL')


def _get_range_bounds(scene):
    if not bool(getattr(scene, "ld_checker_range_enabled", True)):
        return None
    range_obj = getattr(scene, "ld_checker_range_object", None)
    if range_obj is not None:
        bounds = [range_obj.matrix_world @ Vector(corner) for corner in range_obj.bound_box]
        min_v = Vector((min(v.x for v in bounds), min(v.y for v in bounds), min(v.z for v in bounds)))
        max_v = Vector((max(v.x for v in bounds), max(v.y for v in bounds), max(v.z for v in bounds)))
        return min_v, max_v
    return None


def _draw_stats(scene: bpy.types.Scene, font_id: int = 0):
    show_speed = bool(getattr(scene, "ld_checker_show_speed", True))
    show_acc = bool(getattr(scene, "ld_checker_show_acc", True))
    show_distance = bool(getattr(scene, "ld_checker_show_distance", True))

    cache = _update_checker_cache(scene, need_distance=show_distance)
    if not cache:
        return

    speed_vert = cache.get("speed_vert", [])
    speed_horiz = cache.get("speed_horiz", [])
    acc = cache.get("acc", [])
    min_dist = cache.get("min_distance", [])

    limit_up = float(getattr(scene, "ld_proxy_max_speed_up", 0.0))
    limit_down = float(getattr(scene, "ld_proxy_max_speed_down", 0.0))
    limit_horiz = float(getattr(scene, "ld_proxy_max_speed_horiz", 0.0))
    limit_acc = float(getattr(scene, "ld_proxy_max_acc_vert", 0.0))
    limit_dist = float(getattr(scene, "ld_proxy_min_distance", 0.0))

    lines = []
    if show_speed and (speed_vert or speed_horiz):
        max_up = max([v for v in speed_vert if v > 0.0] or [0.0])
        max_down = min([v for v in speed_vert if v < 0.0] or [0.0])
        lines.append(("Max Speed Up", max_up, max_up > limit_up))
        lines.append(("Max Speed Down", abs(max_down), abs(max_down) > limit_down))
        max_horiz = max(speed_horiz or [0.0])
        lines.append(("Max Speed Horiz", max_horiz, max_horiz > limit_horiz))
    if show_acc and acc:
        max_acc = max(acc or [0.0])
        lines.append(("Max Acc", max_acc, max_acc > limit_acc))
    if show_distance and min_dist:
        min_val = min(min_dist)
        lines.append(("Min Distance", min_val, min_val < limit_dist))

    if not lines:
        return

    context = bpy.context
    space_data = context.space_data
    if space_data is None or getattr(space_data, "type", None) != "VIEW_3D":
        return
    overlay = getattr(space_data, "overlay", None)
    if overlay is None or not bool(getattr(overlay, "show_overlays", False)):
        return

    area = context.area
    if area is None:
        return

    ui_scale = context.preferences.system.ui_scale
    if bpy.app.version >= (4, 0, 0):
        left_panel_width = area.regions[4].width
    else:
        left_panel_width = area.regions[2].width

    if bpy.app.version < (2, 90):
        left_margin = left_panel_width + 19 * ui_scale
    else:
        left_margin = left_panel_width + 10 * ui_scale

    y = area.height - 72 * ui_scale
    if bool(getattr(overlay, "show_text", False)):
        y -= 36 * ui_scale
    if bool(getattr(overlay, "show_stats", False)):
        y -= 112 * ui_scale

    x = left_margin
    if bpy.app.version >= (4, 0, 0):
        blf.size(font_id, int(11 * ui_scale))
    else:
        blf.size(font_id, int(11 * ui_scale), 72)
    for label, value, is_error in lines:
        if is_error:
            blf.color(font_id, 1.0, 0.2, 0.2, 1.0)
        else:
            blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, f"{label}: {value:.2f}")
        y -= 16


def draw_gn_vertex_markers():
    context = bpy.context
    region = context.region
    rv3d = context.region_data
    if region is None or rv3d is None:
        return

    show_speed = bool(getattr(context.scene, "ld_checker_show_speed", True))
    show_acc = bool(getattr(context.scene, "ld_checker_show_acc", True))
    show_distance = bool(getattr(context.scene, "ld_checker_show_distance", True))
    show_range = bool(getattr(context.scene, "ld_checker_range_enabled", True))

    cache = _update_checker_cache(context.scene, need_distance=show_distance)
    if not cache:
        return

    positions = cache.get("positions", [])
    speed_vert = cache.get("speed_vert", [])
    speed_horiz = cache.get("speed_horiz", [])
    acc = cache.get("acc", [])
    min_dist = cache.get("min_distance", [])

    limit_up = float(getattr(context.scene, "ld_proxy_max_speed_up", 0.0))
    limit_down = float(getattr(context.scene, "ld_proxy_max_speed_down", 0.0))
    limit_horiz = float(getattr(context.scene, "ld_proxy_max_speed_horiz", 0.0))
    limit_acc = float(getattr(context.scene, "ld_proxy_max_acc_vert", 0.0))
    limit_dist = float(getattr(context.scene, "ld_proxy_min_distance", 0.0))

    range_bounds = _get_range_bounds(context.scene) if show_range else None

    size = float(getattr(context.scene, "ld_checker_size", 6.0))
    size = max(1.0, size)
    step = size + 2.0

    coords_by_color = {
        "speed": [],
        "acc": [],
        "distance": [],
        "range": [],
    }

    for i, world_co in enumerate(positions):
        pos_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, world_co)
        if pos_2d is None:
            continue

        flags = []
        if show_speed and i < len(speed_vert) and i < len(speed_horiz):
            if (
                speed_vert[i] > limit_up
                or speed_vert[i] < -limit_down
                or speed_horiz[i] > limit_horiz
            ):
                flags.append("speed")
        if show_acc and i < len(acc) and acc[i] > limit_acc:
            flags.append("acc")
        if show_distance and i < len(min_dist) and min_dist[i] < limit_dist:
            flags.append("distance")
        if show_range and range_bounds is not None:
            min_v, max_v = range_bounds
            in_range = (
                min_v.x <= world_co.x <= max_v.x
                and min_v.y <= world_co.y <= max_v.y
                and min_v.z <= world_co.z <= max_v.z
            )
            if not in_range:
                flags.append("range")

        if not flags:
            continue

        offset_base = -(len(flags) - 1) * 0.5 * step
        for idx, key in enumerate(flags):
            x = pos_2d.x + offset_base + idx * step
            coords_by_color[key].append((x, pos_2d.y))

    for key, coords in coords_by_color.items():
        _draw_points_2d(coords, ATTR_COLORS[key], size)


def draw_gn_stats():
    _draw_stats(bpy.context.scene)


def is_enabled() -> bool:
    return _handler is not None or _text_handler is not None


def set_enabled(enabled: bool) -> None:
    global _handler, _text_handler
    if enabled:
        if _handler is None:
            _handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_gn_vertex_markers,
                (),
                'WINDOW',
                'POST_PIXEL'
            )
        if _text_handler is None:
            _text_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_gn_stats,
                (),
                'WINDOW',
                'POST_PIXEL'
            )
    else:
        if _handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
            _handler = None
        if _text_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_text_handler, 'WINDOW')
            _text_handler = None


def _tag_redraw(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def menu_func(self, context):
    self.layout.operator(
        "view3d.draw_gn_vertex_markers",
        text="Toggle GN Vertex Markers"
    )


def register():
    bpy.types.VIEW3D_MT_view.append(menu_func)


def unregister():
    if _handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
    if _text_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_text_handler, 'WINDOW')
    bpy.types.VIEW3D_MT_view.remove(menu_func)
