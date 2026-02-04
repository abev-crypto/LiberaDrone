import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDInsideMeshNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask based on whether a point is inside a mesh bounds."""

    bl_idname = "LDLEDInsideMeshNode"
    bl_label = "Inside Mesh"
    bl_icon = "MESH_CUBE"

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
        mesh = self.inputs.new("NodeSocketObject", "Mesh")
        value = self.inputs.new("NodeSocketFloat", "Value")
        value.default_value = 1.0
        try:
            value.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        op = layout.operator("ldled.insidemesh_create_mesh", text="From Selection")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        layout.prop(self, "combine_mode", text="")
        layout.prop(self, "invert")

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        obj_expr = inputs.get("Mesh", "''")
        value = inputs.get("Value", "1.0")
        base_expr = f"1.0 if _point_in_mesh_bbox({obj_expr}, (pos[0], pos[1], pos[2])) else 0.0"
        if self.invert:
            base_expr = f"(1.0 - ({base_expr}))"
        if self.combine_mode == "ADD":
            expr = f"_clamp01(({base_expr}) + ({value}))"
        elif self.combine_mode == "SUB":
            expr = f"_clamp01(({base_expr}) - ({value}))"
        else:
            expr = f"_clamp01(({base_expr}) * ({value}))"
        return f"{out_var} = {expr}"




