import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.le_nodecategory import LDLED_Register
from liberadronecore.formation import fn_parse_pairing
from liberadronecore.reg.base_reg import RegisterBase


class LDLEDIDMaskItem(bpy.types.PropertyGroup, LDLED_Register):
    value: bpy.props.IntProperty(
        name="ID",
        default=0,
        min=0,
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
    return _sorted_ids([node.formation_id])


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
    """Mask by formation id (uses drone index)."""

    bl_idname = "LDLEDIDMaskNode"
    bl_label = "ID Mask"
    bl_icon = "SORTSIZE"

    formation_id: bpy.props.IntProperty(
        name="Formation ID",
        default=0,
        min=0,
    )
    use_custom_ids: bpy.props.BoolProperty(
        name="Use Custom IDs",
        default=False,
        options={'HIDDEN'},
    )
    ids: bpy.props.CollectionProperty(type=LDLEDIDMaskItem)

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        if self.use_custom_ids:
            ids = _node_effective_ids(self, include_legacy=False)
            label = ", ".join(str(i) for i in ids) if ids else "-"
            layout.label(text=f"IDs: {label}")
        else:
            layout.label(text=f"ID: {int(self.formation_id)}")
        row = layout.row(align=True)
        op = row.operator("ldled.idmask_add_selection", text="Add Selection")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op = row.operator("ldled.idmask_remove_selection", text="Remove Selection")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

    def build_code(self, inputs):
        out_var = self.output_var("Mask")
        ids = _node_effective_ids(self, include_legacy=not self.use_custom_ids)
        if not ids:
            return f"{out_var} = 0.0"
        if len(ids) == 1:
            return f"{out_var} = 1.0 if idx == {ids[0]} else 0.0"
        return f"{out_var} = 1.0 if idx in {tuple(ids)} else 0.0"


class LDLED_OT_idmask_add_selection(bpy.types.Operator):
    bl_idname = "ldled.idmask_add_selection"
    bl_label = "Add Formation IDs"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, LDLEDIDMaskNode):
            self.report({'ERROR'}, "ID Mask node not found")
            return {'CANCELLED'}

        selected_ids, error = _read_selected_ids(context)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        existing = set(_node_effective_ids(node, include_legacy=True))
        merged = existing | set(selected_ids or [])
        _set_node_ids(node, _sorted_ids(merged))
        node.use_custom_ids = True
        return {'FINISHED'}


class LDLED_OT_idmask_remove_selection(bpy.types.Operator):
    bl_idname = "ldled.idmask_remove_selection"
    bl_label = "Remove Formation IDs"
    bl_options = {'REGISTER', 'UNDO'}

    node_tree_name: bpy.props.StringProperty()
    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.node_tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None or not isinstance(node, LDLEDIDMaskNode):
            self.report({'ERROR'}, "ID Mask node not found")
            return {'CANCELLED'}

        selected_ids, error = _read_selected_ids(context)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        existing = set(_node_effective_ids(node, include_legacy=True))
        remaining = existing - set(selected_ids or [])
        _set_node_ids(node, _sorted_ids(remaining))
        node.use_custom_ids = True
        return {'FINISHED'}


class LDLED_IDMaskOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LDLED_OT_idmask_add_selection)
        bpy.utils.register_class(LDLED_OT_idmask_remove_selection)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LDLED_OT_idmask_remove_selection)
        bpy.utils.unregister_class(LDLED_OT_idmask_add_selection)
