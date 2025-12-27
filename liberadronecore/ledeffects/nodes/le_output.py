""" 
Color Alpha Entry Influence Priorityを持つ
"""

import bpy
from liberadronecore.ledeffects.le_nodecategory import LDLED_Node


class LDLEDOutputNode(bpy.types.Node, LDLED_Node):
    """Node representing the LED output surface."""

    bl_idname = "LDLEDOutputNode"
    bl_label = "LED Output"
    bl_icon = "OUTPUT"

    priority: bpy.props.IntProperty(
        name="Priority",
        default=0,
        description="Higher values are composited on top",
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
        layout.prop(self, "priority")
