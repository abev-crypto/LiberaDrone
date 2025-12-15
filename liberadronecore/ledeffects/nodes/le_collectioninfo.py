import bpy


class LDLEDCollectionInfoNode(bpy.types.Node):
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
