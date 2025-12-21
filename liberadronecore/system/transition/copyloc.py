"""
Docstring for liberadronecore.system.transition.copyloc
TODO 縺ゅｌ縺ｧ縺ゅ▲縺櫃opyLocation繧剃ｽｿ縺｣縺溘す繝ｳ繝励Ν縺ｪ遘ｻ蜍輔す繧ｹ繝・Β繧剃ｽ懈・縺吶ｋ
"""

import bpy

# -----------------------------
# Settings
# -----------------------------
VG_PREFIX = "PT_vtx_"                 # 菴懊ｊ逶ｴ縺儼G縺ｮ繝励Ξ繝輔ぅ繝・け繧ｹ
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
        raise RuntimeError("繝｡繝・す繝･繧ｪ繝悶ず繧ｧ繧ｯ繝医ｒ縺｡繧・≧縺ｩ2縺､驕ｸ謚槭＠縺ｦ縺上□縺輔＞縲ゑｼ医い繧ｯ繝・ぅ繝・ A縲√ｂ縺・縺､= B・・)

    A = bpy.context.view_layer.objects.active
    if A not in sel:
        raise RuntimeError("繧｢繧ｯ繝・ぅ繝悶が繝悶ず繧ｧ繧ｯ繝医′驕ｸ謚槭Γ繝・す繝･縺ｫ蜷ｫ縺ｾ繧後※縺・∪縺帙ｓ縲・)

    B = sel[0] if sel[1] == A else sel[1]
    return A, B

def ensure_collection(name: str):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col

def link_to_collection(obj, col):
    # 縺吶〒縺ｫ縺ｩ縺薙°縺ｫ繝ｪ繝ｳ繧ｯ縺輔ｌ縺ｦ縺・ｋ蜑肴署縺ｧ縲∫岼逧・さ繝ｬ繧ｯ繧ｷ繝ｧ繝ｳ縺ｫ繧ゅΜ繝ｳ繧ｯ
    if obj.name not in col.objects:
        col.objects.link(obj)

def safe_remove_object(obj):
    # 蜈ｨ繧ｳ繝ｬ繧ｯ繧ｷ繝ｧ繝ｳ縺九ｉ unlink 縺励※蜑企勁
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    bpy.data.objects.remove(obj, do_unlink=True)

def clear_old_objects_in_collection(col):
    # 繧ｳ繝ｬ繧ｯ繧ｷ繝ｧ繝ｳ蜀・・繧ｪ繝悶ず繧ｧ繧ｯ繝医ｒ蜑企勁・・mpty鄒､縺ｪ縺ｩ・・
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
    # 譌｢蟄倥ラ繝ｩ繧､繝先ｶ医＠縺ｦ蠑ｵ繧顔峩縺・
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
# Builder
# -----------------------------
def build_copyloc(
    A,
    B,
    *,
    collection_name: str | None = None,
    controller_name: str | None = None,
    clear_old: bool = True,
):
    ensure_object_mode()
    vcountA = len(A.data.vertices)
    vcountB = len(B.data.vertices)
    if vcountA != vcountB:
        raise RuntimeError(f"頂点数が一致してぁE��せん: A={vcountA} / B={vcountB}")

    col_name = collection_name or f"{COLLECTION_PREFIX}{A.name}_to_{B.name}"
    ctrl_name = controller_name or f"{CONTROLLER_NAME}_{A.name}_to_{B.name}"

    col = ensure_collection(col_name)
    if clear_old:
        clear_old_objects_in_collection(col)

    # VGは「�E利用しなぁE���E prefix一致を両方消して作り直ぁE
    remove_prefixed_vertex_groups(A, VG_PREFIX)
    remove_prefixed_vertex_groups(B, VG_PREFIX)

    # コントローラEmpty�E�Elend一本化！E
    ctrl = bpy.data.objects.new(ctrl_name, None)
    ctrl.empty_display_type = 'PLAIN_AXES'
    ctrl.empty_display_size = 0.2
    bpy.context.scene.collection.objects.link(ctrl)
    link_to_collection(ctrl, col)
    ensure_blend_property(ctrl)

    # 吁E��点刁E��VG作�E + Null作�E + CopyLoc 2本 + ドライチE
    for i in range(vcountA):
        vg_name = f"{VG_PREFIX}{i:06d}"

        # VertexGroup�E�単一頂点 weight=1�E�E
        vgA = A.vertex_groups.new(name=vg_name)
        vgA.add([i], 1.0, 'REPLACE')

        vgB = B.vertex_groups.new(name=vg_name)
        vgB.add([i], 1.0, 'REPLACE')

        # Null(Empty)
        null_name = f"{EMPTY_PREFIX}{i:06d}"
        null = bpy.data.objects.new(null_name, None)
        null.empty_display_type = 'SPHERE'
        null.empty_display_size = 0.03

        # 初期位置はA頂点のワールド座樁E
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

    print(f"Done: {vcountA} Nulls + VG per vertex created in collection '{col_name}'. Controller='{ctrl_name}' prop='{PROP_NAME}'")
    return ctrl, col


# -----------------------------
# Main
# -----------------------------
def main():
    ensure_object_mode()
    A, B = get_two_selected_mesh_objects()
    build_copyloc(A, B, collection_name=None, controller_name=None, clear_old=True)

main()
