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
    speed: bpy.props.FloatProperty(
        name="Speed",
        default=1.0,
        min=0.0,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        start_offset = self.inputs.new("NodeSocketFloat", "Start Offset")
        start_offset.hide_value = True
        duration_offset = self.inputs.new("NodeSocketFloat", "Duration Offset")
        duration_offset.hide_value = True
        speed = self.inputs.new("NodeSocketFloat", "Speed")
        speed.hide_value = True
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        start_socket = self.inputs.get("Start Offset")
        duration_socket = self.inputs.get("Duration Offset")
        speed_socket = self.inputs.get("Speed")
        row = layout.row()
        row.enabled = not (start_socket and start_socket.is_linked)
        row.prop(self, "start_offset")
        row = layout.row()
        row.enabled = not (duration_socket and duration_socket.is_linked)
        row.prop(self, "duration_offset")
        row = layout.row()
        row.enabled = not (speed_socket and speed_socket.is_linked)
        row.prop(self, "speed")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Entry")
        start_sock = self.inputs.get("Start Offset") if hasattr(self, "inputs") else None
        duration_sock = self.inputs.get("Duration Offset") if hasattr(self, "inputs") else None
        speed_sock = self.inputs.get("Speed") if hasattr(self, "inputs") else None
        if start_sock and getattr(start_sock, "is_linked", False):
            start_offset = inputs.get("Start Offset", "0.0")
        else:
            start_offset = str(int(self.start_offset))
        if duration_sock and getattr(duration_sock, "is_linked", False):
            duration_offset = inputs.get("Duration Offset", "0.0")
        else:
            duration_offset = str(int(self.duration_offset))
        if speed_sock and getattr(speed_sock, "is_linked", False):
            speed_val = inputs.get("Speed", "1.0")
        else:
            speed_val = str(float(self.speed))
        entry_var = f"_entry_shift({entry}, {start_offset}, {duration_offset})"
        return f"{out_var} = _entry_scale_duration({entry_var}, {speed_val})"
