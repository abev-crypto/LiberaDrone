import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDLoopEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Loop an entry with an offset and repeat count."""

    bl_idname = "LDLEDLoopEntryNode"
    bl_label = "Loop Entry"
    bl_icon = "RECOVER_LAST"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        offset = self.inputs.new("NodeSocketFloat", "Offset")
        loops = self.inputs.new("NodeSocketFloat", "Loops")
        offset.default_value = 0.0
        loops.default_value = 0.0
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Entry")
        offset_val = inputs.get("Offset", "0.0")
        loops_val = inputs.get("Loops", "0.0")
        return f"{out_var} = _entry_loop({entry}, {offset_val}, {loops_val})"
