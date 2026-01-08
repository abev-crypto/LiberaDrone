import bpy
import bmesh
from typing import Optional
from mathutils import Vector

# -----------------------------
# 險ｭ螳夲ｼ亥ｿ・ｦ√↑繧峨％縺薙□縺大､画峩・・
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
ANY_MESH_VERTS = 1  # 莉ｻ諢上・鬆らせ謨ｰ・医％縺薙ｒ螟峨∴繧具ｼ・
COLLECTION_NAMES = [
    "LD_Objects",
]

# 縺ｩ縺ｮ繧ｳ繝ｬ繧ｯ繧ｷ繝ｧ繝ｳ縺ｫ菴輔ｒ蜈･繧後ｋ縺・
COL_FOR_PREVIEW = "LD_Objects"
COL_FOR_ANYMESH   = "LD_Objects"


# -----------------------------
# 繝ｦ繝ｼ繝・ぅ繝ｪ繝・ぅ
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
    # 譌｢蟄倥さ繝ｬ繧ｯ繧ｷ繝ｧ繝ｳ縺九ｉ螟悶＠縲》arget 縺縺代↓蜈･繧後ｋ
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    target_col.objects.link(obj)

def _get_scene():
    scene = getattr(bpy.context, "scene", None)
    if scene is None and bpy.data.scenes:
        scene = bpy.data.scenes[0]
    return scene

def ensure_color_attribute(mesh, name=ATTR_NAME):
    # Blender縺ｮ繝舌・繧ｸ繝ｧ繝ｳ蟾ｮ繧貞精蜿弱＠縺ｦ "color" 繧ｫ繝ｩ繝ｼ螻樊ｧ繧堤畑諢上☆繧・
    # 縺ｧ縺阪ｌ縺ｰ POINT(=鬆らせ) 繝峨Γ繧､繝ｳ縺ｧ菴懊ｋ
    if hasattr(mesh, "color_attributes"):
        ca = mesh.color_attributes.get(name)
        if ca is None:
            ca = mesh.color_attributes.new(name=name, domain='POINT', type='BYTE_COLOR')
        return ca

    # 縺輔ｉ縺ｫ蜿､縺・驕輔≧API蜷代￠・井ｿ晞匱・・
    if hasattr(mesh, "attributes"):
        a = mesh.attributes.get(name)
        if a is None:
            a = mesh.attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
        return a

    raise RuntimeError("Color attribute API not found for this Blender version.")

def set_viewport_solid_attribute(attr_name=ATTR_NAME):
    # 4縺､縺ｮ鬆伜沺: Viewport Shading 繧・Solid + Attribute陦ｨ遉ｺ縺ｫ縺吶ｋ
    for area in bpy.context.window.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            if space.type != 'VIEW_3D':
                continue
            shading = space.shading
            shading.type = 'SOLID'
            # Blender縺ｮ繝舌・繧ｸ繝ｧ繝ｳ縺ｧ繝励Ο繝代ユ繧｣蜷阪′蠕ｮ螯吶↓驕輔≧縺ｮ縺ｧ蛻・ｲ・
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
    try:
        img.pack(as_png=True)
    except Exception:
        try:
            img.pack()
        except Exception:
            return

    try:
        filepath = getattr(img, "filepath", "") or ""
        if not filepath and getattr(bpy.data, "is_saved", False):
            img.filepath_raw = f"//{img.name}"
            img.file_format = 'PNG'
            filepath = img.filepath
        if filepath:
            img.save()
    except Exception:
        pass


def _ensure_preview_image(name: str, *, ring: bool) -> bpy.types.Image:
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.new(name=name, width=IMG_SIZE, height=IMG_SIZE, alpha=True)
    if img.size[0] != IMG_SIZE or img.size[1] != IMG_SIZE:
        try:
            img.scale(IMG_SIZE, IMG_SIZE)
        except Exception:
            pass
    _fill_preview_image(img, ring)
    img.use_fake_user = True
    _pack_preview_image(img)
    return img


def get_or_create_emission_attr_material(mat_name=MAT_NAME, attr_name=ATTR_NAME, image_name: Optional[str] = None):
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    try:
        mat.blend_method = 'HASHED'
    except Exception:
        pass
    try:
        mat.shadow_method = 'HASHED'
    except Exception:
        pass

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
    # 縲御ｻｻ諢城らせ謨ｰ縺ｮ繝｡繝・す繝･縲・ 縺薙％縺ｧ縺ｯ 窶懃せ縺縺鯛・縺ｮ繝｡繝・す繝･繧剃ｽ懊ｋ・亥ｾ後〒閾ｪ逕ｱ縺ｫ邱ｨ髮・＠繧・☆縺・ｼ・
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)

    bm = bmesh.new()
    # 驕ｩ蠖薙↓蛻・ｸ・ｼ・譁ｹ蜷代↓荳ｦ縺ｹ繧倶ｾ具ｼ・
    for i in range(n_verts):
        x = (i / max(1, n_verts - 1)) * 2.0 - 1.0
        bm.verts.new(Vector((x, 1.5, 0.0)))
    bm.verts.ensure_lookup_table()
    bm.to_mesh(mesh)
    bm.free()

    ensure_color_attribute(mesh, ATTR_NAME)
    return obj


# -----------------------------
# 螳溯｡梧悽菴・
# -----------------------------
def init_scene_env(n_verts=None, *, create_any_mesh: bool = True):
    global ANY_MESH_VERTS
    if n_verts is not None:
        try:
            ANY_MESH_VERTS = int(n_verts)
        except Exception:
            pass
    # 5) 蟆ら畑繧ｳ繝ｬ繧ｯ繧ｷ繝ｧ繝ｳ菴懈・
    root = None
    cols = {n: get_or_create_collection(n, parent=root) for n in COLLECTION_NAMES}

    # 1) Emission + Attribute color 縺ｮ繝槭ユ繝ｪ繧｢繝ｫ
    mat = get_or_create_emission_attr_material(MAT_NAME, ATTR_NAME, image_name=IMG_CIRCLE_NAME)
    get_or_create_emission_attr_material(MAT_RING_NAME, ATTR_NAME, image_name=IMG_RING_NAME)

    # 2) Iso逅・ｽ難ｼ・cosphere・唄ubdiv=2, radius=0.5, ColorAttribute "color"
    iso = create_preview_plane(PREVIEW_NAME, PREVIEW_PLANE_SIZE)
    assign_material(iso, mat)

    # 3) 莉ｻ諢城らせ謨ｰ繝｡繝・す繝･・育せ繝｡繝・す繝･・・
    any_obj = None
    if create_any_mesh:
        any_obj = create_any_mesh_points(ANY_MESH_NAME, ANY_MESH_VERTS)
        assign_material(any_obj, mat)

    # 繧ｳ繝ｬ繧ｯ繧ｷ繝ｧ繝ｳ縺ｸ驟咲ｽｮ
    if COL_FOR_PREVIEW in cols:
        move_object_to_collection(iso, cols[COL_FOR_PREVIEW])
    if create_any_mesh and COL_FOR_ANYMESH in cols and any_obj is not None:
        move_object_to_collection(any_obj, cols[COL_FOR_ANYMESH])

    # 繝槭ユ繝ｪ繧｢繝ｫ閾ｪ菴薙・繧ｳ繝ｬ繧ｯ繧ｷ繝ｧ繝ｳ縺ｫ蜈･繧峨↑縺・・縺ｧ縲∫ｮ｡逅・畑縺ｫ繝・く繧ｹ繝医〒邨ゅｏ繧・
    if create_any_mesh and any_obj is not None:
        print("[Init] Done:",
              f"Material={mat.name}, Preview={iso.name}, AnyMesh={any_obj.name}, Attr={ATTR_NAME}")
    else:
        print("[Init] Done:",
              f"Material={mat.name}, Preview={iso.name}, Attr={ATTR_NAME}")

if __name__ == "__main__":
    init_scene_env()



