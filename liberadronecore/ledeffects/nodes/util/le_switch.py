import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.nodes.util import le_math
from liberadronecore.ledeffects.util import switch as switch_util


class LDLEDSwitchNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Switch between float inputs over entry duration."""

    bl_idname = "LDLEDSwitchNode"
    bl_label = "Switch"
    bl_icon = "ARROW_LEFTRIGHT"

    mode_items = [
        ("ENTRY", "Entry", "Switch while entry is active"),
        ("VALUE", "Switch ID", "Pick input by float switch id"),
    ]

    fade_items = [
        ("NONE", "Instant", "Instant switch"),
        ("IN", "Fade In", "Fade from previous to current"),
        ("OUT", "Fade Out", "Fade from current to next"),
        ("IN_OUT", "Fade In/Out", "Fade at both ends"),
    ]

    switch_mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="ENTRY",
        update=lambda self, _context: self._sync_inputs(),
        options={'LIBRARY_EDITABLE'},
    )
    input_count: bpy.props.IntProperty(
        name="Inputs",
        default=2,
        min=2,
        max=32,
        update=lambda self, _context: self._sync_inputs(),
        options={'LIBRARY_EDITABLE'},
    )
    step_frames: bpy.props.IntProperty(
        name="Step Frames",
        description="Frames between switch increments while entry is active",
        default=1,
        min=1,
        options={'LIBRARY_EDITABLE'},
    )
    fade_mode: bpy.props.EnumProperty(
        name="Fade",
        items=fade_items,
        default="NONE",
        options={'LIBRARY_EDITABLE'},
    )
    fade_frames: bpy.props.FloatProperty(
        name="Fade Frames",
        default=2.0,
        min=0.0,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.inputs.new("NodeSocketFloat", "Switch ID")
        self.outputs.new("NodeSocketFloat", "Value")
        self._sync_inputs()

    def update(self):
        self._sync_inputs()

    def _value_socket_names(self, count: int) -> list[str]:
        count = max(1, int(count))
        return [f"Value {idx + 1}" for idx in range(count)]

    def _sync_inputs(self):
        entry = self.inputs.get("Entry")
        switch_id = self.inputs.get("Switch ID")
        if entry is None:
            entry = self.inputs.new("LDLEDEntrySocket", "Entry")
        if switch_id is None:
            switch_id = self.inputs.new("NodeSocketFloat", "Switch ID")
            switch_id.default_value = 0.0
        is_value_mode = self.switch_mode == "VALUE"
        entry.hide = is_value_mode
        switch_id.hide = not is_value_mode
        desired_count = max(2, int(self.input_count))
        desired_names = self._value_socket_names(desired_count)
        for name in desired_names:
            if self.inputs.get(name) is None:
                sock = self.inputs.new("NodeSocketFloat", name)
                sock.default_value = 0.0
        for sock in list(self.inputs):
            if not sock.name.startswith("Value "):
                continue
            if sock.name not in desired_names:
                self.inputs.remove(sock)

    def draw_buttons(self, context, layout):
        layout.prop(self, "switch_mode", text="")
        layout.prop(self, "input_count")
        if self.switch_mode == "ENTRY":
            layout.prop(self, "step_frames")
            layout.prop(self, "fade_mode", text="")
            if self.fade_mode != "NONE":
                layout.prop(self, "fade_frames")

    def build_code(self, inputs):
        out_var = self.output_var("Value")
        count = max(1, int(self.input_count))
        names = self._value_socket_names(count)
        values = [inputs.get(name, "0.0") for name in names]
        switch_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        if self.switch_mode == "VALUE":
            switch_value = inputs.get("Switch ID", "0.0")
            return "\n".join(
                [
                    f"_choices_{switch_id} = [{', '.join(values)}]",
                    f"_idx_{switch_id} = int({switch_value}) % {count}",
                    f"{out_var} = _choices_{switch_id}[_idx_{switch_id}]",
                ]
            )
        entry = inputs.get("Entry", "_entry_empty()")
        return "\n".join(
            [
                f"_choices_{switch_id} = [{', '.join(values)}]",
                (
                    f"_idx_{switch_id}, _fade_{switch_id} = "
                    f"_switch_eval_fade({entry}, frame, {int(self.step_frames)}, {count}, "
                    f"{self.fade_mode!r}, {float(self.fade_frames)})"
                ),
                f"{out_var} = _choices_{switch_id}[_idx_{switch_id}] * _fade_{switch_id}",
            ]
        )
