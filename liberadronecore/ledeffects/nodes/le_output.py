""" 
Color Alpha Entry Influence Priorityを持つ
"""

import bpy
from liberadronecore.ledeffects.le_nodecategory import LDLED_Node


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
