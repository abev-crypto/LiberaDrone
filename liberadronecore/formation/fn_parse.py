from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import bpy
from bpy.props import CollectionProperty, IntProperty, PointerProperty, StringProperty
from liberadronecore.formation.fn_parse_pairing import (
    _as_collection,
    _assign_formation_ids,
    _collect_mesh_objects,
    _collect_meshes_from_cols,
    _count_collection_vertices,
    _pair_from_previous,
    _seed_pair_ids,
)
from liberadronecore.reg.base_reg import RegisterBase

COMPUTED_SCHEDULE: List["ScheduleEntry"] = []
_UNSET = object()
_CACHED_SCENE_ID: Optional[int] = None
_CACHED_SCENE_VERSION: Optional[int] = None


@dataclass
class ScheduleEntry:
    tree_name: str
    node_name: str
    start: int
    end: int
    collection: Optional[bpy.types.Collection]


class FN_ScheduleEntryProperty(bpy.types.PropertyGroup):
    tree_name: StringProperty(name="Tree")
    node_name: StringProperty(name="Node")
    start: IntProperty(name="Start")
    end: IntProperty(name="End")
    collection: PointerProperty(type=bpy.types.Collection)


class FN_ScheduleStore(RegisterBase):
    @classmethod
    def register(cls) -> None:
        try:
            bpy.utils.register_class(FN_ScheduleEntryProperty)
        except ValueError:
            pass
        if not hasattr(bpy.types.Scene, "fn_schedule_entries"):
            bpy.types.Scene.fn_schedule_entries = CollectionProperty(type=FN_ScheduleEntryProperty)
        if not hasattr(bpy.types.Scene, "fn_schedule_version"):
            bpy.types.Scene.fn_schedule_version = IntProperty(name="Schedule Version", default=0)

    @classmethod
    def unregister(cls) -> None:
        if hasattr(bpy.types.Scene, "fn_schedule_entries"):
            del bpy.types.Scene.fn_schedule_entries
        if hasattr(bpy.types.Scene, "fn_schedule_version"):
            del bpy.types.Scene.fn_schedule_version
        try:
            bpy.utils.unregister_class(FN_ScheduleEntryProperty)
        except ValueError:
            pass


def _scene_id(scene: Optional[bpy.types.Scene]) -> Optional[int]:
    if scene is None:
        return None
    try:
        return int(scene.as_pointer())
    except Exception:
        return None


def _get_scene(context: Optional[bpy.types.Context]) -> Optional[bpy.types.Scene]:
    if context and getattr(context, "scene", None):
        return context.scene
    try:
        return bpy.context.scene
    except Exception:
        return None


def _store_schedule_in_scene(scene: Optional[bpy.types.Scene], schedule: List[ScheduleEntry]) -> None:
    global _CACHED_SCENE_ID, _CACHED_SCENE_VERSION
    if scene is None:
        return
    entries = getattr(scene, "fn_schedule_entries", None)
    if entries is None:
        return
    entries.clear()
    for entry in schedule:
        item = entries.add()
        item.tree_name = entry.tree_name
        item.node_name = entry.node_name
        item.start = int(entry.start)
        item.end = int(entry.end)
        if entry.collection is not None:
            item.collection = entry.collection
        else:
            item.collection = None
    if hasattr(scene, "fn_schedule_version"):
        try:
            scene.fn_schedule_version += 1
        except Exception:
            scene.fn_schedule_version = 1
    _CACHED_SCENE_ID = _scene_id(scene)
    _CACHED_SCENE_VERSION = getattr(scene, "fn_schedule_version", 0)


def _load_schedule_from_scene(scene: bpy.types.Scene) -> List[ScheduleEntry]:
    entries = getattr(scene, "fn_schedule_entries", None)
    if entries is None:
        return []
    schedule: List[ScheduleEntry] = []
    for item in entries:
        col = item.collection if isinstance(item.collection, bpy.types.Collection) else None
        schedule.append(ScheduleEntry(item.tree_name, item.node_name, int(item.start), int(item.end), col))
    return schedule

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
    aval = float(a) if a is not _UNSET and a is not None else 0.0
    bval = float(b) if b is not _UNSET and b is not None else 0.0

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
    stack: set[int],
) -> Any:
    if _is_flow_socket(sock):
        return _UNSET

    sock_id = id(sock)

    stack.add(sock_id)
    value: Any = _UNSET
    if sock.is_output:
        node = sock.node
        bl_idname = getattr(node, "bl_idname", "")
        if bl_idname == "FN_ValueNode":
            value = getattr(node, "value", _UNSET)
        elif bl_idname == "FN_MathNode":
            a_val = _eval_socket_value(node.inputs.get("A"), stack)
            b_val = _eval_socket_value(node.inputs.get("B"), stack)
            value = _eval_math_node(node, a_val, b_val)
        elif bl_idname == "FN_CollectionNode":
            value = getattr(node, "collection", _UNSET)
        elif bl_idname == "FN_VATCacheNode":
            value = getattr(node, "cache_collection", _UNSET)
        else:
            value = _socket_ui_value(sock)
    else:
        if sock.links:
            link = _first_valid_link(sock)
            if link and link.from_socket:
                value = _eval_socket_value(link.from_socket, stack)
        if value is _UNSET:
            value = _socket_ui_value(sock)
    stack.remove(sock_id)
    return value


def _resolve_input_value(
    node: bpy.types.Node,
    socket_name: str,
    default: Any,
    fallback_attr: Optional[str] = None,
) -> Any:
    sock = _find_input_socket(node, socket_name)
    if sock:
        value = _eval_socket_value(sock, set())
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


def _is_transition_node(node: bpy.types.Node) -> bool:
    return getattr(node, "bl_idname", "") in {
        "FN_TransitionNode",
        "FN_SplitTransitionNode",
        "FN_MergeTransitionNode",
    }


def _is_formation_node(node: bpy.types.Node) -> bool:
    return _find_input_socket(node, "Collection") is not None


def _flow_reverse_edges(edges: Dict[bpy.types.Node, List[bpy.types.Node]]) -> Dict[bpy.types.Node, List[bpy.types.Node]]:
    reverse: Dict[bpy.types.Node, List[bpy.types.Node]] = {}
    for src, targets in edges.items():
        for tgt in targets:
            reverse.setdefault(tgt, []).append(src)
    return reverse


def _find_prev_formations(
    node: bpy.types.Node,
    reverse_edges: Dict[bpy.types.Node, List[bpy.types.Node]],
) -> List[bpy.types.Node]:
    formations: List[bpy.types.Node] = []
    seen: set[bpy.types.Node] = set()
    stack: List[bpy.types.Node] = list(reverse_edges.get(node, []))
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if _is_formation_node(cur):
            formations.append(cur)
            continue
        stack.extend(reverse_edges.get(cur, []))
    return formations


def _find_next_formations(
    node: bpy.types.Node,
    edges: Dict[bpy.types.Node, List[bpy.types.Node]],
) -> List[bpy.types.Node]:
    formations: List[bpy.types.Node] = []
    seen: set[bpy.types.Node] = set()
    stack: List[bpy.types.Node] = list(edges.get(node, []))
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if _is_formation_node(cur):
            formations.append(cur)
            continue
        stack.extend(edges.get(cur, []))
    return formations


def _duration_frames(duration_value: Any) -> int:
    frames = int(math.ceil(float(duration_value)))
    return max(0, frames)


def _ensure_geometry_node_group(module, main_builder, target_name: str) -> Optional[bpy.types.NodeTree]:
    """Create or fetch a Geometry Nodes group using the generated builders."""
    node_tree_names: Dict[Any, str] = {}
    err_builder = getattr(module, "gn_drone_errorcheck_1_node_group", None)
    if callable(err_builder):
        existing_err = bpy.data.node_groups.get("GN_Drone_ErrorCheck")
        if existing_err is not None:
            node_tree_names[err_builder] = existing_err.name
        else:
            err_group = err_builder(node_tree_names)
            node_tree_names[err_builder] = getattr(err_group, "name", "GN_Drone_ErrorCheck")
    existing = bpy.data.node_groups.get(target_name)
    if existing is not None:
        node_tree_names[main_builder] = existing.name
        return existing
    created = main_builder(node_tree_names)
    if created is None:
        return None
    if created.name != target_name:
        created.name = target_name
    return bpy.data.node_groups.get(target_name) or created


def _attach_node_group(obj_name: str, node_group: Optional[bpy.types.NodeTree], modifier_name: str) -> bool:
    """Attach a geometry nodes modifier to the named object if possible."""
    if node_group is None:
        return False
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        return False
    mod = obj.modifiers.get(modifier_name)
    if mod is None or mod.type != 'NODES':
        mod = obj.modifiers.new(name=modifier_name, type='NODES')
    try:
        mod.node_group = node_group
        return True
    except Exception:
        return False


def compute_schedule(context: Optional[bpy.types.Context] = None, *, assign_pairs: bool = True) -> List[ScheduleEntry]:
    global COMPUTED_SCHEDULE, _CACHED_SCENE_ID, _CACHED_SCENE_VERSION

    schedule: List[ScheduleEntry] = []

    trees = [ng for ng in bpy.data.node_groups if getattr(ng, "bl_idname", "") == "FN_FormationTree"]
    for tree in trees:
        for node in tree.nodes:
            if hasattr(node, "computed_start_frame"):
                node.computed_start_frame = -1
            if hasattr(node, "collection_vertex_count"):
                col = _resolve_input_value(node, "Collection", None, "collection")
                node.collection_vertex_count = _count_collection_vertices(col)
            if hasattr(node, "error_message"):
                node.error_message = ""

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

        start_value = _resolve_input_value(start_node, "Start Frame", 0, "start_frame")
        start_offset = _coerce_int(start_value, 0)
        node_start[start_node] = 0  # keep traversal relative; apply start_offset when reporting

        ordered: List[bpy.types.Node] = []
        while queue:
            node = queue.pop(0)
            ordered.append(node)
            start = node_start.get(node)
            if start is None:
                start = incoming_max.get(node, 0)
                node_start[node] = start
            duration_value = _resolve_input_value(node, "Duration", 0.0, "duration")
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
            duration_value = _resolve_input_value(node, "Duration", 0.0, "duration")
            dur = _duration_frames(duration_value)
            node_end[node] = start + dur
            ordered.append(node)

        if hasattr(start_node, "computed_start_frame"):
            start_node.computed_start_frame = int(start_offset)

        for node in ordered:
            if node == start_node:
                continue
            start = node_start.get(node, 0)
            end = node_end.get(node, start)
            start_with_offset = start + start_offset
            end_with_offset = end + start_offset
            col = _resolve_input_value(node, "Collection", None, "collection")
            col = _as_collection(col)
            schedule.append(ScheduleEntry(tree.name, node.name, start_with_offset, end_with_offset, col))
            if hasattr(node, "computed_start_frame"):
                node.computed_start_frame = int(start_with_offset)

        formation_nodes = [n for n in reachable if _is_formation_node(n)]
        formation_cols: List[bpy.types.Collection] = []
        for node in formation_nodes:
            col = _resolve_input_value(node, "Collection", None, "collection")
            col = _as_collection(col)
            if col is not None:
                formation_cols.append(col)

        reverse_edges = _flow_reverse_edges(edges)
        transition_nodes = [n for n in reachable if _is_transition_node(n)]

        def _formation_count(node: bpy.types.Node) -> int:
            col = _resolve_input_value(node, "Collection", None, "collection")
            col = _as_collection(col)
            return _count_collection_vertices(col)

        drone_count = None
        start_drone = getattr(start_node, "drone_count", None)
        if start_drone is not None:
            drone_count = max(0, int(start_drone))

        if hasattr(start_node, "error_message"):
            next_nodes = _find_next_formations(start_node, edges)
            if not next_nodes:
                start_node.error_message = "No formation connected."
            else:
                counts = [_formation_count(n) for n in next_nodes]
                if any(c < 0 for c in counts):
                    start_node.error_message = "Missing collection for formation."
                else:
                    total = sum(counts)
                    if drone_count is not None and total != drone_count:
                        start_node.error_message = f"Drone count mismatch: {total} != {drone_count}"

        for node in transition_nodes:
            prev_nodes = _find_prev_formations(node, reverse_edges)
            next_nodes = _find_next_formations(node, edges)
            if not prev_nodes or not next_nodes:
                if hasattr(node, "error_message"):
                    node.error_message = "Missing previous/next formation."
                continue
            prev_counts = [_formation_count(n) for n in prev_nodes]
            next_counts = [_formation_count(n) for n in next_nodes]
            if any(c < 0 for c in prev_counts + next_counts):
                if hasattr(node, "error_message"):
                    node.error_message = "Missing collection for formation."
                continue
            if sum(prev_counts) != sum(next_counts):
                if hasattr(node, "error_message"):
                    node.error_message = f"Vertex count mismatch: {sum(prev_counts)} != {sum(next_counts)}"

        if formation_cols and assign_pairs:
            seen_cols: set[bpy.types.Collection] = set()
            ordered_unique: List[bpy.types.Collection] = []
            for col in formation_cols:
                if col not in seen_cols:
                    ordered_unique.append(col)
                    seen_cols.add(col)

            for col in ordered_unique:
                _assign_formation_ids(col, drone_count, force=True)

            pair_steps: List[tuple[int, List[bpy.types.Node], List[bpy.types.Node]]] = []
            seen_steps: set[tuple[frozenset[int], frozenset[int]]] = set()

            def _add_step(prev_nodes: List[bpy.types.Node], next_nodes: List[bpy.types.Node], sort_key: int) -> None:
                if not prev_nodes or not next_nodes:
                    return
                key = (frozenset(id(n) for n in prev_nodes), frozenset(id(n) for n in next_nodes))
                if key in seen_steps:
                    return
                seen_steps.add(key)
                pair_steps.append((sort_key, prev_nodes, next_nodes))

            if transition_nodes:
                for node in transition_nodes:
                    prev_nodes = _find_prev_formations(node, reverse_edges)
                    next_nodes = _find_next_formations(node, edges)
                    sort_key = getattr(node, "computed_start_frame", 0)
                    _add_step(prev_nodes, next_nodes, sort_key)

            for node in formation_nodes:
                if node not in edges:
                    continue
                for target in edges.get(node, []):
                    if _is_formation_node(target):
                        sort_key = getattr(node, "computed_start_frame", 0)
                        _add_step([node], [target], sort_key)

            pair_steps.sort(key=lambda item: item[0])

            root_formations: List[bpy.types.Node] = []
            for node in formation_nodes:
                if not _find_prev_formations(node, reverse_edges):
                    root_formations.append(node)

            for node in root_formations:
                col = _resolve_input_value(node, "Collection", None, "collection")
                col = _as_collection(col)
                if col is None:
                    continue
                meshes = _collect_mesh_objects(col)
                if meshes:
                    _seed_pair_ids(meshes)

            for _, prev_nodes, next_nodes in pair_steps:
                prev_cols: List[bpy.types.Collection] = []
                prev_seen: set[bpy.types.Collection] = set()
                for node in prev_nodes:
                    col = _resolve_input_value(node, "Collection", None, "collection")
                    col = _as_collection(col)
                    if col is not None and col not in prev_seen:
                        prev_cols.append(col)
                        prev_seen.add(col)
                next_cols: List[bpy.types.Collection] = []
                next_seen: set[bpy.types.Collection] = set()
                for node in next_nodes:
                    col = _resolve_input_value(node, "Collection", None, "collection")
                    col = _as_collection(col)
                    if col is not None and col not in next_seen:
                        next_cols.append(col)
                        next_seen.add(col)
                if not prev_cols or not next_cols:
                    continue
                prev_meshes = _collect_meshes_from_cols(prev_cols)
                next_meshes = _collect_meshes_from_cols(next_cols)
                if prev_meshes and next_meshes:
                    _pair_from_previous(prev_meshes, next_meshes)

    scene = _get_scene(context)
    _store_schedule_in_scene(scene, schedule)
    COMPUTED_SCHEDULE = schedule
    if scene is not None:
        _CACHED_SCENE_ID = _scene_id(scene)
        _CACHED_SCENE_VERSION = getattr(scene, "fn_schedule_version", 0)
    return schedule


def get_cached_schedule(scene: Optional[bpy.types.Scene] = None) -> List[ScheduleEntry]:
    global COMPUTED_SCHEDULE, _CACHED_SCENE_ID, _CACHED_SCENE_VERSION
    if scene is None:
        scene = _get_scene(None)
    if scene is None:
        return list(COMPUTED_SCHEDULE)

    scene_id = _scene_id(scene)
    scene_version = getattr(scene, "fn_schedule_version", 0)
    if COMPUTED_SCHEDULE and _CACHED_SCENE_ID == scene_id and _CACHED_SCENE_VERSION == scene_version:
        return list(COMPUTED_SCHEDULE)

    COMPUTED_SCHEDULE = _load_schedule_from_scene(scene)
    _CACHED_SCENE_ID = scene_id
    _CACHED_SCENE_VERSION = scene_version
    return list(COMPUTED_SCHEDULE)
