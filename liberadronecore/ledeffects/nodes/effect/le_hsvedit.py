import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDHSVEditNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Adjust HSV components of a color."""

    bl_idname = "LDLEDHSVEditNode"
    bl_label = "HSV Edit"
    bl_icon = "COLOR"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        hue = self.inputs.new("NodeSocketFloat", "Hue")
        saturation = self.inputs.new("NodeSocketFloat", "Saturation")
        value = self.inputs.new("NodeSocketFloat", "Value")
        hue.default_value = 0.0
        saturation.default_value = 0.0
        value.default_value = 0.0
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def build_code(self, inputs):
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        hue = inputs.get("Hue", "0.0")
        saturation = inputs.get("Saturation", "0.0")
        value = inputs.get("Value", "0.0")
        out_var = self.output_var("Color")
        hsv_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_hsv_{hsv_id} = _rgb_to_hsv({color})",
                f"_h_{hsv_id} = _fract(_hsv_{hsv_id}[0] + ({hue}))",
                f"_s_{hsv_id} = _clamp01(_hsv_{hsv_id}[1] + ({saturation}))",
                f"_v_{hsv_id} = _clamp01(_hsv_{hsv_id}[2] + ({value}))",
                f"{out_var} = _hsv_to_rgb((_h_{hsv_id}, _s_{hsv_id}, _v_{hsv_id}, _hsv_{hsv_id}[3]))",
            ]
        )
