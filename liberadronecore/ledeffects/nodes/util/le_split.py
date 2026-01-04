import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDSplitNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Split a color into channels (RGB or HSV)."""

    bl_idname = "LDLEDSplitNode"
    bl_label = "Split"
    bl_icon = "SEQUENCE_COLOR_01"

    mode_items = [
        ("RGB", "RGB", "Split into RGB channels"),
        ("HSV", "HSV", "Split into HSV channels"),
    ]

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="RGB",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketFloat", "X")
        self.outputs.new("NodeSocketFloat", "Y")
        self.outputs.new("NodeSocketFloat", "Z")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")

    def build_code(self, inputs):
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        out_x = self.output_var("X")
        out_y = self.output_var("Y")
        out_z = self.output_var("Z")
        if self.mode == "HSV":
            split_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
            return "\n".join(
                [
                    f"_hsv_{split_id} = _rgb_to_hsv({color})",
                    f"{out_x} = _hsv_{split_id}[0]",
                    f"{out_y} = _hsv_{split_id}[1]",
                    f"{out_z} = _hsv_{split_id}[2]",
                ]
            )
        return "\n".join(
            [
                f"{out_x} = {color}[0]",
                f"{out_y} = {color}[1]",
                f"{out_z} = {color}[2]",
            ]
        )
