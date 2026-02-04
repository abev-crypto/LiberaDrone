from mathutils import Vector

from liberadronecore.ledeffects.util import mesh_helpers

_unique_name = mesh_helpers._unique_name
_ensure_collection = mesh_helpers._ensure_collection
_freeze_object_transform = mesh_helpers._freeze_object_transform
_selected_world_vertices = mesh_helpers._selected_world_vertices
_selected_mesh_objects = mesh_helpers._selected_mesh_objects


def _collect_points(context) -> list[Vector]:
    verts = _selected_world_vertices(context)
    if verts:
        return verts
    points: list[Vector] = []
    for obj in _selected_mesh_objects(context):
        mw = obj.matrix_world
        for v in obj.data.vertices:
            points.append(mw @ v.co)
    return points


def _apply_solidify(obj) -> None:
    solid = obj.modifiers.new("Solidify", type='SOLIDIFY')
    solid.thickness = 0.2
    solid.offset = 0.0
    solid.use_rim = True
    solid.use_even_offset = True
    for attr in ("use_quality_normals", "nonmanifold_boundary_mode"):
        if hasattr(solid, attr):
            try:
                setattr(solid, attr, True if isinstance(getattr(solid, attr), bool) else getattr(solid, attr))
            except Exception:
                pass
