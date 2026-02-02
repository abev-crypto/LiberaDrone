import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDNegaNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Invert RGB channels (one-minus)."""

    bl_idname = "LDLEDNegaNode"
    bl_label = "Nega"
    bl_icon = "IMAGE_ALPHA"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def build_code(self, inputs):
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_var = self.output_var("Color")
        return (
            f"{out_var} = ("
            f"1.0 - ({color}[0]), "
            f"1.0 - ({color}[1]), "
            f"1.0 - ({color}[2]), "
            f"{color}[3]"
            f")"
        )
