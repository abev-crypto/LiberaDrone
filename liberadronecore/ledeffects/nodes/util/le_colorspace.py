import bpy
import colorsys
import numpy as np
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


@register_runtime_function
def _rgb_to_hsv(color):
    r, g, b, a = color
    if isinstance(r, np.ndarray) or isinstance(g, np.ndarray) or isinstance(b, np.ndarray):
        r = np.asarray(r)
        g = np.asarray(g)
        b = np.asarray(b)
        maxc = np.maximum.reduce([r, g, b])
        minc = np.minimum.reduce([r, g, b])
        v = maxc
        delta = maxc - minc
        s = np.where(maxc == 0.0, 0.0, delta / maxc)
        h = np.zeros_like(maxc)
        mask = delta > 0.0
        mask_r = mask & (maxc == r)
        mask_g = mask & (maxc == g)
        mask_b = mask & (maxc == b)
        h[mask_r] = ((g - b) / delta)[mask_r] % 6.0
        h[mask_g] = ((b - r) / delta)[mask_g] + 2.0
        h[mask_b] = ((r - g) / delta)[mask_b] + 4.0
        h = (h / 6.0) % 1.0
        return h, s, v, a
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h, s, v, a


@register_runtime_function
def _hsv_to_rgb(color):
    h, s, v, a = color
    if isinstance(h, np.ndarray) or isinstance(s, np.ndarray) or isinstance(v, np.ndarray):
        h = np.asarray(h)
        s = np.asarray(s)
        v = np.asarray(v)
        h = (h % 1.0) * 6.0
        i = np.floor(h).astype(np.int32)
        f = h - i
        p = v * (1.0 - s)
        q = v * (1.0 - f * s)
        t = v * (1.0 - (1.0 - f) * s)
        i_mod = np.mod(i, 6)
        r = np.select(
            [i_mod == 0, i_mod == 1, i_mod == 2, i_mod == 3, i_mod == 4, i_mod == 5],
            [v, q, p, p, t, v],
            default=v,
        )
        g = np.select(
            [i_mod == 0, i_mod == 1, i_mod == 2, i_mod == 3, i_mod == 4, i_mod == 5],
            [t, v, v, q, p, p],
            default=v,
        )
        b = np.select(
            [i_mod == 0, i_mod == 1, i_mod == 2, i_mod == 3, i_mod == 4, i_mod == 5],
            [p, p, t, v, v, q],
            default=v,
        )
        return r, g, b, a
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return r, g, b, a


@register_runtime_function
def _srgb_to_linear_channel(c: float) -> float:
    if isinstance(c, np.ndarray):
        return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


@register_runtime_function
def _linear_to_srgb_channel(c: float) -> float:
    if isinstance(c, np.ndarray):
        return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1.0 / 2.4)) - 0.055)
    if c <= 0.0031308:
        return c * 12.92
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


@register_runtime_function
def _srgb_to_linear(color):
    r, g, b, a = color
    return (
        _srgb_to_linear_channel(r),
        _srgb_to_linear_channel(g),
        _srgb_to_linear_channel(b),
        a,
    )


@register_runtime_function
def _linear_to_srgb(color):
    r, g, b, a = color
    return (
        _linear_to_srgb_channel(r),
        _linear_to_srgb_channel(g),
        _linear_to_srgb_channel(b),
        a,
    )


@register_runtime_function
def _to_grayscale(color):
    r, g, b, a = color
    gray = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return gray, gray, gray, a


class LDLEDColorSpaceNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Convert between color spaces or to grayscale."""

    bl_idname = "LDLEDColorSpaceNode"
    bl_label = "Color Space"
    bl_icon = "IMAGE"

    mode_items = [
        ("SRGB_TO_LINEAR", "sRGB to Linear", "Convert sRGB to linear"),
        ("LINEAR_TO_SRGB", "Linear to sRGB", "Convert linear to sRGB"),
        ("GRAYSCALE", "Grayscale", "Convert to grayscale"),
    ]

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="SRGB_TO_LINEAR",
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")

    def build_code(self, inputs):
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_var = self.output_var("Color")
        if self.mode == "LINEAR_TO_SRGB":
            return f"{out_var} = _linear_to_srgb({color})"
        if self.mode == "GRAYSCALE":
            return f"{out_var} = _to_grayscale({color})"
        return f"{out_var} = _srgb_to_linear({color})"
