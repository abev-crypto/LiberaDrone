import os

import bpy

from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.ui import liberadrone_panel
from liberadronecore.util import image_util


class LD_OT_create_range_object(bpy.types.Operator):
    bl_idname = "liberadrone.create_range_object"
    bl_label = "Create Area Object"
    bl_description = "Create or update AreaObject from area parameters"

    def execute(self, context):
        scene = context.scene
        width = float(getattr(scene, "ld_checker_range_width", 0.0))
        if width <= 0.0:
            self.report({'ERROR'}, "Area Width must be > 0")
            return {'CANCELLED'}
        height = float(getattr(scene, "ld_checker_range_height", 0.0))
        depth = float(getattr(scene, "ld_checker_range_depth", 0.0))
        if height <= 0.0:
            height = width
        if depth <= 0.0:
            depth = width

        obj = bpy.data.objects.get(liberadrone_panel.RANGE_OBJ_NAME)
        if obj is None or obj.type != 'MESH':
            mesh = bpy.data.meshes.new(f"{liberadrone_panel.RANGE_OBJ_NAME}Mesh")
            obj = bpy.data.objects.new(liberadrone_panel.RANGE_OBJ_NAME, mesh)
        else:
            mesh = obj.data
            if mesh is None or mesh.users > 1:
                mesh = bpy.data.meshes.new(f"{liberadrone_panel.RANGE_OBJ_NAME}Mesh")
                obj.data = mesh
        liberadrone_panel._update_range_mesh(mesh, width, height, depth)
        if obj.name not in scene.collection.objects:
            scene.collection.objects.link(obj)
        try:
            obj.display_type = 'WIRE'
        except Exception:
            pass
        from liberadronecore.system import sence_setup

        target_col = sence_setup.get_or_create_collection(sence_setup.COL_FOR_PREVIEW)
        sence_setup.move_object_to_collection(obj, target_col)

        scene.ld_checker_range_object = obj
        self.report({'INFO'}, f"Area object created: {obj.name}")
        return {'FINISHED'}


class LD_OT_pack_scene_images(bpy.types.Operator):
    bl_idname = "liberadrone.pack_scene_images"
    bl_label = "Pack Cache Images"
    bl_description = "Pack images saved in the scene cache folder into the blend file"

    def execute(self, context):
        cache_dir = image_util.get_scene_cache_dir(context.scene, create=False)
        if not cache_dir:
            self.report({'ERROR'}, "Save the blend file before packing cache images.")
            return {'CANCELLED'}
        cache_dir = os.path.normpath(cache_dir)
        packed = 0
        skipped = 0
        for img in bpy.data.images:
            if img is None:
                continue
            if getattr(img, "packed_file", None) is not None:
                skipped += 1
                continue
            filepath = getattr(img, "filepath", "") or getattr(img, "filepath_raw", "")
            if not filepath:
                continue
            abs_path = bpy.path.abspath(filepath)
            if not abs_path:
                continue
            try:
                in_cache = os.path.commonpath([cache_dir, os.path.normpath(abs_path)]) == cache_dir
            except Exception:
                in_cache = False
            if not in_cache:
                continue
            try:
                img.pack()
                packed += 1
            except Exception:
                pass
        self.report({'INFO'}, f"Packed {packed} images (skipped {skipped}).")
        return {'FINISHED'}


class LiberadroneOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LD_OT_pack_scene_images)
        bpy.utils.register_class(LD_OT_create_range_object)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LD_OT_create_range_object)
        bpy.utils.unregister_class(LD_OT_pack_scene_images)
