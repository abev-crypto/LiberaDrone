import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDTimeMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Output a 0-1 mask based on entry progress."""

    bl_idname = "LDLEDTimeMaskNode"
    bl_label = "Time"
    bl_icon = "TIME"

    mode_items = [
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

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="LINEAR",
        options={'LIBRARY_EDITABLE'},
    )

    combine_mode: bpy.props.EnumProperty(
        name="Combine",
        items=combine_items,
        default="MULTIPLY",
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        value = self.inputs.new("NodeSocketFloat", "Value")
        value.default_value = 1.0
        try:
            value.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Factor")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")
        layout.prop(self, "combine_mode", text="")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        value = inputs.get("Value", "1.0")
        out_var = self.output_var("Factor")
        base_expr = f"_entry_progress({entry}, frame, {self.mode!r})"
        if self.combine_mode == "ADD":
            expr = f"_clamp01(({base_expr}) + ({value}))"
        elif self.combine_mode == "SUB":
            expr = f"_clamp01(({base_expr}) - ({value}))"
        else:
            expr = f"_clamp01(({base_expr}) * ({value}))"
        return f"{out_var} = {expr}"
