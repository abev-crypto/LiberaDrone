import bpy

import liberadronecore.system.request as request
from liberadronecore.operators.addon import LD_OT_dummy, LD_OT_install_deps


class LD_Preferences(bpy.types.AddonPreferences):
    # Addon module id must match the package name in __init__.py.
    bl_idname = "liberadronecore"
    bl_label = "LiberaDrone Preferences"
    gh_owner: bpy.props.StringProperty(name="GitHub Owner", default="abev-crypto")
    gh_repo: bpy.props.StringProperty(name="GitHub Repo", default="LiberaDrone")
    gh_branch: bpy.props.StringProperty(name="Branch", default="main")
    gh_addon_subdir: bpy.props.StringProperty(
        name="Addon Subdir (in repo)",
        default="liberadronecore",
        description="Relative path in the repo, e.g. src/my_addon",
    )

    update_available: bpy.props.BoolProperty(name="Update Available", default=False)
    last_local_version: bpy.props.StringProperty(name="Local Version", default="")
    last_remote_version: bpy.props.StringProperty(name="Remote Version", default="")
    auto_check: bpy.props.BoolProperty(name="Auto Check Update", default=True)
    led_task_update: bpy.props.BoolProperty(
        name="LED Task Update",
        default=True,
        description="Update LED effects via scheduled tasks instead of immediate updates",
    )

    def draw(self, context):
        layout = self.layout
        missing = request.deps_missing()

        layout.label(text="Python Dependencies", icon='SCRIPT')

        if missing:
            box = layout.box()
            box.label(text="Missing packages:", icon='ERROR')
            for pip_name, import_name in missing:
                box.label(text=f"- {pip_name}  (import: {import_name})")

            layout.operator("liberadrone.install_deps", icon='IMPORT')
            layout.separator()
            layout.label(text="After installation:", icon='INFO')
            layout.label(text="Restart Blender or use 'Reload Scripts'.")
        else:
            layout.label(text="All dependencies are installed.", icon='CHECKMARK')


        col = layout.column(align=True)
        col.label(text="GitHub main updater")

        col.prop(self, "gh_owner")
        col.prop(self, "gh_repo")
        col.prop(self, "gh_branch")
        col.prop(self, "gh_addon_subdir")
        col.prop(self, "auto_check")

        row = col.row(align=True)
        row.operator("liberadrone.check_update", text="Check Update")

        if self.update_available:
            col.alert = True
            col.label(text="Update available!", icon='ERROR')
            col.alert = False
            col.operator("liberadrone.apply_update", text="Update Now", icon='IMPORT')
        else:
            col.label(text="No update detected (or not checked yet).")

        col.separator()
        col.label(text=f"Local:  {self.last_local_version}")
        col.label(text=f"Remote: {self.last_remote_version}")
        layout.separator()
        layout.label(text="LED Effects")
        layout.prop(self, "led_task_update")


# ---- (Register core prefs/operators even when deps are missing) ----
_bootstrap_classes = (
    LD_OT_install_deps,
    LD_Preferences,
)

_full_classes = (
    LD_OT_dummy,
)

_registered_full = False


def register():
    print("LiberaDrone: register addon_pref")
    global _registered_full
    for c in _bootstrap_classes:
        bpy.utils.register_class(c)

    # If deps are available, register optional operators.
    if not request.deps_missing():
        for c in _full_classes:
            bpy.utils.register_class(c)
        _registered_full = True
    else:
        _registered_full = False


def unregister():
    global _registered_full
    if _registered_full:
        for c in reversed(_full_classes):
            bpy.utils.unregister_class(c)

    for c in reversed(_bootstrap_classes):
        bpy.utils.unregister_class(c)

