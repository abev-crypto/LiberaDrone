import bpy
from liberadronecore.formation.fn_nodecategory import FN_Node

class FN_StartNode(bpy.types.Node, FN_Node):
    bl_idname = "FN_StartNode"
    bl_label  = "Start"
    bl_icon = "ACTION"

    computed_start_frame: bpy.props.IntProperty(name="Computed Start", default=-1, options={'SKIP_SAVE'})
    drone_count: bpy.props.IntProperty(name="Drone Count", default=1000, min=1)
    error_message: bpy.props.StringProperty(name="Error", default="", options={'SKIP_SAVE'})

    def init(self, context):
        sock = self.inputs.new("FN_SocketInt", "Start Frame")
        sock.value = 0
        self.outputs.new("FN_SocketFlow", "Next")

    def draw_buttons(self, context, layout):
        layout.prop(self, "drone_count")
        if self.error_message:
            layout.label(text=self.error_message, icon='ERROR')
        if self.computed_start_frame >= 0:
            row = layout.row()
            row.alignment = 'RIGHT'
            row.label(text=f"start:{self.computed_start_frame}f")
