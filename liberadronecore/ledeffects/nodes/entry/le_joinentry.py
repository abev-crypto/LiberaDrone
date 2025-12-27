import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDJoinEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Join multiple entry inputs into a single entry output."""

    bl_idname = "LDLEDJoinEntryNode"
    bl_label = "LED Join Entry"
    bl_icon = "NODETREE"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        sock = self.inputs.new("LDLEDEntrySocket", "Entries")
        sock.is_multi_input = True
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def build_code(self, inputs):
        entries = inputs.get("Entries", "_entry_empty()")
        out_var = self.output_var("Entry")
        return f"{out_var} = {entries}"
