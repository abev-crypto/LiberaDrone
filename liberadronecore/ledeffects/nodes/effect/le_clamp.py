import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDClampNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Clamp a color between min and max values."""

    bl_idname = "LDLEDClampNode"
    bl_label = "Clamp"
    bl_icon = "MODIFIER"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        min_sock = self.inputs.new("NodeSocketFloat", "Min")
        max_sock = self.inputs.new("NodeSocketFloat", "Max")
        min_sock.default_value = 0.0
        max_sock.default_value = 1.0
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def build_code(self, inputs):
        min_val = inputs.get("Min", "0.0")
        max_val = inputs.get("Max", "1.0")
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_var = self.output_var("Color")
        return "\n".join(
            [
                f"{out_var} = [",
                f"    _clamp({color}[0], {min_val}, {max_val}),",
                f"    _clamp({color}[1], {min_val}, {max_val}),",
                f"    _clamp({color}[2], {min_val}, {max_val}),",
                f"    _clamp({color}[3], {min_val}, {max_val}),",
                "]",
            ]
        )
