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
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        uv_layer = mesh.uv_layers.new(name="UVMap")
    poly = mesh.polygons[0]
    loop_start = poly.loop_start
    uvs = (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    )
    for idx, uv in enumerate(uvs):
        uv_layer.data[loop_start + idx].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    _ensure_collection(context).objects.link(obj)
    _freeze_object_transform(obj)
    return obj


def _preview_material_name(image: bpy.types.Image) -> str:
    return f"LD_ProjectionUV_{image.name}"


def _get_or_create_preview_material(image: bpy.types.Image) -> bpy.types.Material:
    mat_name = _preview_material_name(image)
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    mat.blend_method = 'HASHED'
    if hasattr(mat, "shadow_method"):
        mat.shadow_method = 'HASHED'
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    for n in list(nodes):
        nodes.remove(n)

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (360, 0)

    image_tex = nodes.new("ShaderNodeTexImage")
    image_tex.location = (-260, 0)
    image_tex.extension = 'REPEAT'
    image_tex.interpolation = 'Linear'
    image_tex.projection = 'FLAT'
    image_tex.image = image

    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (120, 0)
    principled.inputs[1].default_value = 0.0
    roughness_input = principled.inputs.get("Roughness")
    if roughness_input is None and len(principled.inputs) > 7:
        roughness_input = principled.inputs[7]
    if roughness_input is not None:
        roughness_input.default_value = 0.0
    if principled.inputs.get("Emission Strength"):
        principled.inputs["Emission Strength"].default_value = 1.0
    elif len(principled.inputs) > 28:
        principled.inputs[28].default_value = 1.0

    links.new(image_tex.outputs[0], principled.inputs[0])
    emission_input = principled.inputs.get("Emission") or principled.inputs.get("Emission Color")
    if emission_input is None and len(principled.inputs) > 17:
        emission_input = principled.inputs[17]
    if emission_input is not None:
        links.new(image_tex.outputs[0], emission_input)

    alpha_input = principled.inputs.get("Alpha")
    if alpha_input is None and len(principled.inputs) > 19:
        alpha_input = principled.inputs[19]
    image_alpha = image_tex.outputs.get("Alpha")
    if image_alpha is None and len(image_tex.outputs) > 1:
        image_alpha = image_tex.outputs[1]
    if alpha_input is not None and image_alpha is not None:
        links.new(image_alpha, alpha_input)

    links.new(principled.outputs[0], out.inputs[0])
    return mat


def _is_preview_material_assigned(obj: bpy.types.Object, image: bpy.types.Image) -> bool:
    if obj is None or obj.type != 'MESH':
        return False
    mats = obj.data.materials
    if not mats:
        return False
    mat = mats[0]
    if mat is None:
        return False
    return mat.name == _preview_material_name(image)
