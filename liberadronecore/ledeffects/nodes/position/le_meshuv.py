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
        self.outputs.new("NodeSocketVector", "UV")

    def draw_buttons(self, context, layout):
        layout.prop(self, "collection")
        layout.prop(self, "use_children")

    def build_code(self, inputs):
        out_var = self.output_var("UV")
        col_name = self.collection.name if self.collection else ""
        return "\n".join(
            [
                f"_uv = _collection_nearest_uv({col_name!r}, (pos[0], pos[1], pos[2]), {bool(self.use_children)!r})",
                f"{out_var} = (_uv[0], _uv[1], 0.0)",
            ]
        )
