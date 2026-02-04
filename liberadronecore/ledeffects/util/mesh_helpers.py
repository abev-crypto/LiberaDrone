import bpy
import bmesh
from mathutils import Matrix, Vector


def _unique_name(base: str) -> str:
    if not bpy.data.objects.get(base):
        return base
    idx = 1
    while True:
        name = f"{base}.{idx:03d}"
        if not bpy.data.objects.get(name):
            return name
        idx += 1


def _ensure_collection(context) -> bpy.types.Collection:
    if context and getattr(context, "collection", None):
        return context.collection
    scene = getattr(context, "scene", None) or bpy.context.scene
    return scene.collection


def _freeze_object_transform(obj: bpy.types.Object) -> None:
    if obj is None or obj.type != 'MESH':
        return
    if obj.matrix_world != Matrix.Identity(4):
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)
        obj.data.update()


def _selected_world_vertices(context) -> list[Vector]:
    obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
        return []
    bm = bmesh.from_edit_mesh(obj.data)
    mw = obj.matrix_world
    return [mw @ v.co for v in bm.verts if v.select]


def _selected_mesh_objects(context) -> list[bpy.types.Object]:
    selected = getattr(context, "selected_objects", None) or []
    return [obj for obj in selected if obj.type == 'MESH']
