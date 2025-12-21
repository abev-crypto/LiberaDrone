from __future__ import annotations

from typing import Optional

import bpy
from liberadronecore.formation.fn_nodecategory import FN_Register
from liberadronecore.formation.fn_parse import (
    _attach_node_group,
    _ensure_geometry_node_group,
    compute_schedule,
    get_cached_schedule,
)
from liberadronecore.formation.fn_parse_pairing import _count_collection_vertices


class FN_OT_calculate_schedule(bpy.types.Operator, FN_Register):
    bl_idname = "fn.calculate_schedule"
    bl_label = "Calculate Formation"
    bl_description = "Assign PairID/FormationID and build schedule from Formation nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        schedule = compute_schedule(context)
        self.report({'INFO'}, f"Schedule entries: {len(schedule)}")
        return {'FINISHED'}


class FN_OT_setup_scene(bpy.types.Operator, FN_Register):
    bl_idname = "fn.setup_scene"
    bl_label = "Setup Scene"
    bl_description = "Run scene setup using Start node drone count"

    def execute(self, context):
        tree = None
        space = context.space_data
        if space and getattr(space, "edit_tree", None):
            tree = space.edit_tree
        if tree is None or getattr(tree, "bl_idname", "") != "FN_FormationTree":
            tree = next((ng for ng in bpy.data.node_groups if getattr(ng, "bl_idname", "") == "FN_FormationTree"), None)

        drone_count: Optional[int] = None
        if tree:
            for node in tree.nodes:
                if getattr(node, "bl_idname", "") == "FN_StartNode":
                    drone_count = getattr(node, "drone_count", None)
                    break
        from liberadronecore.system import sence_setup
        if drone_count is not None:
            drone_count = max(1, int(drone_count))
        if drone_count is not None:
            sence_setup.ANY_MESH_VERTS = drone_count
            sence_setup.init_scene_env(n_verts=drone_count)
        else:
            sence_setup.init_scene_env()

        proxy_group = None
        preview_group = None
        from liberadronecore.system.drone import proxy_points_gn, preview_drone_gn

        proxy_group = _ensure_geometry_node_group(
            proxy_points_gn,
            proxy_points_gn.geometry_nodes_001_1_node_group,
            "GN_ProxyPoints",
        )
        preview_group = _ensure_geometry_node_group(
            preview_drone_gn,
            preview_drone_gn.geometry_nodes_001_1_node_group,
            "GN_PreviewDrone",
        )

        _attach_node_group("AnyMesh", proxy_group, "ProxyPointsGN")
        _attach_node_group("Iso", preview_group, "PreviewDroneGN")

        self.report({'INFO'}, "Setup completed")
        return {'FINISHED'}


class FN_OT_create_collection_from_label(bpy.types.Operator, FN_Register):
    bl_idname = "fn.create_collection_from_label"
    bl_label = "Create Formation Collection"
    bl_description = "Create a collection using the active node label"

    node_name: bpy.props.StringProperty()

    def execute(self, context):
        node = None
        tree = context.space_data.edit_tree if context.space_data else None
        if tree and self.node_name:
            node = tree.nodes.get(self.node_name)
        if node is None:
            node = getattr(context, "active_node", None)
        if node is None:
            self.report({'ERROR'}, "Active node not found")
            return {'CANCELLED'}

        name = node.label or node.name
        col = bpy.data.collections.get(name)
        if col is None:
            col = bpy.data.collections.new(name)
            context.scene.collection.children.link(col)
            self.report({'INFO'}, f"Created collection {name}")
        else:
            self.report({'INFO'}, f"Collection {name} already exists")
        if hasattr(node, "inputs"):
            sock = node.inputs.get("Collection")
            if sock and hasattr(sock, "collection"):
                sock.collection = col
        if hasattr(node, "collection"):
            node.collection = col
        if hasattr(node, "collection_vertex_count"):
            node.collection_vertex_count = _count_collection_vertices(col)
        return {'FINISHED'}


class FN_PT_formation_panel(bpy.types.Panel, FN_Register):
    bl_idname = "FN_PT_formation_panel"
    bl_label = "Formation Nodes"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Formation"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return bool(space and getattr(space, "tree_type", "") == "FN_FormationTree")

    def draw(self, context):
        layout = self.layout
        layout.operator("fn.setup_scene", text="Setup")
        layout.operator("fn.calculate_schedule", text="Calculate")
        if get_cached_schedule():
            layout.label(text=f"Cached entries: {len(get_cached_schedule())}")

        node = getattr(context, "active_node", None)
        if node:
            box = layout.box()
            box.label(text="Active Node")
            box.prop(node, "label", text="Label")
            op = box.operator("fn.create_collection_from_label", text="Create Collection")
            op.node_name = node.name
