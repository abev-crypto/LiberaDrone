import bpy
from liberadronecore.formation.fn_nodecategory import FN_Node

class FN_StartNode(bpy.types.Node, FN_Node):
    bl_idname = "FN_StartNode"
    bl_label  = "Start"
    bl_icon = "ACTION"

    computed_start_frame: bpy.props.IntProperty(name="Computed Start", default=-1, options={'SKIP_SAVE'})

    def init(self, context):
        sock = self.inputs.new("FN_SocketInt", "Start Frame")
        sock.value = 1
        self.outputs.new("FN_SocketFlow", "Next")
