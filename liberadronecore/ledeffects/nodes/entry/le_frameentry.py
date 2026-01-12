import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDFrameEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Entry active between start and duration frames."""

    bl_idname = "LDLEDFrameEntryNode"
    bl_label = "Frame Entry"
    bl_icon = "TIME"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "Start")
        self.inputs.new("NodeSocketFloat", "Duration")
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def build_code(self, inputs):
        out_var = self.output_var("Entry")
        entry_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        start_val = inputs.get("Start", "0.0")
        duration_val = inputs.get("Duration", "0.0")
        return f"{out_var} = _entry_from_range({entry_key!r}, {start_val}, {duration_val})"
