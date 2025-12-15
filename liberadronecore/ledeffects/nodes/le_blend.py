import bpy


class LDLEDBlendNode(bpy.types.Node):
    """Blend two LED colors together."""

    bl_idname = "LDLEDBlendNode"
    bl_label = "LED Blend"
    bl_icon = "NODE_COMPOSITING"

    blend_modes = [
        ("MIX", "Mix", "Average the two colors"),
        ("ADD", "Add", "Add the second color to the first"),
        ("MULTIPLY", "Multiply", "Multiply colors"),
    ]

    blend_type: bpy.props.EnumProperty(
        name="Blend Type",
        items=blend_modes,
        default="MIX",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color 1")
        self.inputs.new("NodeSocketColor", "Color 2")
        self.inputs.new("NodeSocketFloat", "Factor")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "blend_type", text="")
