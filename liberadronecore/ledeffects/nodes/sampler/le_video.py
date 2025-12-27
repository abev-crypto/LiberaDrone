import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDVideoSamplerNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Sample a video frame (uses image data for now) based on entry progress."""

    bl_idname = "LDLEDVideoSamplerNode"
    bl_label = "LED Video Sampler"
    bl_icon = "SEQUENCE"

    image: bpy.props.PointerProperty(
        name="Video",
        type=bpy.types.Image,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketVector", "UV")
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "image")

    def build_code(self, inputs):
        uv = inputs.get("UV", "(0.0, 0.0, 0.0)")
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Color")
        image_name = self.image.name if self.image else ""
        vid_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_progress_{vid_id} = _entry_progress({entry}, frame)",
                f"{out_var} = _sample_image({image_name!r}, ({uv}[0], {uv}[1])) if _progress_{vid_id} > 0.0 else (0.0, 0.0, 0.0, 1.0)",
            ]
        )
