import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDProjectionUVNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Project position into a mesh bbox to produce UV."""

    bl_idname = "LDLEDProjectionUVNode"
    bl_label = "Projection UV"
    bl_icon = "MOD_UVPROJECT"

    target_object: bpy.props.PointerProperty(
        name="Mesh",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "U")
        self.outputs.new("NodeSocketFloat", "V")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")

    def build_code(self, inputs):
        out_u = self.output_var("U")
        out_v = self.output_var("V")
        obj_name = self.target_object.name if self.target_object else ""
        return "\n".join(
            [
                f"_uv = _project_bbox_uv({obj_name!r}, (pos[0], pos[1], pos[2]))",
                f"{out_u} = _uv[0]",
                f"{out_v} = _uv[1]",
            ]
        )
