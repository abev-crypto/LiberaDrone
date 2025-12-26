import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase

"""
TODO: Step Saturate Fraction Floor Ceil Sine Cosine OneMinusを実装
"""

class LDLEDMathNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Basic math node for LED intensities."""

    bl_idname = "LDLEDMathNode"
    bl_label = "LED Math"
    bl_icon = "MODIFIER"

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

    def build_code(self, inputs):
        a = inputs.get("Value A", "0.0")
        b = inputs.get("Value B", "0.0")
        out_var = self.output_var("Value")
        op = self.operation
        if op == "ADD":
            expr = f"({a}) + ({b})"
        elif op == "SUBTRACT":
            expr = f"({a}) - ({b})"
        elif op == "MULTIPLY":
            expr = f"({a}) * ({b})"
        elif op == "DIVIDE":
            expr = f"({a}) / ({b}) if ({b}) != 0.0 else 0.0"
        elif op == "MAX":
            expr = f"({a}) if ({a}) > ({b}) else ({b})"
        elif op == "MIN":
            expr = f"({a}) if ({a}) < ({b}) else ({b})"
        else:
            expr = f"({a})"
        if self.clamp_result:
            expr = f"_clamp01({expr})"
        return f"{out_var} = {expr}"
