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
        return f"{out_var} = _blend_colors({color_1}, {color_2}, {factor}, {self.blend_type!r})"
