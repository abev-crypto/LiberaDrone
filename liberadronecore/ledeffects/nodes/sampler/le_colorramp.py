import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDColorRampNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Color ramp with Blender-style interpolation."""

    bl_idname = "LDLEDColorRampNode"
    bl_label = "LED Color Ramp"
    bl_icon = "NODE_COMPOSITING"

    color_ramp_tex: bpy.props.PointerProperty(
        name="Color Ramp",
        type=bpy.types.Texture,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        factor = self.inputs.new("NodeSocketFloat", "Factor")
        factor.default_value = 0.0
        self.outputs.new("NodeSocketColor", "Color")
        if self.color_ramp_tex is None:
            tex = bpy.data.textures.new(name="LDLEDColorRamp", type='BLEND')
            tex.use_color_ramp = True
            self.color_ramp_tex = tex

    def draw_buttons(self, context, layout):
        if self.color_ramp_tex is None:
            layout.label(text="Color ramp not initialized")
            return
        layout.template_color_ramp(self.color_ramp_tex, "color_ramp", expand=True)

    def build_code(self, inputs):
        factor = inputs.get("Factor", "0.0")
        out_var = self.output_var("Color")
        ramp = self.color_ramp_tex.color_ramp if self.color_ramp_tex else None
        elements = []
        if ramp:
            for element in ramp.elements:
                elements.append((float(element.position), tuple(float(c) for c in element.color)))
        interpolation = ramp.interpolation if ramp else "LINEAR"
        color_mode = ramp.color_mode if ramp else "RGB"
        return f"{out_var} = _color_ramp_eval({elements!r}, {interpolation!r}, {color_mode!r}, {factor})"
