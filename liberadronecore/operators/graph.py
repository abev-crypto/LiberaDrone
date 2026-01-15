import bpy

from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.ui.graph import check_graph


class LD_OT_show_check_graph(bpy.types.Operator):
    bl_idname = "liberadrone.show_check_graph"
    bl_label = "Show Check Graph"
    bl_options = {'REGISTER'}

    def execute(self, context):
        check_graph.VelocityCandleWindow.show_window()
        return {'FINISHED'}


class GraphOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LD_OT_show_check_graph)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LD_OT_show_check_graph)
