import bpy

from liberadronecore.reg.base_reg import RegisterBase
from liberadronecore.system import update as update_mod


class LD_OT_check_update(bpy.types.Operator):
    bl_idname = "liberadrone.check_update"
    bl_label = "Check Update (GitHub main)"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        addon_key = __package__.split(".")[0]
        prefs = context.preferences.addons[addon_key].preferences

        repo = update_mod.GithubRepo(
            owner=prefs.gh_owner,
            repo=prefs.gh_repo,
            branch=prefs.gh_branch,
            addon_subdir=prefs.gh_addon_subdir,
        )

        try:
            local_v = update_mod.get_local_version(addon_key)
            remote_v = update_mod.get_remote_version(repo)
        except Exception as exc:
            self.report({'ERROR'}, f"Update check failed: {exc}")
            return {'CANCELLED'}

        prefs.last_local_version = str(local_v) if local_v else "None"
        prefs.last_remote_version = str(remote_v) if remote_v else "None"

        if not local_v or not remote_v:
            prefs.update_available = False
            self.report({'WARNING'}, "Version info unavailable. Check addon prefs.")
            return {'FINISHED'}

        prefs.update_available = update_mod._version_gt(remote_v, local_v)
        if prefs.update_available:
            self.report({'INFO'}, f"Update available: local {local_v} -> remote {remote_v}")
        else:
            self.report({'INFO'}, f"Up to date: {local_v}")
        return {'FINISHED'}


class LD_OT_apply_update(bpy.types.Operator):
    bl_idname = "liberadrone.apply_update"
    bl_label = "Update Now (Download & Install)"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        addon_key = __package__.split(".")[0]
        prefs = context.preferences.addons[addon_key].preferences
        repo = update_mod.GithubRepo(
            owner=prefs.gh_owner,
            repo=prefs.gh_repo,
            branch=prefs.gh_branch,
            addon_subdir=prefs.gh_addon_subdir,
        )

        try:
            addon_dir = update_mod._addon_root_dir_from_module(addon_key)
            zip_bytes = update_mod.download_main_zip(repo)
            update_mod.install_from_zip_bytes(zip_bytes, repo, addon_dir)

            prefs.update_available = False
            self.report({'INFO'}, "Update installed. Reload scripts or restart Blender.")
            return {'FINISHED'}

        except Exception as exc:
            self.report({'ERROR'}, f"Update failed: {exc}")
            return {'CANCELLED'}


class UpdateOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LD_OT_check_update)
        bpy.utils.register_class(LD_OT_apply_update)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LD_OT_apply_update)
        bpy.utils.unregister_class(LD_OT_check_update)
