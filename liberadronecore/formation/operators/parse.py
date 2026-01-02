from __future__ import annotations

from typing import Optional

import bpy
from liberadronecore.formation.fn_nodecategory import FN_Register
from liberadronecore.formation.fn_parse import (
    _attach_node_group,
    _ensure_geometry_node_group,
    compute_schedule,
    get_cached_schedule,
    _flow_edges,
    _flow_reachable,
    _is_transition_node,
)
from liberadronecore.formation.fn_parse_pairing import _count_collection_vertices
from liberadronecore.system.transition.transition_apply import apply_transition


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
    bl_description = "Assign formation_id/pair_id and build schedule from Formation nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        schedule = compute_schedule(context, assign_pairs=False)
        applied = 0
        errors = []
        trees = [ng for ng in bpy.data.node_groups if getattr(ng, "bl_idname", "") == "FN_FormationTree"]
        for tree in trees:
            start_nodes = [n for n in tree.nodes if n.bl_idname == "FN_StartNode"]
            if not start_nodes:
                continue
            edges = _flow_edges(tree)
            reachable = _flow_reachable(start_nodes[0], edges)
            for node in reachable:
                if not _is_transition_node(node):
                    continue
                if not hasattr(node, "collection"):
                    continue
                if getattr(node, "collection", None) is not None:
                    continue
                try:
                    ok, message = apply_transition(node, context, assign_pairs_after=False)
                except Exception as exc:
                    ok = False
                    message = str(exc)
                if ok:
                    applied += 1
                else:
                    errors.append(message)
        schedule = compute_schedule(context, assign_pairs=True)
        entries = _formation_entries(schedule)
        overall = _overall_range(entries)
        if overall and context.scene:
            _set_render_range(context.scene, overall[0], overall[1])
        if errors:
            self.report({'WARNING'}, f"Transition apply failed: {errors[0]}")
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

        def _ensure_color_verts(scene: bpy.types.Scene, count: Optional[int]) -> Optional[bpy.types.Object]:
            if count is None:
                return None
            count = max(1, int(count))
            obj = bpy.data.objects.get("ColorVerts")
            if obj is not None and obj.type != 'MESH':
                return None
            if obj is None:
                mesh = bpy.data.meshes.new("ColorVertsMesh")
                obj = bpy.data.objects.new("ColorVerts", mesh)
                scene.collection.objects.link(obj)
            mesh = obj.data
            if len(mesh.vertices) != count:
                mesh.clear_geometry()
                mesh.vertices.add(count)
                mesh.update()
            if obj.name not in scene.collection.objects:
                scene.collection.objects.link(obj)
            return obj

        def _ensure_proxy_verts(obj: Optional[bpy.types.Object], count: Optional[int]) -> None:
            if obj is None or obj.type != 'MESH' or count is None:
                return
            count = max(1, int(count))
            mesh = obj.data
            if len(mesh.vertices) != count:
                mesh.clear_geometry()
                mesh.vertices.add(count)
                mesh.update()

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

        try:
            from liberadronecore.ui import liberadrone_panel
            liberadrone_panel._apply_limit_profile(context.scene, "MODEL_X")
        except Exception:
            pass

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
                sence_setup.ANY_MESH_VERTS = max(1, int(drone_count))
                sence_setup.init_scene_env(n_verts=max(1, int(drone_count)))
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

        color_verts_obj = _ensure_color_verts(context.scene, drone_count)
        if color_verts_obj:
            geo_col = sence_setup.get_or_create_collection(sence_setup.COL_FOR_PREVIEW)
            sence_setup.move_object_to_collection(color_verts_obj, geo_col)
        _ensure_proxy_verts(proxy_obj, drone_count)

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
            mat = sence_setup.get_or_create_emission_attr_material(
                sence_setup.MAT_NAME,
                sence_setup.ATTR_NAME,
                image_name=sence_setup.IMG_CIRCLE_NAME,
            )
            ring_mat = sence_setup.get_or_create_emission_attr_material(
                sence_setup.MAT_RING_NAME,
                sence_setup.ATTR_NAME,
                image_name=sence_setup.IMG_RING_NAME,
            )
            _set_gn_input(mod, "Material", mat)
            _set_gn_input(mod, "CircleMat", ring_mat)
            formation_col = _ensure_collection(context.scene, "Formation")
            _set_gn_input(mod, "Collection", formation_col)
            if color_verts_obj:
                _set_gn_input(mod, "ColorVerts", color_verts_obj)

        self.report({'INFO'}, "Setup completed")
        return {'FINISHED'}


class FN_OT_create_node_chain(bpy.types.Operator, FN_Register):
    bl_idname = "fn.create_node_chain"
    bl_label = "Create Node"
    bl_description = "Create a basic Start/Show chain or append a Transition before Show"

    def execute(self, context):
        def _ensure_tree():
            tree = None
            space = context.space_data
            if space and getattr(space, "edit_tree", None):
                tree = space.edit_tree
            if tree is None or getattr(tree, "bl_idname", "") != "FN_FormationTree":
                tree = next((ng for ng in bpy.data.node_groups if getattr(ng, "bl_idname", "") == "FN_FormationTree"), None)
            if tree is None:
                tree = bpy.data.node_groups.new("FormationTree", "FN_FormationTree")
                if space and getattr(space, "type", "") == "NODE_EDITOR":
                    try:
                        space.tree_type = "FN_FormationTree"
                        space.node_tree = tree
                    except Exception:
                        pass
            return tree

        def _first_flow_out(node):
            for sock in getattr(node, "outputs", []):
                if getattr(sock, "bl_idname", "") == "FN_SocketFlow":
                    return sock
            return None

        def _first_flow_in(node):
            for sock in getattr(node, "inputs", []):
                if getattr(sock, "bl_idname", "") == "FN_SocketFlow":
                    return sock
            return None

        def _link_flow(tree, from_node, to_node):
            out_sock = _first_flow_out(from_node)
            in_sock = _first_flow_in(to_node)
            if out_sock and in_sock:
                tree.links.new(out_sock, in_sock)

        tree = _ensure_tree()
        if tree is None:
            self.report({'ERROR'}, "Formation node tree not available")
            return {'CANCELLED'}

        start_node = next((n for n in tree.nodes if getattr(n, "bl_idname", "") == "FN_StartNode"), None)
        if start_node is None:
            start_node = tree.nodes.new("FN_StartNode")
            start_node.location = (-300, 0)
            show_node = tree.nodes.new("FN_ShowNode")
            show_node.location = (200, 0)
            _link_flow(tree, start_node, show_node)
            self.report({'INFO'}, "Created Start and Show nodes")
            return {'FINISHED'}

        edges = _flow_edges(tree)
        reachable = _flow_reachable(start_node, edges)
        last_nodes = [node for node in reachable if not edges.get(node)]
        show_last = next((n for n in last_nodes if getattr(n, "bl_idname", "") == "FN_ShowNode"), None)
        if show_last is None:
            self.report({'INFO'}, "No terminal Show node found")
            return {'CANCELLED'}

        transition_node = tree.nodes.new("FN_TransitionNode")
        transition_node.location = (show_last.location.x + 260, show_last.location.y)
        new_show = tree.nodes.new("FN_ShowNode")
        new_show.location = (transition_node.location.x + 260, transition_node.location.y)

        _link_flow(tree, show_last, transition_node)
        _link_flow(tree, transition_node, new_show)
        self.report({'INFO'}, "Appended Transition and Show nodes")
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


class FN_OT_create_markers(bpy.types.Operator, FN_Register):
    bl_idname = "fn.create_formation_markers"
    bl_label = "Create Formation Markers"
    bl_description = "Create timeline markers at each formation start frame"

    def execute(self, context):
        schedule = get_cached_schedule(context.scene)
        if not schedule:
            schedule = compute_schedule(context, assign_pairs=False)
        entries = _formation_entries(schedule)
        if not entries:
            self.report({'ERROR'}, "No formation entries found.")
            return {'CANCELLED'}

        scene = context.scene
        markers = scene.timeline_markers
        created = 0
        updated = 0

        for entry in entries:
            name = entry.collection.name if entry.collection else entry.node_name
            if not name:
                continue
            marker = markers.get(name)
            frame = int(entry.start)
            if marker is None:
                markers.new(name=name, frame=frame)
                created += 1
            else:
                marker.frame = frame
                updated += 1

        self.report({'INFO'}, f"Markers created: {created}, updated: {updated}")
        return {'FINISHED'}
