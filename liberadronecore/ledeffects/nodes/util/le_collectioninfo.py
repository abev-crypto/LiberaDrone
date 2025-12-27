import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDCollectionInfoNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Provides access to a Blender collection for LED assignment."""

    bl_idname = "LDLEDCollectionInfoNode"
    bl_label = "LED Collection Info"
    bl_icon = "OUTLINER_COLLECTION"

    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
    )

    use_children: bpy.props.BoolProperty(
        name="Include Children",
        default=True,
        description="Include objects from child collections",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketFloat", "Intensity")
        self.outputs.new("NodeSocketString", "Collection Name")

    def draw_buttons(self, context, layout):
        layout.prop(self, "collection")
        layout.prop(self, "use_children")

    def build_code(self, inputs):
        out_color = self.output_var("Color")
        out_intensity = self.output_var("Intensity")
        out_name = self.output_var("Collection Name")
        col_name = self.collection.name if self.collection else ""
        enabled = 1.0 if self.collection else 0.0
        return "\n".join(
            [
                f"{out_name} = {col_name!r}",
                f"{out_intensity} = {enabled}",
                f"{out_color} = (1.0, 1.0, 1.0, 1.0) if {enabled} > 0.0 else (0.0, 0.0, 0.0, 1.0)",
            ]
        )
