import bpy
from bpy.props import BoolProperty, EnumProperty

from liberadronecore.formation.fn_nodecategory import FN_Node


_math_items = [
    ("ADD", "Add", "Add inputs"),
    ("SUBTRACT", "Subtract", "Subtract B from A"),
    ("MULTIPLY", "Multiply", "Multiply inputs"),
    ("DIVIDE", "Divide", "Divide A by B"),
    ("MAX", "Max", "Maximum of A and B"),
    ("MIN", "Min", "Minimum of A and B"),
]


class FN_MathNode(bpy.types.Node, FN_Node):
    bl_idname = "FN_MathNode"
    bl_label = "Math"
    bl_icon = "MODIFIER"

    operation: EnumProperty(
        name="Operation",
        items=_math_items,
        default="ADD",
        update=lambda self, context: self._recompute(),
    )

    clamp_result: BoolProperty(
        name="Clamp",
        description="Clamp result to 0..1",
        default=False,
        update=lambda self, context: self._recompute(),
    )

    def init(self, context):
        self.inputs.new("FN_SocketFloat", "A")
        self.inputs.new("FN_SocketFloat", "B")
        self.outputs.new("FN_SocketFloat", "Result")
        self._recompute()

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")
        layout.prop(self, "clamp_result")

    def _get_input_value(self, name: str) -> float:
        sock = self.inputs.get(name)
        if sock is None:
            return 0.0
        return float(getattr(sock, "value", 0.0))

    def _set_output_value(self, value: float) -> None:
        sock = self.outputs.get("Result")
        if sock and hasattr(sock, "value"):
            sock.value = float(value)

    def _recompute(self):
        a = self._get_input_value("A")
        b = self._get_input_value("B")
        op = self.operation

        if op == "ADD":
            res = a + b
        elif op == "SUBTRACT":
            res = a - b
        elif op == "MULTIPLY":
            res = a * b
        elif op == "DIVIDE":
            res = a / b if b != 0 else 0.0
        elif op == "MAX":
            res = max(a, b)
        elif op == "MIN":
            res = min(a, b)
        else:
            res = 0.0

        if self.clamp_result:
            res = max(0.0, min(1.0, res))

        self._set_output_value(res)

    def update(self):
        self._recompute()
