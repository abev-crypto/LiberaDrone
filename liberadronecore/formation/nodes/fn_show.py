import bpy
from liberadronecore.formation.fn_nodecategory import FN_Node

class FN_ShowNode(bpy.types.Node, FN_Node):
    bl_idname = "FN_ShowNode"
    bl_label  = "Show"
    bl_icon = "ACTION"

    # 例えば Skybrush エフェクト名とか時間
    effect_name: bpy.props.StringProperty(name="Effect")
    duration: bpy.props.FloatProperty(name="Duration", default=5.0, min=0.0)

    def init(self, context):
        self.inputs.new("FN_SocketFlow", "In")
        self.outputs.new("FN_SocketFlow", "Next")

    def draw_buttons(self, context, layout):
        layout.prop(self, "effect_name")            
        layout.prop(self, "duration")