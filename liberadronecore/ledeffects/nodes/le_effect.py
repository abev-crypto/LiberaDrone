import bpy


class LDLEDEffectNode(bpy.types.Node):
    """Prototype effect node that modulates LED values."""

    bl_idname = "LDLEDEffectNode"
    bl_label = "LED Effect"
    bl_icon = "SHADERFX"

    effect_modes = [
        ("SOLID", "Solid", "Pass values through"),
        ("PULSE", "Pulse", "Animate intensity using speed"),
        ("WAVE", "Wave", "Wave effect using phase"),
    ]

    effect_type: bpy.props.EnumProperty(
        name="Effect",
        items=effect_modes,
        default="SOLID",
    )

    speed: bpy.props.FloatProperty(
        name="Speed",
        default=1.0,
        min=0.0,
        soft_max=10.0,
    )

    phase: bpy.props.FloatProperty(
        name="Phase",
        default=0.0,
        soft_min=-3.14,
        soft_max=3.14,
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
        layout.prop(self, "effect_type", text="")
        layout.prop(self, "speed")
        if self.effect_type in {"PULSE", "WAVE"}:
            layout.prop(self, "phase")
