""" 
Color Alpha Entry Influence Priorityを持つ
"""

import bpy
import numpy as np
from liberadronecore.ledeffects.le_nodecategory import LDLED_Node
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp01


@register_runtime_function
def _alpha_over(dst, src, alpha: float):
    if isinstance(dst, np.ndarray) or isinstance(src, np.ndarray) or isinstance(alpha, np.ndarray):
        return _blend_over_vec(dst, src, alpha, "MIX", None)
    inv = 1.0 - alpha
    return [
        src[0] * alpha + dst[0] * inv,
        src[1] * alpha + dst[1] * inv,
        src[2] * alpha + dst[2] * inv,
        1.0,
    ]


@register_runtime_function
def _blend_over(dst, src, alpha: float, mode: str):
    if isinstance(dst, np.ndarray) or isinstance(src, np.ndarray) or isinstance(alpha, np.ndarray):
        return _blend_over_vec(dst, src, alpha, mode, None)
    alpha = _clamp01(float(alpha))
    if alpha <= 0.0:
        return [dst[0], dst[1], dst[2], 1.0]
    mode = (mode or "MIX").upper()
    if mode == "MIX":
        return _alpha_over(dst, src, alpha)

    def blend_channel(a: float, b: float) -> float:
        if mode == "ADD":
            return a + b
        if mode == "MULTIPLY":
            return a * b
        if mode == "SCREEN":
            return 1.0 - (1.0 - a) * (1.0 - b)
        if mode == "OVERLAY":
            return (2.0 * a * b) if (a < 0.5) else (1.0 - 2.0 * (1.0 - a) * (1.0 - b))
        if mode == "HARD_LIGHT":
            return (2.0 * a * b) if (b < 0.5) else (1.0 - 2.0 * (1.0 - a) * (1.0 - b))
        if mode == "SOFT_LIGHT":
            return (a - (1.0 - 2.0 * b) * a * (1.0 - a)) if (b < 0.5) else (
                a + (2.0 * b - 1.0) * (_clamp01(a) ** 0.5 - a)
            )
        if mode == "BURN":
            return _clamp01(1.0 - (1.0 - a) / (b if b > 0.0 else 1e-5))
        if mode == "SUBTRACT":
            return a - b
        if mode == "MAX":
            return a if a > b else b
        return b

    inv = 1.0 - alpha
    r = dst[0] * inv + blend_channel(dst[0], src[0]) * alpha
    g = dst[1] * inv + blend_channel(dst[1], src[1]) * alpha
    b = dst[2] * inv + blend_channel(dst[2], src[2]) * alpha
    return [r, g, b, 1.0]


def _blend_channel_np(a, b, mode: str):
    if mode == "ADD":
        return a + b
    if mode == "MULTIPLY":
        return a * b
    if mode == "SCREEN":
        return 1.0 - (1.0 - a) * (1.0 - b)
    if mode == "OVERLAY":
        return np.where(a < 0.5, 2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b))
    if mode == "HARD_LIGHT":
        return np.where(b < 0.5, 2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b))
    if mode == "SOFT_LIGHT":
        return np.where(
            b < 0.5,
            a - (1.0 - 2.0 * b) * a * (1.0 - a),
            a + (2.0 * b - 1.0) * (np.sqrt(_clamp01(a)) - a),
        )
    if mode == "BURN":
        return _clamp01(1.0 - (1.0 - a) / np.maximum(b, 1e-5))
    if mode == "SUBTRACT":
        return a - b
    if mode == "MAX":
        return np.maximum(a, b)
    return b


@register_runtime_function
def _zeros_color(count: int):
    return np.zeros((int(count), 4), dtype=np.float32)


@register_runtime_function
def _as_array(value, count: int):
    if isinstance(value, np.ndarray):
        return value
    return np.full(int(count), float(value), dtype=np.float32)


@register_runtime_function
def _as_color_array(color, count: int):
    if isinstance(color, np.ndarray):
        if color.ndim == 1:
            if color.shape[0] == 4:
                return np.repeat(color.reshape((1, 4)), int(count), axis=0)
            if color.shape[0] == 3:
                color = np.concatenate([color, np.array([1.0], dtype=color.dtype)])
                return np.repeat(color.reshape((1, 4)), int(count), axis=0)
        if color.shape[0] == int(count):
            if color.shape[1] == 3:
                alpha = np.ones((color.shape[0], 1), dtype=color.dtype)
                return np.concatenate([color, alpha], axis=1)
            return color
    if isinstance(color, (list, tuple)) and len(color) == 4:
        channels = [_as_array(ch, count) for ch in color]
        return np.stack(channels, axis=1)
    return np.tile(np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32), (int(count), 1))


@register_runtime_function
def _mask_any(mask) -> bool:
    if isinstance(mask, np.ndarray):
        return bool(mask.any())
    return bool(mask)


@register_runtime_function
def _blend_over_vec(dst, src, alpha, mode: str, mask=None):
    if not isinstance(dst, np.ndarray):
        return _blend_over(dst, src, float(alpha), mode)
    if dst.size == 0:
        return dst
    alpha = _clamp01(_as_array(alpha, dst.shape[0]))
    mode = (mode or "MIX").upper()
    if mask is None:
        mask = np.ones((dst.shape[0],), dtype=bool)
    elif not isinstance(mask, np.ndarray):
        mask = np.full((dst.shape[0],), bool(mask), dtype=bool)
    if not mask.any():
        return dst
    inv = 1.0 - alpha
    out = dst.copy()
    if mode == "MIX":
        out[mask, 0] = src[mask, 0] * alpha[mask] + dst[mask, 0] * inv[mask]
        out[mask, 1] = src[mask, 1] * alpha[mask] + dst[mask, 1] * inv[mask]
        out[mask, 2] = src[mask, 2] * alpha[mask] + dst[mask, 2] * inv[mask]
        out[mask, 3] = 1.0
        return out
    blended_r = _blend_channel_np(dst[:, 0], src[:, 0], mode)
    blended_g = _blend_channel_np(dst[:, 1], src[:, 1], mode)
    blended_b = _blend_channel_np(dst[:, 2], src[:, 2], mode)
    out[mask, 0] = dst[mask, 0] * inv[mask] + blended_r[mask] * alpha[mask]
    out[mask, 1] = dst[mask, 1] * inv[mask] + blended_g[mask] * alpha[mask]
    out[mask, 2] = dst[mask, 2] * inv[mask] + blended_b[mask] * alpha[mask]
    out[mask, 3] = 1.0
    return out


@register_runtime_function
def _blend_colors(color_a, color_b, factor, mode: str):
    if isinstance(color_a, np.ndarray) or isinstance(color_b, np.ndarray) or isinstance(factor, np.ndarray):
        count = None
        if isinstance(color_a, np.ndarray) and color_a.ndim > 1:
            count = color_a.shape[0]
        elif isinstance(color_b, np.ndarray) and color_b.ndim > 1:
            count = color_b.shape[0]
        elif isinstance(factor, np.ndarray):
            count = factor.shape[0]
        if count is None:
            count = 1
        a = _as_color_array(color_a, count)
        b = _as_color_array(color_b, count)
        f = _clamp01(_as_array(factor, count))
        inv = 1.0 - f
        mode = (mode or "MIX").upper()
        blended_r = _blend_channel_np(a[:, 0], b[:, 0], mode)
        blended_g = _blend_channel_np(a[:, 1], b[:, 1], mode)
        blended_b = _blend_channel_np(a[:, 2], b[:, 2], mode)
        out = np.zeros_like(a)
        out[:, 0] = a[:, 0] * inv + blended_r * f
        out[:, 1] = a[:, 1] * inv + blended_g * f
        out[:, 2] = a[:, 2] * inv + blended_b * f
        out[:, 3] = a[:, 3] * inv + b[:, 3] * f
        return out

    a = color_a
    b = color_b
    f = _clamp01(float(factor))
    inv = 1.0 - f
    mode = (mode or "MIX").upper()
    blended = [
        _blend_channel_np(a[0], b[0], mode),
        _blend_channel_np(a[1], b[1], mode),
        _blend_channel_np(a[2], b[2], mode),
    ]
    return [
        a[0] * inv + blended[0] * f,
        a[1] * inv + blended[1] * f,
        a[2] * inv + blended[2] * f,
        a[3] * inv + b[3] * f,
    ]


@register_runtime_function
def _cutoff_color(color, threshold: float):
    if isinstance(color, np.ndarray):
        thresh = float(threshold)
        max_val = np.maximum.reduce([color[:, 0], color[:, 1], color[:, 2]])
        mask = max_val <= thresh
        out = color.copy()
        out[mask, 0:3] = 0.0
        return out
    max_val = max(color[0], color[1], color[2])
    if max_val <= float(threshold):
        return (0.0, 0.0, 0.0, color[3])
    return color


class LDLEDOutputNode(bpy.types.Node, LDLED_Node):
    """Node representing the LED output surface."""

    bl_idname = "LDLEDOutputNode"
    bl_label = "Output"
    bl_icon = "OUTPUT"

    blend_modes = [
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

    blend_mode: bpy.props.EnumProperty(
        name="Blend Mode",
        items=blend_modes,
        default="MIX",
        options={'LIBRARY_EDITABLE'},
    )

    priority: bpy.props.IntProperty(
        name="Priority",
        default=0,
        description="Higher values are composited on top",
        options={'LIBRARY_EDITABLE'},
    )

    random: bpy.props.FloatProperty(
        name="Random",
        default=0.0,
        min=0.0,
        max=1.0,
        description="Chance to shuffle output order within the same priority",
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        color = self.inputs.new("NodeSocketColor", "Color")
        intensity = self.inputs.new("NodeSocketFloat", "Intensity")
        alpha = self.inputs.new("NodeSocketFloat", "Alpha")
        entry = self.inputs.new("LDLEDEntrySocket", "Entry")
        if hasattr(entry, "link_limit"):
            entry.link_limit = 0
        intensity.default_value = 1.0
        alpha.default_value = 1.0

    def draw_buttons(self, context, layout):
        layout.prop(self, "blend_mode")
        layout.prop(self, "random")
        layout.prop(self, "priority")
