import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDEditEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Offset start and duration of an entry."""

    bl_idname = "LDLEDEditEntryNode"
    bl_label = "Edit Entry"
    bl_icon = "MODIFIER"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        start_offset = self.inputs.new("NodeSocketFloat", "Start Offset")
        duration_offset = self.inputs.new("NodeSocketFloat", "Duration Offset")
        speed = self.inputs.new("NodeSocketFloat", "Speed")
        start_offset.default_value = 0.0
        duration_offset.default_value = 0.0
        speed.default_value = 1.0
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Entry")
        start_offset = inputs.get("Start Offset", "0.0")
        duration_offset = inputs.get("Duration Offset", "0.0")
        speed_val = inputs.get("Speed", "1.0")
        entry_var = f"_entry_shift({entry}, {start_offset}, {duration_offset})"
        return f"{out_var} = _entry_scale_duration({entry_var}, {speed_val})"
