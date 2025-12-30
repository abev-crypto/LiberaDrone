import bpy
from bpy.types import Node
from bpy.props import IntProperty
from liberadronecore.formation.fn_nodecategory import FN_Node
from liberadronecore.formation.nodes.transition.fn_transitionbase import FN_TransitionBase


class FN_TransitionNode(Node, FN_Node, FN_TransitionBase):
    bl_idname = "FN_TransitionNode"
    bl_label = "Transition"
    bl_icon = "DECORATE_KEYFRAME"

    computed_start_frame: IntProperty(name="Computed Start", default=-1, options={'SKIP_SAVE'})

    def init(self, context):
        self.inputs.new("FN_SocketFlow", "In")
        duration = self.inputs.new("FN_SocketFloat", "Duration")
        duration.value = 480.0
        self.outputs.new("FN_SocketFlow", "Out")
