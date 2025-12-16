"""
Docstring for liberadronecore.system.transition.copyloc
TODO あれであったCopyLocationを使ったシンプルな移動システムを作成する
"""

import bpy

# -----------------------------
# Settings
# -----------------------------
VG_PREFIX = "PT_vtx_"                 # 作り直すVGのプレフィックス
COLLECTION_PREFIX = "PT_VGBlend_"
CONTROLLER_NAME = "PT_VGBlend_CTRL"
EMPTY_PREFIX = "PT_vtxNull_"
PROP_NAME = "blend"                   # 0..1 : 0=A, 1=B

# -----------------------------
# Helpers
# -----------------------------
def ensure_object_mode():
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

def get_two_selected_mesh_objects():
    sel = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(sel) != 2:
        raise RuntimeError("メッシュオブジェクトをちょうど2つ選択してください。（アクティブ= A、もう1つ= B）")

    A = bpy.context.view_layer.objects.active
    if A not in sel:
        raise RuntimeError("アクティブオブジェクトが選択メッシュに含まれていません。")

    B = sel[0] if sel[1] == A else sel[1]
    return A, B

def ensure_collection(name: str):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col

def link_to_collection(obj, col):
    # すでにどこかにリンクされている前提で、目的コレクションにもリンク
    if obj.name not in col.objects:
        col.objects.link(obj)

def safe_remove_object(obj):
    # 全コレクションから unlink して削除
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    bpy.data.objects.remove(obj, do_unlink=True)

def clear_old_objects_in_collection(col):
    # コレクション内のオブジェクトを削除（Empty群など）
    for obj in list(col.objects):
        safe_remove_object(obj)

def remove_prefixed_vertex_groups(obj, prefix):
    vgs = obj.vertex_groups
    to_remove = [vg for vg in vgs if vg.name.startswith(prefix)]
    for vg in to_remove:
        vgs.remove(vg)

def ensure_blend_property(ctrl_obj):
    if PROP_NAME not in ctrl_obj:
        ctrl_obj[PROP_NAME] = 0.0
    ui = ctrl_obj.id_properties_ui(PROP_NAME)
    ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, description="0=A, 1=B")

def set_influence_driver(con, ctrl_obj, invert=False):
    # 既存ドライバ消して張り直し
    try:
        con.driver_remove("influence")
    except TypeError:
        pass

    fcurve = con.driver_add("influence")
    drv = fcurve.driver
    drv.type = 'SCRIPTED'

    var = drv.variables.new()
    var.name = "t"
    var.type = 'SINGLE_PROP'
    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ctrl_obj
    targ.data_path = f'["{PROP_NAME}"]'

    drv.expression = "(1.0 - t)" if invert else "t"

# -----------------------------
# Main
# -----------------------------
def main():
    ensure_object_mode()
    A, B = get_two_selected_mesh_objects()

    vcountA = len(A.data.vertices)
    vcountB = len(B.data.vertices)
    if vcountA != vcountB:
        raise RuntimeError(f"頂点数が一致していません: A={vcountA} / B={vcountB}")

    # コレクション（以前のを破棄して作り直し）
    col_name = f"{COLLECTION_PREFIX}{A.name}_to_{B.name}"
    col = ensure_collection(col_name)
    clear_old_objects_in_collection(col)

    # VGは「再利用しない」→ prefix一致を両方消して作り直し
    remove_prefixed_vertex_groups(A, VG_PREFIX)
    remove_prefixed_vertex_groups(B, VG_PREFIX)

    # コントローラEmpty（blend一本化）
    ctrl = bpy.data.objects.new(CONTROLLER_NAME, None)
    ctrl.empty_display_type = 'PLAIN_AXES'
    ctrl.empty_display_size = 0.2
    bpy.context.scene.collection.objects.link(ctrl)
    link_to_collection(ctrl, col)
    ensure_blend_property(ctrl)

    # 各頂点分：VG作成 + Null作成 + CopyLoc 2本 + ドライバ
    for i in range(vcountA):
        vg_name = f"{VG_PREFIX}{i:06d}"

        # VertexGroup（単一頂点 weight=1）
        vgA = A.vertex_groups.new(name=vg_name)
        vgA.add([i], 1.0, 'REPLACE')

        vgB = B.vertex_groups.new(name=vg_name)
        vgB.add([i], 1.0, 'REPLACE')

        # Null(Empty)
        null_name = f"{EMPTY_PREFIX}{i:06d}"
        null = bpy.data.objects.new(null_name, None)
        null.empty_display_type = 'SPHERE'
        null.empty_display_size = 0.03

        # 初期位置はA頂点のワールド座標
        null.location = A.matrix_world @ A.data.vertices[i].co

        bpy.context.scene.collection.objects.link(null)
        link_to_collection(null, col)

        # Copy Location A (subtarget = VG)
        cA = null.constraints.new(type='COPY_LOCATION')
        cA.name = "CopyLoc_A"
        cA.target = A
        cA.subtarget = vg_name
        cA.owner_space = 'WORLD'
        cA.target_space = 'WORLD'

        # Copy Location B (subtarget = VG)
        cB = null.constraints.new(type='COPY_LOCATION')
        cB.name = "CopyLoc_B"
        cB.target = B
        cB.subtarget = vg_name
        cB.owner_space = 'WORLD'
        cB.target_space = 'WORLD'

        # influence driven by ctrl[blend]
        set_influence_driver(cA, ctrl, invert=True)   # 1 - blend
        set_influence_driver(cB, ctrl, invert=False)  # blend

    print(f"Done: {vcountA} Nulls + VG per vertex created in collection '{col_name}'. Controller='{CONTROLLER_NAME}' prop='{PROP_NAME}'")

main()
