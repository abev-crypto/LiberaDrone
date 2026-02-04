import bpy
import bmesh
import os
from typing import Optional
from mathutils import Vector

# -----------------------------
# Settings (edit here).
# -----------------------------
ATTR_NAME = "color"

MAT_NAME = "MAT_Emission_AttrColor"
MAT_RING_NAME = "MAT_Emission_AttrColor_Ring"
IMG_CIRCLE_NAME = "PreviewDrone_Circle.png"
IMG_RING_NAME = "PreviewDrone_Ring.png"
IMG_SIZE = 64

PREVIEW_NAME = "Iso"
PREVIEW_PLANE_SIZE = 1.0

ANY_MESH_NAME = "AnyMesh"
ANY_MESH_VERTS = 1  # Change to control the point count.
COLLECTION_NAMES = [
    "LD_Objects",
]

# Collection assignments.
COL_FOR_PREVIEW = "LD_Objects"
COL_FOR_ANYMESH   = "LD_Objects"


# -----------------------------
# Utilities.
# -----------------------------
def get_or_create_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        if parent is None:
            bpy.context.scene.collection.children.link(col)
        else:
            parent.children.link(col)
    return col

def move_object_to_collection(obj, target_col):
    # Unlink from existing collections and link to target.
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    target_col.objects.link(obj)

def _get_scene():
    scene = getattr(bpy.context, "scene", None)
    if scene is None and bpy.data.scenes:
        scene = bpy.data.scenes[0]
    return scene

def ensure_color_attribute(mesh, name=ATTR_NAME):
    # Create or reuse a color attribute across Blender versions.
    # Prefer POINT domain when available.
    if hasattr(mesh, "color_attributes"):
        ca = mesh.color_attributes.get(name)
        if ca is None:
            ca = mesh.color_attributes.new(name=name, domain='POINT', type='BYTE_COLOR')
        return ca

    # Fallback for older attribute APIs.
    if hasattr(mesh, "attributes"):
        a = mesh.attributes.get(name)
        if a is None:
            a = mesh.attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
        return a

    raise RuntimeError("Color attribute API not found for this Blender version.")

def set_viewport_solid_attribute(attr_name=ATTR_NAME):
    # Set viewport shading to Solid + Attribute.
    for area in bpy.context.window.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            if space.type != 'VIEW_3D':
                continue
            shading = space.shading
            shading.type = 'SOLID'
            # Property names differ slightly across Blender versions.
            if hasattr(shading, "color_type"):
                items = getattr(shading.bl_rna.properties.get("color_type"), "enum_items", None)
                if items and "ATTRIBUTE" in items:
                    shading.color_type = 'ATTRIBUTE'
                else:
                    shading.color_type = 'VERTEX'
            if hasattr(shading, "attribute_color"):
                shading.attribute_color = attr_name
            elif hasattr(shading, "attribute"):
                shading.attribute = attr_name

def _fill_preview_image(img: bpy.types.Image, ring: bool) -> None:
    width, height = img.size
    center_x = (width - 1) * 0.5
    center_y = (height - 1) * 0.5
    outer_radius = 32.0
    inner_radius = 30.0
    outer_sq = outer_radius * outer_radius
    inner_sq = inner_radius * inner_radius

    pixels = [0.0] * (width * height * 4)
    for y in range(height):
        dy = y - center_y
        for x in range(width):
            dx = x - center_x
            dist_sq = dx * dx + dy * dy
            if ring:
                is_white = inner_sq < dist_sq <= outer_sq
            else:
                is_white = dist_sq <= outer_sq
            idx = (y * width + x) * 4
            if is_white:
                pixels[idx:idx + 4] = (1.0, 1.0, 1.0, 1.0)
            else:
                pixels[idx:idx + 4] = (0.0, 0.0, 0.0, 1.0)
    img.pixels = pixels


def _pack_preview_image(img: bpy.types.Image) -> None:
    if getattr(bpy.app, "version", (0, 0, 0)) >= (4, 0, 0):
        filepath = bpy.path.abspath(getattr(img, "filepath", "") or "")
        if not filepath:
            filepath = bpy.path.abspath(getattr(img, "filepath_raw", "") or "")
        if not filepath:
            temp_dir = getattr(bpy.app, "tempdir", "") or ""
            if not temp_dir:
                raise RuntimeError(f"Preview image tempdir missing: {img.name}")
            filepath = os.path.join(temp_dir, f"{img.name}")
            if not filepath.lower().endswith(".png"):
                filepath += ".png"
            img.filepath_raw = filepath
            img.file_format = 'PNG'
            img.save()
            filepath = bpy.path.abspath(getattr(img, "filepath_raw", "") or "")
        if not filepath or not os.path.isfile(filepath):
            raise RuntimeError(f"Preview image path not found: {img.name}")
        with open(filepath, "rb") as handle:
            data = handle.read()
        if not data:
            raise RuntimeError(f"Preview image empty for pack: {img.name}")
        img.pack(data=data, data_len=len(data))
        return

    img.pack(as_png=True)
    filepath = getattr(img, "filepath", "") or ""
    if not filepath and getattr(bpy.data, "is_saved", False):
        img.filepath_raw = f"//{img.name}"
        img.file_format = 'PNG'
        filepath = img.filepath
    if filepath:
        img.save()
def _ensure_preview_image(name: str, *, ring: bool) -> bpy.types.Image:
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.new(name=name, width=IMG_SIZE, height=IMG_SIZE, alpha=True)
    if img.size[0] != IMG_SIZE or img.size[1] != IMG_SIZE:
        img.scale(IMG_SIZE, IMG_SIZE)
    _fill_preview_image(img, ring)
    img.use_fake_user = True
    _pack_preview_image(img)
    return img


def get_or_create_emission_attr_material(mat_name=MAT_NAME, attr_name=ATTR_NAME, image_name: Optional[str] = None):
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
    out.location = (560, 120)

    attr = nodes.new("ShaderNodeAttribute")
    attr.location = (-220, 0)
    attr.attribute_name = attr_name

    image_tex = nodes.new("ShaderNodeTexImage")
    image_tex.location = (-220, 240)
    image_tex.extension = 'REPEAT'
    image_tex.interpolation = 'Linear'
    image_tex.projection = 'FLAT'
    if image_name:
        ring = image_name == IMG_RING_NAME
        image_tex.image = _ensure_preview_image(image_name, ring=ring)

    mix = nodes.new("ShaderNodeMix")
    mix.location = (160, 120)
    mix.blend_type = 'MULTIPLY'
    mix.data_type = 'RGBA'
    mix.factor_mode = 'UNIFORM'
    mix.inputs[0].default_value = 1.0

    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (360, 120)
    principled.inputs[1].default_value = 0.0
    principled.inputs[2].default_value = 0.5
    principled.inputs[13].default_value = 0.5
    roughness_input = principled.inputs.get("Roughness")
    if roughness_input is None and len(principled.inputs) > 7:
        roughness_input = principled.inputs[7]
    if roughness_input is not None:
        roughness_input.default_value = 0
    if principled.inputs.get("Emission Strength"):
        principled.inputs["Emission Strength"].default_value = 1.0
    elif len(principled.inputs) > 28:
        principled.inputs[28].default_value = 1.0

    links.new(image_tex.outputs[0], mix.inputs[6])
    links.new(attr.outputs[0], mix.inputs[7])
    links.new(mix.outputs[2], principled.inputs[0])
    emission_input = principled.inputs.get("Emission") or principled.inputs.get("Emission Color")
    if emission_input is None and len(principled.inputs) > 17:
        emission_input = principled.inputs[17]
    if emission_input is not None:
        links.new(mix.outputs[2], emission_input)
    links.new(image_tex.outputs[0], principled.inputs[4])
    links.new(principled.outputs[0], out.inputs[0])

    return mat

def assign_material(obj, mat):
    if obj.type != 'MESH':
        return
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def create_preview_plane(name=PREVIEW_NAME, size=PREVIEW_PLANE_SIZE):
    scene = _get_scene()
    if scene is None:
        raise RuntimeError("No active scene for preview plane.")
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)

    bm = bmesh.new()
    half = size * 0.5
    v0 = bm.verts.new((-half, -half, 0.0))
    v1 = bm.verts.new((half, -half, 0.0))
    v2 = bm.verts.new((half, half, 0.0))
    v3 = bm.verts.new((-half, half, 0.0))
    bm.faces.new((v0, v1, v2, v3))
    bm.to_mesh(mesh)
    bm.free()
    return obj

def create_any_mesh_points(name=ANY_MESH_NAME, n_verts=ANY_MESH_VERTS):
    scene = _get_scene()
    if scene is None:
        raise RuntimeError("No active scene for AnyMesh.")
    # Create a point-only mesh with a configurable vertex count.
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)

    bm = bmesh.new()
    # Place points along X for a simple preview.
    for i in range(n_verts):
        x = (i / max(1, n_verts - 1)) * 2.0 - 1.0
        bm.verts.new(Vector((x, 1.5, 0.0)))
    bm.verts.ensure_lookup_table()
    bm.to_mesh(mesh)
    bm.free()

    ensure_color_attribute(mesh, ATTR_NAME)
    return obj


# -----------------------------
# Entry point.
# -----------------------------
def init_scene_env(n_verts=None, *, create_any_mesh: bool = True):
    global ANY_MESH_VERTS
    if n_verts is not None:
        ANY_MESH_VERTS = int(n_verts)
    # 1) Collections.
    root = None
    cols = {n: get_or_create_collection(n, parent=root) for n in COLLECTION_NAMES}

    # 2) Emission + attribute color materials.
    mat = get_or_create_emission_attr_material(MAT_NAME, ATTR_NAME, image_name=IMG_CIRCLE_NAME)
    get_or_create_emission_attr_material(MAT_RING_NAME, ATTR_NAME, image_name=IMG_RING_NAME)

    # 3) Preview plane (iso marker).
    iso = create_preview_plane(PREVIEW_NAME, PREVIEW_PLANE_SIZE)
    assign_material(iso, mat)

    # 4) Any-mesh point cloud.
    any_obj = None
    if create_any_mesh:
        any_obj = create_any_mesh_points(ANY_MESH_NAME, ANY_MESH_VERTS)
        assign_material(any_obj, mat)

    # Move objects into collections.
    if COL_FOR_PREVIEW in cols:
        move_object_to_collection(iso, cols[COL_FOR_PREVIEW])
    if create_any_mesh and COL_FOR_ANYMESH in cols and any_obj is not None:
        move_object_to_collection(any_obj, cols[COL_FOR_ANYMESH])

    # Materials are datablocks and do not live in collections.
    if create_any_mesh and any_obj is not None:
        print("[Init] Done:",
              f"Material={mat.name}, Preview={iso.name}, AnyMesh={any_obj.name}, Attr={ATTR_NAME}")
    else:
        print("[Init] Done:",
              f"Material={mat.name}, Preview={iso.name}, Attr={ATTR_NAME}")

if __name__ == "__main__":
    init_scene_env()



