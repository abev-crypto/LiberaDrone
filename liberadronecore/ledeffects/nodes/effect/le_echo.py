from __future__ import annotations

from typing import Dict, Tuple

import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


_ECHO_CACHE: Dict[str, Dict[str, object]] = {}


def _echo_state(key: str, frame: float) -> Dict[str, object]:
    state = _ECHO_CACHE.get(key)
    if state is None:
        state = {"frame": None, "colors": {}, "prev_colors": {}}
        _ECHO_CACHE[key] = state
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
def _echo_color(
    key: str,
    idx: int,
    frame: float,
    color: Tuple[float, float, float, float],
    decay: float,
) -> Tuple[float, float, float, float]:
    try:
        idx_i = int(idx)
    except Exception:
        return 0.0, 0.0, 0.0, 1.0
    state = _echo_state(str(key or ""), frame)
    cur_color = color
    if not isinstance(cur_color, (list, tuple)):
        cur_color = (0.0, 0.0, 0.0, 1.0)
    color_vals = [float(cur_color[0]) if len(cur_color) > 0 else 0.0]
    color_vals.append(float(cur_color[1]) if len(cur_color) > 1 else 0.0)
    color_vals.append(float(cur_color[2]) if len(cur_color) > 2 else 0.0)
    color_vals.append(float(cur_color[3]) if len(cur_color) > 3 else 1.0)
    state.get("colors", {})[idx_i] = tuple(color_vals)

    prev_color = state.get("prev_colors", {}).get(idx_i)
    if not prev_color:
        return 0.0, 0.0, 0.0, 1.0
    try:
        decay_val = float(decay)
    except Exception:
        decay_val = 0.0
    if decay_val < 0.0:
        decay_val = 0.0
    elif decay_val > 1.0:
        decay_val = 1.0
    scale = 1.0 - decay_val
    alpha = float(prev_color[3]) if len(prev_color) > 3 else 1.0
    return (
        float(prev_color[0]) * scale,
        float(prev_color[1]) * scale,
        float(prev_color[2]) * scale,
        alpha,
    )


class LDLEDEchoSamplerNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Echo the previous frame input color with decay."""

    bl_idname = "LDLEDEchoSamplerNode"
    bl_label = "Echo"
    bl_icon = "SEQ_HISTOGRAM"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        decay = self.inputs.new("NodeSocketFloat", "Decay")
        decay.default_value = 0.1
        try:
            decay.min_value = 0.0
            decay.max_value = 1.0
        except Exception:
            pass
        self.outputs.new("NodeSocketColor", "Color")

    def build_code(self, inputs):
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        decay = inputs.get("Decay", "0.0")
        out_var = self.output_var("Color")
        cache_key = self.name or self.codegen_id()
        return f"{out_var} = _echo_color({cache_key!r}, idx, frame, {color}, {decay})"
