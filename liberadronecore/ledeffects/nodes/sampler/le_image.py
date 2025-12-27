import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDImageSamplerNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Sample a Blender image by UV."""

    bl_idname = "LDLEDImageSamplerNode"
    bl_label = "LED Image Sampler"
    bl_icon = "IMAGE_DATA"

    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketVector", "UV")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "image")

    def build_code(self, inputs):
        uv = inputs.get("UV", "(0.0, 0.0, 0.0)")
        out_var = self.output_var("Color")
        image_name = self.image.name if self.image else ""
        return f"{out_var} = _sample_image({image_name!r}, ({uv}[0], {uv}[1]))"
