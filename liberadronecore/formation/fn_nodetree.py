import bpy
from liberadronecore.formation.fn_nodecategory import FN_Register

class FN_FormationTree(bpy.types.NodeTree, FN_Register):
    bl_idname = "FN_FormationTree"
    bl_label  = "FN Formaiton"
    bl_icon   = 'NODETREE'  # 好きなアイコン
    bl_use_link_search = True

    @classmethod
    def poll(cls, context):
        # ぁE��でも表示でよけれ�E True
        return True
