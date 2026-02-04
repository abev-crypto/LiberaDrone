import bpy
import bmesh

from liberadronecore.ledeffects.util import formation_ids


def _sorted_ids(values) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for val in values:
        item = int(val)
        if item in seen:
            continue
        seen.add(item)
        ids.append(item)
    ids.sort()
    return ids


def _node_effective_ids(node: "LDLEDIDMaskNode", include_legacy: bool) -> list[int]:
    if getattr(node, "use_custom_ids", False):
        return _sorted_ids([item.value for item in node.ids])
    if not include_legacy:
        return []
    fid = getattr(node, "formation_id", -1)
    if fid < 0:
        return []
    return _sorted_ids([fid])


def _set_node_ids(node: "LDLEDIDMaskNode", ids: list[int]) -> None:
    node.ids.clear()
    for val in ids:
        item = node.ids.add()
        item.value = int(val)


def _read_selected_ids(context) -> tuple[set[int] | None, str | None]:
    obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH':
        return None, "Select mesh objects"
    if obj.mode != 'EDIT':
        selected = [o for o in getattr(context, "selected_objects", []) if o.type == 'MESH']
        if not selected:
            selected = [obj]
        ids = set()
        for sel in selected:
            values, error = formation_ids.read_mesh_formation_ids(sel.data)
            if error:
                return None, error
            ids.update(values)
        if not ids:
            return None, "No IDs found on selected objects"
        return ids, None
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    selected = [v for v in bm.verts if v.select]
    if not selected:
        return None, "No selected vertices"

    ids, error = formation_ids.read_bmesh_formation_ids(bm, selected)
    if error:
        indices = [v.index for v in selected]
        ids, error = formation_ids.read_mesh_index_ids(obj.data, indices)
        if error:
            return None, error
    return set(ids), None
