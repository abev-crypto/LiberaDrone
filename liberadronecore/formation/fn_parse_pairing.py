from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import bpy
from mathutils.kdtree import KDTree

PAIR_ID_ATTR = "PairID"
FORMATION_ID_ATTR = "FormationID"
FORMATION_ATTR_NAME = "formation_id"
PAIR_ATTR_NAME = "pair_id"


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

    values = list(range(len(mesh.vertices)))
    pair_attr.data.foreach_set("value", values)
    form_attr.data.foreach_set("value", values)


def _pair_vertices(prev_obj: bpy.types.Object, cur_obj: bpy.types.Object) -> None:
    prev_mesh = prev_obj.data
    cur_mesh = cur_obj.data
    if len(prev_mesh.vertices) != len(cur_mesh.vertices):
        return

    prev_pair = _ensure_int_attribute(prev_mesh, PAIR_ID_ATTR)
    cur_pair = _ensure_int_attribute(cur_mesh, PAIR_ID_ATTR)
    prev_values = [0] * len(prev_mesh.vertices)
    prev_pair.data.foreach_get("value", prev_values)

    prev_coords = [prev_obj.matrix_world @ v.co for v in prev_mesh.vertices]
    kd = KDTree(len(prev_coords))
    for i, co in enumerate(prev_coords):
        kd.insert(co, i)
    kd.balance()

    used: set[int] = set()
    cur_values = [0] * len(cur_mesh.vertices)
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
        cur_values[idx] = prev_values[target_idx]
    cur_pair.data.foreach_set("value", cur_values)


def _propagate_formation_ids(prev_mesh: bpy.types.Mesh, cur_mesh: bpy.types.Mesh) -> None:
    if _has_valid_int_attr(cur_mesh, FORMATION_ID_ATTR):
        return

    prev_form = _ensure_int_attribute(prev_mesh, FORMATION_ID_ATTR)
    prev_pair = _ensure_int_attribute(prev_mesh, PAIR_ID_ATTR)
    cur_pair = _ensure_int_attribute(cur_mesh, PAIR_ID_ATTR)
    cur_form = _ensure_int_attribute(cur_mesh, FORMATION_ID_ATTR)

    prev_pair_values = [0] * len(prev_mesh.vertices)
    prev_form_values = [0] * len(prev_mesh.vertices)
    prev_pair.data.foreach_get("value", prev_pair_values)
    prev_form.data.foreach_get("value", prev_form_values)
    mapping: Dict[int, int] = dict(zip(prev_pair_values, prev_form_values))

    cur_pair_values = [0] * len(cur_mesh.vertices)
    cur_pair.data.foreach_get("value", cur_pair_values)
    cur_form_values = [mapping.get(pid, pid) for pid in cur_pair_values]
    cur_form.data.foreach_set("value", cur_form_values)


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


def _ensure_int_point_attr(mesh: bpy.types.Mesh, name: str) -> bpy.types.Attribute:
    """Ensure an INT attribute on point domain, recreating if mismatched."""
    attr = mesh.attributes.get(name)
    if attr and attr.data_type == 'INT' and attr.domain == 'POINT' and len(attr.data) == len(mesh.vertices):
        return attr
    if attr:
        mesh.attributes.remove(attr)
    return mesh.attributes.new(name=name, type='INT', domain='POINT')


def _assign_formation_ids(col: bpy.types.Collection, drone_count: Optional[int]) -> bool:
    """Assign formation_id/pair_id once per collection if missing."""
    meshes = _collect_mesh_objects(col)
    if not meshes:
        return False

    need_assign = False
    for obj in meshes:
        attr = obj.data.attributes.get(FORMATION_ATTR_NAME)
        if not attr or attr.domain != 'POINT' or attr.data_type != 'INT' or len(attr.data) != len(obj.data.vertices):
            need_assign = True
            break
    if not need_assign:
        return False

    count = max(0, int(drone_count)) if drone_count else None
    next_id = 0
    for obj in meshes:
        mesh = obj.data
        form_attr = _ensure_int_point_attr(mesh, FORMATION_ATTR_NAME)
        pair_attr = _ensure_int_point_attr(mesh, PAIR_ATTR_NAME)
        vert_len = len(mesh.vertices)
        values = []
        for i in range(vert_len):
            if count:
                vid = next_id % count
            else:
                vid = next_id
            values.append(vid)
            next_id += 1
        # bulk write
        form_attr.data.foreach_set("value", values)
        pair_attr.data.foreach_set("value", values)
    return True


def _seed_pair_ids(meshes: List[bpy.types.Object]) -> None:
    for obj in meshes:
        mesh = obj.data
        form = mesh.attributes.get(FORMATION_ATTR_NAME)
        if not form or form.data_type != 'INT' or form.domain != 'POINT' or len(form.data) != len(mesh.vertices):
            form = _ensure_int_point_attr(mesh, FORMATION_ATTR_NAME)
            form.data.foreach_set("value", list(range(len(mesh.vertices))))
        pair_attr = _ensure_int_point_attr(mesh, PAIR_ATTR_NAME)
        values = [0] * len(mesh.vertices)
        form.data.foreach_get("value", values)
        pair_attr.data.foreach_set("value", values)


def _collect_meshes_from_cols(cols: Sequence[bpy.types.Collection]) -> List[bpy.types.Object]:
    meshes: List[bpy.types.Object] = []
    for col in sorted(cols, key=lambda c: c.name):
        meshes.extend(_collect_mesh_objects(col))
    return meshes


def _pair_from_previous(prev_meshes: List[bpy.types.Object], next_meshes: List[bpy.types.Object]) -> bool:
    """Assign pair_id on next_meshes as mapping from previous formation_id to next formation_id."""
    if not prev_meshes or not next_meshes:
        return False
    from liberadronecore.system.drone import calculate_mapping
    import numpy as np

    def _flatten(meshes, attr_name: Optional[str]) -> tuple[np.ndarray, List[int], List[tuple[bpy.types.Mesh, int]]]:
        coords = []
        ids: List[int] = []
        spans: List[tuple[bpy.types.Mesh, int]] = []
        for obj in meshes:
            mesh = obj.data
            mat = obj.matrix_world
            spans.append((mesh, len(mesh.vertices)))
            coords.extend([(mat @ v.co)[:] for v in mesh.vertices])
            if attr_name:
                attr = mesh.attributes.get(attr_name)
                if attr and attr.data_type == 'INT' and attr.domain == 'POINT' and len(attr.data) == len(mesh.vertices):
                    values = [0] * len(mesh.vertices)
                    attr.data.foreach_get("value", values)
                    ids.extend(values)
                    continue
            ids.extend(list(range(len(mesh.vertices))))
        return np.asarray(coords, dtype=np.float64), ids, spans

    pts_prev, _prev_ids, _prev_spans = _flatten(prev_meshes, FORMATION_ATTR_NAME)
    pts_next, next_ids, next_spans = _flatten(next_meshes, FORMATION_ATTR_NAME)
    if len(pts_prev) != len(pts_next) or len(pts_prev) == 0:
        return False

    pairA, _ = calculate_mapping.hungarian_from_points(pts_prev, pts_next)

    # Build flat array of mapped ids for next (prev formation_id -> next formation_id)
    mapped_ids = [next_ids[p] for p in pairA]

    offset = 0
    for mesh, span in next_spans:
        attr = _ensure_int_point_attr(mesh, PAIR_ATTR_NAME)
        values = mapped_ids[offset:offset + span]
        attr.data.foreach_set("value", values)
        offset += span
    return True
