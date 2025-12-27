import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDFormationUVNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Project position into the DroneSystem bounds to produce UV."""

    bl_idname = "LDLEDFormationUVNode"
    bl_label = "LED Formation UV"
    bl_icon = "OUTLINER_OB_GROUP_INSTANCE"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "U")
        self.outputs.new("NodeSocketFloat", "V")

    def build_code(self, inputs):
        out_u = self.output_var("U")
        out_v = self.output_var("V")
        return "\n".join(
            [
                "_uv = _formation_bbox_uv((pos[0], pos[1], pos[2]))",
                f"{out_u} = _uv[0]",
                f"{out_v} = _uv[1]",
            ]
        )
