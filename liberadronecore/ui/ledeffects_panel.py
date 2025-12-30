import bpy

from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.ledeffects import led_codegen_runtime

_LED_OUTPUT_ACTIVITY: dict[str, bool] = {}


def _get_led_tree(context) -> bpy.types.NodeTree | None:
    space = getattr(context, "space_data", None)
    if space and getattr(space, "edit_tree", None) and getattr(space, "tree_type", "") == "LD_LedEffectsTree":
        return space.edit_tree
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", "") == "LD_LedEffectsTree":
            return tree
    return None


def _ensure_led_tree(context) -> bpy.types.NodeTree | None:
    tree = _get_led_tree(context)
    if tree is not None:
        return tree
    tree = bpy.data.node_groups.new("LEDEffectsTree", "LD_LedEffectsTree")
    space = getattr(context, "space_data", None)
    if space and getattr(space, "type", "") == "NODE_EDITOR":
        try:
            space.tree_type = "LD_LedEffectsTree"
            space.node_tree = tree
        except Exception:
            pass
    return tree


def _sync_output_items(scene: bpy.types.Scene, tree: bpy.types.NodeTree, *, allow_index_update: bool = True) -> None:
    items = scene.ld_led_output_items
    output_nodes = [n for n in tree.nodes if getattr(n, "bl_idname", "") == "LDLEDOutputNode"]
    output_names = {n.name for n in output_nodes}

    active_name = None
    if 0 <= scene.ld_led_output_index < len(items):
        active_name = items[scene.ld_led_output_index].node_name

    for idx in reversed(range(len(items))):
        if items[idx].node_name not in output_names:
            items.remove(idx)

    existing = {item.node_name for item in items}
    for node in output_nodes:
        if node.name not in existing:
            item = items.add()
            item.node_name = node.name

    if not allow_index_update:
        return

    target_index = scene.ld_led_output_index
    if active_name:
        for idx, item in enumerate(items):
            if item.node_name == active_name:
                target_index = idx
                break
        else:
            target_index = min(scene.ld_led_output_index, max(len(items) - 1, 0))
    else:
        target_index = min(scene.ld_led_output_index, max(len(items) - 1, 0))

    try:
        scene.ld_led_output_index = target_index
    except Exception:
        pass


def _set_active_output(context, node: bpy.types.Node) -> None:
    tree = getattr(node, "id_data", None)
    if tree is None:
        return
    for n in tree.nodes:
        n.select = False
    node.select = True
    tree.nodes.active = node
    if context and getattr(context, "space_data", None):
        try:
            context.space_data.node_tree = tree
        except Exception:
            pass


def _update_output_index(self, context):
    tree = _get_led_tree(context)
    if tree is None:
        return
    idx = int(getattr(self, "ld_led_output_index", 0))
    items = getattr(self, "ld_led_output_items", [])
    if idx < 0 or idx >= len(items):
        return
    node = tree.nodes.get(items[idx].node_name)
    if node is not None:
        _set_active_output(context, node)


class LDLEDOutputItem(bpy.types.PropertyGroup):
    node_name: bpy.props.StringProperty(name="Output Node")


class LDLED_UL_OutputList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        tree = _get_led_tree(context)
        node = tree.nodes.get(item.node_name) if tree else None
        row = layout.row(align=True)
        is_active = bool(_LED_OUTPUT_ACTIVITY.get(item.node_name, False))
        row.alert = is_active
        row.label(text="", icon='CHECKMARK' if is_active else 'BLANK1')
        if node is None:
            row.label(text=item.node_name)
        else:
            row.prop(node, "name", text="")


class LDLED_OT_create_output_node(bpy.types.Operator):
    bl_idname = "ldled.create_output_node"
    bl_label = "CreateNode"
    bl_description = "Create LED Effects tree and add an Output node"

    def execute(self, context):
        tree = _ensure_led_tree(context)
        if tree is None:
            self.report({'ERROR'}, "LED node tree not available")
            return {'CANCELLED'}
        node = tree.nodes.new("LDLEDOutputNode")
        node.location = (200.0, 0.0)
        _set_active_output(context, node)
        _sync_output_items(context.scene, tree)
        for idx, item in enumerate(context.scene.ld_led_output_items):
            if item.node_name == node.name:
                context.scene.ld_led_output_index = idx
                break
        return {'FINISHED'}


class LDLED_PT_panel(bpy.types.Panel):
    bl_label = "LED Effects"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "LED"

    @classmethod
    def poll(cls, context):
        space = getattr(context, "space_data", None)
        return bool(space and getattr(space, "tree_type", "") == "LD_LedEffectsTree")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        tree = _get_led_tree(context)

        layout.operator("ldled.create_output_node", text="CreateNode")

        if tree is None:
            layout.label(text="No LED node tree", icon='ERROR')
            return

        _sync_output_items(scene, tree, allow_index_update=False)
        global _LED_OUTPUT_ACTIVITY
        try:
            _LED_OUTPUT_ACTIVITY = led_codegen_runtime.get_output_activity(tree, scene.frame_current)
        except Exception:
            _LED_OUTPUT_ACTIVITY = {}

        layout.template_list(
            "LDLED_UL_OutputList",
            "",
            scene,
            "ld_led_output_items",
            scene,
            "ld_led_output_index",
            rows=4,
        )

        node = tree.nodes.active if tree else None
        if node is None or getattr(node, "bl_idname", "") != "LDLEDOutputNode":
            if 0 <= scene.ld_led_output_index < len(scene.ld_led_output_items):
                node_name = scene.ld_led_output_items[scene.ld_led_output_index].node_name
                node = tree.nodes.get(node_name)

        if node is not None and getattr(node, "bl_idname", "") == "LDLEDOutputNode":
            box = layout.box()
            box.label(text="Active Output")
            box.prop(node, "name", text="Name")


class LDLED_UI(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LDLEDOutputItem)
        bpy.utils.register_class(LDLED_UL_OutputList)
        bpy.utils.register_class(LDLED_OT_create_output_node)
        bpy.utils.register_class(LDLED_PT_panel)
        if not hasattr(bpy.types.Scene, "ld_led_output_items"):
            bpy.types.Scene.ld_led_output_items = bpy.props.CollectionProperty(type=LDLEDOutputItem)
        if not hasattr(bpy.types.Scene, "ld_led_output_index"):
            bpy.types.Scene.ld_led_output_index = bpy.props.IntProperty(
                name="Output Index",
                default=0,
                update=_update_output_index,
            )

    @classmethod
    def unregister(cls) -> None:
        if hasattr(bpy.types.Scene, "ld_led_output_index"):
            del bpy.types.Scene.ld_led_output_index
        if hasattr(bpy.types.Scene, "ld_led_output_items"):
            del bpy.types.Scene.ld_led_output_items
        bpy.utils.unregister_class(LDLED_PT_panel)
        bpy.utils.unregister_class(LDLED_OT_create_output_node)
        bpy.utils.unregister_class(LDLED_UL_OutputList)
        bpy.utils.unregister_class(LDLEDOutputItem)
