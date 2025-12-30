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
        self.inputs.new("NodeSocketFloat", "Value")
        self.outputs.new("NodeSocketFloat", "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "seed")

    def build_code(self, inputs):
        chance = inputs.get("Chance", "0.0")
        seed = inputs.get("Seed", repr(float(self.seed)))
        value = inputs.get("Value", "0.0")
        out_var = self.output_var("Value")
        legacy_color = None
        for sock in getattr(self, "outputs", []):
            if sock.name == "Color":
                legacy_color = self.output_var("Color")
                break
        rand_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        color_assign = ""
        if legacy_color:
            color_assign = f"    {legacy_color} = ({out_var}, {out_var}, {out_var}, 1.0)"
        return "\n".join(
            [
                f"_rand_{rand_id} = _rand01_static(idx, {seed})",
                f"if _rand_{rand_id} < ({chance}):",
                f"    {out_var} = _rand01_static(idx, {seed} + 1.0)",
                color_assign,
                "else:",
                f"    {out_var} = {value}",
                color_assign,
            ]
        )
