import bpy
from liberadronecore.formation.fn_nodecategory import FN_Register

class FN_FormationTree(bpy.types.NodeTree, FN_Register):
    bl_idname = "FN_FormationTree"
    bl_label  = "FN Formaiton"
    bl_icon   = 'NODETREE'  # 好きなアイコン

    @classmethod
    def poll(cls, context):
        # いつでも表示でよければ True
        return True
