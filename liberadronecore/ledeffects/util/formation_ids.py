import bpy
import bmesh

from liberadronecore.formation import fn_parse_pairing


def _get_formation_attr(mesh: bpy.types.Mesh):
    attr = mesh.attributes.get(fn_parse_pairing.FORMATION_ATTR_NAME)
    if attr is None:
        attr = mesh.attributes.get(fn_parse_pairing.FORMATION_ID_ATTR)
    return attr


def read_mesh_formation_ids(mesh: bpy.types.Mesh):
    attr = _get_formation_attr(mesh)
    if attr is None or attr.domain != 'POINT' or attr.data_type != 'INT':
        return None, "formation_id attribute not found"
    if len(attr.data) != len(mesh.vertices):
        return None, "formation_id data missing"
    values = [0] * len(mesh.vertices)
    attr.data.foreach_get("value", values)
    return values, None


def read_mesh_index_ids(mesh: bpy.types.Mesh, indices):
    attr = _get_formation_attr(mesh)
    if attr is None or attr.domain != 'POINT' or attr.data_type != 'INT':
        return None, "formation_id attribute not found"
    if len(attr.data) != len(mesh.vertices):
        return None, "formation_id data missing"
    return [int(attr.data[idx].value) for idx in indices], None


def read_bmesh_formation_ids(bm: bmesh.types.BMesh, verts):
    layer = bm.verts.layers.int.get(fn_parse_pairing.FORMATION_ATTR_NAME)
    if layer is None:
        layer = bm.verts.layers.int.get(fn_parse_pairing.FORMATION_ID_ATTR)
    if layer is None:
        return None, "formation_id attribute not found"
    ids = [int(v[layer]) for v in verts]
    if not ids:
        return None, "formation_id data missing"
    return ids, None
