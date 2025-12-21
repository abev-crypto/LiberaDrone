import bpy
from bpy.types import NodeTree, Node, NodeSocket, Operator, Panel
from bpy.props import IntProperty, EnumProperty, StringProperty
from liberadronecore.formation.fn_nodecategory import FN_Node, FN_Register
from liberadronecore.formation.nodes.transition.fn_transitionbase import FN_TransitionBase

class FN_MergeTransitionNode(Node, FN_Node, FN_TransitionBase):
    bl_idname = "FN_MergeTransitionNode"
    bl_label = "Merge Transition"
    bl_icon = "DECORATE_KEYFRAME"

    computed_start_frame: IntProperty(name="Computed Start", default=-1, options={'SKIP_SAVE'})

    def init(self, context):
        duration = self.inputs.new("FN_SocketFloat", "Duration")
        duration.value = 1.0
        num = self.inputs.new("FN_SocketInt", "Num")
        num.value = 2
        self.outputs.new("FN_SocketFlow", "Out")
        self._update_flow_inputs()

    def _get_num_value(self) -> int:
        sock = self.inputs.get("Num")
        if sock and hasattr(sock, "value"):
            return int(sock.value)
        return 1

    def _update_flow_inputs(self):
        desired = max(1, self._get_num_value())
        flow_inputs = [s for s in self.inputs if s.bl_idname == "FN_SocketFlow"]
        while len(flow_inputs) > desired:
            sock = flow_inputs.pop()
            self.inputs.remove(sock)
        for idx in range(len(flow_inputs), desired):
            self.inputs.new("FN_SocketFlow", str(idx + 1))

    def update(self):
        self._update_flow_inputs()
