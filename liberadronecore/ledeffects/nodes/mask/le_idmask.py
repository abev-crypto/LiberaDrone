import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.le_nodecategory import LDLED_Register
from liberadronecore.ledeffects.util import idmask as idmask_util


class LDLEDIDMaskItem(bpy.types.PropertyGroup, LDLED_Register):
    value: bpy.props.IntProperty(
        name="ID",
        default=0,
        min=0,
        options={'LIBRARY_EDITABLE'},
    )



class LDLEDIDMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask by formation_id attribute."""

    bl_idname = "LDLEDIDMaskNode"
    bl_label = "ID Mask"
    bl_icon = "SORTSIZE"

    combine_items = [
        ("MULTIPLY", "Multiply", "Multiply the mask with the value"),
        ("ADD", "Add", "Add the value to the mask"),
        ("SUB", "Subtract", "Subtract the value from the mask"),
    ]

    formation_id: bpy.props.IntProperty(
        name="Formation ID",
        default=-1,
        min=-1,
        options={'LIBRARY_EDITABLE'},
    )
    use_custom_ids: bpy.props.BoolProperty(
        name="Use Custom IDs",
        default=False,
        options={'HIDDEN'},
    )
    ids: bpy.props.CollectionProperty(type=LDLEDIDMaskItem, options={'LIBRARY_EDITABLE'})
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
    remap_rows: bpy.props.BoolProperty(
        name="Remap Rows",
        description="Match IDs using the current drone index mapping",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )
    remap_frame: bpy.props.IntProperty(
        name="Remap Frame",
        description="Use formation IDs from this frame when remapping rows",
        default=-1,
        options={'LIBRARY_EDITABLE'},
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
        self.outputs.new("LDLEDIDSocket", "IDs")

    def draw_buttons(self, context, layout):
        if self.use_custom_ids:
            ids = idmask_util._node_effective_ids(self, include_legacy=False)
            label = ", ".join(str(i) for i in ids) if ids else "-"
            layout.label(text=f"IDs: {label}")
        else:
            if int(self.formation_id) < 0:
                layout.label(text="ID: -")
            else:
                layout.label(text=f"ID: {int(self.formation_id)}")
        row = layout.row(align=True)
        op = row.operator("ldled.idmask_add_selection", text="Add Selection")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op = row.operator("ldled.idmask_remove_selection", text="Remove Selection")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op = layout.operator("ldled.select_formation_ids", text="Select IDs")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        layout.prop(self, "combine_mode", text="")
        layout.prop(self, "invert")
        layout.prop(self, "remap_rows")
        row = layout.row(align=True)
        row.enabled = self.remap_rows
        row.prop(self, "remap_frame")
        op = row.operator("ldled.remapframe_fill_current", text="Now")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        out_ids = self.output_var("IDs")
        ids = idmask_util._node_effective_ids(self, include_legacy=not self.use_custom_ids)
        value = inputs.get("Value", "1.0")
        fid_var = f"_fid_{self.codegen_id()}_{int(self.as_pointer())}"
        if self.remap_rows:
            if int(self.remap_frame) >= 0:
                fid_expr = f"_cat_ref_fid_locked(idx, frame, {int(self.remap_frame)})"
            else:
                fid_expr = "_cat_ref_fid(idx)"
        else:
            fid_expr = "_formation_id(idx)"
        ids_expr = repr(ids)
        if not ids:
            base_expr = "0.0"
        elif len(ids) == 1:
            base_expr = f"1.0 if {fid_var} == {ids[0]} else 0.0"
        else:
            base_expr = f"1.0 if {fid_var} in {tuple(ids)} else 0.0"
        if self.invert:
            base_expr = f"(1.0 - ({base_expr}))"
        if self.combine_mode == "ADD":
            expr = f"_clamp01(({base_expr}) + ({value}))"
        elif self.combine_mode == "SUB":
            expr = f"_clamp01(({base_expr}) - ({value}))"
        else:
            expr = f"_clamp01(({base_expr}) * ({value}))"
        return "\n".join(
            [
                f"{fid_var} = {fid_expr}",
                f"{out_ids} = {ids_expr}",
                f"{out_var} = {expr}",
            ]
        )


