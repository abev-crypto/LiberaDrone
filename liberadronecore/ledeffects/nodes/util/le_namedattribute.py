import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.util import namedattribute as namedattribute_util


class LDLEDNamedAttributeNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Read a cached float attribute from Formation meshes."""

    bl_idname = "LDLEDNamedAttributeNode"
    bl_label = "Named Attribute"
    bl_icon = "NODETREE"
    NODE_CATEGORY_ID = "LD_LED_SOURCE"
    NODE_CATEGORY_LABEL = "Source"

    attribute_name: bpy.props.StringProperty(
        name="Attribute",
        default="",
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "attribute_name")

    def build_code(self, inputs):
        out_var = self.output_var("Value")
        name = str(self.attribute_name or "")
        if not name:
            return f"{out_var} = 0.0"
        return "\n".join(
            [
                f"_named_attr_cache({name!r})",
                f"{out_var} = _named_attr_value({name!r}, idx)",
            ]
        )
