import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDEntrySwitchNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Switch output based on the active entry index."""

    bl_idname = "LDLEDEntrySwitchNode"
    bl_label = "Entry Switch"
    bl_icon = "ARROW_LEFTRIGHT"

    output_type_items = [
        ("VALUE", "Value", "Switch float values"),
        ("COLOR", "Color", "Switch colors"),
        ("MESH", "Mesh", "Switch mesh objects"),
    ]

    output_type: bpy.props.EnumProperty(
        name="Type",
        items=output_type_items,
        default="VALUE",
        update=lambda self, context: self._sync_sockets(),
    )

    length: bpy.props.IntProperty(
        name="Len",
        default=2,
        min=1,
        update=lambda self, context: self._sync_sockets(),
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self._sync_sockets()

    def draw_buttons(self, context, layout):
        layout.prop(self, "output_type", text="")
        layout.prop(self, "length")

    def _socket_type(self) -> str:
        if self.output_type == "COLOR":
            return "NodeSocketColor"
        if self.output_type == "MESH":
            return "NodeSocketObject"
        return "NodeSocketFloat"

    def _default_value(self):
        if self.output_type == "COLOR":
            return (0.0, 0.0, 0.0, 1.0)
        if self.output_type == "MESH":
            return None
        return 0.0

    def _sync_sockets(self):
        entry = self.inputs.get("Entry") if hasattr(self, "inputs") else None
        for sock in list(self.inputs):
            if sock is entry:
                continue
            self.inputs.remove(sock)
        for sock in list(self.outputs):
            self.outputs.remove(sock)

        sock_type = self._socket_type()
        default = self._default_value()
        count = max(1, int(self.length))
        for idx in range(count):
            sock = self.inputs.new(sock_type, f"In {idx + 1}")
            if hasattr(sock, "default_value"):
                try:
                    sock.default_value = default
                except Exception:
                    pass
        self.outputs.new(sock_type, "Out")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Out")
        count = max(1, int(self.length))
        if self.output_type == "COLOR":
            default = "(0.0, 0.0, 0.0, 1.0)"
        elif self.output_type == "MESH":
            default = "None"
        else:
            default = "0.0"
        choices = []
        for idx in range(count):
            sock_name = f"In {idx + 1}"
            choices.append(inputs.get(sock_name, default))
        switch_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        choice_list = ", ".join(choices)
        return "\n".join(
            [
                f"_entry_idx_{switch_id} = _entry_active_index({entry}, frame)",
                f"if _entry_idx_{switch_id} < 0:",
                f"    {out_var} = {default}",
                "else:",
                f"    _sel_{switch_id} = _entry_idx_{switch_id}",
                f"    if _sel_{switch_id} >= {count}:",
                f"        _sel_{switch_id} = {count - 1}",
                f"    _choices_{switch_id} = [{choice_list}]",
                f"    {out_var} = _choices_{switch_id}[_sel_{switch_id}]",
            ]
        )
