import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.util import projectionuv as projectionuv_util


class LDLEDProjectionUVNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Project position into a mesh bbox to produce UV."""

    bl_idname = "LDLEDProjectionUVNode"
    bl_label = "Projection UV"
    bl_icon = "MOD_UVPROJECT"

    preview_image: bpy.props.PointerProperty(
        name="Preview Image",
        type=bpy.types.Image,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketObject", "Mesh")
        self.outputs.new("NodeSocketFloat", "U")
        self.outputs.new("NodeSocketFloat", "V")

    def draw_buttons(self, context, layout):
        mesh_socket = self.inputs.get("Mesh")
        mesh_obj = None
        mesh_assigned = False
        if mesh_socket:
            if mesh_socket.is_linked and mesh_socket.links:
                mesh_assigned = True
                link = mesh_socket.links[0]
                from_node = link.from_node
                if hasattr(from_node, "target_object"):
                    mesh_obj = getattr(from_node, "target_object", None)
            else:
                mesh_obj = mesh_socket.default_value
                mesh_assigned = mesh_obj is not None

        if not mesh_assigned:
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
            return

        layout.template_ID(self, "preview_image", open="image.open")
        use_preview = bool(mesh_obj and self.preview_image)
        assigned = False
        if use_preview:
            assigned = projectionuv_util._is_preview_material_assigned(mesh_obj, self.preview_image)
        label = "Clear Preview Material" if assigned else "Assign Preview Material"
        row = layout.row()
        row.enabled = use_preview
        op = row.operator("ldled.projectionuv_toggle_preview_material", text=label)
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

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




