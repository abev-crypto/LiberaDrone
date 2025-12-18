import bpy
from bpy.types import NodeTree, Node, NodeSocket, Operator, Panel
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty, IntProperty

class FN_MergeNode(Node):
    bl_idname = "FN_MergeNode"
    bl_label = "Merge"
    bl_icon = "DECORATE_KEYFRAME"

    num: IntProperty(name="Num", default=2)

    def init(self, context):
        self.inputs.new("FN_SocketFlow", "1")
        self.inputs.new("FN_SocketFlow", "2")
        self.inputs.new("FN_SocketInt", "Num")
        self.outputs.new("FN_SocketFlow", "Out")

    def draw_buttons(self, context, layout):
        layout.prop(self, "num")