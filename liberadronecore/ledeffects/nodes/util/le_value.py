import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDValueNode(bpy.types.Node, LDLED_CodeNodeBase):
    """A minimal node to test the LED effects node tree."""

    bl_idname = "LDLEDValueNode"
    bl_label = "Color"
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

    def build_code(self, inputs):
        color_var = self.output_var("Color")
        intensity_var = self.output_var("Intensity")
        color = tuple(float(c) for c in self.color)
        intensity = float(self.intensity)
        return "\n".join(
            [
                f"{color_var} = {color!r}",
                f"{intensity_var} = {intensity!r}",
            ]
        )
