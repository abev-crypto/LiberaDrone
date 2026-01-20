import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDCombineNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Combine channels into a color (RGB or HSV)."""

    bl_idname = "LDLEDCombineNode"
    bl_label = "Combine"
    bl_icon = "SEQ_CHROMA_SCOPE"

    mode_items = [
        ("RGB", "RGB", "Combine RGB channels"),
        ("HSV", "HSV", "Combine HSV channels"),
    ]

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="RGB",
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "X")
        self.inputs.new("NodeSocketFloat", "Y")
        self.inputs.new("NodeSocketFloat", "Z")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")

    def build_code(self, inputs):
        x = inputs.get("X", "0.0")
        y = inputs.get("Y", "0.0")
        z = inputs.get("Z", "0.0")
        a = "1.0"
        out_var = self.output_var("Color")
        if self.mode == "HSV":
            combine_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
            return "\n".join(
                [
                    f"_rgb_{combine_id} = _hsv_to_rgb(({x}, {y}, {z}, {a}))",
                    f"{out_var} = _rgb_{combine_id}",
                ]
            )
        return f"{out_var} = ({x}, {y}, {z}, {a})"
