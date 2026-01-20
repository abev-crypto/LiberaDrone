import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDFadeMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Fade a value in/out based on entry timing."""

    bl_idname = "LDLEDFadeMaskNode"
    bl_label = "Fade In/Out"
    bl_icon = "IPO_SINE"

    direction_items = [
        ("IN", "In", "Fade in from 0 to 1"),
        ("OUT", "Out", "Fade out from 1 to 0"),
        ("IN_OUT", "In/Out", "Fade in then out"),
    ]

    ease_items = [
        ("LINEAR", "Linear", "Linear progress"),
        ("EASE_IN", "Ease In", "Slow start, fast end"),
        ("EASE_OUT", "Ease Out", "Fast start, slow end"),
        ("EASE_IN_OUT", "Ease In Out", "Slow start and end"),
    ]

    combine_items = [
        ("MULTIPLY", "Multiply", "Multiply the mask with the value"),
        ("ADD", "Add", "Add the value to the mask"),
        ("SUB", "Subtract", "Subtract the value from the mask"),
    ]

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=direction_items,
        default="IN",
        options={'LIBRARY_EDITABLE'},
    )

    ease_mode: bpy.props.EnumProperty(
        name="Ease",
        items=ease_items,
        default="LINEAR",
        options={'LIBRARY_EDITABLE'},
    )

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
        self.inputs.new("LDLEDEntrySocket", "Entry")
        duration = self.inputs.new("NodeSocketInt", "Duration")
        value = self.inputs.new("NodeSocketFloat", "Value")
        duration.default_value = 1
        value.default_value = 1.0
        try:
            duration.min_value = 0
            value.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "direction", text="")
        layout.prop(self, "ease_mode", text="")
        layout.prop(self, "combine_mode", text="")
        layout.prop(self, "invert")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        duration = inputs.get("Duration", "0.0")
        value = inputs.get("Value", "1.0")
        out_var = self.output_var("Value")
        base_expr = f"_entry_fade({entry}, frame, {duration}, {self.ease_mode!r}, {self.direction!r})"
        if self.invert:
            base_expr = f"(1.0 - ({base_expr}))"
        if self.combine_mode == "ADD":
            expr = f"_clamp01(({base_expr}) + ({value}))"
        elif self.combine_mode == "SUB":
            expr = f"_clamp01(({base_expr}) - ({value}))"
        else:
            expr = f"_clamp01(({base_expr}) * ({value}))"
        return f"{out_var} = {expr}"
