"""
Viewport overlay for GN error attributes.
"""

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader

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
}

_handler = None


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


def _draw_points(coords, color):
    if not coords:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": coords})
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    gpu.state.depth_mask_set(False)
    gpu.state.point_size_set(6.0)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.depth_mask_set(True)
    gpu.state.depth_test_set('LESS_EQUAL')


def _draw_stats(mesh, font_id: int = 0):
    speed_vert = _get_attr_values(_get_attr(mesh, "speed_vert"))
    speed_horiz = _get_attr_values(_get_attr(mesh, "speed_horiz"))
    acc = _get_attr_values(_get_attr(mesh, "acc"))
    min_dist = _get_attr_values(_get_attr(mesh, "min_distance"))

    lines = []
    if speed_vert or speed_horiz:
        max_up = max([v for v in speed_vert if v > 0.0] or [0.0])
        max_down = min([v for v in speed_vert if v < 0.0] or [0.0])
        lines.append(f"Max Speed Up: {max_up:.2f}")
        lines.append(f"Max Speed Down: {abs(max_down):.2f}")
        lines.append(f"Max Speed Horiz: {max(speed_horiz or [0.0]):.2f}")
    if acc:
        lines.append(f"Max Acc: {max(acc or [0.0]):.2f}")
    if min_dist:
        lines.append(f"Min Distance: {min(min_dist):.2f}")

    if not lines:
        return

    region = bpy.context.region
    if region is None:
        return

    x = 20
    y = region.height - 30
    blf.size(font_id, 12)
    for line in lines:
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, line)
        y -= 16


def draw_gn_vertex_markers():
    obj = bpy.data.objects.get(TARGET_OBJ_NAME)
    if obj is None:
        return

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = getattr(eval_obj, "data", None)
    if mesh is None:
        return

    err_speed = _get_attr_flags(_get_attr(mesh, "err_speed"))
    err_acc = _get_attr_flags(_get_attr(mesh, "err_acc"))
    err_close = _get_attr_flags(_get_attr(mesh, "err_close"))

    coords_speed = []
    coords_acc = []
    coords_dist = []

    for i, v in enumerate(mesh.vertices):
        world_co = eval_obj.matrix_world @ v.co
        if i < len(err_acc) and err_acc[i]:
            coords_acc.append(world_co)
            continue
        if i < len(err_close) and err_close[i]:
            coords_dist.append(world_co)
            continue
        if i < len(err_speed) and err_speed[i]:
            coords_speed.append(world_co)

    _draw_points(coords_acc, ATTR_COLORS["acc"])
    _draw_points(coords_dist, ATTR_COLORS["distance"])
    _draw_points(coords_speed, ATTR_COLORS["speed"])
    _draw_stats(mesh)


def is_enabled() -> bool:
    return _handler is not None


def set_enabled(enabled: bool) -> None:
    global _handler
    if enabled and _handler is None:
        _handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_gn_vertex_markers,
            (),
            'WINDOW',
            'POST_VIEW'
        )
    elif not enabled and _handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
        _handler = None


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
    bpy.types.VIEW3D_MT_view.remove(menu_func)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
