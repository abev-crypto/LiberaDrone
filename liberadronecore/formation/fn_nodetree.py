class FN_FormationTree(bpy.types.NodeTree):
    bl_idname = "FN_FormationTree"
    bl_label  = "FN Formaiton"
    bl_icon   = 'NODETREE'  # 好きなアイコン

    @classmethod
    def poll(cls, context):
        # いつでも表示でよければ True
        return True
