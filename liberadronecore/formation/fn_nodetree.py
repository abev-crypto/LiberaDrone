class LD_FormationTree(bpy.types.NodeTree):
    bl_idname = "LD_FormationTree"
    bl_label  = "LD Formaiton"
    bl_icon   = 'SEQ_STRIP'  # 好きなアイコン

    @classmethod
    def poll(cls, context):
        # いつでも表示でよければ True
        return True
