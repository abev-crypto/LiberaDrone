from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Vector

from liberadronecore.formation import fn_parse, fn_parse_pairing
from liberadronecore.formation.fn_parse_pairing import _collect_mesh_objects
from liberadronecore.system.transition import bakedt, copyloc, vat_gn
from liberadronecore.system.vat import create_vat
from liberadronecore.util import image_util
from liberadronecore.util import pair_id


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
    pair_ids: List[int]


def _ensure_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
    elif col.name not in scene.collection.children:
        scene.collection.children.link(col)
    return col


def _hide_collection(col: bpy.types.Collection) -> None:
    if col is None:
        return
    for attr in ("hide_viewport", "hide_render", "hide_select"):
        if hasattr(col, attr):
            setattr(col, attr, True)
def _link_object_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)


def _remove_collection_recursive(col: bpy.types.Collection) -> None:
    for child in list(col.children):
        _remove_collection_recursive(child)
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col, do_unlink=True)
def _transition_base_name(node: bpy.types.Node) -> str:
    label = (getattr(node, "label", "") or "").strip()
    return label if label else node.name


def _transition_collection_name(node: bpy.types.Node) -> str:
    return f"Transition_{_transition_base_name(node)}"


def _purge_transition_collections(node: bpy.types.Node) -> None:
    names: set[str] = {f"Transition_{node.name}"}
    label = (getattr(node, "label", "") or "").strip()
    if label:
        names.add(f"Transition_{label}")
    for col in list(bpy.data.collections):
        if col.name in names or col.name.startswith(f"PT_{node.name}_"):
            _remove_collection_recursive(col)


def purge_transition_nodes(nodes: Sequence[bpy.types.Node]) -> None:
    removed: set[str] = set()
    for node in nodes:
        _purge_transition_collections(node)
        col = getattr(node, "collection", None)
        if col:
            col_name = col.name
            if col_name and col_name not in removed:
                _remove_collection_recursive(col)
                removed.add(col_name)
        if hasattr(node, "collection"):
            node.collection = None
def _set_transition_collection(node: bpy.types.Node, scene: bpy.types.Scene) -> None:
    if not hasattr(node, "collection"):
        return
    col = _ensure_collection(scene, _transition_collection_name(node))
    _hide_collection(col)
    node.collection = col
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


def _set_pair_ids(mesh: bpy.types.Mesh, pair_ids: Sequence[int]) -> None:
    attr = fn_parse_pairing._ensure_int_point_attr(mesh, fn_parse_pairing.PAIR_ATTR_NAME)
    if len(attr.data) != len(pair_ids):
        return
    attr.data.foreach_set("value", list(pair_ids))


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
    collect_form_ids: bool = False,
    as_numpy: bool = False,
) -> Tuple[List[Vector], Optional[List[int]], Optional[List[int]]]:
    positions: List[Vector] = []
    positions_np: list[np.ndarray] = []
    pair_ids: List[int] | None = []
    form_ids: List[int] | None = [] if collect_form_ids else None
    pairs_ok = True
    forms_ok = True
    meshes = _collect_mesh_objects(col)
    for obj in meshes:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        if as_numpy:
            count = len(eval_mesh.vertices)
            if count:
                coords = np.empty(count * 3, dtype=np.float32)
                eval_mesh.vertices.foreach_get("co", coords)
                coords = coords.reshape((count, 3))
                mw = np.asarray(eval_obj.matrix_world, dtype=np.float32)
                world = coords @ mw[:3, :3].T + mw[:3, 3]
                positions_np.append(world)
        else:
            for vtx in eval_mesh.vertices:
                positions.append(eval_obj.matrix_world @ vtx.co)
        if pairs_ok and pair_ids is not None:
            attr = eval_mesh.attributes.get(fn_parse_pairing.PAIR_ATTR_NAME)
            if (
                attr is None
                or attr.data_type != 'INT'
                or attr.domain != 'POINT'
                or len(attr.data) != len(eval_mesh.vertices)
            ):
                attr = obj.data.attributes.get(fn_parse_pairing.PAIR_ATTR_NAME)
            if (
                attr is None
                or attr.data_type != 'INT'
                or attr.domain != 'POINT'
                or len(attr.data) != len(eval_mesh.vertices)
            ):
                pairs_ok = False
            else:
                values = [0] * len(eval_mesh.vertices)
                attr.data.foreach_get("value", values)
                pair_ids.extend(values)
        if collect_form_ids and forms_ok and form_ids is not None:
            attr = eval_mesh.attributes.get(fn_parse_pairing.FORMATION_ATTR_NAME)
            if (
                attr is None
                or attr.data_type != 'INT'
                or attr.domain != 'POINT'
                or len(attr.data) != len(eval_mesh.vertices)
            ):
                attr = obj.data.attributes.get(fn_parse_pairing.FORMATION_ATTR_NAME)
            if (
                attr is None
                or attr.data_type != 'INT'
                or attr.domain != 'POINT'
                or len(attr.data) != len(eval_mesh.vertices)
            ):
                forms_ok = False
            else:
                values = [0] * len(eval_mesh.vertices)
                attr.data.foreach_get("value", values)
                form_ids.extend(values)
        eval_obj.to_mesh_clear()
    if as_numpy:
        positions = np.concatenate(positions_np, axis=0) if positions_np else np.empty((0, 3), dtype=np.float32)
    if not pairs_ok:
        pair_ids = None
    if collect_form_ids and not forms_ok:
        form_ids = None
    return positions, pair_ids, form_ids


def _collect_positions_for_nodes(
    nodes: Sequence[bpy.types.Node],
    entry_map: Dict[str, fn_parse.ScheduleEntry],
    frame_selector,
    scene: bpy.types.Scene,
    depsgraph: bpy.types.Depsgraph,
) -> Tuple[List[Vector], Optional[List[int]], Optional[List[int]]]:
    positions: List[Vector] = []
    pair_ids: List[int] | None = []
    pairs_ok = True
    form_ids: List[int] | None = []
    forms_ok = True
    for node in nodes:
        entry = entry_map.get(node.name)
        if not entry or not entry.collection:
            continue
        frame = frame_selector(entry)
        scene.frame_set(frame)
        pos, pairs, forms = _collect_positions_for_collection(
            entry.collection,
            frame,
            depsgraph,
            collect_form_ids=True,
        )
        positions.extend(pos)
        if pairs_ok:
            if pairs is None:
                pairs_ok = False
            elif pair_ids is not None:
                pair_ids.extend(pairs)
        if forms_ok:
            if forms is None:
                forms_ok = False
            elif form_ids is not None:
                form_ids.extend(forms)
    if not pairs_ok:
        pair_ids = None
    if not forms_ok:
        form_ids = None
    return positions, pair_ids, form_ids


def _update_transition_move_stats(
    node: bpy.types.Node,
    prev_positions: Sequence[Vector],
    next_positions: Sequence[Vector],
) -> None:
    if not hasattr(node, "max_move_up"):
        return
    if not prev_positions or not next_positions:
        node.max_move_up = -1.0
        node.max_move_down = -1.0
        node.max_move_horiz = -1.0
        return
    max_up = 0.0
    max_down = 0.0
    max_horiz = 0.0
    for prev, nxt in zip(prev_positions, next_positions):
        dx = float(nxt.x - prev.x)
        dy = float(nxt.y - prev.y)
        dz = float(nxt.z - prev.z)
        if dz > max_up:
            max_up = dz
        if -dz > max_down:
            max_down = -dz
        horiz = math.hypot(dx, dy)
        if horiz > max_horiz:
            max_horiz = horiz
    node.max_move_up = max_up
    node.max_move_down = max_down
    node.max_move_horiz = max_horiz
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

    schedule = fn_parse.compute_schedule(context, assign_pairs=False)
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

    prev_positions, _prev_pair_ids, prev_form_ids = _collect_positions_for_nodes(
        prev_nodes,
        entry_map,
        _prev_frame,
        scene,
        depsgraph,
    )
    next_positions, next_pair_ids, _next_form_ids = _collect_positions_for_nodes(
        next_nodes,
        entry_map,
        lambda entry: entry.start,
        scene,
        depsgraph,
    )

    scene.frame_set(original_frame)

    if len(prev_positions) != len(next_positions):
        raise RuntimeError("Start/End vertex counts do not match")
    if not prev_positions:
        raise RuntimeError("No vertices found for transition")

    prev_list = list(prev_positions)
    next_list = list(next_positions)

    if prev_form_ids is None or not pair_id.is_pair_id_permutation(prev_form_ids, len(prev_list)):
        raise RuntimeError("formation_id not set on previous formation")
    if next_pair_ids is None or not pair_id.is_pair_id_permutation(next_pair_ids, len(next_list)):
        raise RuntimeError("pair_id not set on next formation")

    prev_list = pair_id.order_items_by_pair_id(list(prev_list), prev_form_ids)
    next_list = pair_id.order_items_by_pair_id(list(next_list), next_pair_ids)
    prev_form_ids = list(range(len(prev_list)))
    _update_transition_move_stats(node, prev_list, next_list)

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
        pair_ids=prev_form_ids,
    )


def _keyframe_constraint_influence(
    con: bpy.types.Constraint,
    bone_name: str,
    start_frame: int,
    end_frame: int,
) -> None:
    con.influence = 0.0
    con.keyframe_insert(data_path="influence", frame=start_frame)
    con.influence = 1.0
    con.keyframe_insert(data_path="influence", frame=end_frame)

    fcurve = None
    id_data = getattr(con, "id_data", None)
    ad = getattr(id_data, "animation_data", None) if id_data else None
    if ad and ad.action:
        data_path = f'pose.bones["{bone_name}"].constraints["{con.name}"].influence'
        for fc in ad.action.fcurves:
            if fc.data_path == data_path:
                fcurve = fc
                break
    if fcurve:
        for kp in fcurve.keyframe_points:
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
        scene=ctx.scene,
    )

    image_prefix = _transition_base_name(ctx.node)
    collection_name = _transition_collection_name(ctx.node)
    pos_img, pos_min, pos_max, duration, drone_count = create_vat.build_vat_images_from_tracks(
        tracks,
        ctx.fps,
        image_name_prefix=image_prefix,
        recreate_images=True,
    )
    image_util.save_image_to_scene_cache(
        pos_img,
        pos_img.name,
        "OPEN_EXR",
        scene=ctx.scene,
        use_float=True,
        colorspace="Non-Color",
        link=True,
    )

    col = _ensure_collection(ctx.scene, collection_name)
    obj = _ensure_point_object(
        f"{collection_name}_VAT",
        ctx.prev_positions,
        col,
        update=True,
    )
    _set_pair_ids(obj.data, ctx.pair_ids)

    frame_count = max(int(duration) + 1, 1)
    group = vat_gn._create_gn_vat_group(
        pos_img,
        pos_min,
        pos_max,
        frame_count,
        drone_count,
        start_frame=ctx.start_frame,
        base_name=collection_name,
    )
    vat_gn._apply_gn_to_object(obj, group)
    return f"Auto transition VAT created: {obj.name}"


def _stagger_tracks_by_distance(
    tracks: List[dict],
    prev_positions: Sequence[Vector],
    next_positions: Sequence[Vector],
    start_frame: int,
    end_frame: int,
    *,
    start_per_frame: int,
) -> None:
    if not tracks:
        return
    if start_per_frame <= 0:
        return
    total_frames = max(0, int(end_frame) - int(start_frame))
    if total_frames <= 0:
        return

    distances = []
    for idx, (prev, nxt) in enumerate(zip(prev_positions, next_positions)):
        distances.append((idx, (nxt - prev).length))
    distances.sort(key=lambda item: (item[1], item[0]))
    rank_by_index = {idx: rank for rank, (idx, _dist) in enumerate(distances)}

    for track_idx, track in enumerate(tracks):
        data = track.get("data") or []
        if not data:
            continue
        rank = rank_by_index.get(track_idx, 0)
        delay = int(rank // start_per_frame)
        if delay <= 0:
            continue
        available = max(1, total_frames - delay)
        scale = total_frames / available

        track_frames = max(0, len(data) - 1)
        base_x = [row.get("x", 0.0) for row in data]
        base_y = [row.get("y", 0.0) for row in data]
        base_z = [row.get("z", 0.0) for row in data]
        base_r = data[0].get("r", 255)
        base_g = data[0].get("g", 255)
        base_b = data[0].get("b", 255)

        new_data = []
        for f in range(int(start_frame), int(end_frame) + 1):
            if f - start_frame <= delay:
                x = base_x[0]
                y = base_y[0]
                z = base_z[0]
            else:
                t = start_frame + (f - start_frame - delay) * scale
                if t <= start_frame:
                    idx0 = 0
                    alpha = 0.0
                elif t >= end_frame:
                    idx0 = track_frames
                    alpha = 0.0
                else:
                    pos = t - start_frame
                    idx0 = int(math.floor(pos))
                    alpha = pos - idx0
                idx0 = max(0, min(idx0, track_frames))
                idx1 = min(idx0 + 1, track_frames)
                x = base_x[idx0] + (base_x[idx1] - base_x[idx0]) * alpha
                y = base_y[idx0] + (base_y[idx1] - base_y[idx0]) * alpha
                z = base_z[idx0] + (base_z[idx1] - base_z[idx0]) * alpha
            new_data.append(
                {
                    "frame": float(f),
                    "x": float(x),
                    "y": float(y),
                    "z": float(z),
                    "r": base_r,
                    "g": base_g,
                    "b": base_b,
                }
            )
        track["data"] = new_data


def _apply_construction(ctx: TransitionContext, *, start_per_frame: int) -> str:
    tracks = bakedt.build_tracks_from_positions(
        ctx.prev_positions,
        ctx.next_positions,
        ctx.start_frame,
        ctx.end_frame,
        ctx.fps,
        scene=ctx.scene,
    )
    _stagger_tracks_by_distance(
        tracks,
        ctx.prev_positions,
        ctx.next_positions,
        ctx.start_frame,
        ctx.end_frame,
        start_per_frame=start_per_frame,
    )

    image_prefix = _transition_base_name(ctx.node)
    collection_name = _transition_collection_name(ctx.node)
    pos_img, pos_min, pos_max, duration, drone_count = create_vat.build_vat_images_from_tracks(
        tracks,
        ctx.fps,
        image_name_prefix=image_prefix,
        recreate_images=True,
    )
    image_util.save_image_to_scene_cache(
        pos_img,
        pos_img.name,
        "OPEN_EXR",
        scene=ctx.scene,
        use_float=True,
        colorspace="Non-Color",
        link=True,
    )

    col = _ensure_collection(ctx.scene, collection_name)
    obj = _ensure_point_object(
        f"{collection_name}_VAT",
        ctx.prev_positions,
        col,
        update=True,
    )
    _set_pair_ids(obj.data, ctx.pair_ids)

    frame_count = max(int(duration) + 1, 1)
    group = vat_gn._create_gn_vat_group(
        pos_img,
        pos_min,
        pos_max,
        frame_count,
        drone_count,
        start_frame=ctx.start_frame,
        base_name=collection_name,
    )
    vat_gn._apply_gn_to_object(obj, group)
    return f"Construction transition VAT created: {obj.name}"


def _apply_copyloc(ctx: TransitionContext, *, mode: str, split_count: int, grid_spacing: float) -> str:
    output_col = _ensure_collection(ctx.scene, _transition_collection_name(ctx.node))
    targets_col = _ensure_collection(ctx.scene, f"PT_{ctx.node.name}_Targets")

    end_obj = _ensure_point_object(
        f"{ctx.node.name}_End",
        ctx.next_positions,
        targets_col,
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
                targets_col,
                update=False,
            )
            mid_objects.append(obj)
    elif mode == "GRID":
        positions = _grid_positions(ctx.prev_positions, ctx.next_positions, grid_spacing)
        obj = _ensure_point_object(
            f"{ctx.node.name}_Grid",
            positions,
            targets_col,
            update=False,
        )
        mid_objects.append(obj)

    targets = mid_objects + [end_obj]
    steps = len(targets)
    if steps <= 0:
        raise RuntimeError("No target meshes for CopyLoc.")

    arm_name = f"Transition_{ctx.node.name}_Armature"
    mesh_name = f"Transition_{ctx.node.name}_Mesh"
    arm_obj, mesh_obj = copyloc.build_armature_copyloc(
        ctx.prev_positions,
        targets,
        collection_name=output_col.name,
        armature_name=arm_name,
        mesh_name=mesh_name,
        clear_old=True,
    )
    _ensure_point_attributes(mesh_obj.data)
    _set_pair_ids(mesh_obj.data, ctx.pair_ids)

    frame_span = max(0, ctx.end_frame - ctx.start_frame)
    segment_frames = []
    for i in range(steps):
        seg_start = ctx.start_frame + int(round(i * frame_span / steps))
        seg_end = ctx.start_frame + int(round((i + 1) * frame_span / steps))
        seg_end = max(seg_end, seg_start)
        segment_frames.append((seg_start, seg_end))

    for bone in arm_obj.pose.bones:
        for idx in range(steps):
            con = bone.constraints.get(f"CopyLoc_{idx + 1}")
            if con is None:
                continue
            seg_start, seg_end = segment_frames[idx]
            _keyframe_constraint_influence(con, bone.name, seg_start, seg_end)

    return f"CopyLoc transition created: steps={steps}"


def apply_transition_by_node_name(node_name: str, context=None) -> Tuple[bool, str]:
    tree, node = _node_tree_from_context(context, node_name)
    if node is None:
        return False, "Node not found"
    return apply_transition(node, context)
def apply_transition(node: bpy.types.Node, context=None, *, assign_pairs_after: bool = True) -> Tuple[bool, str]:
    ctx = _build_transition_context(node, context)
    _purge_transition_collections(node)
    if hasattr(node, "collection"):
        node.collection = None
    mode = getattr(node, "mode", "AUTO")
    if mode == "AUTO":
        message = _apply_auto(ctx)
        _set_transition_collection(node, ctx.scene)
        fn_parse.compute_schedule(context, assign_pairs=assign_pairs_after)
        _update_transition_move_stats(ctx.node, ctx.prev_positions, ctx.next_positions)
        return True, message
    if mode == "CONSTRUCTION":
        start_per_frame = getattr(node, "construction_start_count", 1)
        start_per_frame = int(start_per_frame)
        message = _apply_construction(ctx, start_per_frame=max(1, start_per_frame))
        _set_transition_collection(node, ctx.scene)
        fn_parse.compute_schedule(context, assign_pairs=assign_pairs_after)
        _update_transition_move_stats(ctx.node, ctx.prev_positions, ctx.next_positions)
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
    fn_parse.compute_schedule(context, assign_pairs=assign_pairs_after)
    _update_transition_move_stats(ctx.node, ctx.prev_positions, ctx.next_positions)
    return True, message
