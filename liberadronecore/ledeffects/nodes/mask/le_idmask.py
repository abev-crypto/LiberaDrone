import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.le_nodecategory import LDLED_Register
from liberadronecore.formation import fn_parse_pairing


class LDLEDIDMaskItem(bpy.types.PropertyGroup, LDLED_Register):
    value: bpy.props.IntProperty(
        name="ID",
        default=0,
        min=0,
        options={'LIBRARY_EDITABLE'},
    )


def _sorted_ids(values) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for val in values:
        try:
            item = int(val)
        except (TypeError, ValueError):
            continue
        if item in seen:
            continue
        seen.add(item)
        ids.append(item)
    ids.sort()
    return ids


def _node_effective_ids(node: "LDLEDIDMaskNode", include_legacy: bool) -> list[int]:
    if getattr(node, "use_custom_ids", False):
        return _sorted_ids([item.value for item in node.ids])
    if not include_legacy:
        return []
    fid = getattr(node, "formation_id", -1)
    if fid < 0:
        return []
    return _sorted_ids([fid])


def _set_node_ids(node: "LDLEDIDMaskNode", ids: list[int]) -> None:
    node.ids.clear()
    for val in ids:
        item = node.ids.add()
        item.value = int(val)


def _read_selected_ids(context) -> tuple[set[int] | None, str | None]:
    obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
        return None, "Select vertices in Edit Mode"
    try:
        import bmesh
    except Exception:
        return None, "bmesh not available"

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    selected = [v for v in bm.verts if v.select]
    if not selected:
        return None, "No selected vertices"

    layer = bm.verts.layers.int.get(fn_parse_pairing.FORMATION_ATTR_NAME)
    if layer is None:
        layer = bm.verts.layers.int.get(fn_parse_pairing.FORMATION_ID_ATTR)
    if layer is not None:
        ids = set()
        for v in selected:
            try:
                ids.add(int(v[layer]))
            except Exception:
                continue
        if ids:
            return ids, None

    attr = obj.data.attributes.get(fn_parse_pairing.FORMATION_ATTR_NAME)
    if attr is None:
        attr = obj.data.attributes.get(fn_parse_pairing.FORMATION_ID_ATTR)
    if attr is None or attr.domain != 'POINT' or attr.data_type != 'INT':
        return None, "formation_id attribute not found"

    ids = set()
    for v in selected:
        if v.index >= len(attr.data):
            continue
        try:
            ids.add(int(attr.data[v.index].value))
        except Exception:
            continue
    if not ids:
        return None, "formation_id data missing"
    return ids, None


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
            ids = _node_effective_ids(self, include_legacy=False)
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
        layout.prop(self, "combine_mode", text="")
        layout.prop(self, "invert")

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        out_ids = self.output_var("IDs")
        ids = _node_effective_ids(self, include_legacy=not self.use_custom_ids)
        value = inputs.get("Value", "1.0")
        fid_var = f"_fid_{self.codegen_id()}_{int(self.as_pointer())}"
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
                f"{fid_var} = _formation_id()",
                f"{out_ids} = {ids_expr}",
                f"{out_var} = {expr}",
            ]
        )


