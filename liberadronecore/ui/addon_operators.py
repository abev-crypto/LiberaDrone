import bpy
import liberadronecore.system.request as request


class LD_OT_install_deps(bpy.types.Operator):
    bl_idname = "liberadrone.install_deps"
    bl_label = "Install Missing Python Packages"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        missing = request.deps_missing()
        if not missing:
            self.report({'INFO'}, "All dependencies are already installed.")
            return {'FINISHED'}

        for pip_name, _import_name in missing:
            ver = None
            for p, i, v in request.REQUIRED:
                if p == pip_name:
                    ver = v
                    break
            try:
                request.pip_install(pip_name, ver)
            except Exception as e:
                self.report({'ERROR'}, f"Failed: {pip_name} ({e})")
                return {'CANCELLED'}

        self.report({'INFO'}, "Installed. Restart Blender or Reload Scripts.")
        return {'FINISHED'}


class LD_OT_dummy(bpy.types.Operator):
    bl_idname = "liberadrone.dummy"
    bl_label = "Dummy"

    def execute(self, context):
        self.report({'INFO'}, "Hello")
        return {'FINISHED'}
