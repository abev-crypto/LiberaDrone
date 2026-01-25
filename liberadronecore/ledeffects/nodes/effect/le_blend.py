import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDBlendNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Blend two LED colors together."""

    bl_idname = "LDLEDBlendNode"
    bl_label = "Blend"
    bl_icon = "NODE_COMPOSITING"

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

    blend_type: bpy.props.EnumProperty(
        name="Blend Type",
        items=blend_modes,
        default="MIX",
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color 1")
        self.inputs.new("NodeSocketColor", "Color 2")
        self.inputs.new("NodeSocketFloat", "Factor")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "blend_type", text="")

    def build_code(self, inputs):
        color_1 = inputs.get("Color 1", "(0.0, 0.0, 0.0, 1.0)")
        color_2 = inputs.get("Color 2", "(0.0, 0.0, 0.0, 1.0)")
        factor = inputs.get("Factor", "0.0")
        out_var = self.output_var("Color")
        inv = f"(1.0 - ({factor}))"
        mode = self.blend_type
        if mode == "ADD":
            expr = "({a} + {b})"
        elif mode == "MULTIPLY":
            expr = "({a} * {b})"
        elif mode == "SCREEN":
            expr = "(1.0 - (1.0 - {a}) * (1.0 - {b}))"
        elif mode == "OVERLAY":
            expr = "((2.0 * {a} * {b}) if ({a} < 0.5) else (1.0 - 2.0 * (1.0 - {a}) * (1.0 - {b})))"
        elif mode == "HARD_LIGHT":
            expr = "((2.0 * {a} * {b}) if ({b} < 0.5) else (1.0 - 2.0 * (1.0 - {a}) * (1.0 - {b})))"
        elif mode == "SOFT_LIGHT":
            expr = "(({a} - (1.0 - 2.0 * {b}) * {a} * (1.0 - {a})) if ({b} < 0.5) else ({a} + (2.0 * {b} - 1.0) * (max(0.0, min(1.0, {a})) ** 0.5 - {a})))"
        elif mode == "BURN":
            expr = "(max(0.0, min(1.0, 1.0 - (1.0 - {a}) / ({b} if {b} > 0.0 else 1e-5))))"
        elif mode == "SUBTRACT":
            expr = "({a} - {b})"
        elif mode == "MAX":
            expr = "({a} if {a} > {b} else {b})"
        else:
            expr = "{b}"

        def blend_channel(channel_index: int) -> str:
            a = f"{color_1}[{channel_index}]"
            b = f"{color_2}[{channel_index}]"
            blended = expr.format(a=a, b=b)
            return f"(({a} * {inv}) + ({blended} * ({factor})))"

        return "\n".join(
            [
                f"{out_var} = [",
                f"    {blend_channel(0)},",
                f"    {blend_channel(1)},",
                f"    {blend_channel(2)},",
                f"    ({color_1}[3] * {inv}) + ({color_2}[3] * ({factor})),",
                "]",
            ]
        )
