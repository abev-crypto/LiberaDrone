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
        offset = self.inputs.new("NodeSocketFloat", "Offset")
        offset.hide_value = True
        loops = self.inputs.new("NodeSocketFloat", "Loops")
        loops.hide_value = True
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        offset_socket = self.inputs.get("Offset")
        loops_socket = self.inputs.get("Loops")
        row = layout.row()
        row.enabled = not (offset_socket and offset_socket.is_linked)
        row.prop(self, "offset")
        row = layout.row()
        row.enabled = not (loops_socket and loops_socket.is_linked)
        row.prop(self, "loops")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Entry")
        offset_sock = self.inputs.get("Offset") if hasattr(self, "inputs") else None
        loops_sock = self.inputs.get("Loops") if hasattr(self, "inputs") else None
        if offset_sock and getattr(offset_sock, "is_linked", False):
            offset_val = inputs.get("Offset", "0.0")
        else:
            offset_val = str(int(self.offset))
        if loops_sock and getattr(loops_sock, "is_linked", False):
            loops_val = inputs.get("Loops", "0.0")
        else:
            loops_val = str(int(self.loops))
        return f"{out_var} = _entry_loop({entry}, {offset_val}, {loops_val})"
