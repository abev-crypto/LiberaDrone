""" 
Color Alpha Entry Influence Priorityを持つ
"""

import bpy
from liberadronecore.ledeffects.le_nodecategory import LDLED_Node
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp01


@register_runtime_function
def _alpha_over(dst, src, alpha: float):
    inv = 1.0 - alpha
    return [
        src[0] * alpha + dst[0] * inv,
        src[1] * alpha + dst[1] * inv,
        src[2] * alpha + dst[2] * inv,
        1.0,
    ]


@register_runtime_function
def _blend_over(dst, src, alpha: float, mode: str):
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
    )

    priority: bpy.props.IntProperty(
        name="Priority",
        default=0,
        description="Higher values are composited on top",
    )

    random: bpy.props.FloatProperty(
        name="Random",
        default=0.0,
        min=0.0,
        max=1.0,
        description="Chance to shuffle output order within the same priority",
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
