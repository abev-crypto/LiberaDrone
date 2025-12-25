import bpy
from liberadronecore.ui.graph import check_graph


class LD_OT_show_check_graph(bpy.types.Operator):
    bl_idname = "liberadrone.show_check_graph"
    bl_label = "Show Check Graph"
    bl_options = {'REGISTER'}

    def execute(self, context):
        check_graph.VelocityCandleWindow.show_window()
        return {'FINISHED'}
