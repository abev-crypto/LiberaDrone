import bpy
import bmesh
from mathutils import Vector

# -----------------------------
# 設定（必要ならここだけ変更）
# -----------------------------
ATTR_NAME = "color"

MAT_NAME = "MAT_Emission_AttrColor"
ICOSPHERE_NAME = "Iso"
ICOSPHERE_SUBDIV = 2
ICOSPHERE_RADIUS = 0.5

ANY_MESH_NAME = "AnyMesh"
ANY_MESH_VERTS = 200  # 任意の頂点数（ここを変える）

COLLECTION_NAMES = [
    "COL_System",
    "COL_Geo",
    "COL_Render",
    "COL_Debug",
]

# どのコレクションに何を入れるか
COL_FOR_ICOSPHERE = "COL_Geo"
COL_FOR_ANYMESH   = "COL_Geo"
COL_FOR_MATERIALS = "COL_Render"


# -----------------------------
# ユーティリティ
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
    # 既存コレクションから外し、target だけに入れる
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    target_col.objects.link(obj)

def ensure_color_attribute(mesh, name=ATTR_NAME):
    # Blenderのバージョン差を吸収して "color" カラー属性を用意する
    # できれば POINT(=頂点) ドメインで作る
    if hasattr(mesh, "color_attributes"):
        ca = mesh.color_attributes.get(name)
        if ca is None:
            ca = mesh.color_attributes.new(name=name, domain='POINT', type='BYTE_COLOR')
        return ca

    # さらに古い/違うAPI向け（保険）
    if hasattr(mesh, "attributes"):
        a = mesh.attributes.get(name)
        if a is None:
            a = mesh.attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
        return a

    raise RuntimeError("このBlenderではカラー属性APIが見つかりませんでした。")

def set_viewport_solid_attribute(attr_name=ATTR_NAME):
    # 4つの領域: Viewport Shading を Solid + Attribute表示にする
    for area in bpy.context.window.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            if space.type != 'VIEW_3D':
                continue
            shading = space.shading
            shading.type = 'SOLID'
            # Blenderのバージョンでプロパティ名が微妙に違うので分岐
            if hasattr(shading, "color_type"):
                shading.color_type = 'ATTRIBUTE'
            if hasattr(shading, "attribute_color"):
                shading.attribute_color = attr_name
            elif hasattr(shading, "attribute"):
                shading.attribute = attr_name

def get_or_create_emission_attr_material(mat_name=MAT_NAME, attr_name=ATTR_NAME):
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True

    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links

    # 既存を軽く整理（必要なら外してOK）
    for n in list(nodes):
        nodes.remove(n)

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)

    emission = nodes.new("ShaderNodeEmission")
    emission.location = (150, 0)
    emission.inputs["Strength"].default_value = 1.0

    attr = nodes.new("ShaderNodeAttribute")
    attr.location = (-200, 0)
    attr.attribute_name = attr_name

    # 接続：Attribute Color -> Emission Color -> Output
    links.new(attr.outputs.get("Color"), emission.inputs.get("Color"))
    links.new(emission.outputs.get("Emission"), out.inputs.get("Surface"))

    return mat

def assign_material(obj, mat):
    if obj.type != 'MESH':
        return
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def create_icosphere(name=ICOSPHERE_NAME, subdiv=ICOSPHERE_SUBDIV, radius=ICOSPHERE_RADIUS):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    ensure_color_attribute(obj.data, ATTR_NAME)
    return obj

def create_any_mesh_points(name=ANY_MESH_NAME, n_verts=ANY_MESH_VERTS):
    # 「任意頂点数のメッシュ」: ここでは “点だけ” のメッシュを作る（後で自由に編集しやすい）
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    # 適当に分布（X方向に並べる例）
    for i in range(n_verts):
        x = (i / max(1, n_verts - 1)) * 2.0 - 1.0
        bm.verts.new(Vector((x, 1.5, 0.0)))
    bm.verts.ensure_lookup_table()
    bm.to_mesh(mesh)
    bm.free()

    ensure_color_attribute(mesh, ATTR_NAME)
    return obj


# -----------------------------
# 実行本体
# -----------------------------
def init_scene_env(n_verts=None):
    global ANY_MESH_VERTS
    if n_verts is not None:
        try:
            ANY_MESH_VERTS = int(n_verts)
        except Exception:
            pass
    # 5) 専用コレクション作成
    root = None
    cols = {n: get_or_create_collection(n, parent=root) for n in COLLECTION_NAMES}

    # 1) Emission + Attribute color のマテリアル
    mat = get_or_create_emission_attr_material(MAT_NAME, ATTR_NAME)

    # 2) Iso球体（Icosphere）Subdiv=2, radius=0.5, ColorAttribute "color"
    iso = create_icosphere(ICOSPHERE_NAME, ICOSPHERE_SUBDIV, ICOSPHERE_RADIUS)
    assign_material(iso, mat)

    # 3) 任意頂点数メッシュ（点メッシュ）
    any_obj = create_any_mesh_points(ANY_MESH_NAME, ANY_MESH_VERTS)
    assign_material(any_obj, mat)

    # 4) Solid View の Color を Attribute 表示に
    set_viewport_solid_attribute(ATTR_NAME)

    # コレクションへ配置
    if COL_FOR_ICOSPHERE in cols:
        move_object_to_collection(iso, cols[COL_FOR_ICOSPHERE])
    if COL_FOR_ANYMESH in cols:
        move_object_to_collection(any_obj, cols[COL_FOR_ANYMESH])

    # マテリアル自体はコレクションに入らないので、管理用にテキストで終わり
    print("[Init] Done:",
          f"Material={mat.name}, Icosphere={iso.name}, AnyMesh={any_obj.name}, Attr={ATTR_NAME}")

if __name__ == "__main__":
    init_scene_env()
