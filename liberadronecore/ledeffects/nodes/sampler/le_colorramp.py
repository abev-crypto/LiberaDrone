import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDColorRampNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Simple two-point color ramp."""

    bl_idname = "LDLEDColorRampNode"
    bl_label = "LED Color Ramp"
    bl_icon = "NODE_COMPOSITING"

    color_a: bpy.props.FloatVectorProperty(
        name="Color A",
        subtype='COLOR',
        default=(0.0, 0.0, 0.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
    )

    color_b: bpy.props.FloatVectorProperty(
        name="Color B",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        factor = self.inputs.new("NodeSocketFloat", "Factor")
        factor.default_value = 0.0
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "color_a", text="")
        layout.prop(self, "color_b", text="")

    def build_code(self, inputs):
        factor = inputs.get("Factor", "0.0")
        out_var = self.output_var("Color")
        a = tuple(float(c) for c in self.color_a)
        b = tuple(float(c) for c in self.color_b)
        ramp_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_t_{ramp_id} = _clamp01({factor})",
                f"{out_var} = (",
                f"    ({a}[0] * (1.0 - _t_{ramp_id})) + ({b}[0] * _t_{ramp_id}),",
                f"    ({a}[1] * (1.0 - _t_{ramp_id})) + ({b}[1] * _t_{ramp_id}),",
                f"    ({a}[2] * (1.0 - _t_{ramp_id})) + ({b}[2] * _t_{ramp_id}),",
                f"    ({a}[3] * (1.0 - _t_{ramp_id})) + ({b}[3] * _t_{ramp_id}),",
                ")",
            ]
        )
