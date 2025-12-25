"""
Viewport overlay for GN error attributes.
"""

import bpy
import blf
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

TARGET_OBJ_NAME = "ProxyPoints"
ATTR_NAMES = (
    "err_speed",
    "err_acc",
    "err_close",
)
ATTR_COLORS = {
    "speed": (1.0, 1.0, 0.2, 1.0),
    "acc": (1.0, 0.2, 1.0, 1.0),
    "distance": (1.0, 0.2, 0.2, 1.0),
    "range": (0.2, 0.8, 1.0, 1.0),
}

_handler = None
_text_handler = None


def _get_attr(mesh, name: str):
    attr = mesh.attributes.get(name)
    return attr if attr is not None else None


def _get_attr_flags(attr) -> list[bool]:
    flags: list[bool] = []
    if attr is None:
        return flags
    for data in attr.data:
        val = getattr(data, "value", None)
        if isinstance(val, bool):
            flags.append(val)
        else:
            try:
                flags.append(float(val) > 0.5)
            except Exception:
                flags.append(False)
    return flags


def _get_attr_values(attr) -> list[float]:
    values: list[float] = []
    if attr is None:
        return values
    for data in attr.data:
        val = getattr(data, "value", 0.0)
        try:
            values.append(float(val))
        except Exception:
            values.append(0.0)
    return values


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
    if width <= 0.0:
        return None
    depth = width
    height = width
    half_w = width * 0.5
    half_d = depth * 0.5
    min_v = Vector((-half_w, 0.0, -half_d))
    max_v = Vector((half_w, height, half_d))
    return min_v, max_v


def _draw_stats(mesh, font_id: int = 0):
    speed_vert = _get_attr_values(_get_attr(mesh, "speed_vert"))
    speed_horiz = _get_attr_values(_get_attr(mesh, "speed_horiz"))
    acc = _get_attr_values(_get_attr(mesh, "acc"))
    min_dist = _get_attr_values(_get_attr(mesh, "min_distance"))

    scene = bpy.context.scene
    limit_up = float(getattr(scene, "ld_proxy_max_speed_up", 0.0))
    limit_down = float(getattr(scene, "ld_proxy_max_speed_down", 0.0))
    limit_horiz = float(getattr(scene, "ld_proxy_max_speed_horiz", 0.0))
    limit_acc = float(getattr(scene, "ld_proxy_max_acc_vert", 0.0))
    limit_dist = float(getattr(scene, "ld_proxy_min_distance", 0.0))

    show_speed = bool(getattr(scene, "ld_checker_show_speed", True))
    show_acc = bool(getattr(scene, "ld_checker_show_acc", True))
    show_distance = bool(getattr(scene, "ld_checker_show_distance", True))

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
    obj = bpy.data.objects.get(TARGET_OBJ_NAME)
    if obj is None:
        return

    context = bpy.context
    region = context.region
    rv3d = context.region_data
    if region is None or rv3d is None:
        return

    depsgraph = context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = getattr(eval_obj, "data", None)
    if mesh is None:
        return

    show_speed = bool(getattr(context.scene, "ld_checker_show_speed", True))
    show_acc = bool(getattr(context.scene, "ld_checker_show_acc", True))
    show_distance = bool(getattr(context.scene, "ld_checker_show_distance", True))
    show_range = bool(getattr(context.scene, "ld_checker_range_enabled", True))

    err_speed = _get_attr_flags(_get_attr(mesh, "err_speed")) if show_speed else []
    err_acc = _get_attr_flags(_get_attr(mesh, "err_acc")) if show_acc else []
    err_close = _get_attr_flags(_get_attr(mesh, "err_close")) if show_distance else []
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

    for i, v in enumerate(mesh.vertices):
        world_co = eval_obj.matrix_world @ v.co
        pos_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, world_co)
        if pos_2d is None:
            continue

        flags = []
        if show_speed and i < len(err_speed) and err_speed[i]:
            flags.append("speed")
        if show_acc and i < len(err_acc) and err_acc[i]:
            flags.append("acc")
        if show_distance and i < len(err_close) and err_close[i]:
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
    obj = bpy.data.objects.get(TARGET_OBJ_NAME)
    if obj is None:
        return

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = getattr(eval_obj, "data", None)
    if mesh is None:
        return

    _draw_stats(mesh)


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
