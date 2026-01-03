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
    "scene_id": None,
    "frame": None,
    "prev_frame": None,
    "signature": None,
    "positions": [],
    "positions_np": None,
    "prev_positions": [],
    "prev_positions_np": None,
    "prev_vel": [],
    "prev_vel_np": None,
    "speed_vert": [],
    "speed_horiz": [],
    "acc": [],
    "min_distance": [],
}


def _scene_id(scene) -> int | None:
    if scene is None:
        return None
    try:
        return int(scene.as_pointer())
    except Exception:
        return None


def _get_fps(scene: bpy.types.Scene) -> float:
    fps = float(getattr(scene.render, "fps", 0.0))
    base = float(getattr(scene.render, "fps_base", 1.0) or 1.0)
    if base <= 0.0:
        base = 1.0
    if fps <= 0.0:
        fps = 24.0
    return fps / base


def _collect_formation_positions(scene: bpy.types.Scene, depsgraph) -> tuple[list[Vector], tuple[tuple[str, int], ...]]:
    col = bpy.data.collections.get(FORMATION_ROOT)
    if col is None:
        return [], ()
    meshes = [obj for obj in col.all_objects if obj.type == 'MESH']
    meshes.sort(key=lambda o: o.name)

    positions: list[Vector] = []
    signature: list[tuple[str, int]] = []
    for obj in meshes:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        if eval_mesh is None:
            continue
        signature.append((obj.name, len(eval_mesh.vertices)))
        mw = eval_obj.matrix_world
        positions.extend([mw @ v.co for v in eval_mesh.vertices])
        eval_obj.to_mesh_clear()
    return positions, tuple(signature)


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


def _update_checker_cache(scene: bpy.types.Scene, *, need_distance: bool) -> dict | None:
    cache = _CHECK_CACHE
    if scene is None:
        return None

    scene_id = _scene_id(scene)
    frame = int(getattr(scene, "frame_current", 0))
    if cache["scene_id"] == scene_id and cache["frame"] == frame and cache["positions"]:
        if need_distance and not cache["min_distance"]:
            cache["min_distance"] = _compute_min_distances(cache["positions"])
        return cache

    depsgraph = bpy.context.evaluated_depsgraph_get()
    positions, signature = _collect_formation_positions(scene, depsgraph)
    if not positions:
        cache.update(
            {
                "scene_id": scene_id,
                "frame": frame,
                "prev_frame": None,
                "signature": signature,
                "positions": [],
                "positions_np": None,
                "prev_positions": [],
                "prev_positions_np": None,
                "prev_vel": [],
                "prev_vel_np": None,
                "speed_vert": [],
                "speed_horiz": [],
                "acc": [],
                "min_distance": [],
            }
        )
        return None

    reset = cache["scene_id"] != scene_id or cache["signature"] != signature

    if reset:
        positions_np = _positions_to_numpy(positions)
        zeros = [0.0] * len(positions)
        cache.update(
            {
                "scene_id": scene_id,
                "frame": frame,
                "prev_frame": None,
                "signature": signature,
                "positions": list(positions),
                "positions_np": positions_np,
                "prev_positions": list(positions),
                "prev_positions_np": positions_np.copy(),
                "prev_vel": [],
                "prev_vel_np": np.zeros_like(positions_np),
                "speed_vert": list(zeros),
                "speed_horiz": list(zeros),
                "acc": list(zeros),
                "min_distance": _compute_min_distances(positions) if need_distance else [],
            }
        )
        return cache

    if cache["frame"] == frame and cache["positions"]:
        if need_distance and not cache["min_distance"]:
            cache["min_distance"] = _compute_min_distances(cache["positions"])
        return cache

    prev_positions_np = cache.get("prev_positions_np")
    prev_vel_np = cache.get("prev_vel_np")
    if prev_positions_np is None or prev_positions_np.shape[0] != len(positions):
        positions_np = _positions_to_numpy(positions)
        zeros = [0.0] * len(positions)
        cache.update(
            {
                "scene_id": scene_id,
                "frame": frame,
                "prev_frame": None,
                "signature": signature,
                "positions": list(positions),
                "positions_np": positions_np,
                "prev_positions": list(positions),
                "prev_positions_np": positions_np.copy(),
                "prev_vel": [],
                "prev_vel_np": np.zeros_like(positions_np),
                "speed_vert": list(zeros),
                "speed_horiz": list(zeros),
                "acc": list(zeros),
                "min_distance": _compute_min_distances(positions) if need_distance else [],
            }
        )
        return cache

    prev_frame = cache.get("frame")
    fps = _get_fps(scene)
    frame_delta = frame - prev_frame if prev_frame is not None else 1
    if frame_delta == 0:
        frame_delta = 1
    dt = (frame_delta / fps) if fps > 0.0 else 1.0
    positions_np = _positions_to_numpy(positions)
    if prev_vel_np is None or prev_vel_np.shape[0] != positions_np.shape[0]:
        prev_vel_np = np.zeros_like(positions_np)

    vel = (positions_np - prev_positions_np) / dt
    speed_vert = vel[:, 2].tolist()
    speed_horiz = np.linalg.norm(vel[:, :2], axis=1).tolist()
    acc_vec = (vel - prev_vel_np) / dt
    acc = np.linalg.norm(acc_vec, axis=1).tolist()

    cache.update(
        {
            "scene_id": scene_id,
            "frame": frame,
            "prev_frame": prev_frame,
            "signature": signature,
            "positions": list(positions),
            "positions_np": positions_np,
            "prev_positions": list(positions),
            "prev_positions_np": positions_np.copy(),
            "prev_vel": [],
            "prev_vel_np": vel,
            "speed_vert": speed_vert,
            "speed_horiz": speed_horiz,
            "acc": acc,
            "min_distance": _compute_min_distances(positions) if need_distance else [],
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

    width = float(getattr(scene, "ld_checker_range_width", 0.0))
    height = float(getattr(scene, "ld_checker_range_height", 0.0))
    depth = float(getattr(scene, "ld_checker_range_depth", 0.0))
    if width <= 0.0:
        return None
    if height <= 0.0:
        height = width
    if depth <= 0.0:
        depth = width
    half_w = width * 0.5
    half_d = depth * 0.5
    min_v = Vector((-half_w, 0.0, -half_d))
    max_v = Vector((half_w, height, half_d))
    return min_v, max_v


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


class VIEW3D_OT_draw_gn_vertex_markers(bpy.types.Operator):
    """Toggle drawing GN vertex markers in viewport"""
    bl_idname = "view3d.draw_gn_vertex_markers"
    bl_label = "Toggle GN Vertex Markers"

    def execute(self, context):
        set_enabled(not is_enabled())
        self.report({'INFO'}, "GN vertex markers: ON" if is_enabled() else "GN vertex markers: OFF")
        _tag_redraw(context)
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(
        VIEW3D_OT_draw_gn_vertex_markers.bl_idname,
        text="Toggle GN Vertex Markers"
    )


classes = (
    VIEW3D_OT_draw_gn_vertex_markers,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_view.append(menu_func)


def unregister():
    if _handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
    if _text_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_text_handler, 'WINDOW')
    bpy.types.VIEW3D_MT_view.remove(menu_func)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
