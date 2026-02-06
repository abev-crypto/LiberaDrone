import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDFloatValueNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Provide a constant float value."""

    bl_idname = "LDLEDFloatValueNode"
    bl_label = "Value"
    bl_icon = "DRIVER"
    NODE_CATEGORY_ID = "LD_LED_SOURCE"
    NODE_CATEGORY_LABEL = "Source"

    value: bpy.props.FloatProperty(
        name="Value",
        default=0.0,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value")

    def build_code(self, inputs):
        out_var = self.output_var("Value")
        return f"{out_var} = {float(self.value)!r}"
