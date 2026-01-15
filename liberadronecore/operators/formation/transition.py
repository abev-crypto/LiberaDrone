import bpy
from bpy.props import FloatProperty, StringProperty

from liberadronecore.formation import fn_parse
from liberadronecore.formation.fn_nodecategory import FN_Register
from liberadronecore.system.transition import transition_apply
from liberadronecore.system.transition.transition_apply import apply_transition_by_node_name
from liberadronecore.util import copyloc_utils


class FN_OT_apply_transition(bpy.types.Operator, FN_Register):
    bl_idname = "fn.apply_transition"
    bl_label = "Apply Transition"
    node_name: StringProperty()

    def execute(self, context):
        ok, message = apply_transition_by_node_name(self.node_name, context)
        if ok:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        self.report({'ERROR'}, message)
        return {'CANCELLED'}


class FN_OT_shape_copyloc_influence(bpy.types.Operator, FN_Register):
    bl_idname = "fn.shape_copyloc_influence"
    bl_label = "Shape CopyLoc Influence"
    node_name: StringProperty()
    handle_frames: FloatProperty(name="Handle Frames", default=2.0, min=0.0)

    def execute(self, context):
        if not self.node_name:
            self.report({'ERROR'}, "Missing node name.")
            return {'CANCELLED'}

        arm_name = f"Transition_{self.node_name}_Armature"
        arm_obj = bpy.data.objects.get(arm_name)
        if arm_obj is None:
            self.report({'ERROR'}, f"Armature not found: {arm_name}")
            return {'CANCELLED'}

        updated = copyloc_utils.shape_copyloc_influence_handles(
            arm_obj,
            self.handle_frames,
        )
        if updated <= 0:
            self.report({'WARNING'}, "No CopyLoc influence curves updated.")
            return {'FINISHED'}
        self.report({'INFO'}, f"Updated {updated} CopyLoc influence curves.")
        return {'FINISHED'}


class FN_OT_force_apply_transition(bpy.types.Operator, FN_Register):
    bl_idname = "fn.force_apply_transition"
    bl_label = "Force Apply Transition"
    node_name: StringProperty()

    def execute(self, context):
        if not self.node_name:
            self.report({'ERROR'}, "Missing node name.")
            return {'CANCELLED'}

        tree, node = transition_apply._node_tree_from_context(context, self.node_name)
        if node is None:
            self.report({'ERROR'}, "Node not found.")
            return {'CANCELLED'}

        transition_nodes = [n for n in tree.nodes if fn_parse._is_transition_node(n)]
        transition_apply.purge_transition_nodes(transition_nodes)
        try:
            ok, message = transition_apply.apply_transition(node, context)
        except Exception as exc:
            ok = False
            message = str(exc)
        if ok:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        self.report({'ERROR'}, message)
        return {'CANCELLED'}
