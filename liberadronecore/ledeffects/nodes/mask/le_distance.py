import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDDistanceMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask by distance to a mesh bounds."""

    bl_idname = "LDLEDDistanceMaskNode"
    bl_label = "LED Distance Mask"
    bl_icon = "MOD_SCREW"

    target_object: bpy.props.PointerProperty(
        name="Mesh",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    max_distance: bpy.props.FloatProperty(
        name="Max Distance",
        default=1.0,
        min=0.0,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")
        layout.prop(self, "max_distance")

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        obj_name = self.target_object.name if self.target_object else ""
        max_dist = max(0.0001, float(self.max_distance))
        return "\n".join(
            [
                f"_dist = _distance_to_mesh_bbox({obj_name!r}, (pos[0], pos[1], pos[2]))",
                f"{out_var} = _clamp01(1.0 - (_dist / {max_dist!r}))",
            ]
        )
