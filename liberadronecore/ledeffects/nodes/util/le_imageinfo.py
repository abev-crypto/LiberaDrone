import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDImageInfoNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Expose a Blender image for reuse in LED nodes."""

    bl_idname = "LDLEDImageInfoNode"
    bl_label = "Image Info"
    bl_icon = "IMAGE_DATA"

    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketImage", "Image")

    def draw_buttons(self, context, layout):
        layout.prop(self, "image")

    def build_code(self, inputs):
        out_var = self.output_var("Image")
        image_name = self.image.name if self.image else ""
        if image_name:
            return f"{out_var} = bpy.data.images.get({image_name!r})"
        return f"{out_var} = None"
