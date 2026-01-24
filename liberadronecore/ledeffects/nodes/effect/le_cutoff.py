import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDCutoffNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Zero out colors below a threshold."""

    bl_idname = "LDLEDCutoffNode"
    bl_label = "Cutoff"
    bl_icon = "MODIFIER"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        threshold = self.inputs.new("NodeSocketFloat", "Threshold")
        threshold.default_value = 0.0
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def build_code(self, inputs):
        threshold = inputs.get("Threshold", "0.0")
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_var = self.output_var("Color")
        return f"{out_var} = _cutoff_color({color}, {threshold})"
