import bpy
from mathutils import Vector

from liberadronecore.ledeffects.util import mesh_helpers

_unique_name = mesh_helpers._unique_name
_ensure_collection = mesh_helpers._ensure_collection
_freeze_object_transform = mesh_helpers._freeze_object_transform
_selected_world_vertices = mesh_helpers._selected_world_vertices
_selected_mesh_objects = mesh_helpers._selected_mesh_objects


def _world_bbox_from_points(points: list[Vector]) -> tuple[Vector, Vector] | None:
    if not points:
        return None
    min_v = Vector((float("inf"), float("inf"), float("inf")))
    max_v = Vector((float("-inf"), float("-inf"), float("-inf")))
    for p in points:
        min_v.x = min(min_v.x, p.x)
        min_v.y = min(min_v.y, p.y)
        min_v.z = min(min_v.z, p.z)
        max_v.x = max(max_v.x, p.x)
        max_v.y = max(max_v.y, p.y)
        max_v.z = max(max_v.z, p.z)
    return min_v, max_v


def _world_bbox_from_object(obj: bpy.types.Object) -> tuple[Vector, Vector] | None:
    if obj is None or obj.type != 'MESH':
        return None
    bbox = obj.bound_box
    if not bbox:
        return None
    mw = obj.matrix_world
    points = [mw @ Vector(corner) for corner in bbox]
    return _world_bbox_from_points(points)


def _world_bbox_from_collection(col: bpy.types.Collection) -> tuple[Vector, Vector] | None:
    if col is None:
        return None
    bounds = None
    for obj in col.all_objects:
        if obj.type != 'MESH':
            continue
        obj_bounds = _world_bbox_from_object(obj)
        if obj_bounds is None:
            continue
        min_v, max_v = obj_bounds
        if bounds is None:
            bounds = (min_v.copy(), max_v.copy())
        else:
            bounds[0].x = min(bounds[0].x, min_v.x)
            bounds[0].y = min(bounds[0].y, min_v.y)
            bounds[0].z = min(bounds[0].z, min_v.z)
            bounds[1].x = max(bounds[1].x, max_v.x)
            bounds[1].y = max(bounds[1].y, max_v.y)
            bounds[1].z = max(bounds[1].z, max_v.z)
    return bounds


def _create_xz_plane(name: str, bounds: tuple[Vector, Vector], context) -> bpy.types.Object:
    min_v, max_v = bounds
    y = (min_v.y + max_v.y) * 0.5
    verts = [
        (min_v.x, y, min_v.z),
        (max_v.x, y, min_v.z),
        (max_v.x, y, max_v.z),
        (min_v.x, y, max_v.z),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    _ensure_collection(context).objects.link(obj)
    _freeze_object_transform(obj)
    return obj
