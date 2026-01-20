import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDCollectionInfoNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Provides access to a Blender collection for LED assignment."""

    bl_idname = "LDLEDCollectionInfoNode"
    bl_label = "Collection Info"
    bl_icon = "OUTLINER_COLLECTION"

    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        options={'LIBRARY_EDITABLE'},
    )

    use_children: bpy.props.BoolProperty(
        name="Include Children",
        default=True,
        description="Include objects from child collections",
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketCollection", "Collection")

    def draw_buttons(self, context, layout):
        layout.prop(self, "collection")
        layout.prop(self, "use_children")

    def build_code(self, inputs):
        out_collection = self.output_var("Collection")
        col_name = self.collection.name if self.collection else ""
        return f"{out_collection} = bpy.data.collections.get({col_name!r}) if {col_name!r} else None"
