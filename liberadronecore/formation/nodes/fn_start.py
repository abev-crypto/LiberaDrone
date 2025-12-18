import bpy


class FN_StartNode(bpy.types.Node):
    bl_idname = "FN_StartNode"
    bl_label  = "Start"
    bl_icon = "ACTION"

    def init(self, context):
        self.outputs.new("FN_SocketFlow", "Next")