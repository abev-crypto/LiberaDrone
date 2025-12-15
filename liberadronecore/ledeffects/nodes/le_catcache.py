import bpy


class LDLEDCatCacheNode(bpy.types.Node):
    """Represents cached LED categories to reuse across effects."""

    bl_idname = "LDLEDCatCacheNode"
    bl_label = "LED Category Cache"
    bl_icon = "FILE_CACHE"

    cache_modes = [
        ("WRITE", "Write", "Store incoming data to a named cache"),
        ("READ", "Read", "Read data from a named cache"),
    ]

    cache_mode: bpy.props.EnumProperty(
        name="Mode",
        items=cache_modes,
        default="WRITE",
    )

    cache_name: bpy.props.StringProperty(
        name="Cache Name",
        default="Default",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.inputs.new("NodeSocketFloat", "Intensity")
        self.outputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketFloat", "Intensity")

    def draw_buttons(self, context, layout):
        layout.prop(self, "cache_mode", text="")
        layout.prop(self, "cache_name")
