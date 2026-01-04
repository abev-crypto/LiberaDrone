import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDVideoSamplerNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Sample a video frame (uses image data for now) based on entry progress."""

    bl_idname = "LDLEDVideoSamplerNode"
    bl_label = "Video Sampler"
    bl_icon = "SEQUENCE"

    filepath: bpy.props.StringProperty(
        name="Video",
        subtype='FILE_PATH',
        default="",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "U")
        self.inputs.new("NodeSocketFloat", "V")
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "filepath")

    def build_code(self, inputs):
        u = inputs.get("U", "0.0")
        v = inputs.get("V", "0.0")
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Color")
        video_path = bpy.path.abspath(self.filepath) if self.filepath else ""
        vid_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_progress_{vid_id} = _entry_progress({entry}, frame)",
                f"{out_var} = _sample_video({video_path!r}, frame, {u}, {v}) if _progress_{vid_id} > 0.0 else (0.0, 0.0, 0.0, 1.0)",
            ]
        )
