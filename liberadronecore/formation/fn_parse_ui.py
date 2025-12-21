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
        def _ensure_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
            col = bpy.data.collections.get(name)
            if col is None:
                col = bpy.data.collections.new(name)
                scene.collection.children.link(col)
            else:
                try:
                    if col.name not in scene.collection.children:
                        scene.collection.children.link(col)
                except TypeError:
                    scene.collection.children.link(col)
            return col

        def _set_gn_input(mod: bpy.types.Modifier, name: str, value) -> None:
            if mod is None:
                return
            try:
                mod[name] = value
                return
            except Exception:
                pass
            node_group = getattr(mod, "node_group", None)
            if node_group is None:
                return
            for inp in node_group.inputs:
                if inp.name == name:
                    try:
                        mod[inp.identifier] = value
                    except Exception:
                        pass
                    break

        def _get_nodes_modifier(obj: bpy.types.Object, name: str) -> Optional[bpy.types.Modifier]:
            mod = obj.modifiers.get(name)
            if mod and mod.type == 'NODES':
                return mod
            for m in obj.modifiers:
                if m.type == 'NODES':
                    return m
            return None

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

        proxy_obj = bpy.data.objects.get("ProxyPoints")
        preview_obj = bpy.data.objects.get("PreviewDrone")
        legacy_proxy = bpy.data.objects.get("AnyMesh")
        legacy_preview = bpy.data.objects.get("Iso")
        if proxy_obj is None and legacy_proxy is not None:
            legacy_proxy.name = "ProxyPoints"
            proxy_obj = legacy_proxy
        if preview_obj is None and legacy_preview is not None:
            legacy_preview.name = "PreviewDrone"
            preview_obj = legacy_preview

        if proxy_obj is None or preview_obj is None:
            if drone_count is not None:
                sence_setup.ANY_MESH_VERTS = drone_count
                sence_setup.init_scene_env(n_verts=drone_count)
            else:
                sence_setup.init_scene_env()

            proxy_obj = bpy.data.objects.get("AnyMesh")
            preview_obj = bpy.data.objects.get("Iso")
            if proxy_obj:
                proxy_obj.name = "ProxyPoints"
            if preview_obj:
                preview_obj.name = "PreviewDrone"

        proxy_group = None
        preview_group = None
        from liberadronecore.system.drone import proxy_points_gn, preview_drone_gn

        proxy_builder = getattr(proxy_points_gn, "geometry_nodes_001_1_node_group", None)
        if proxy_builder is None:
            proxy_builder = getattr(proxy_points_gn, "geometry_nodes_002_1_node_group", None)
        if proxy_builder is not None:
            proxy_group = _ensure_geometry_node_group(
                proxy_points_gn,
                proxy_builder,
                "GN_ProxyPoints",
            )

        preview_builder = getattr(preview_drone_gn, "geometry_nodes_001_1_node_group", None)
        if preview_builder is None:
            preview_builder = getattr(preview_drone_gn, "geometry_nodes_002_1_node_group", None)
        if preview_builder is not None:
            preview_group = _ensure_geometry_node_group(
                preview_drone_gn,
                preview_builder,
                "GN_PreviewDrone",
            )

        if proxy_obj and proxy_group:
            _attach_node_group(proxy_obj.name, proxy_group, "ProxyPointsGN")
            mod = _get_nodes_modifier(proxy_obj, "ProxyPointsGN")
            formation_col = _ensure_collection(context.scene, "Formation")
            _set_gn_input(mod, "Formation", formation_col)
        if preview_obj and preview_group:
            _attach_node_group(preview_obj.name, preview_group, "PreviewDroneGN")
            mod = _get_nodes_modifier(preview_obj, "PreviewDroneGN")
            mat = sence_setup.get_or_create_emission_attr_material(sence_setup.MAT_NAME, sence_setup.ATTR_NAME)
            _set_gn_input(mod, "Material", mat)
            if proxy_obj:
                _set_gn_input(mod, "Object", proxy_obj)

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


class FN_OT_assign_selected_to_show(bpy.types.Operator, FN_Register):
    bl_idname = "fn.assign_selected_to_show"
    bl_label = "Assign Selected to Show"
    bl_description = "Create collection from selected meshes and assign to active Show node"

    formation_name: bpy.props.StringProperty(name="Formation Name", default="")

    def invoke(self, context, event):
        node = getattr(context, "active_node", None)
        if node and not self.formation_name:
            self.formation_name = node.label or node.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        node = getattr(context, "active_node", None)
        if node is None or getattr(node, "bl_idname", "") != "FN_ShowNode":
            self.report({'ERROR'}, "Active Show node not found")
            return {'CANCELLED'}

        selected = getattr(context, "selected_objects", None)
        meshes = [o for o in (selected or []) if o.type == 'MESH']
        if not meshes:
            self.report({'ERROR'}, "Select at least one mesh object")
            return {'CANCELLED'}

        name = (self.formation_name or "").strip()
        if not name:
            self.report({'ERROR'}, "Formation name is required")
            return {'CANCELLED'}

        col = bpy.data.collections.get(name)
        if col is None:
            col = bpy.data.collections.new(name)
            context.scene.collection.children.link(col)

        for obj in meshes:
            if obj.name not in col.objects:
                col.objects.link(obj)

        node.label = name
        if hasattr(node, "inputs"):
            sock = node.inputs.get("Collection")
            if sock and hasattr(sock, "collection"):
                sock.collection = col
        if hasattr(node, "collection"):
            node.collection = col
        if hasattr(node, "collection_vertex_count"):
            node.collection_vertex_count = _count_collection_vertices(col)

        self.report({'INFO'}, f"Assigned {len(meshes)} meshes to {name}")
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
            box.operator("fn.assign_selected_to_show", text="Assign Selected to Show")
