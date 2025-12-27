import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDVertexColorNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Sample nearest vertex color from a mesh."""

    bl_idname = "LDLEDVertexColorNode"
    bl_label = "LED Vertex Color"
    bl_icon = "GROUP_VERTEX"

    target_object: bpy.props.PointerProperty(
        name="Mesh",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")

    def build_code(self, inputs):
        out_var = self.output_var("Color")
        obj_name = self.target_object.name if self.target_object else ""
        return f"{out_var} = _nearest_vertex_color({obj_name!r}, (pos[0], pos[1], pos[2]))"
