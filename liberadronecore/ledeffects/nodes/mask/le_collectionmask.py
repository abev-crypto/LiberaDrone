import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDCollectionMaskNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Mask by formation_id list from a collection."""

    bl_idname = "LDLEDCollectionMaskNode"
    bl_label = "Collection Mask"
    bl_icon = "OUTLINER_COLLECTION"

    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        options={'LIBRARY_EDITABLE'},
    )

    use_children: bpy.props.BoolProperty(
        name="Include Children",
        default=True,
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
    remap_rows: bpy.props.BoolProperty(
        name="Remap Rows",
        description="Match collection IDs using the current drone index mapping",
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
        self.inputs.new("NodeSocketCollection", "Collection")
        value = self.inputs.new("NodeSocketFloat", "Value")
        value.default_value = 1.0
        try:
            value.min_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Mask")
        self.outputs.new("LDLEDIDSocket", "IDs")

    def draw_buttons(self, context, layout):
        op = layout.operator("ldled.collectionmask_create_collection", text="From Selection")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        layout.prop(self, "use_children")
        layout.prop(self, "combine_mode", text="")
        layout.prop(self, "invert")
        layout.prop(self, "remap_rows")
        row = layout.row()
        row.enabled = self.remap_rows
        row.prop(self, "remap_frame")

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        out_ids = self.output_var("IDs")
        col_socket = self.inputs.get("Collection")
        col_name = inputs.get("Collection", "None")
        if (col_socket is None or not col_socket.is_linked) and col_name in {"None", "''"} and self.collection:
            col_name = repr(self.collection.name)
        value = inputs.get("Value", "1.0")
        ids_var = f"_col_ids_{self.codegen_id()}_{int(self.as_pointer())}"
        list_var = f"_col_list_{self.codegen_id()}_{int(self.as_pointer())}"
        row_var = f"_col_row_{self.codegen_id()}_{int(self.as_pointer())}"
        if self.remap_rows:
            if int(self.remap_frame) >= 0:
                row_expr = f"_cat_row_index_at_frame(idx, {int(self.remap_frame)}, 0)"
            else:
                row_expr = "_cat_row_index(idx, 0)"
        else:
            row_expr = "idx"
        base_expr = f"{ids_var}[{row_var}] if {row_var} < len({ids_var}) else 0.0"
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
                f"{ids_var} = _collection_formation_ids({col_name}, {bool(self.use_children)!r})",
                f"{list_var} = [i for i, v in enumerate({ids_var}) if v]",
                f"{row_var} = {row_expr}",
                f"{out_ids} = {list_var}",
                f"{out_var} = {expr}",
            ]
        )


def _unique_collection_name(base: str) -> str:
    if not bpy.data.collections.get(base):
        return base
    idx = 1
    while True:
        name = f"{base}.{idx:03d}"
        if not bpy.data.collections.get(name):
            return name
        idx += 1
