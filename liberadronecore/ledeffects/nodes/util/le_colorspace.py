import bpy
import colorsys
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


@register_runtime_function
def _rgb_to_hsv(color):
    r, g, b, a = color
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h, s, v, a


@register_runtime_function
def _hsv_to_rgb(color):
    h, s, v, a = color
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return r, g, b, a


@register_runtime_function
def _srgb_to_linear_channel(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


@register_runtime_function
def _linear_to_srgb_channel(c: float) -> float:
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
