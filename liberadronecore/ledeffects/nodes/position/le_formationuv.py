import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDFormationUVNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Project position into the DroneSystem bounds to produce relative coords."""

    bl_idname = "LDLEDFormationUVNode"
    bl_label = "Formation UV"
    bl_icon = "OUTLINER_OB_GROUP_INSTANCE"

    static: bpy.props.BoolProperty(
        name="Static",
        description="Reuse cached formation bounds while the effect runs",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "X")
        self.outputs.new("NodeSocketFloat", "Y")
        self.outputs.new("NodeSocketFloat", "Z")

    def draw_buttons(self, context, layout):
        layout.prop(self, "static")

    def build_code(self, inputs):
        out_x = self.output_var("X")
        out_y = self.output_var("Y")
        out_z = self.output_var("Z")
        cache_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_rel = _formation_bbox_relpos((pos[0], pos[1], pos[2]), {cache_key!r}, {bool(self.static)!r})",
                f"{out_x} = _rel[0]",
                f"{out_y} = _rel[1]",
                f"{out_z} = _rel[2]",
            ]
        )
