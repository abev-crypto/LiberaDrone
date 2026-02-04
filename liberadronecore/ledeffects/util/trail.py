import bpy
import bmesh

from liberadronecore.ledeffects.util import formation_ids


def _ordered_selected_verts(context, target_obj: bpy.types.Object | None = None):
    obj = None
    if target_obj is not None and target_obj.type == 'MESH' and target_obj.mode == 'EDIT':
        obj = target_obj
    else:
        active = getattr(context, "active_object", None)
        if active is not None and active.type == 'MESH' and active.mode == 'EDIT':
            obj = active
    if obj is None:
        return None, None, None, "Select vertices in Edit Mode"
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    ordered = []
    seen = set()
    for elem in bm.select_history:
        if not isinstance(elem, bmesh.types.BMVert):
            continue
        if not elem.select:
            continue
        idx = elem.index
        if idx in seen:
            continue
        seen.add(idx)
        ordered.append(elem)
    if not ordered:
        ordered = [v for v in bm.verts if v.select]
    if not ordered:
        return None, None, None, "No selected vertices"
    return ordered, obj, bm, None


def _read_selected_ids_ordered(context, target_obj: bpy.types.Object | None = None):
    ordered, mesh_obj, bm, error = _ordered_selected_verts(context, target_obj)
    if error:
        return None, error
    if not ordered:
        return None, "No selected vertices"
    ids, error = formation_ids.read_bmesh_formation_ids(bm, ordered)
    if error:
        if mesh_obj is None or mesh_obj.type != 'MESH':
            return None, error
        indices = [v.index for v in ordered]
        ids, error = formation_ids.read_mesh_index_ids(mesh_obj.data, indices)
        if error:
            return None, error
    return ids, None
