"""
Viewport overlay for LED paint preview.
"""

import bpy
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader

from liberadronecore.ledeffects.util import paint as paint_util
from liberadronecore.util import formation_positions

_handler = None
_POINT_SIZE = 6.0
_CACHE = {
    "scene_name": None,
    "frame": None,
    "signature": None,
    "positions": [],
    "form_ids": None,
}


def _update_cache(scene: bpy.types.Scene):
    cache = _CACHE
    if scene is None:
        return None
    scene_name = scene.name
    frame = int(getattr(scene, "frame_current", 0))
    if cache["scene_name"] == scene_name and cache["frame"] == frame and cache["positions"]:
        return cache
    depsgraph = bpy.context.evaluated_depsgraph_get()
    positions, _pair_ids, form_ids, signature = formation_positions.collect_formation_positions_with_form_ids(
        scene,
        depsgraph,
        sort_by_pair_id=False,
        include_signature=True,
        as_numpy=False,
    )
    cache.update(
        {
            "scene_name": scene_name,
            "frame": frame,
            "signature": signature,
            "positions": positions or [],
            "form_ids": form_ids,
        }
    )
    return cache


def _draw_points_2d(coords, colors, size):
    if not coords:
        return
    coords_3d = [(co[0], co[1], 0.0) for co in coords]
    shader = gpu.shader.from_builtin('SMOOTH_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": coords_3d, "color": colors})
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    gpu.state.depth_mask_set(False)
    gpu.state.point_size_set(size)
    shader.bind()
    batch.draw(shader)
    gpu.state.depth_mask_set(True)
    gpu.state.depth_test_set('LESS_EQUAL')


def draw_paint_preview():
    context = bpy.context
    region = context.region
    rv3d = context.region_data
    if region is None or rv3d is None:
        return

    space_data = context.space_data
    if space_data is None or getattr(space_data, "type", None) != "VIEW_3D":
        return
    overlay = getattr(space_data, "overlay", None)
    if overlay is None or not bool(getattr(overlay, "show_overlays", False)):
        return

    node = paint_util.active_node()
    if node is None:
        return
    colors_by_id = paint_util.get_paint_cache(node)
    if not colors_by_id:
        return

    cache = _update_cache(context.scene)
    if not cache:
        return
    positions = cache.get("positions", [])
    form_ids = cache.get("form_ids")
    if not positions or not form_ids:
        return

    coords = []
    colors = []
    for pos, fid in zip(positions, form_ids):
        color = colors_by_id.get(int(fid))
        if color is None:
            continue
        pos_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, pos)
        if pos_2d is None:
            continue
        coords.append((pos_2d.x, pos_2d.y))
        colors.append((color[0], color[1], color[2], 1.0))

    if coords:
        _draw_points_2d(coords, colors, _POINT_SIZE)


def is_enabled() -> bool:
    return _handler is not None


def get_point_size() -> float:
    return float(_POINT_SIZE)


def set_point_size(value: float) -> None:
    global _POINT_SIZE
    _POINT_SIZE = max(1.0, float(value))
    _tag_redraw()


def set_enabled(enabled: bool) -> None:
    global _handler
    if enabled:
        if _handler is None:
            _handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_paint_preview,
                (),
                'WINDOW',
                'POST_PIXEL'
            )
        _tag_redraw()
    else:
        if _handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
            _handler = None
        _tag_redraw()


def _tag_redraw():
    context = bpy.context
    screen = getattr(context, "screen", None)
    if screen is None:
        return
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
