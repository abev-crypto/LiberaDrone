import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDDistanceMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask by distance to a mesh bounds."""

    bl_idname = "LDLEDDistanceMaskNode"
    bl_label = "Distance Mask"
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

    combine_items = [
        ("MULTIPLY", "Multiply", "Multiply the mask with the value"),
        ("ADD", "Add", "Add the value to the mask"),
        ("SUB", "Subtract", "Subtract the value from the mask"),
    ]

    combine_mode: bpy.props.EnumProperty(
        name="Combine",
        items=combine_items,
        default="MULTIPLY",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        value = self.inputs.new("NodeSocketFloat", "Value")
        value.default_value = 1.0
        try:
            value.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")
        layout.prop(self, "max_distance")
        layout.prop(self, "combine_mode", text="")

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        obj_name = self.target_object.name if self.target_object else ""
        max_dist = max(0.0001, float(self.max_distance))
        value = inputs.get("Value", "1.0")
        base_expr = f"_clamp01(1.0 - (_dist / {max_dist!r}))"
        if self.combine_mode == "ADD":
            expr = f"_clamp01(({base_expr}) + ({value}))"
        elif self.combine_mode == "SUB":
            expr = f"_clamp01(({base_expr}) - ({value}))"
        else:
            expr = f"_clamp01(({base_expr}) * ({value}))"
        return "\n".join(
            [
                f"_dist = _distance_to_mesh_bbox({obj_name!r}, (pos[0], pos[1], pos[2]))",
                f"{out_var} = {expr}",
            ]
        )
