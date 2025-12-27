import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDInsideMeshNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask based on whether a point is inside a mesh bounds."""

    bl_idname = "LDLEDInsideMeshNode"
    bl_label = "LED Inside Mesh"
    bl_icon = "MESH_CUBE"

    target_object: bpy.props.PointerProperty(
        name="Mesh",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        obj_name = self.target_object.name if self.target_object else ""
        return f"{out_var} = 1.0 if _point_in_mesh_bbox({obj_name!r}, (pos[0], pos[1], pos[2])) else 0.0"
