import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDValueNode(bpy.types.Node, LDLED_CodeNodeBase):
    """A minimal node to test the LED effects node tree."""

    bl_idname = "LDLEDValueNode"
    bl_label = "Color"
    bl_icon = 'COLOR'
    NODE_CATEGORY_ID = "LD_LED_SOURCE"
    NODE_CATEGORY_LABEL = "Source"

    color: bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "color", text="")

    def build_code(self, inputs):
        color_var = self.output_var("Color")
        color = tuple(float(c) for c in self.color)
        return f"{color_var} = {color!r}"
