import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDBlendNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Blend two LED colors together."""

    bl_idname = "LDLEDBlendNode"
    bl_label = "LED Blend"
    bl_icon = "NODE_COMPOSITING"

    blend_modes = [
        ("MIX", "Mix", "Average the two colors"),
        ("ADD", "Add", "Add the second color to the first"),
        ("MULTIPLY", "Multiply", "Multiply colors"),
    ]

    blend_type: bpy.props.EnumProperty(
        name="Blend Type",
        items=blend_modes,
        default="MIX",
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
        return "\n".join(
            [
                f"{out_var} = [",
                f"    ({color_1}[0] * {inv}) + ({color_2}[0] * ({factor})),",
                f"    ({color_1}[1] * {inv}) + ({color_2}[1] * ({factor})),",
                f"    ({color_1}[2] * {inv}) + ({color_2}[2] * ({factor})),",
                f"    ({color_1}[3] * {inv}) + ({color_2}[3] * ({factor})),",
                "]",
            ]
        )
