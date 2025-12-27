import bpy


def _get_drone_system_object():
    obj = bpy.data.objects.get("DroneSystem")
    if obj and obj.type == 'MESH':
        return obj
    return None


def get_all_drones_in_scene(scene):
    system_obj = _get_drone_system_object()
    if system_obj and system_obj.data:
        return list(range(len(system_obj.data.vertices)))
    return [obj for obj in scene.objects if obj.type == 'MESH']


def get_position_of_object(obj):
    system_obj = _get_drone_system_object()
    if isinstance(obj, int) and system_obj and system_obj.data:
        if 0 <= obj < len(system_obj.data.vertices):
            v = system_obj.data.vertices[obj]
            world = system_obj.matrix_world @ v.co
            return (float(world.x), float(world.y), float(world.z))
    if hasattr(obj, "matrix_world"):
        world = obj.matrix_world.translation
        return (float(world.x), float(world.y), float(world.z))
    if isinstance(obj, (tuple, list)) and len(obj) >= 3:
        return (float(obj[0]), float(obj[1]), float(obj[2]))
    return (0.0, 0.0, 0.0)
