import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDImageSamplerNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Sample a Blender image by UV."""

    bl_idname = "LDLEDImageSamplerNode"
    bl_label = "Image Sampler"
    bl_icon = "IMAGE_DATA"

    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        image = self.inputs.new("NodeSocketImage", "Image")
        image.hide_value = True
        self.inputs.new("NodeSocketFloat", "U")
        self.inputs.new("NodeSocketFloat", "V")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        image_socket = self.inputs.get("Image")
        row = layout.row()
        row.enabled = not (image_socket and image_socket.is_linked)
        row.prop(self, "image")

    def build_code(self, inputs):
        u = inputs.get("U", "0.0")
        v = inputs.get("V", "0.0")
        out_var = self.output_var("Color")
        image_socket = self.inputs.get("Image") if hasattr(self, "inputs") else None
        if image_socket and getattr(image_socket, "is_linked", False):
            image_val = inputs.get("Image", "None")
        else:
            image_name = self.image.name if self.image else ""
            image_val = repr(image_name) if image_name else "None"
        return f"{out_var} = _sample_image({image_val}, ({u}, {v}))"
