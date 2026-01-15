import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDMeshInfoNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Expose a mesh object for LED sampling."""

    bl_idname = "LDLEDMeshInfoNode"
    bl_label = "Mesh Info"
    bl_icon = "MESH_DATA"

    target_object: bpy.props.PointerProperty(
        name="Mesh",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketObject", "Mesh")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")

    def build_code(self, inputs):
        out_mesh = self.output_var("Mesh")
        obj_name = self.target_object.name if self.target_object else ""
        return f"{out_mesh} = bpy.data.objects.get({obj_name!r}) if {obj_name!r} else None"
