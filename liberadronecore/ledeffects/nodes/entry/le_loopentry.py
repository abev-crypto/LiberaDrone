import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDLoopEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Loop an entry with an offset and repeat count."""

    bl_idname = "LDLEDLoopEntryNode"
    bl_label = "Loop Entry"
    bl_icon = "RECOVER_LAST"

    offset: bpy.props.IntProperty(
        name="Offset",
        default=0,
    )
    loops: bpy.props.IntProperty(
        name="Loops",
        default=0,
        min=0,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        layout.prop(self, "offset")
        layout.prop(self, "loops")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Entry")
        return f"{out_var} = _entry_loop({entry}, {int(self.offset)}, {int(self.loops)})"
