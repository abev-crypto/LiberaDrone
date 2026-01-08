from __future__ import annotations

import bpy
from liberadronecore.formation.fn_nodecategory import FN_Register
from liberadronecore.formation.fn_parse import get_cached_schedule
from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.system.transition import bakedt

_TRANSITION_NODE_TYPES = {
    "FN_StartNode",
    "FN_ShowNode",
    "FN_TransitionNode",
    "FN_SplitTransitionNode",
    "FN_MergeTransitionNode",
}

_TRANSITION_NODE_ICONS = {
    "FN_StartNode": "ERROR",
    "FN_ShowNode": "CHECKMARK",
    "FN_TransitionNode": "KEYFRAME",
    "FN_SplitTransitionNode": "NODETREE",
    "FN_MergeTransitionNode": "NODETREE",
}


def _get_formation_tree(context) -> bpy.types.NodeTree | None:
    space = getattr(context, "space_data", None)
    if space and getattr(space, "edit_tree", None) and getattr(space, "tree_type", "") == "FN_FormationTree":
        return space.edit_tree
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", "") == "FN_FormationTree":
            return tree
    return None


def _node_start_frame(node: bpy.types.Node, schedule_map: dict[str, int] | None) -> int | None:
    if schedule_map:
        frame = schedule_map.get(node.name)
        if frame is not None:
            return int(frame)
    frame = getattr(node, "computed_start_frame", None)
    if frame is not None:
        try:
            frame = int(frame)
        except Exception:
            frame = None
    if frame is not None and frame >= 0:
        return frame
    if getattr(node, "bl_idname", "") == "FN_StartNode":
        sock = node.inputs.get("Start Frame") if getattr(node, "inputs", None) else None
        if sock is not None and hasattr(sock, "value"):
            try:
                return int(sock.value)
            except Exception:
                pass
    return None


def _transition_node_sort_key(node: bpy.types.Node, schedule_map: dict[str, int] | None) -> tuple[int, str]:
    if getattr(node, "bl_idname", "") == "FN_StartNode":
        return -1, node.name
    frame = _node_start_frame(node, schedule_map)
    if frame is None:
        frame = 10**9
    return int(frame), node.name


def _sync_transition_items(
    scene: bpy.types.Scene,
    tree: bpy.types.NodeTree,
    *,
    allow_index_update: bool = True,
) -> None:
    if not hasattr(scene, "ld_transition_items"):
        return
    items = scene.ld_transition_items
    active_name = None
    if 0 <= scene.ld_transition_index < len(items):
        active_name = items[scene.ld_transition_index].node_name

    nodes = [n for n in tree.nodes if getattr(n, "bl_idname", "") in _TRANSITION_NODE_TYPES]
    schedule_map = {
        entry.node_name: int(entry.start)
        for entry in get_cached_schedule(scene)
        if entry.tree_name == tree.name
    }
    nodes.sort(key=lambda node: _transition_node_sort_key(node, schedule_map))

    items.clear()
    for node in nodes:
        item = items.add()
        item.node_name = node.name
        item.node_id = str(node.as_pointer())
        item.node_type = getattr(node, "bl_idname", "")

    if not allow_index_update:
        return

    target_index = scene.ld_transition_index
    if active_name:
        for idx, item in enumerate(items):
            if item.node_name == active_name:
                target_index = idx
                break
        else:
            target_index = min(scene.ld_transition_index, max(len(items) - 1, 0))
    else:
        target_index = min(scene.ld_transition_index, max(len(items) - 1, 0))

    try:
        scene.ld_transition_index = target_index
    except Exception:
        pass


def sync_transition_items(context, *, allow_index_update: bool = True) -> None:
    if context is None or getattr(context, "scene", None) is None:
        return
    tree = _get_formation_tree(context)
    if tree is None:
        return
    _sync_transition_items(context.scene, tree, allow_index_update=allow_index_update)


def _set_active_transition_node(context, node: bpy.types.Node) -> None:
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


def _find_transition_node(tree: bpy.types.NodeTree, item) -> bpy.types.Node | None:
    node_id = getattr(item, "node_id", "")
    if node_id:
        try:
            node_id_int = int(node_id)
        except Exception:
            node_id_int = 0
    else:
        node_id_int = 0
    if node_id_int:
        for node in tree.nodes:
            try:
                if node.as_pointer() == node_id_int:
                    return node
            except Exception:
                continue
    node_name = getattr(item, "node_name", "")
    if node_name:
        return tree.nodes.get(node_name)
    return None


def _update_transition_index(self, context):
    tree = _get_formation_tree(context)
    if tree is None:
        return
    idx = int(getattr(self, "ld_transition_index", 0))
    items = getattr(self, "ld_transition_items", [])
    if idx < 0 or idx >= len(items):
        return
    node = _find_transition_node(tree, items[idx])
    if node is not None:
        _set_active_transition_node(context, node)


def _socket_display_name(sock: bpy.types.NodeSocket) -> str:
    name = getattr(sock, "name", "")
    return name if name else getattr(sock, "bl_idname", "Socket")


def _draw_socket_status(layout, sock: bpy.types.NodeSocket) -> None:
    icon = "LINKED" if getattr(sock, "is_linked", False) else "UNLINKED"
    row = layout.row(align=True)
    row.label(text="", icon=icon)
    if getattr(sock, "is_output", False):
        row.label(text=_socket_display_name(sock))
        return
    if getattr(sock, "is_linked", False):
        row.label(text=_socket_display_name(sock))
        return
    if hasattr(sock, "collection"):
        row.prop(sock, "collection", text=_socket_display_name(sock))
        return
    if hasattr(sock, "value"):
        row.prop(sock, "value", text=_socket_display_name(sock))
        return
    row.label(text=_socket_display_name(sock))


def _node_editor_cursor(context) -> tuple[float, float]:
    space = getattr(context, "space_data", None)
    cursor = getattr(space, "cursor_location", None) if space else None
    if cursor is None:
        return (0.0, 0.0)
    try:
        return (float(cursor.x), float(cursor.y))
    except Exception:
        return (0.0, 0.0)


class FN_OT_add_frame(bpy.types.Operator, FN_Register):
    bl_idname = "fn.add_frame"
    bl_label = "Frame"
    bl_description = "Wrap selected Formation nodes in a frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        tree = _get_formation_tree(context)
        if tree is None:
            self.report({'ERROR'}, "Formation tree not available")
            return {'CANCELLED'}
        selected = [n for n in tree.nodes if n.select]
        frame = tree.nodes.new("NodeFrame")
        frame.label = "Frame"
        frame.shrink = True
        if selected:
            xs = [float(n.location.x) for n in selected if hasattr(n, "location")]
            ys = [float(n.location.y) for n in selected if hasattr(n, "location")]
            if xs and ys:
                frame.location = (min(xs) - 60.0, max(ys) + 60.0)
            for node in selected:
                if node == frame:
                    continue
                node.parent = frame
        else:
            frame.location = _node_editor_cursor(context)
        for node in tree.nodes:
            node.select = False
        frame.select = True
        tree.nodes.active = frame
        return {'FINISHED'}


class FN_TransitionListItem(bpy.types.PropertyGroup):
    node_name: bpy.props.StringProperty(name="Node Name")
    node_id: bpy.props.StringProperty(name="Node Id", default="")
    node_type: bpy.props.StringProperty(name="Node Type", default="")


class FN_UL_TransitionList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        tree = _get_formation_tree(context)
        node = _find_transition_node(tree, item) if tree else None
        node_type = getattr(item, "node_type", "")
        if node is not None:
            if item.node_name != node.name:
                item.node_name = node.name
            if node_type != node.bl_idname:
                node_type = node.bl_idname
                item.node_type = node_type
        row = layout.row(align=True)
        row.label(text="", icon=_TRANSITION_NODE_ICONS.get(node_type, "DOT"))
        if node is None:
            row.label(text=item.node_name)
        else:
            row.prop(node, "label", text="")
            if not getattr(node, "label", ""):
                row.label(text=node.name)


class FN_PT_transition_list(bpy.types.Panel):
    bl_idname = "FN_PT_transition_list"
    bl_label = "Transition List"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Formation"
    bl_order = 0

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return bool(space and getattr(space, "tree_type", "") == "FN_FormationTree")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        tree = _get_formation_tree(context)
        if tree is None:
            layout.label(text="No Formation node tree", icon='ERROR')
            return
        if not hasattr(scene, "ld_transition_items"):
            layout.label(text="Transition list not available", icon='ERROR')
            return

        layout.template_list(
            "FN_UL_TransitionList",
            "",
            scene,
            "ld_transition_items",
            scene,
            "ld_transition_index",
            rows=6,
        )

        node = None
        if 0 <= scene.ld_transition_index < len(scene.ld_transition_items):
            node = _find_transition_node(tree, scene.ld_transition_items[scene.ld_transition_index])

        if node is None:
            layout.label(text="Select a node to edit")
            return

        box = layout.box()
        box.label(text="Active Node")
        if hasattr(node, "draw_buttons"):
            node.draw_buttons(context, box)
        box.operator("fn.create_or_assign_collection", text="Create/Assign Collection")

        socket_box = layout.box()
        socket_box.label(text="Sockets")
        if getattr(node, "inputs", None):
            socket_box.label(text="Inputs")
            for sock in node.inputs:
                _draw_socket_status(socket_box, sock)
        if getattr(node, "outputs", None):
            socket_box.label(text="Outputs")
            for sock in node.outputs:
                _draw_socket_status(socket_box, sock)


class FN_TransitionListProps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(FN_TransitionListItem)
        bpy.utils.register_class(FN_UL_TransitionList)
        bpy.utils.register_class(FN_PT_transition_list)
        if not hasattr(bpy.types.Scene, "ld_transition_items"):
            bpy.types.Scene.ld_transition_items = bpy.props.CollectionProperty(type=FN_TransitionListItem)
        if not hasattr(bpy.types.Scene, "ld_transition_index"):
            bpy.types.Scene.ld_transition_index = bpy.props.IntProperty(
                name="Transition Index",
                default=0,
                update=_update_transition_index,
            )

    @classmethod
    def unregister(cls) -> None:
        if hasattr(bpy.types.Scene, "ld_transition_index"):
            del bpy.types.Scene.ld_transition_index
        if hasattr(bpy.types.Scene, "ld_transition_items"):
            del bpy.types.Scene.ld_transition_items
        bpy.utils.unregister_class(FN_PT_transition_list)
        bpy.utils.unregister_class(FN_UL_TransitionList)
        bpy.utils.unregister_class(FN_TransitionListItem)


class FN_PT_formation_panel(bpy.types.Panel, FN_Register):
    bl_idname = "FN_PT_formation_panel"
    bl_label = "Formation Nodes"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Formation"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return bool(space and getattr(space, "tree_type", "") == "FN_FormationTree")

    def draw(self, context):
        layout = self.layout
        layout.operator("fn.create_node_chain", text="CreateNode")
        layout.operator("fn.calculate_schedule", text="Calculate")
        layout.operator("fn.force_calculate_schedule", text="Force Calculate")
        layout.operator("fn.create_formation_markers", text="CreateMarker")
        layout.separator()
        row = layout.row(align=True)
        row.operator("fn.render_range_current", text="CurrentFormation")
        row = layout.row(align=True)
        row.operator("fn.render_range_prev", text="PrevFormation")
        row.operator("fn.render_range_next", text="NextFormation")
        if get_cached_schedule():
            layout.label(text=f"Cached entries: {len(get_cached_schedule())}")

        node = getattr(context, "active_node", None)
        if node:
            box = layout.box()
            box.label(text="Active Node")
            box.operator("fn.create_or_assign_collection", text="Create/Assign Collection")


class FN_PT_transition_settings(bpy.types.Panel, FN_Register):
    bl_idname = "FN_PT_transition_settings"
    bl_label = "Transition Settings"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Formation"
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return bool(space and getattr(space, "tree_type", "") == "FN_FormationTree")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        col.prop(scene, "ld_bakedt_max_subdiv", text="Max Subdiv")
        col.prop(scene, "ld_bakedt_check_relax_iters", text="Check Relax Iters")
        col.prop(scene, "ld_bakedt_pre_relax_iters", text="Pre Relax Iters")
        col.prop(scene, "ld_bakedt_exp_distance", text="Exp Distance")
        col.prop(scene, "ld_bakedt_relax_dmin_scale", text="Relax DMin Scale")
        col.prop(scene, "ld_bakedt_relax_edge_frames", text="Relax Edge Frames")
        col.prop(scene, "ld_bakedt_speed_acc_margin", text="Speed/Acc Margin")
        col.prop(scene, "ld_bakedt_max_neighbors", text="Max Neighbors")


class FN_TransitionSettingsProps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.types.Scene.ld_bakedt_max_subdiv = bpy.props.IntProperty(
            name="Max Subdiv",
            default=bakedt.MAX_SUBDIV,
            min=0,
        )
        bpy.types.Scene.ld_bakedt_check_relax_iters = bpy.props.IntProperty(
            name="Check Relax Iters",
            default=bakedt.CHECK_RELAX_ITERS,
            min=0,
        )
        bpy.types.Scene.ld_bakedt_pre_relax_iters = bpy.props.IntProperty(
            name="Pre Relax Iters",
            default=bakedt.PRE_RELAX_ITERS,
            min=0,
        )
        bpy.types.Scene.ld_bakedt_exp_distance = bpy.props.FloatProperty(
            name="Exp Distance",
            default=bakedt.EXP_DISTANCE,
            min=0.0,
        )
        bpy.types.Scene.ld_bakedt_relax_dmin_scale = bpy.props.FloatProperty(
            name="Relax DMin Scale",
            default=bakedt.RELAX_DMIN_SCALE,
            min=0.0,
        )
        bpy.types.Scene.ld_bakedt_relax_edge_frames = bpy.props.IntProperty(
            name="Relax Edge Frames",
            default=bakedt.RELAX_EDGE_FRAMES,
            min=0,
        )
        bpy.types.Scene.ld_bakedt_speed_acc_margin = bpy.props.FloatProperty(
            name="Speed/Acc Margin",
            default=bakedt.SPEED_ACC_MARGIN,
            min=0.0,
            max=1.0,
        )
        bpy.types.Scene.ld_bakedt_max_neighbors = bpy.props.IntProperty(
            name="Max Neighbors",
            default=bakedt.MAX_NEIGHBORS,
            min=1,
        )

    @classmethod
    def unregister(cls) -> None:
        for name in (
            "ld_bakedt_max_subdiv",
            "ld_bakedt_check_relax_iters",
            "ld_bakedt_pre_relax_iters",
            "ld_bakedt_exp_distance",
            "ld_bakedt_relax_dmin_scale",
            "ld_bakedt_relax_edge_frames",
            "ld_bakedt_speed_acc_margin",
            "ld_bakedt_max_neighbors",
        ):
            if hasattr(bpy.types.Scene, name):
                delattr(bpy.types.Scene, name)
