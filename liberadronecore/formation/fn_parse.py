from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import bpy
from mathutils.kdtree import KDTree
from liberadronecore.formation.fn_nodecategory import FN_Register

PAIR_ID_ATTR = "PairID"
FORMATION_ID_ATTR = "FormationID"

COMPUTED_SCHEDULE: List["ScheduleEntry"] = []
_UNSET = object()


@dataclass
class ScheduleEntry:
    tree_name: str
    node_name: str
    start: int
    end: int
    collection: Optional[bpy.types.Collection]


def _ensure_int_attribute(mesh: bpy.types.Mesh, name: str) -> bpy.types.Attribute:
    attr = mesh.attributes.get(name)
    if attr and attr.domain == 'POINT' and attr.data_type == 'INT':
        return attr
    if attr:
        mesh.attributes.remove(attr)
    return mesh.attributes.new(name=name, type='INT', domain='POINT')


def _has_valid_int_attr(mesh: bpy.types.Mesh, name: str) -> bool:
    attr = mesh.attributes.get(name)
    return bool(attr and attr.domain == 'POINT' and attr.data_type == 'INT' and len(attr.data) == len(mesh.vertices))


def _assign_initial_ids(mesh: bpy.types.Mesh) -> None:
    pair_attr = _ensure_int_attribute(mesh, PAIR_ID_ATTR)
    form_attr = mesh.attributes.get(FORMATION_ID_ATTR)
    if not form_attr or form_attr.domain != 'POINT' or form_attr.data_type != 'INT':
        form_attr = _ensure_int_attribute(mesh, FORMATION_ID_ATTR)

    for idx in range(len(mesh.vertices)):
        pair_attr.data[idx].value = idx
        form_attr.data[idx].value = idx


def _pair_vertices(prev_obj: bpy.types.Object, cur_obj: bpy.types.Object) -> None:
    prev_mesh = prev_obj.data
    cur_mesh = cur_obj.data
    if len(prev_mesh.vertices) != len(cur_mesh.vertices):
        return

    prev_pair = _ensure_int_attribute(prev_mesh, PAIR_ID_ATTR)
    cur_pair = _ensure_int_attribute(cur_mesh, PAIR_ID_ATTR)

    prev_coords = [prev_obj.matrix_world @ v.co for v in prev_mesh.vertices]
    kd = KDTree(len(prev_coords))
    for i, co in enumerate(prev_coords):
        kd.insert(co, i)
    kd.balance()

    used: set[int] = set()
    for idx, v in enumerate(cur_mesh.vertices):
        co = cur_obj.matrix_world @ v.co
        target_idx = None
        for (_, pidx, _) in kd.find_n(co, len(prev_coords)):
            if pidx not in used:
                target_idx = pidx
                break
        if target_idx is None:
            target_idx = idx
        used.add(target_idx)
        cur_pair.data[idx].value = prev_pair.data[target_idx].value


def _propagate_formation_ids(prev_mesh: bpy.types.Mesh, cur_mesh: bpy.types.Mesh) -> None:
    if _has_valid_int_attr(cur_mesh, FORMATION_ID_ATTR):
        return

    prev_form = _ensure_int_attribute(prev_mesh, FORMATION_ID_ATTR)
    prev_pair = _ensure_int_attribute(prev_mesh, PAIR_ID_ATTR)
    cur_pair = _ensure_int_attribute(cur_mesh, PAIR_ID_ATTR)
    cur_form = _ensure_int_attribute(cur_mesh, FORMATION_ID_ATTR)

    mapping: Dict[int, int] = {}
    for idx in range(len(prev_mesh.vertices)):
        mapping[prev_pair.data[idx].value] = prev_form.data[idx].value

    for idx in range(len(cur_mesh.vertices)):
        pid = cur_pair.data[idx].value
        cur_form.data[idx].value = mapping.get(pid, pid)


def _as_collection(value: Any) -> Optional[bpy.types.Collection]:
    if isinstance(value, bpy.types.Collection):
        return value
    return None


def _collect_mesh_objects(col: bpy.types.Collection) -> List[bpy.types.Object]:
    col = _as_collection(col)
    if col is None:
        return []
    meshes = [obj for obj in col.all_objects if obj.type == 'MESH']
    meshes.sort(key=lambda o: o.name)
    return meshes


def _assign_ids_for_collections(cols: Sequence[bpy.types.Collection]) -> None:
    prev_meshes: Optional[List[bpy.types.Object]] = None
    for col in cols:
        meshes = _collect_mesh_objects(col)
        if not meshes:
            continue

        if prev_meshes is None:
            for obj in meshes:
                _assign_initial_ids(obj.data)
        else:
            prev_map = {o.name: o for o in prev_meshes}
            for idx, obj in enumerate(meshes):
                pobj = prev_map.get(obj.name)
                if pobj is None:
                    pobj = prev_meshes[idx % len(prev_meshes)]
                _pair_vertices(pobj, obj)
                _propagate_formation_ids(pobj.data, obj.data)
        prev_meshes = meshes


def _count_collection_vertices(col: Optional[bpy.types.Collection]) -> int:
    col = _as_collection(col)
    if col is None:
        return -1
    count = 0
    for obj in col.all_objects:
        if obj.type == 'MESH' and obj.data is not None:
            count += len(obj.data.vertices)
    return count


def _is_flow_socket(sock: bpy.types.NodeSocket) -> bool:
    return getattr(sock, "bl_idname", "") == "FN_SocketFlow"


def _first_valid_link(sock: bpy.types.NodeSocket) -> Optional[bpy.types.NodeLink]:
    for link in sock.links:
        if link.is_valid:
            return link
    for link in sock.links:
        return link
    return None


def _socket_ui_value(sock: bpy.types.NodeSocket) -> Any:
    if hasattr(sock, "value"):
        return sock.value
    if hasattr(sock, "collection"):
        return sock.collection
    if hasattr(sock, "default_value"):
        return sock.default_value
    return _UNSET


def _find_input_socket(node: bpy.types.Node, name: str) -> Optional[bpy.types.NodeSocket]:
    if not hasattr(node, "inputs"):
        return None
    sock = node.inputs.get(name)
    if sock:
        return sock
    for candidate in node.inputs:
        if getattr(candidate, "name", None) == name or getattr(candidate, "identifier", None) == name or getattr(candidate, "label", None) == name:
            return candidate
    return None


def _eval_math_node(node: bpy.types.Node, a: Any, b: Any) -> float:
    try:
        aval = float(a) if a is not _UNSET and a is not None else 0.0
    except Exception:
        aval = 0.0
    try:
        bval = float(b) if b is not _UNSET and b is not None else 0.0
    except Exception:
        bval = 0.0

    op = getattr(node, "operation", "ADD")
    if op == "ADD":
        res = aval + bval
    elif op == "SUBTRACT":
        res = aval - bval
    elif op == "MULTIPLY":
        res = aval * bval
    elif op == "DIVIDE":
        res = aval / bval if bval != 0.0 else 0.0
    elif op == "MAX":
        res = max(aval, bval)
    elif op == "MIN":
        res = min(aval, bval)
    else:
        res = 0.0

    if getattr(node, "clamp_result", False):
        res = max(0.0, min(1.0, res))
    return res


def _eval_socket_value(
    sock: Optional[bpy.types.NodeSocket],
    cache: Dict[int, Any],
    stack: set[int],
) -> Any:
    if sock is None or _is_flow_socket(sock):
        return _UNSET

    sock_id = id(sock)
    if sock_id in cache:
        return cache[sock_id]
    if sock_id in stack:
        return _UNSET

    stack.add(sock_id)
    value: Any = _UNSET
    if sock.is_output:
        node = sock.node
        bl_idname = getattr(node, "bl_idname", "")
        if bl_idname == "FN_ValueNode":
            value = getattr(node, "value", _UNSET)
        elif bl_idname == "FN_MathNode":
            a_val = _eval_socket_value(node.inputs.get("A"), cache, stack)
            b_val = _eval_socket_value(node.inputs.get("B"), cache, stack)
            value = _eval_math_node(node, a_val, b_val)
        elif bl_idname == "FN_CollectionNode":
            value = getattr(node, "collection", _UNSET)
        else:
            value = _socket_ui_value(sock)
    else:
        if sock.links:
            link = _first_valid_link(sock)
            if link and link.from_socket:
                value = _eval_socket_value(link.from_socket, cache, stack)
        if value is _UNSET:
            value = _socket_ui_value(sock)

    stack.remove(sock_id)
    cache[sock_id] = value
    return value


def _resolve_input_value(
    node: bpy.types.Node,
    socket_name: str,
    cache: Dict[int, Any],
    default: Any,
    fallback_attr: Optional[str] = None,
) -> Any:
    sock = _find_input_socket(node, socket_name)
    if sock:
        value = _eval_socket_value(sock, cache, set())
        if value is not _UNSET:
            return value
    if fallback_attr and hasattr(node, fallback_attr):
        return getattr(node, fallback_attr)
    return default


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return default


def _flow_edges(tree: bpy.types.NodeTree) -> Dict[bpy.types.Node, List[bpy.types.Node]]:
    edges: Dict[bpy.types.Node, List[bpy.types.Node]] = {}
    for node in tree.nodes:
        targets: List[bpy.types.Node] = []
        for out_sock in node.outputs:
            if not _is_flow_socket(out_sock):
                continue
            for link in out_sock.links:
                if not link.is_valid:
                    continue
                target = link.to_node
                if target is None:
                    continue
                targets.append(target)
        if targets:
            edges[node] = targets
    return edges


def _flow_reachable(start_node: bpy.types.Node, edges: Dict[bpy.types.Node, List[bpy.types.Node]]) -> List[bpy.types.Node]:
    reachable: List[bpy.types.Node] = []
    seen: set[bpy.types.Node] = set()
    stack: List[bpy.types.Node] = [start_node]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        reachable.append(node)
        for target in edges.get(node, []):
            if target not in seen:
                stack.append(target)
    return reachable


def _duration_frames(duration_value: Any) -> int:
    try:
        frames = int(math.ceil(float(duration_value)))
    except Exception:
        frames = 0
    return max(0, frames)


def compute_schedule(context: Optional[bpy.types.Context] = None) -> List[ScheduleEntry]:
    global COMPUTED_SCHEDULE

    schedule: List[ScheduleEntry] = []

    trees = [ng for ng in bpy.data.node_groups if getattr(ng, "bl_idname", "") == "FN_FormationTree"]
    for tree in trees:
        value_cache: Dict[int, Any] = {}
        # clear cached start frames and refresh collection vertex counts before computing
        for node in tree.nodes:
            if hasattr(node, "computed_start_frame"):
                try:
                    node.computed_start_frame = -1
                except Exception:
                    pass
            if hasattr(node, "collection_vertex_count"):
                try:
                    col = _resolve_input_value(node, "Collection", value_cache, None, "collection")
                    node.collection_vertex_count = _count_collection_vertices(col)
                except Exception:
                    node.collection_vertex_count = -1

        start_nodes = [n for n in tree.nodes if n.bl_idname == "FN_StartNode"]
        if not start_nodes:
            continue

        start_node = start_nodes[0]
        edges = _flow_edges(tree)
        reachable = _flow_reachable(start_node, edges)
        if not reachable:
            continue

        in_degree: Dict[bpy.types.Node, int] = {node: 0 for node in reachable}
        for node in reachable:
            for target in edges.get(node, []):
                if target in in_degree:
                    in_degree[target] += 1

        queue: List[bpy.types.Node] = [node for node in reachable if in_degree[node] == 0]
        if start_node in queue:
            queue.remove(start_node)
            queue.insert(0, start_node)

        incoming_max: Dict[bpy.types.Node, int] = {}
        node_start: Dict[bpy.types.Node, int] = {}
        node_end: Dict[bpy.types.Node, int] = {}

        start_value = _resolve_input_value(start_node, "Start Frame", value_cache, 0, "start_frame")
        node_start[start_node] = _coerce_int(start_value, 0)

        ordered: List[bpy.types.Node] = []
        while queue:
            node = queue.pop(0)
            ordered.append(node)
            start = node_start.get(node)
            if start is None:
                start = incoming_max.get(node, 0)
                node_start[node] = start
            duration_value = _resolve_input_value(node, "Duration", value_cache, 0.0, "duration")
            dur = _duration_frames(duration_value)
            end = start + dur
            node_end[node] = end

            for target in edges.get(node, []):
                if target not in in_degree:
                    continue
                prev = incoming_max.get(target)
                if prev is None or end > prev:
                    incoming_max[target] = end
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    node_start[target] = incoming_max.get(target, 0)
                    queue.append(target)

        for node in reachable:
            if node in ordered:
                continue
            start = incoming_max.get(node, 0)
            node_start[node] = start
            duration_value = _resolve_input_value(node, "Duration", value_cache, 0.0, "duration")
            dur = _duration_frames(duration_value)
            node_end[node] = start + dur
            ordered.append(node)

        if hasattr(start_node, "computed_start_frame"):
            try:
                start_node.computed_start_frame = int(node_start[start_node])
            except Exception:
                pass

        for node in ordered:
            if node == start_node:
                continue
            start = node_start.get(node, 0)
            end = node_end.get(node, start)
            col = _resolve_input_value(node, "Collection", value_cache, None, "collection")
            col = _as_collection(col)
            schedule.append(ScheduleEntry(tree.name, node.name, start, end, col))
            if hasattr(node, "computed_start_frame"):
                try:
                    node.computed_start_frame = int(start)
                except Exception:
                    node.computed_start_frame = -1

    ordered_cols: List[bpy.types.Collection] = []
    for entry in schedule:
        if entry.collection:
            ordered_cols.append(entry.collection)

    if ordered_cols:
        _assign_ids_for_collections(ordered_cols)

    COMPUTED_SCHEDULE = schedule
    return schedule


def get_cached_schedule() -> List[ScheduleEntry]:
    return list(COMPUTED_SCHEDULE)


class FN_OT_calculate_schedule(bpy.types.Operator, FN_Register):
    bl_idname = "fn.calculate_schedule"
    bl_label = "Calculate Formation"
    bl_description = "Assign PairID/FormationID and build schedule from Formation nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            schedule = compute_schedule(context)
            self.report({'INFO'}, f"Schedule entries: {len(schedule)}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Calculate failed: {e}")
            return {'CANCELLED'}


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

        drone_count = None
        if tree:
            for node in tree.nodes:
                if getattr(node, "bl_idname", "") == "FN_StartNode":
                    drone_count = getattr(node, "drone_count", None)
                    break

        try:
            from liberadronecore.system import sence_setup
            if drone_count is not None:
                try:
                    drone_count = max(1, int(drone_count))
                except Exception:
                    drone_count = None
            if drone_count is not None:
                sence_setup.ANY_MESH_VERTS = drone_count
                sence_setup.init_scene_env(n_verts=drone_count)
            else:
                sence_setup.init_scene_env()
            self.report({'INFO'}, "Setup completed")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Setup failed: {e}")
            return {'CANCELLED'}


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
                try:
                    sock.collection = col
                except Exception:
                    pass
        if hasattr(node, "collection"):
            try:
                node.collection = col
            except Exception:
                pass
        if hasattr(node, "collection_vertex_count"):
            try:
                node.collection_vertex_count = _count_collection_vertices(col)
            except Exception:
                node.collection_vertex_count = -1
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
        if COMPUTED_SCHEDULE:
            layout.label(text=f"Cached entries: {len(COMPUTED_SCHEDULE)}")

        node = getattr(context, "active_node", None)
        if node:
            box = layout.box()
            box.label(text="Active Node")
            box.prop(node, "label", text="Label")
            op = box.operator("fn.create_collection_from_label", text="Create Collection")
            op.node_name = node.name
