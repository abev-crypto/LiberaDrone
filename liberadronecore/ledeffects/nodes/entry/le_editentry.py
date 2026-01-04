import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDEditEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Offset start and duration of an entry."""

    bl_idname = "LDLEDEditEntryNode"
    bl_label = "Edit Entry"
    bl_icon = "MODIFIER"

    start_offset: bpy.props.IntProperty(
        name="Start Offset",
        default=0,
    )
    duration_offset: bpy.props.IntProperty(
        name="Duration Offset",
        default=0,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        layout.prop(self, "start_offset")
        layout.prop(self, "duration_offset")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Entry")
        return f"{out_var} = _entry_shift({entry}, {int(self.start_offset)}, {int(self.duration_offset)})"
