import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDLevelNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Adjust color levels with gain, offset, and gamma."""

    bl_idname = "LDLEDLevelNode"
    bl_label = "LED Level"
    bl_icon = "NODE_COMPOSITING"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        gain = self.inputs.new("NodeSocketFloat", "Gain")
        offset = self.inputs.new("NodeSocketFloat", "Offset")
        gamma = self.inputs.new("NodeSocketFloat", "Gamma")
        gain.default_value = 1.0
        offset.default_value = 0.0
        gamma.default_value = 1.0
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def build_code(self, inputs):
        gain = inputs.get("Gain", "1.0")
        offset = inputs.get("Offset", "0.0")
        gamma = inputs.get("Gamma", "1.0")
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_var = self.output_var("Color")
        lvl_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_lvl_r_{lvl_id} = _clamp(({color}[0] + ({offset})) * ({gain}), 0.0, 1.0)",
                f"_lvl_g_{lvl_id} = _clamp(({color}[1] + ({offset})) * ({gain}), 0.0, 1.0)",
                f"_lvl_b_{lvl_id} = _clamp(({color}[2] + ({offset})) * ({gain}), 0.0, 1.0)",
                f"_lvl_gamma_{lvl_id} = max(0.0001, ({gamma}))",
                f"{out_var} = (",
                f"    _clamp(_lvl_r_{lvl_id} ** (1.0 / _lvl_gamma_{lvl_id}), 0.0, 1.0),",
                f"    _clamp(_lvl_g_{lvl_id} ** (1.0 / _lvl_gamma_{lvl_id}), 0.0, 1.0),",
                f"    _clamp(_lvl_b_{lvl_id} ** (1.0 / _lvl_gamma_{lvl_id}), 0.0, 1.0),",
                f"    {color}[3],",
                ")",
            ]
        )
