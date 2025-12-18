import bpy
from liberadronecore.ledeffects.le_nodecategory import LDLED_Node


class LDLEDMathNode(bpy.types.Node, LDLED_Node):
    """Basic math node for LED intensities."""

    bl_idname = "LDLEDMathNode"
    bl_label = "LED Math"
    bl_icon = "MOD_MATH"

    math_items = [
        ("ADD", "Add", "Add inputs"),
        ("SUBTRACT", "Subtract", "Subtract B from A"),
        ("MULTIPLY", "Multiply", "Multiply inputs"),
        ("DIVIDE", "Divide", "Divide A by B"),
        ("MAX", "Max", "Maximum of A and B"),
        ("MIN", "Min", "Minimum of A and B"),
    ]

    operation: bpy.props.EnumProperty(
        name="Operation",
        items=math_items,
        default="ADD",
    )

    clamp_result: bpy.props.BoolProperty(
        name="Clamp",
        description="Clamp the result between 0 and 1",
        default=False,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "Value A")
        self.inputs.new("NodeSocketFloat", "Value B")
        self.outputs.new("NodeSocketFloat", "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")
        layout.prop(self, "clamp_result")
