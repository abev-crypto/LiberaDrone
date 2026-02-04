import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDProjectionUVNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Project position into a mesh bbox to produce UV."""

    bl_idname = "LDLEDProjectionUVNode"
    bl_label = "Projection UV"
    bl_icon = "MOD_UVPROJECT"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketObject", "Mesh")
        self.outputs.new("NodeSocketFloat", "U")
        self.outputs.new("NodeSocketFloat", "V")

    def draw_buttons(self, context, layout):
        row = layout.row()
        row = layout.row(align=True)
        op = row.operator("ldled.projectionuv_create_mesh", text="Area XZ")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op.mode = "AREA"
        op = row.operator("ldled.projectionuv_create_mesh", text="Formation XZ")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op.mode = "FORMATION"
        op = row.operator("ldled.projectionuv_create_mesh", text="Selection XZ")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op.mode = "SELECT"

    def build_code(self, inputs):
        out_u = self.output_var("U")
        out_v = self.output_var("V")
        obj_expr = inputs.get("Mesh", "''")
        return "\n".join(
            [
                f"_uv = _project_bbox_uv({obj_expr}, (pos[0], pos[1], pos[2]))",
                f"{out_u} = _uv[0]",
                f"{out_v} = _uv[1]",
            ]
        )




