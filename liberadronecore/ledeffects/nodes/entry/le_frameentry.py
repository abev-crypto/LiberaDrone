import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDFrameEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Entry active between start and duration frames."""

    bl_idname = "LDLEDFrameEntryNode"
    bl_label = "Frame Entry"
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
        start = self.inputs.new("NodeSocketFloat", "Start")
        start.hide_value = True
        duration = self.inputs.new("NodeSocketFloat", "Duration")
        duration.hide_value = True
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        start_socket = self.inputs.get("Start")
        duration_socket = self.inputs.get("Duration")
        row = layout.row()
        row.enabled = not (start_socket and start_socket.is_linked)
        row.prop(self, "start")
        row = layout.row()
        row.enabled = not (duration_socket and duration_socket.is_linked)
        row.prop(self, "duration")

    def build_code(self, inputs):
        out_var = self.output_var("Entry")
        entry_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        start_sock = self.inputs.get("Start") if hasattr(self, "inputs") else None
        duration_sock = self.inputs.get("Duration") if hasattr(self, "inputs") else None
        if start_sock and getattr(start_sock, "is_linked", False):
            start_val = inputs.get("Start", "0.0")
        else:
            start_val = str(int(self.start))
        if duration_sock and getattr(duration_sock, "is_linked", False):
            duration_val = inputs.get("Duration", "0.0")
        else:
            duration_val = str(int(self.duration))
        return f"{out_var} = _entry_from_range({entry_key!r}, {start_val}, {duration_val})"
