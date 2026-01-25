import bpy
import math
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


@register_runtime_function
def _rand01(idx: int, frame: float, seed: float) -> float:
    value = math.sin(idx * 12.9898 + frame * 78.233 + seed * 37.719)
    return value - math.floor(value)


@register_runtime_function
def _rand01_static(idx: int, seed: float) -> float:
    value = math.sin(idx * 12.9898 + seed * 78.233)
    return value - math.floor(value)


class LDLEDRandomNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Randomize the input value based on a probability."""

    bl_idname = "LDLEDRandomNode"
    bl_label = "Random"
    bl_icon = "RNDCURVE"

    seed: bpy.props.FloatProperty(
        name="Seed",
        default=0.0,
        options={'LIBRARY_EDITABLE'},
    )

    combine_items = [
        ("MULTIPLY", "Multiply", "Multiply the mask with the value"),
        ("ADD", "Add", "Add the value to the mask"),
        ("SUB", "Subtract", "Subtract the value from the mask"),
    ]

    combine_mode: bpy.props.EnumProperty(
        name="Combine",
        items=combine_items,
        default="MULTIPLY",
        options={'LIBRARY_EDITABLE'},
    )
    invert: bpy.props.BoolProperty(
        name="Invert",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        chance = self.inputs.new("NodeSocketFloat", "Chance")
        chance.default_value = 0.0
        try:
            chance.min_value = 0.0
            chance.max_value = 1.0
        except Exception:
            pass
        seed = self.inputs.new("NodeSocketFloat", "Seed")
        seed.default_value = 0.0
        value = self.inputs.new("NodeSocketFloat", "Value")
        value.default_value = 1.0
        try:
            value.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "combine_mode", text="")
        layout.prop(self, "invert")

    def build_code(self, inputs):
        chance = inputs.get("Chance", "0.0")
        chance_expr = f"max(0.0, min(1.0, {chance}))"
        seed = inputs.get("Seed", repr(float(self.seed)))
        value = inputs.get("Value", "1.0")
        out_var = self.output_var("Value")
        rand_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        base_var = f"_rand_val_{rand_id}"
        base_expr = base_var
        if self.invert:
            base_expr = f"(1.0 - ({base_var}))"
        if self.combine_mode == "ADD":
            expr = f"max(0.0, min(1.0, ({base_expr}) + ({value})))"
        elif self.combine_mode == "SUB":
            expr = f"max(0.0, min(1.0, ({base_expr}) - ({value})))"
        else:
            expr = f"max(0.0, min(1.0, ({base_expr}) * ({value})))"
        lines = [
            f"_rand_{rand_id} = _rand01_static(idx, {seed})",
            f"if _rand_{rand_id} < ({chance_expr}):",
            f"    {base_var} = _rand01_static(idx, {seed} + 1.0)",
            "else:",
            f"    {base_var} = {value}",
            f"{out_var} = {expr}",
        ]
        legacy_color = None
        for sock in getattr(self, "outputs", []):
            if sock.name == "Color":
                legacy_color = self.output_var("Color")
                break
        if legacy_color:
            lines.append(f"{legacy_color} = ({out_var}, {out_var}, {out_var}, 1.0)")
        return "\n".join(lines)
