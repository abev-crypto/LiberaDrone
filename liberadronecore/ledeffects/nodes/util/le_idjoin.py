import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


@register_runtime_function
def _idjoin_ids(value):
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {int(v) for v in value if int(v) >= 0}
    return {int(value)}


@register_runtime_function
def _idjoin_universe():
    mask = le_meshinfo._collection_formation_ids("Formation", True)
    return {idx for idx, enabled in enumerate(mask) if enabled}


@register_runtime_function
def _idjoin_apply(mode: str, values):
    mode = (mode or "OR").upper()
    current = None
    for val in values:
        ids = _idjoin_ids(val)
        if current is None:
            current = ids
            continue
        if mode == "AND":
            current = current & ids
        elif mode == "XOR":
            current = current ^ ids
        elif mode == "NAND":
            current = _idjoin_universe() - (current & ids)
        elif mode == "NOR":
            current = _idjoin_universe() - (current | ids)
        else:
            current = current | ids
    if not current:
        return []
    return sorted(current)


class LDLEDIDJoinNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Join ID lists with boolean operations."""

    bl_idname = "LDLEDIDJoinNode"
    bl_label = "ID Join"
    bl_icon = "NODETREE"

    mode_items = [
        ("OR", "OR", "Union of IDs"),
        ("NOR", "NOR", "NOT of union"),
        ("XOR", "XOR", "Symmetric difference"),
        ("AND", "AND", "Intersection of IDs"),
        ("NAND", "NAND", "NOT of intersection"),
    ]

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="OR",
        update=lambda self, _context: self._sync_inputs(),
        options={'LIBRARY_EDITABLE'},
    )

    input_count: bpy.props.IntProperty(
        name="Inputs",
        default=2,
        min=2,
        max=8,
        update=lambda self, _context: self._sync_inputs(),
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDIDSocket", "ID 1")
        self.inputs.new("LDLEDIDSocket", "ID 2")
        self.outputs.new("LDLEDIDSocket", "IDs")
        self._sync_inputs()

    def update(self):
        self._sync_inputs()

    def _id_socket_names(self, count: int) -> list[str]:
        count = max(1, int(count))
        return [f"ID {idx + 1}" for idx in range(count)]

    def _sync_inputs(self):
        desired_count = max(2, int(self.input_count))
        desired_names = self._id_socket_names(desired_count)

        for name in desired_names:
            if self.inputs.get(name) is None:
                self.inputs.new("LDLEDIDSocket", name)

        for sock in list(self.inputs):
            if not sock.name.startswith("ID "):
                continue
            if sock.name not in desired_names:
                self.inputs.remove(sock)

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")
        layout.prop(self, "input_count")

    def build_code(self, inputs):
        count = max(2, int(self.input_count))
        names = self._id_socket_names(count)
        values = [inputs.get(name, "None") for name in names]
        out_var = self.output_var("IDs")
        return f"{out_var} = _idjoin_apply({self.mode!r}, [{', '.join(values)}])"
