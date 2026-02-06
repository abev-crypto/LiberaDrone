from __future__ import annotations

import math
import bpy
import bmesh
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from mathutils.kdtree import KDTree

from liberadronecore.ledeffects.nodes.le_output import _blend_over
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


DEFAULT_BRUSH_RADIUS_PX = 40.0
DEFAULT_FALLOFF_POWER = 2.0

PAINT_BLEND_MODES = [
    ("MIX", "Mix", "Average the two colors"),
    ("ADD", "Add", "Add the second color to the first"),
    ("MULTIPLY", "Multiply", "Multiply colors"),
    ("OVERLAY", "Overlay", "Overlay blend"),
    ("SCREEN", "Screen", "Screen blend"),
    ("HARD_LIGHT", "Hard Light", "Hard light blend"),
    ("SOFT_LIGHT", "Soft Light", "Soft light blend"),
    ("BURN", "Burn", "Color burn blend"),
    ("SUBTRACT", "Subtract", "Subtract colors"),
    ("MAX", "Max", "Max channel value"),
]

_PAINT_CACHE: dict[str, dict[int, tuple[float, float, float, float]]] = {}
_ACTIVE_NODE: tuple[str, str] | None = None
_LAST_MOUSE: tuple[int, int] | None = None
_EYEDROP_MODE: str | None = None
_MODAL_ACTIVE = False
_PAINT_HISTORY: dict[str, list[dict[int, tuple[float, float, float, float]]]] = {}
_PAINT_REDO: dict[str, list[dict[int, tuple[float, float, float, float]]]] = {}
_PAINT_HISTORY_LIMIT = 32


def _paint_key(tree_name: str, node_name: str) -> str:
    return f"{tree_name}::{node_name}"


def set_last_mouse(x: int, y: int) -> None:
    global _LAST_MOUSE
    _LAST_MOUSE = (int(x), int(y))


def last_mouse() -> tuple[int, int] | None:
    return _LAST_MOUSE


def set_paint_modal_active(active: bool) -> None:
    global _MODAL_ACTIVE
    _MODAL_ACTIVE = bool(active)


def is_paint_modal_active() -> bool:
    return _MODAL_ACTIVE


def set_eyedrop_mode(mode: str | None) -> None:
    global _EYEDROP_MODE
    _EYEDROP_MODE = mode


def eyedrop_mode() -> str | None:
    return _EYEDROP_MODE


def set_active_node(node: bpy.types.Node) -> None:
    global _ACTIVE_NODE
    _ACTIVE_NODE = (node.id_data.name, node.name)
    ensure_paint_cache(node)


def clear_active_node() -> None:
    global _ACTIVE_NODE
    _ACTIVE_NODE = None


def active_node() -> bpy.types.Node | None:
    if _ACTIVE_NODE is None:
        return None
    tree_name, node_name = _ACTIVE_NODE
    return bpy.data.node_groups[tree_name].nodes[node_name]


def get_paint_cache(node: bpy.types.Node | None) -> dict[int, tuple[float, float, float, float]]:
    if node is None:
        return {}
    return _get_cache(node)



def ensure_paint_cache(node: bpy.types.Node) -> dict[int, tuple[float, float, float, float]]:
    key = _paint_key(node.id_data.name, node.name)
    colors = {}
    for item in node.paint_items:
        idx = int(item.index)
        color = tuple(float(c) for c in item.color)
        colors[idx] = color
    _PAINT_CACHE[key] = colors
    return colors


def _get_cache(node: bpy.types.Node) -> dict[int, tuple[float, float, float, float]]:
    key = _paint_key(node.id_data.name, node.name)
    colors = _PAINT_CACHE.get(key)
    if colors is None:
        colors = ensure_paint_cache(node)
    return colors


def clear_paint_cache(node: bpy.types.Node) -> None:
    key = _paint_key(node.id_data.name, node.name)
    _PAINT_CACHE.pop(key, None)


def push_history(node: bpy.types.Node) -> None:
    key = _paint_key(node.id_data.name, node.name)
    history = _PAINT_HISTORY.setdefault(key, [])
    snapshot = {int(item.index): tuple(float(c) for c in item.color) for item in node.paint_items}
    history.append(snapshot)
    if len(history) > _PAINT_HISTORY_LIMIT:
        history.pop(0)
    _PAINT_REDO.pop(key, None)


def undo_history(node: bpy.types.Node) -> bool:
    key = _paint_key(node.id_data.name, node.name)
    history = _PAINT_HISTORY.get(key)
    if not history:
        return False
    redo = _PAINT_REDO.setdefault(key, [])
    current = {int(item.index): tuple(float(c) for c in item.color) for item in node.paint_items}
    redo.append(current)
    snapshot = history.pop()
    _restore_history(node, snapshot)
    clear_paint_cache(node)
    return True


def redo_history(node: bpy.types.Node) -> bool:
    key = _paint_key(node.id_data.name, node.name)
    redo = _PAINT_REDO.get(key)
    if not redo:
        return False
    history = _PAINT_HISTORY.setdefault(key, [])
    current = {int(item.index): tuple(float(c) for c in item.color) for item in node.paint_items}
    history.append(current)
    if len(history) > _PAINT_HISTORY_LIMIT:
        history.pop(0)
    snapshot = redo.pop()
    _restore_history(node, snapshot)
    clear_paint_cache(node)
    return True


def clear_history(node: bpy.types.Node) -> None:
    key = _paint_key(node.id_data.name, node.name)
    _PAINT_HISTORY.pop(key, None)
    _PAINT_REDO.pop(key, None)


def _restore_history(node: bpy.types.Node, snapshot: dict[int, tuple[float, float, float, float]]) -> None:
    node.paint_items.clear()
    for idx, color in sorted(snapshot.items(), key=lambda item: item[0]):
        item = node.paint_items.add()
        item.index = int(idx)
        item.color = color


def set_paint_color(
    node: bpy.types.Node,
    idx: int,
    color: tuple[float, float, float, float],
    item_map: dict[int, bpy.types.PropertyGroup] | None = None,
) -> None:
    colors = _get_cache(node)
    if item_map is None:
        item_map = {int(item.index): item for item in node.paint_items}
    item = item_map.get(int(idx))
    if item is None:
        item = node.paint_items.add()
        item.index = int(idx)
        item_map[int(idx)] = item
    item.color = color
    colors[int(idx)] = color


def apply_paint(
    node: bpy.types.Node,
    hits: list[tuple[int, float]],
    color_rgb: tuple[float, float, float],
    alpha: float,
    blend_mode: str,
    erase: bool = False,
) -> None:
    if not hits:
        return
    colors = _get_cache(node)
    item_map = {int(item.index): item for item in node.paint_items}
    r, g, b = (float(color_rgb[0]), float(color_rgb[1]), float(color_rgb[2]))
    alpha_val = float(alpha)
    for vidx, weight in hits:
        strength = alpha_val * float(weight)
        if strength <= 0.0:
            continue
        current = colors.get(int(vidx), (0.0, 0.0, 0.0, 0.0))
        if erase:
            new_alpha = current[3] - strength
            if new_alpha <= 0.0:
                set_paint_color(node, int(vidx), (0.0, 0.0, 0.0, 0.0), item_map=item_map)
            else:
                set_paint_color(
                    node,
                    int(vidx),
                    (float(current[0]), float(current[1]), float(current[2]), float(new_alpha)),
                    item_map=item_map,
                )
            continue
        dst = [current[0], current[1], current[2], 1.0]
        src = [r, g, b, 1.0]
        blended = _blend_over(dst, src, strength, blend_mode)
        new_alpha = current[3] + (alpha_val - current[3]) * float(weight)
        set_paint_color(
            node,
            int(vidx),
            (float(blended[0]), float(blended[1]), float(blended[2]), float(new_alpha)),
            item_map=item_map,
        )


def selected_vertex_indices(obj: bpy.types.Object) -> list[int]:
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    return [int(v.index) for v in bm.verts if v.select]


def build_screen_kdtree(
    context,
    obj: bpy.types.Object,
    only_selected: bool,
) -> tuple[KDTree, list[int], int]:
    region = context.region
    rv3d = context.region_data
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    selected_idx = {int(v.index) for v in bm.verts if v.select} if only_selected else None

    depsgraph = context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

    pts2d = []
    vidx_list = []
    mw = eval_obj.matrix_world
    try:
        for v in eval_mesh.vertices:
            idx = int(v.index)
            if selected_idx is not None and idx not in selected_idx:
                continue
            wco = mw @ v.co
            p2d = view3d_utils.location_3d_to_region_2d(region, rv3d, wco)
            if p2d is None:
                continue
            pts2d.append((float(p2d.x), float(p2d.y), 0.0))
            vidx_list.append(idx)
    finally:
        eval_obj.to_mesh_clear()

    kd = KDTree(len(pts2d))
    for i, p in enumerate(pts2d):
        kd.insert(Vector(p), i)
    kd.balance()
    return kd, vidx_list, len(pts2d)


def find_hits(
    kd: KDTree,
    vidx_list: list[int],
    mouse_xy: tuple[int, int],
    radius_px: float,
    power: float,
    hard: bool = False,
) -> list[tuple[int, float]]:
    mx, my = mouse_xy
    center = Vector((float(mx), float(my), 0.0))
    hits = []
    for (co, k_i, dist) in kd.find_range(center, float(radius_px)):
        if hard:
            w = 1.0
        else:
            t = max(0.0, 1.0 - (float(dist) / float(radius_px)))
            w = (t ** float(power)) if power != 1.0 else t
        hits.append((int(vidx_list[k_i]), float(w)))
    return hits


def average_color(
    node: bpy.types.Node,
    hits: list[tuple[int, float]],
) -> tuple[float, float, float, float] | None:
    if not hits:
        return None
    colors = _get_cache(node)
    total = 0.0
    acc = Vector((0.0, 0.0, 0.0, 0.0))
    for vidx, weight in hits:
        col = colors.get(int(vidx))
        if col is None:
            continue
        acc += Vector(col) * float(weight)
        total += float(weight)
    if total <= 0.0:
        return None
    out = acc / total
    return (float(out[0]), float(out[1]), float(out[2]), float(out[3]))


def sample_screen_color(context, mouse_xy: tuple[int, int]) -> tuple[float, float, float, float] | None:
    region = context.region
    local_x = int(mouse_xy[0])
    local_y = int(mouse_xy[1])
    if local_x < 0 or local_y < 0 or local_x >= region.width or local_y >= region.height:
        return None
    rx = int(getattr(region, "x", 0))
    ry = int(getattr(region, "y", 0))
    x = local_x + rx
    y = local_y + ry
    fb = gpu.state.active_framebuffer_get()
    buf = fb.read_color(x, y, 1, 1, 4, 0, 'FLOAT')
    pixels = buf.to_list() if hasattr(buf, "to_list") else list(buf)
    row = pixels[0]
    vals = row[0] if isinstance(row[0], (list, tuple)) else row
    return (float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3]))


def draw_circle_2d(center, radius_px, segments=64) -> None:
    if center is None or radius_px is None or radius_px <= 0.5:
        return
    cx, cy = center
    verts = []
    for i in range(int(segments) + 1):
        t = (i / float(segments)) * math.tau
        verts.append((cx + math.cos(t) * radius_px, cy + math.sin(t) * radius_px, 0.0))

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINE_STRIP", {"pos": verts})

    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(2.0)
    shader.bind()
    shader.uniform_float("color", (1.0, 1.0, 1.0, 0.9))
    batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


def draw_callback_px(self, _context):
    if eyedrop_mode() is not None:
        return
    draw_circle_2d(self._brush_center_2d, self._brush_radius_px)


@register_runtime_function
def _paint_color(tree_name: str, node_name: str, idx: int):
    key = _paint_key(str(tree_name), str(node_name))
    colors = _PAINT_CACHE.get(key)
    if colors is None:
        node = bpy.data.node_groups[str(tree_name)].nodes[str(node_name)]
        colors = ensure_paint_cache(node)
    return colors.get(int(idx), (0.0, 0.0, 0.0, 0.0))
