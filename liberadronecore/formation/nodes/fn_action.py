class LD_ActionNode(bpy.types.Node):
    bl_idname = "LD_ActionNode"
    bl_label  = "Action"
    bl_icon = "ACTION"

    # 例えば Skybrush エフェクト名とか時間
    effect_name: bpy.props.StringProperty(name="Effect")
    duration: bpy.props.FloatProperty(name="Duration", default=5.0, min=0.0)

    def init(self, context):
        self.inputs.new("LD_SocketFlow", "In")
        self.outputs.new("LD_SocketFlow", "Next")

    def draw_buttons(self, context, layout):
        layout.prop(self, "effect_name")
        layout.prop(self, "duration")
