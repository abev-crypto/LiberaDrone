import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDRandomNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Randomize the input color based on a probability."""

    bl_idname = "LDLEDRandomNode"
    bl_label = "LED Random"
    bl_icon = "RNDCURVE"

    seed: bpy.props.FloatProperty(
        name="Seed",
        default=0.0,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        chance = self.inputs.new("NodeSocketFloat", "Chance")
        chance.default_value = 0.0
        seed = self.inputs.new("NodeSocketFloat", "Seed")
        seed.default_value = 0.0
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "seed")

    def build_code(self, inputs):
        chance = inputs.get("Chance", "0.0")
        seed = inputs.get("Seed", repr(float(self.seed)))
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_var = self.output_var("Color")
        rand_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_rand_{rand_id} = _rand01(idx, frame, {seed})",
                f"if _rand_{rand_id} < ({chance}):",
                f"    _r_{rand_id} = _rand01(idx, frame, {seed} + 1.0)",
                f"    _g_{rand_id} = _rand01(idx, frame, {seed} + 2.0)",
                f"    _b_{rand_id} = _rand01(idx, frame, {seed} + 3.0)",
                f"    {out_var} = (_r_{rand_id}, _g_{rand_id}, _b_{rand_id}, 1.0)",
                "else:",
                f"    {out_var} = {color}",
            ]
        )
