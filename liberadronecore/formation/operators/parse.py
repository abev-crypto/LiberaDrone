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


def _render_end_for_range(start: int, end: int) -> int:
    if end <= start:
        return int(start)
    return int(end - 1)


def _formation_entries(schedule):
    return [entry for entry in schedule if entry.collection]


def _overall_range(entries):
    if not entries:
        return None
    start = min(entry.start for entry in entries)
    end = max(entry.end for entry in entries)
    return int(start), int(end)


def _set_render_range(scene: bpy.types.Scene, start: int, end: int) -> None:
    scene.frame_start = int(start)
    scene.frame_end = _render_end_for_range(start, end)


def _find_active_entry(entries, frame: int):
    for entry in entries:
        if entry.start <= frame < entry.end:
            return entry
    return None


class FN_OT_calculate_schedule(bpy.types.Operator, FN_Register):
    bl_idname = "fn.calculate_schedule"
    bl_label = "Calculate Formation"
    bl_description = "Assign PairID/FormationID and build schedule from Formation nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        schedule = compute_schedule(context)
        entries = _formation_entries(schedule)
        overall = _overall_range(entries)
        if overall and context.scene:
            _set_render_range(context.scene, overall[0], overall[1])
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
                if col.name not in scene.collection.children:
                    scene.collection.children.link(col)
            return col

        def _set_gn_input(mod: bpy.types.Modifier, name: str, value) -> None:
            if mod is None:
                return
            node_group = getattr(mod, "node_group", None)
            if node_group is not None:
                iface = getattr(node_group, "interface", None)
                if iface is not None:
                    for sock in iface.items_tree:
                        if getattr(sock, "in_out", None) != 'INPUT':
                            continue
                        if sock.name == name:
                            try:
                                mod[sock.identifier] = value
                                return
                            except Exception:
                                pass
                for inp in getattr(node_group, "inputs", []):
                    if inp.name == name:
                        try:
                            mod[inp.identifier] = value
                            return
                        except Exception:
                            pass
            try:
                mod[name] = value
            except Exception:
                pass

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


class FN_OT_render_range_current(bpy.types.Operator, FN_Register):
    bl_idname = "fn.render_range_current"
    bl_label = "Current Formation"
    bl_description = "Set render range to the formation at current frame"

    def execute(self, context):
        schedule = get_cached_schedule(context.scene)
        entries = _formation_entries(schedule)
        if not entries:
            self.report({'ERROR'}, "No cached schedule. Run Calculate first.")
            return {'CANCELLED'}

        frame = context.scene.frame_current
        current = _find_active_entry(entries, frame)
        if current is None:
            current = entries[0]

        start = int(current.start)
        end = int(current.end)
        render_end = _render_end_for_range(start, end)
        if context.scene.frame_start == start and context.scene.frame_end == render_end:
            overall = _overall_range(entries)
            if overall:
                _set_render_range(context.scene, overall[0], overall[1])
        else:
            _set_render_range(context.scene, start, end)
        return {'FINISHED'}


class FN_OT_render_range_prev(bpy.types.Operator, FN_Register):
    bl_idname = "fn.render_range_prev"
    bl_label = "Prev Formation"
    bl_description = "Set render range to the previous formation"

    def execute(self, context):
        schedule = get_cached_schedule(context.scene)
        entries = _formation_entries(schedule)
        if not entries:
            self.report({'ERROR'}, "No cached schedule. Run Calculate first.")
            return {'CANCELLED'}

        frame = context.scene.frame_current
        current = _find_active_entry(entries, frame)
        if current is None:
            target = entries[-1]
        else:
            idx = entries.index(current)
            target = entries[idx - 1] if idx > 0 else entries[0]

        _set_render_range(context.scene, int(target.start), int(target.end))
        context.scene.frame_set(int(target.start))
        return {'FINISHED'}


class FN_OT_render_range_next(bpy.types.Operator, FN_Register):
    bl_idname = "fn.render_range_next"
    bl_label = "Next Formation"
    bl_description = "Set render range to the next formation"

    def execute(self, context):
        schedule = get_cached_schedule(context.scene)
        entries = _formation_entries(schedule)
        if not entries:
            self.report({'ERROR'}, "No cached schedule. Run Calculate first.")
            return {'CANCELLED'}

        frame = context.scene.frame_current
        current = _find_active_entry(entries, frame)
        if current is None:
            target = entries[0]
        else:
            idx = entries.index(current)
            target = entries[idx + 1] if idx + 1 < len(entries) else entries[-1]

        _set_render_range(context.scene, int(target.start), int(target.end))
        context.scene.frame_set(int(target.start))
        return {'FINISHED'}
