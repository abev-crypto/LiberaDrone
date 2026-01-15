import bpy

from liberadronecore.overlay import checker
from liberadronecore.reg.base_reg import RegisterBase


class VIEW3D_OT_draw_gn_vertex_markers(bpy.types.Operator):
    """Toggle drawing GN vertex markers in viewport."""

    bl_idname = "view3d.draw_gn_vertex_markers"
    bl_label = "Toggle GN Vertex Markers"

    def execute(self, context):
        checker.set_enabled(not checker.is_enabled())
        self.report({'INFO'}, "GN vertex markers: ON" if checker.is_enabled() else "GN vertex markers: OFF")
        checker._tag_redraw(context)
        return {'FINISHED'}


class OverlayOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(VIEW3D_OT_draw_gn_vertex_markers)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(VIEW3D_OT_draw_gn_vertex_markers)
