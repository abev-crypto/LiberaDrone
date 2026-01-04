import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDIDMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask by formation id (uses drone index)."""

    bl_idname = "LDLEDIDMaskNode"
    bl_label = "ID Mask"
    bl_icon = "SORTSIZE"

    formation_id: bpy.props.IntProperty(
        name="Formation ID",
        default=0,
        min=0,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        layout.prop(self, "formation_id")

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        return f"{out_var} = 1.0 if idx == {int(self.formation_id)} else 0.0"
