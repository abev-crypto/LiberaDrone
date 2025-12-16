import bpy
from bpy.types import NodeTree, Node, NodeSocket, Operator, Panel
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty

class FN_SplitNode(Node):
    bl_idname = "FN_SplitNode"
    bl_label = "Split"
    bl_icon = "DECORATE_KEYFRAME"

    mode: EnumProperty(
        name="Condition Source",
        items=[
            ("SOCKET", "Socket", "Use input Bool socket"),
            ("PROPERTY", "Property", "Use node property boolean"),
        ],
        default="PROPERTY",
    )
    condition: BoolProperty(name="Condition", default=True)

    def init(self, context):
        self.inputs.new("FN_SocketFlow", "In")
        self.inputs.new("FN_SocketBool", "Cond")
        self.outputs.new("FN_SocketFlow", "True")
        self.outputs.new("FN_SocketFlow", "False")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="Cond")
        if self.mode == "PROPERTY":
            layout.prop(self, "condition", text="Value")