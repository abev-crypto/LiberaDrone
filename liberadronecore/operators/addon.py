import bpy

import liberadronecore.system.request as request
from liberadronecore.reg.base_reg import RegisterBase


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


class LD_OT_setup_all(bpy.types.Operator):
    bl_idname = "liberadrone.setup_all"
    bl_label = "Setup"
    bl_description = "Run Formation setup and add Formation/LED workspaces"
    bl_options = {'REGISTER'}

    drone_count: bpy.props.IntProperty(
        name="Drone Count",
        default=0,
        min=0,
        soft_min=1,
    )

    @staticmethod
    def _find_start_drone_count(context) -> int | None:
        tree = None
        space = getattr(context, "space_data", None)
        if space and getattr(space, "edit_tree", None):
            tree = space.edit_tree
        if tree is None or getattr(tree, "bl_idname", "") != "FN_FormationTree":
            tree = next(
                (ng for ng in bpy.data.node_groups if getattr(ng, "bl_idname", "") == "FN_FormationTree"),
                None,
            )
        if tree:
            for node in tree.nodes:
                if getattr(node, "bl_idname", "") == "FN_StartNode":
                    count = getattr(node, "drone_count", None)
                    if count is not None:
                        return max(1, int(count))
                    break
        return None

    def invoke(self, context, event):
        default_count = self._find_start_drone_count(context)
        if default_count is not None:
            self.drone_count = default_count
        elif self.drone_count <= 0:
            self.drone_count = 1
        self._from_dialog = True
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "drone_count", text="Drone Count")

    def execute(self, context):
        use_override = getattr(self, "_from_dialog", False)
        if not use_override:
            try:
                use_override = self.properties.is_property_set("drone_count")
            except Exception:
                use_override = False
        if use_override and self.drone_count <= 0:
            self.report({'ERROR'}, "Drone Count must be at least 1.")
            return {'CANCELLED'}
        if use_override and self.drone_count > 0:
            bpy.ops.fn.setup_scene(drone_count_override=self.drone_count)
        else:
            bpy.ops.fn.setup_scene()
        bpy.ops.liberadrone.setup_workspace_formation()
        bpy.ops.liberadrone.setup_workspace_led()
        return {'FINISHED'}


class AddonOps(RegisterBase):
    @classmethod
    def register(cls) -> None:
        bpy.utils.register_class(LD_OT_setup_all)

    @classmethod
    def unregister(cls) -> None:
        bpy.utils.unregister_class(LD_OT_setup_all)
