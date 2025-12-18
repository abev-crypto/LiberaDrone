import bpy
from liberadronecore.ledeffects.le_nodecategory import LDLED_Node


class LDLEDOutputNode(bpy.types.Node, LDLED_Node):
    """Node representing the LED output surface."""

    bl_idname = "LDLEDOutputNode"
    bl_label = "LED Output"
    bl_icon = "OUTPUT"

    exposure: bpy.props.FloatProperty(
        name="Exposure",
        default=0.0,
        min=-10.0,
        max=10.0,
        description="Simple exposure control applied to incoming intensity",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.inputs.new("NodeSocketFloat", "Intensity")

    def draw_buttons(self, context, layout):
        layout.prop(self, "exposure")
