import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDMeshUVNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Find UV from the nearest mesh vertex in a collection."""

    bl_idname = "LDLEDMeshUVNode"
    bl_label = "LED Mesh UV"
    bl_icon = "UV"

    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
    )

    use_children: bpy.props.BoolProperty(
        name="Include Children",
        default=True,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "U")
        self.outputs.new("NodeSocketFloat", "V")

    def draw_buttons(self, context, layout):
        layout.prop(self, "collection")
        layout.prop(self, "use_children")

    def build_code(self, inputs):
        out_u = self.output_var("U")
        out_v = self.output_var("V")
        col_name = self.collection.name if self.collection else ""
        return "\n".join(
            [
                f"_uv = _collection_nearest_uv({col_name!r}, (pos[0], pos[1], pos[2]), {bool(self.use_children)!r})",
                f"{out_u} = _uv[0]",
                f"{out_v} = _uv[1]",
            ]
        )
