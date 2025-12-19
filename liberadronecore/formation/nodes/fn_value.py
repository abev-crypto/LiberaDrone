import bpy
from liberadronecore.formation.fn_nodecategory import FN_Node

class FN_ValueNode(bpy.types.Node, FN_Node):
    bl_idname = "FN_ValueNode"
    bl_label  = "Value"
    bl_icon = "ACTION"

    value: bpy.props.IntProperty(name="Value", default=0)

    def init(self, context):
        self.outputs.new("FN_SocketInt", "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value")
