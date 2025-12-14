import bpy


class LDLEDValueNode(bpy.types.Node):
    """A minimal node to test the LED effects node tree."""

    bl_idname = "LDLEDValueNode"
    bl_label = "LED Base Color"
    bl_icon = 'COLOR'

    color: bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
    )

    intensity: bpy.props.FloatProperty(
        name="Intensity",
        default=1.0,
        min=0.0,
        soft_max=5.0,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketFloat", "Intensity")

    def draw_buttons(self, context, layout):
        layout.prop(self, "color", text="")
        layout.prop(self, "intensity")
