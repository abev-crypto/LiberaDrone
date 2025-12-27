import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDColorSpaceNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Convert between color spaces or to grayscale."""

    bl_idname = "LDLEDColorSpaceNode"
    bl_label = "LED Color Space"
    bl_icon = "IMAGE"

    mode_items = [
        ("SRGB_TO_LINEAR", "sRGB to Linear", "Convert sRGB to linear"),
        ("LINEAR_TO_SRGB", "Linear to sRGB", "Convert linear to sRGB"),
        ("GRAYSCALE", "Grayscale", "Convert to grayscale"),
    ]

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="SRGB_TO_LINEAR",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")

    def build_code(self, inputs):
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_var = self.output_var("Color")
        if self.mode == "LINEAR_TO_SRGB":
            return f"{out_var} = _linear_to_srgb({color})"
        if self.mode == "GRAYSCALE":
            return f"{out_var} = _to_grayscale({color})"
        return f"{out_var} = _srgb_to_linear({color})"
