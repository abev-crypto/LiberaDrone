import bpy
import liberadronecore.system.request as request
from liberadronecore.ui.operators import LD_OT_dummy, LD_OT_install_deps


class LD_Preferences(bpy.types.AddonPreferences):
    # ☁Eここはアドオンのモジュール名（フォルダ吁E/ __init__.py のパッケージ名！E
    bl_idname = "liberadronecore"
    bl_label = "LiberaDrone Preferences"
    gh_owner: bpy.props.StringProperty(name="GitHub Owner", default="abev-crypto")
    gh_repo: bpy.props.StringProperty(name="GitHub Repo", default="LiberaDrone")
    gh_branch: bpy.props.StringProperty(name="Branch", default="main")
    gh_addon_subdir: bpy.props.StringProperty(
        name="Addon Subdir (in repo)",
        default="",
        description="リポジトリ直下なら空。侁E src/my_addon",
    )

    update_available: bpy.props.BoolProperty(name="Update Available", default=False)
    last_local_version: bpy.props.StringProperty(name="Local Version", default="")
    last_remote_version: bpy.props.StringProperty(name="Remote Version", default="")
    auto_check: bpy.props.BoolProperty(name="Auto Check Update", default=True)

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


# ---- (侁E 本体機�E�E�依存OKの時だけ登録したぁE��らここに入れる ----
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

    # 依存が揁E��てぁE��ば本体も登録
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

