import bpy
from bpy.props import FloatProperty

from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.util import view_setup


class LD_OT_setup_glare_compositor(bpy.types.Operator):
    bl_idname = "liberadrone.setup_glare_compositor"
    bl_label = "Setup Glare Compositor"
    bl_description = "Create a bloom glare compositor setup for the active scene"
    bl_options = {'REGISTER'}

    def execute(self, context):
        view_setup.setup_glare_compositor(context.scene)
        self.report({'INFO'}, "Glare compositor configured")
        return {'FINISHED'}


class LD_OT_frame_from_neg_y(bpy.types.Operator):
    bl_idname = "liberadrone.frame_from_neg_y"
    bl_label = "Frame From -Y"
    bl_description = "Reposition the camera on the negative Y axis to frame the selection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        margin = getattr(context.scene, "ld_camera_margin", 1.2)
        if view_setup.frame_selection_from_neg_y(margin_scale=margin):
            self.report({'INFO'}, "Camera framed from -Y")
            return {'FINISHED'}

        self.report({'WARNING'}, "Select at least one non-camera object")
        return {'CANCELLED'}


class ViewOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LD_OT_setup_glare_compositor)
        bpy.utils.register_class(LD_OT_frame_from_neg_y)

        if not hasattr(bpy.types.Scene, "ld_camera_margin"):
            bpy.types.Scene.ld_camera_margin = FloatProperty(
                name="Camera Margin",
                description="Scale factor applied to the bounding box when framing the camera",
                default=1.4,
                min=1.0,
                soft_max=3.0,
            )

    @classmethod
    def unregister(cls) -> None:
        if hasattr(bpy.types.Scene, "ld_camera_margin"):
            del bpy.types.Scene.ld_camera_margin

        bpy.utils.unregister_class(LD_OT_frame_from_neg_y)
        bpy.utils.unregister_class(LD_OT_setup_glare_compositor)
