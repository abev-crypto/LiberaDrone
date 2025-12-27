import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDTimeMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Output a 0-1 mask based on entry progress."""

    bl_idname = "LDLEDTimeMaskNode"
    bl_label = "LED Time Mask"
    bl_icon = "TIME"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.outputs.new("NodeSocketFloat", "Factor")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Factor")
        return f"{out_var} = _entry_progress({entry}, frame)"
