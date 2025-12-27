import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDFrameEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Entry active between start and duration frames."""

    bl_idname = "LDLEDFrameEntryNode"
    bl_label = "LED Frame Entry"
    bl_icon = "TIME"

    start: bpy.props.IntProperty(
        name="Start",
        default=0,
        min=0,
    )
    duration: bpy.props.IntProperty(
        name="Duration",
        default=0,
        min=0,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        layout.prop(self, "start")
        layout.prop(self, "duration")

    def build_code(self, inputs):
        out_var = self.output_var("Entry")
        entry_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return f"{out_var} = _entry_from_range({entry_key!r}, {int(self.start)}, {int(self.duration)})"
