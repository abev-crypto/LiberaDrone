import bpy
import colorsys
from typing import Dict, Sequence, Tuple
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp01, _ease, _lerp


_COLOR_RAMP_LUTS: Dict[str, Tuple[Tuple[float, float, float, float], ...]] = {}


def _register_color_ramp_lut(key: str, lut: Sequence[Tuple[float, float, float, float]]) -> None:
    _COLOR_RAMP_LUTS[str(key)] = tuple(tuple(float(c) for c in color) for color in lut)


@register_runtime_function
def _color_ramp_lut(key: str):
    return _COLOR_RAMP_LUTS.get(str(key), ())


@register_runtime_function
def _color_ramp_eval_lut(lut, factor: float):
    if not lut:
        return 0.0, 0.0, 0.0, 1.0
    t = _clamp01(float(factor))
    steps = len(lut)
    if steps <= 1:
        return tuple(lut[0])
    pos = t * (steps - 1)
    idx0 = int(pos)
    if idx0 >= steps - 1:
        return tuple(lut[-1])
    idx1 = idx0 + 1
    local_t = pos - idx0
    c0 = lut[idx0]
    c1 = lut[idx1]
    return (
        _lerp(c0[0], c1[0], local_t),
        _lerp(c0[1], c1[1], local_t),
        _lerp(c0[2], c1[2], local_t),
        _lerp(c0[3], c1[3], local_t),
    )


@register_runtime_function
def _hue_lerp(h0: float, h1: float, t: float) -> float:
    delta = (h1 - h0) % 1.0
    if delta > 0.5:
        delta -= 1.0
    return (h0 + delta * t) % 1.0


@register_runtime_function
def _lerp_color(c0, c1, t: float, mode: str):
    mode = (mode or "RGB").upper()
    if mode == "HSV":
        h0, s0, v0 = colorsys.rgb_to_hsv(c0[0], c0[1], c0[2])
        h1, s1, v1 = colorsys.rgb_to_hsv(c1[0], c1[1], c1[2])
        h = _hue_lerp(h0, h1, t)
        s = _lerp(s0, s1, t)
        v = _lerp(v0, v1, t)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return r, g, b, _lerp(c0[3], c1[3], t)
    if mode == "HSL":
        h0, l0, s0 = colorsys.rgb_to_hls(c0[0], c0[1], c0[2])
        h1, l1, s1 = colorsys.rgb_to_hls(c1[0], c1[1], c1[2])
        h = _hue_lerp(h0, h1, t)
        l = _lerp(l0, l1, t)
        s = _lerp(s0, s1, t)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return r, g, b, _lerp(c0[3], c1[3], t)
    return (
        _lerp(c0[0], c1[0], t),
        _lerp(c0[1], c1[1], t),
        _lerp(c0[2], c1[2], t),
        _lerp(c0[3], c1[3], t),
    )


@register_runtime_function
def _color_ramp_eval(elements, interpolation: str, color_mode: str, factor: float):
    if not elements:
        return 0.0, 0.0, 0.0, 1.0
    t = _clamp01(float(factor))
    elements = sorted(elements, key=lambda e: e[0])
    if t <= elements[0][0]:
        return tuple(elements[0][1])
    if t >= elements[-1][0]:
        return tuple(elements[-1][1])
    interp = (interpolation or "LINEAR").upper()
    for idx in range(len(elements) - 1):
        p0, c0 = elements[idx]
        p1, c1 = elements[idx + 1]
        if p0 <= t <= p1:
            if p1 <= p0:
                return tuple(c1)
            local_t = (t - p0) / (p1 - p0)
            if interp == "CONSTANT":
                return tuple(c0)
            if interp in {"EASE", "CARDINAL", "B_SPLINE"}:
                local_t = _ease(local_t)
            return _lerp_color(tuple(c0), tuple(c1), local_t, color_mode)
    return tuple(elements[-1][1])


@register_runtime_function
def _color_ramp_eval_sorted(elements, interpolation: str, color_mode: str, factor: float):
    if not elements:
        return 0.0, 0.0, 0.0, 1.0
    t = _clamp01(float(factor))
    if t <= elements[0][0]:
        return tuple(elements[0][1])
    if t >= elements[-1][0]:
        return tuple(elements[-1][1])
    interp = (interpolation or "LINEAR").upper()
    for idx in range(len(elements) - 1):
        p0, c0 = elements[idx]
        p1, c1 = elements[idx + 1]
        if p0 <= t <= p1:
            if p1 <= p0:
                return tuple(c1)
            local_t = (t - p0) / (p1 - p0)
            if interp == "CONSTANT":
                return tuple(c0)
            if interp in {"EASE", "CARDINAL", "B_SPLINE"}:
                local_t = _ease(local_t)
            return _lerp_color(tuple(c0), tuple(c1), local_t, color_mode)
    return tuple(elements[-1][1])


class LDLEDColorRampNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Color ramp with Blender-style interpolation."""

    bl_idname = "LDLEDColorRampNode"
    bl_label = "Color Ramp"
    bl_icon = "NODE_COMPOSITING"

    color_ramp_tex: bpy.props.PointerProperty(
        name="Color Ramp",
        type=bpy.types.Texture,
        options={'LIBRARY_EDITABLE'},
    )

    loop_items = [
        ("REPEAT", "Repeat", "Wrap the factor each loop"),
        ("PINGPONG", "Ping-Pong", "Mirror each loop"),
    ]

    loop_mode: bpy.props.EnumProperty(
        name="Loop",
        items=loop_items,
        default="REPEAT",
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        factor = self.inputs.new("NodeSocketFloat", "Factor")
        factor.default_value = 0.0
        loop = self.inputs.new("NodeSocketFloat", "Loop")
        loop.default_value = 1.0
        self.outputs.new("NodeSocketColor", "Color")
        if self.color_ramp_tex is None:
            tex = bpy.data.textures.new(name="LDLEDColorRamp", type='BLEND')
            tex.use_color_ramp = True
            self.color_ramp_tex = tex

    def draw_buttons(self, context, layout):
        if self.color_ramp_tex is None:
            layout.label(text="Color ramp not initialized")
            return
        layout.prop(self, "loop_mode", text="Loop")
        layout.template_color_ramp(self.color_ramp_tex, "color_ramp", expand=True)

    def build_code(self, inputs):
        factor = inputs.get("Factor", "0.0")
        loop = inputs.get("Loop", "1.0")
        out_var = self.output_var("Color")
        ramp = self.color_ramp_tex.color_ramp if self.color_ramp_tex else None
        elements = []
        if ramp:
            for element in ramp.elements:
                elements.append((float(element.position), tuple(float(c) for c in element.color)))
        elements.sort(key=lambda e: e[0])
        interpolation = ramp.interpolation if ramp else "LINEAR"
        color_mode = ramp.color_mode if ramp else "RGB"
        steps = 256
        if not elements:
            lut = [(0.0, 0.0, 0.0, 1.0)] * steps
        else:
            lut = [
                _color_ramp_eval_sorted(elements, interpolation, color_mode, idx / (steps - 1))
                for idx in range(steps)
            ]
        lut_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        _register_color_ramp_lut(lut_key, lut)
        factor_expr = f"_loop_factor(({factor}) * ({loop}), {self.loop_mode!r})"
        return f"{out_var} = _color_ramp_eval_lut(_color_ramp_lut({lut_key!r}), {factor_expr})"
