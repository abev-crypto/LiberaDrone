from __future__ import annotations

from typing import Dict, Tuple

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util import le_meshinfo


_BLUR_CACHE: Dict[str, object] = {
    "frame": None,
    "positions_id": None,
    "kd": None,
}
_BLUR_COLOR_CACHE: Dict[str, Dict[str, object]] = {}


def _blur_kdtree(positions, frame: float):
    cache = _BLUR_CACHE
    frame_i = int(frame)
    pos_id = id(positions)
    if (
        cache.get("frame") == frame_i
        and cache.get("positions_id") == pos_id
        and cache.get("kd") is not None
    ):
        return cache["kd"]
    kd = KDTree(len(positions))
    for idx, pos in enumerate(positions):
        kd.insert(Vector(pos), idx)
    kd.balance()
    cache["frame"] = frame_i
    cache["positions_id"] = pos_id
    cache["kd"] = kd
    return kd


def _blur_state(key: str, frame: float) -> Dict[str, object]:
    state = _BLUR_COLOR_CACHE.get(key)
    if state is None:
        state = {"frame": None, "colors": {}, "prev_colors": {}}
        _BLUR_COLOR_CACHE[key] = state
    frame_i = int(frame)
    if state.get("frame") != frame_i:
        if state.get("frame") == frame_i - 1:
            state["prev_colors"] = state.get("colors", {})
        else:
            state["prev_colors"] = {}
        state["colors"] = {}
        state["frame"] = frame_i
    return state


@register_runtime_function
def _blur_color(
    key: str,
    idx: int,
    frame: float,
    color: Tuple[float, float, float, float],
    radius: float,
) -> Tuple[float, float, float, float]:
    positions = le_meshinfo._LED_FRAME_CACHE.get("positions") or []
    if not positions:
        return color
    try:
        idx_i = int(idx)
    except Exception:
        return color
    if idx_i < 0 or idx_i >= len(positions):
        return color

    state = _blur_state(str(key or ""), frame)
    prev_colors = state.get("prev_colors", {})
    cur_color = color
    if not isinstance(cur_color, (list, tuple)):
        cur_color = (0.0, 0.0, 0.0, 1.0)
    color_vals = [float(cur_color[0]) if len(cur_color) > 0 else 0.0]
    color_vals.append(float(cur_color[1]) if len(cur_color) > 1 else 0.0)
    color_vals.append(float(cur_color[2]) if len(cur_color) > 2 else 0.0)
    color_vals.append(float(cur_color[3]) if len(cur_color) > 3 else 1.0)
    state.get("colors", {})[idx_i] = tuple(color_vals)

    try:
        radius_val = float(radius)
    except Exception:
        radius_val = 0.0
    if radius_val <= 0.0:
        return color

    kd = _blur_kdtree(positions, frame)
    neighbors = kd.find_range(Vector(positions[idx_i]), radius_val)
    if not neighbors:
        return color

    r = float(color[0]) if len(color) > 0 else 0.0
    g = float(color[1]) if len(color) > 1 else 0.0
    b = float(color[2]) if len(color) > 2 else 0.0
    a = float(color[3]) if len(color) > 3 else 1.0
    count = 1
    for _co, n_idx, _dist in neighbors:
        if n_idx == idx_i:
            continue
        n_color = prev_colors.get(int(n_idx))
        if not n_color:
            continue
        r += float(n_color[0])
        g += float(n_color[1])
        b += float(n_color[2])
        a += float(n_color[3]) if len(n_color) > 3 else 1.0
        count += 1

    if count <= 1:
        return color
    inv = 1.0 / float(count)
    return (r * inv, g * inv, b * inv, a * inv)


class LDLEDBlurNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mix input color with neighboring colors."""

    bl_idname = "LDLEDBlurNode"
    bl_label = "Blur"
    bl_icon = "BRUSH_DATA"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        radius = self.inputs.new("NodeSocketFloat", "Radius")
        radius.default_value = 1.0
        try:
            radius.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketColor", "Color")

    def build_code(self, inputs):
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        radius = inputs.get("Radius", "0.0")
        out_var = self.output_var("Color")
        cache_key = self.name or self.codegen_id()
        return f"{out_var} = _blur_color({cache_key!r}, idx, frame, {color}, {radius})"
