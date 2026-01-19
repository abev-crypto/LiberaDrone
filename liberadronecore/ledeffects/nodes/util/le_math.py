import bpy
import math
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


@register_runtime_function
def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


@register_runtime_function
def _clamp(x: float, low: float, high: float) -> float:
    if x < low:
        return low
    if x > high:
        return high
    return x


@register_runtime_function
def _fract(x: float) -> float:
    return x - math.floor(x)


@register_runtime_function
def _loop_factor(value: float, mode: str = "REPEAT") -> float:
    mode = (mode or "REPEAT").upper()
    frac = _fract(float(value))
    if mode in {"PINGPONG", "PING_PONG", "PING-PONG"}:
        return 1.0 - abs(2.0 * frac - 1.0)
    return frac


@register_runtime_function
def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@register_runtime_function
def _ease(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


@register_runtime_function
def _ease_in(t: float) -> float:
    t = _clamp01(t)
    return t * t


@register_runtime_function
def _ease_out(t: float) -> float:
    t = _clamp01(t)
    inv = 1.0 - t
    return 1.0 - inv * inv


@register_runtime_function
def _ease_in_out(t: float) -> float:
    t = _clamp01(t)
    return _ease(t)


@register_runtime_function
def _apply_ease(t: float, mode: str) -> float:
    mode = (mode or "LINEAR").upper()
    if mode in {"EASEIN", "EASE_IN"}:
        return _ease_in(t)
    if mode in {"EASEOUT", "EASE_OUT"}:
        return _ease_out(t)
    if mode in {"EASEINOUT", "EASE_IN_OUT"}:
        return _ease_in_out(t)
    return _clamp01(t)


class LDLEDMathNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Basic math node for LED intensities."""

    bl_idname = "LDLEDMathNode"
    bl_label = "Math"
    bl_icon = "MODIFIER"

    math_items = [
        ("ADD", "Add", "Add inputs"),
        ("SUBTRACT", "Subtract", "Subtract B from A"),
        ("MULTIPLY", "Multiply", "Multiply inputs"),
        ("DIVIDE", "Divide", "Divide A by B"),
        ("MAX", "Max", "Maximum of A and B"),
        ("MIN", "Min", "Minimum of A and B"),
        ("STEP", "Step", "0 if A < B else 1"),
        ("SATURATE", "Saturate", "Clamp A between 0 and 1"),
        ("FRACTION", "Fraction", "Fractional part of A"),
        ("FLOOR", "Floor", "Floor A"),
        ("CEIL", "Ceil", "Ceil A"),
        ("SINE", "Sine", "Sine of A"),
        ("COSINE", "Cosine", "Cosine of A"),
        ("ONE_MINUS", "One Minus", "1 - A"),
    ]

    single_input_ops = {
        "SATURATE",
        "FRACTION",
        "FLOOR",
        "CEIL",
        "SINE",
        "COSINE",
        "ONE_MINUS",
    }

    operation: bpy.props.EnumProperty(
        name="Operation",
        items=math_items,
        default="ADD",
        update=lambda self, _context: self._sync_inputs(),
    )

    clamp_result: bpy.props.BoolProperty(
        name="Clamp",
        description="Clamp the result between 0 and 1",
        default=False,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "Value A")
        self.inputs.new("NodeSocketFloat", "Value B")
        self.outputs.new("NodeSocketFloat", "Value")
        self._sync_inputs()

    def update(self):
        self._sync_inputs()

    def _sync_inputs(self):
        socket = self.inputs.get("Value B")
        if socket is not None:
            socket.hide = self.operation in self.single_input_ops

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")
        layout.prop(self, "clamp_result")

    def build_code(self, inputs):
        a = inputs.get("Value A", "0.0")
        b = inputs.get("Value B", "0.0")
        out_var = self.output_var("Value")
        op = self.operation
        if op == "ADD":
            expr = f"({a}) + ({b})"
        elif op == "SUBTRACT":
            expr = f"({a}) - ({b})"
        elif op == "MULTIPLY":
            expr = f"({a}) * ({b})"
        elif op == "DIVIDE":
            expr = f"({a}) / ({b}) if ({b}) != 0.0 else 0.0"
        elif op == "MAX":
            expr = f"({a}) if ({a}) > ({b}) else ({b})"
        elif op == "MIN":
            expr = f"({a}) if ({a}) < ({b}) else ({b})"
        elif op == "STEP":
            expr = f"1.0 if ({a}) >= ({b}) else 0.0"
        elif op == "SATURATE":
            expr = f"_clamp01({a})"
        elif op == "FRACTION":
            expr = f"({a}) - float(int({a}))"
        elif op == "FLOOR":
            expr = f"math.floor({a})"
        elif op == "CEIL":
            expr = f"math.ceil({a})"
        elif op == "SINE":
            expr = f"math.sin({a})"
        elif op == "COSINE":
            expr = f"math.cos({a})"
        elif op == "ONE_MINUS":
            expr = f"1.0 - ({a})"
        else:
            expr = f"({a})"
        if self.clamp_result:
            expr = f"_clamp01({expr})"
        return f"{out_var} = {expr}"
