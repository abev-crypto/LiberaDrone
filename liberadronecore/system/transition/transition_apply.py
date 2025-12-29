from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import bpy
from mathutils import Vector

from liberadronecore.formation import fn_parse, fn_parse_pairing
from liberadronecore.formation.fn_parse_pairing import PAIR_ATTR_NAME, _collect_mesh_objects
from liberadronecore.system.transition import bakedt, copyloc, vat_gn
from liberadronecore.system.vat import create_vat


@dataclass
class TransitionContext:
    node: bpy.types.Node
    tree: bpy.types.NodeTree
    scene: bpy.types.Scene
    start_frame: int
    end_frame: int
    fps: float
    prev_positions: List[Vector]
    next_positions: List[Vector]


def _ensure_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
    elif col.name not in scene.collection.children:
        scene.collection.children.link(col)
    return col


def _link_object_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)


def _remove_collection_recursive(col: bpy.types.Collection) -> None:
    for child in list(col.children):
        _remove_collection_recursive(child)
    for obj in list(col.objects):
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except TypeError:
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            bpy.data.objects.remove(obj)
    try:
        bpy.data.collections.remove(col, do_unlink=True)
    except TypeError:
        bpy.data.collections.remove(col)


def _purge_transition_collections(node_name: str) -> None:
    base_name = f"Transition_{node_name}"
    for col in list(bpy.data.collections):
        if col.name == base_name or col.name.startswith(f"PT_{node_name}_"):
            _remove_collection_recursive(col)


def _set_transition_collection(node: bpy.types.Node, scene: bpy.types.Scene) -> None:
    if not hasattr(node, "collection"):
        return
    col = _ensure_collection(scene, f"Transition_{node.name}")
    try:
        node.collection = col
    except Exception:
        pass


def _create_point_mesh(name: str, positions: Sequence[Vector]) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    verts = [(float(p.x), float(p.y), float(p.z)) for p in positions]
    mesh.from_pydata(verts, [], [])
    mesh.update()
    return mesh


def _ensure_point_attributes(mesh: bpy.types.Mesh) -> None:
    pair_attr = fn_parse_pairing._ensure_int_point_attr(mesh, fn_parse_pairing.PAIR_ATTR_NAME)
    form_attr = fn_parse_pairing._ensure_int_point_attr(mesh, fn_parse_pairing.FORMATION_ATTR_NAME)
    values = list(range(len(mesh.vertices)))
    pair_attr.data.foreach_set("value", values)
    form_attr.data.foreach_set("value", values)


def _ensure_point_object(
    name: str,
    positions: Sequence[Vector],
    collection: bpy.types.Collection,
    *,
    update: bool,
) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        mesh = _create_point_mesh(name, positions)
        _ensure_point_attributes(mesh)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj

    if update:
        mesh = _create_point_mesh(name, positions)
        _ensure_point_attributes(mesh)
        old_mesh = obj.data
        obj.data = mesh
        if old_mesh and old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)

    _ensure_point_attributes(obj.data)
    _link_object_to_collection(obj, collection)
    return obj


def _resolve_node_collection(node: bpy.types.Node) -> Optional[bpy.types.Collection]:
    col = fn_parse._resolve_input_value(node, "Collection", None, "collection")
    return fn_parse._as_collection(col)


def _collect_positions_for_collection(
    col: bpy.types.Collection,
    frame: int,
    depsgraph: bpy.types.Depsgraph,
    *,
    require_pair_id: bool,
) -> Dict[int, Vector]:
    positions: Dict[int, Vector] = {}
    meshes = _collect_mesh_objects(col)
    for obj in meshes:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        attr = eval_mesh.attributes.get(PAIR_ATTR_NAME) if eval_mesh else None
        if not attr or attr.domain != 'POINT' or attr.data_type != 'INT':
            if eval_obj and eval_mesh:
                eval_obj.to_mesh_clear()
            if require_pair_id:
                raise RuntimeError(f"pair_id attribute missing on {obj.name}")
            continue
        pair_ids = [0] * len(eval_mesh.vertices)
        attr.data.foreach_get("value", pair_ids)
        for idx, vtx in enumerate(eval_mesh.vertices):
            pid = pair_ids[idx]
            if pid in positions:
                continue
            positions[pid] = eval_obj.matrix_world @ vtx.co
        eval_obj.to_mesh_clear()
    return positions


def _collect_positions_for_nodes(
    nodes: Sequence[bpy.types.Node],
    entry_map: Dict[str, fn_parse.ScheduleEntry],
    frame_selector,
    scene: bpy.types.Scene,
    depsgraph: bpy.types.Depsgraph,
) -> Dict[int, Vector]:
    positions: Dict[int, Vector] = {}
    for node in nodes:
        entry = entry_map.get(node.name)
        if not entry or not entry.collection:
            continue
        frame = frame_selector(entry)
        scene.frame_set(frame)
        positions.update(_collect_positions_for_collection(entry.collection, frame, depsgraph, require_pair_id=True))
    return positions


def _node_tree_from_context(context, node_name: str) -> Tuple[Optional[bpy.types.NodeTree], Optional[bpy.types.Node]]:
    tree = None
    node = None
    if context and getattr(context, "space_data", None) and getattr(context.space_data, "edit_tree", None):
        tree = context.space_data.edit_tree
        if tree:
            node = tree.nodes.get(node_name)

    if node is None:
        for ng in bpy.data.node_groups:
            if getattr(ng, "bl_idname", "") != "FN_FormationTree":
                continue
            node = ng.nodes.get(node_name)
            if node:
                tree = ng
                break

    return tree, node


def _build_transition_context(node: bpy.types.Node, context) -> TransitionContext:
    tree = node.id_data
    scene = context.scene if context else bpy.context.scene
    depsgraph = context.evaluated_depsgraph_get() if context else bpy.context.evaluated_depsgraph_get()

    schedule = fn_parse.compute_schedule(context)
    if getattr(node, "error_message", ""):
        raise RuntimeError(node.error_message)
    entry_map = {entry.node_name: entry for entry in schedule if entry.tree_name == tree.name}

    edges = fn_parse._flow_edges(tree)
    reverse_edges = fn_parse._flow_reverse_edges(edges)
    prev_nodes = fn_parse._find_prev_formations(node, reverse_edges)
    next_nodes = fn_parse._find_next_formations(node, edges)
    if not prev_nodes or not next_nodes:
        raise RuntimeError("Missing previous/next formation nodes")

    original_frame = scene.frame_current

    def _prev_frame(entry: fn_parse.ScheduleEntry) -> int:
        if entry.end > entry.start:
            return max(entry.start, entry.end - 1)
        return entry.start

    prev_positions = _collect_positions_for_nodes(
        prev_nodes,
        entry_map,
        _prev_frame,
        scene,
        depsgraph,
    )
    next_positions = _collect_positions_for_nodes(
        next_nodes,
        entry_map,
        lambda entry: entry.start,
        scene,
        depsgraph,
    )

    scene.frame_set(original_frame)

    common_ids = sorted(set(prev_positions) & set(next_positions))
    if not common_ids:
        raise RuntimeError("No matching pair_id vertices found")

    prev_list = [prev_positions[i] for i in common_ids]
    next_list = [next_positions[i] for i in common_ids]

    start_frame = int(getattr(node, "computed_start_frame", 0) or 0)
    duration_value = fn_parse._resolve_input_value(node, "Duration", 0.0, "duration")
    duration = fn_parse._duration_frames(duration_value)
    if duration <= 0:
        raise RuntimeError("Duration is 0")

    fps = scene.render.fps / scene.render.fps_base if scene.render.fps_base else float(scene.render.fps)
    end_frame = start_frame + duration

    return TransitionContext(
        node=node,
        tree=tree,
        scene=scene,
        start_frame=start_frame,
        end_frame=end_frame,
        fps=fps,
        prev_positions=prev_list,
        next_positions=next_list,
    )


def _keyframe_blend(ctrl: bpy.types.Object, start_frame: int, end_frame: int) -> None:
    ctrl[copyloc.PROP_NAME] = 0.0
    ctrl.keyframe_insert(data_path=f'["{copyloc.PROP_NAME}"]', frame=start_frame)
    ctrl[copyloc.PROP_NAME] = 1.0
    ctrl.keyframe_insert(data_path=f'["{copyloc.PROP_NAME}"]', frame=end_frame)

    ad = ctrl.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            if fc.data_path != f'["{copyloc.PROP_NAME}"]':
                continue
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
                kp.handle_left_type = 'VECTOR'
                kp.handle_right_type = 'VECTOR'


def _grid_positions(
    prev_positions: Sequence[Vector],
    next_positions: Sequence[Vector],
    spacing: float,
) -> List[Vector]:
    if spacing <= 0.0:
        spacing = 0.5

    def _bounds(pts):
        min_v = Vector((float("inf"), float("inf"), float("inf")))
        max_v = Vector((float("-inf"), float("-inf"), float("-inf")))
        for p in pts:
            min_v.x = min(min_v.x, p.x)
            min_v.y = min(min_v.y, p.y)
            min_v.z = min(min_v.z, p.z)
            max_v.x = max(max_v.x, p.x)
            max_v.y = max(max_v.y, p.y)
            max_v.z = max(max_v.z, p.z)
        return min_v, max_v

    prev_min, prev_max = _bounds(prev_positions)
    next_min, next_max = _bounds(next_positions)
    mid_min = (prev_min + next_min) * 0.5
    mid_max = (prev_max + next_max) * 0.5

    size = mid_max - mid_min
    steps = Vector((
        max(1, int(round(size.x / spacing))),
        max(1, int(round(size.y / spacing))),
        max(1, int(round(size.z / spacing))),
    ))

    if steps.x <= 0:
        steps.x = 1
    if steps.y <= 0:
        steps.y = 1
    if steps.z <= 0:
        steps.z = 1

    points: List[Vector] = []
    for ix in range(int(steps.x) + 1):
        for iy in range(int(steps.y) + 1):
            for iz in range(int(steps.z) + 1):
                frac = Vector((
                    ix / steps.x if steps.x else 0.0,
                    iy / steps.y if steps.y else 0.0,
                    iz / steps.z if steps.z else 0.0,
                ))
                points.append(mid_min.lerp(mid_max, frac))

    center = (mid_min + mid_max) * 0.5
    points.sort(key=lambda p: (p - center).length)

    count = len(prev_positions)
    if len(points) < count:
        while len(points) < count:
            points.append(center.copy())
    return points[:count]


def _apply_auto(ctx: TransitionContext) -> str:
    tracks = bakedt.build_tracks_from_positions(
        ctx.prev_positions,
        ctx.next_positions,
        ctx.start_frame,
        ctx.end_frame,
        ctx.fps,
    )

    prefix = f"Transition_{ctx.node.name}"
    pos_img, _col_img, pos_min, pos_max, duration, drone_count = create_vat.build_vat_images_from_tracks(
        tracks,
        ctx.fps,
        image_name_prefix=prefix,
        recreate_images=True,
    )

    col = _ensure_collection(ctx.scene, prefix)
    obj = _ensure_point_object(
        f"{prefix}_VAT",
        ctx.prev_positions,
        col,
        update=True,
    )

    frame_count = max(int(duration) + 1, 1)
    group = vat_gn._create_gn_vat_group(
        pos_img,
        pos_min,
        pos_max,
        frame_count,
        drone_count,
        start_frame=ctx.start_frame,
        base_name=prefix,
    )
    vat_gn._apply_gn_to_object(obj, group)
    return f"Auto transition VAT created: {obj.name}"


def _apply_copyloc(ctx: TransitionContext, *, mode: str, split_count: int, grid_spacing: float) -> str:
    col = _ensure_collection(ctx.scene, f"Transition_{ctx.node.name}")

    start_obj = _ensure_point_object(
        f"{ctx.node.name}_Start",
        ctx.prev_positions,
        col,
        update=True,
    )
    end_obj = _ensure_point_object(
        f"{ctx.node.name}_End",
        ctx.next_positions,
        col,
        update=True,
    )

    mid_objects: List[bpy.types.Object] = []
    if mode == "SPLIT":
        count = max(1, int(split_count))
        for idx in range(count):
            frac = (idx + 1) / (count + 1)
            positions = [
                a.lerp(b, frac) for a, b in zip(ctx.prev_positions, ctx.next_positions)
            ]
            obj = _ensure_point_object(
                f"{ctx.node.name}_Split_{idx + 1}",
                positions,
                col,
                update=False,
            )
            mid_objects.append(obj)
    elif mode == "GRID":
        positions = _grid_positions(ctx.prev_positions, ctx.next_positions, grid_spacing)
        obj = _ensure_point_object(
            f"{ctx.node.name}_Grid",
            positions,
            col,
            update=False,
        )
        mid_objects.append(obj)

    chain = [start_obj] + mid_objects + [end_obj]

    for idx in range(len(chain) - 1):
        a = chain[idx]
        b = chain[idx + 1]
        ctrl, _ = copyloc.build_copyloc(
            a,
            b,
            collection_name=f"PT_{ctx.node.name}_{idx + 1}",
            controller_name=f"PT_CTRL_{ctx.node.name}_{idx + 1}",
            clear_old=True,
        )
        _keyframe_blend(ctrl, ctx.start_frame, ctx.end_frame)

    return f"CopyLoc transition created: steps={len(chain) - 1}"


def apply_transition_by_node_name(node_name: str, context=None) -> Tuple[bool, str]:
    tree, node = _node_tree_from_context(context, node_name)
    if node is None:
        return False, "Node not found"
    try:
        return apply_transition(node, context)
    except Exception as exc:
        return False, str(exc)


def apply_transition(node: bpy.types.Node, context=None) -> Tuple[bool, str]:
    ctx = _build_transition_context(node, context)
    _purge_transition_collections(node.name)
    if hasattr(node, "collection"):
        try:
            node.collection = None
        except Exception:
            pass
    mode = getattr(node, "mode", "AUTO")
    if mode == "AUTO":
        message = _apply_auto(ctx)
        _set_transition_collection(node, ctx.scene)
        return True, message

    copyloc_mode = getattr(node, "copyloc_mode", "NORMAL")
    split_count = fn_parse._resolve_input_value(node, "Num", getattr(node, "split_count", 1), "split_count")
    grid_spacing = getattr(node, "grid_spacing", 0.5)
    message = _apply_copyloc(
        ctx,
        mode=copyloc_mode,
        split_count=split_count,
        grid_spacing=grid_spacing,
    )
    _set_transition_collection(node, ctx.scene)
    return True, message
