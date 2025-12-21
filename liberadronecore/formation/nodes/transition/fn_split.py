import bpy
from bpy.types import NodeTree, Node, NodeSocket, Operator, Panel
from bpy.props import IntProperty, EnumProperty, StringProperty
from liberadronecore.formation.fn_nodecategory import FN_Node, FN_Register
from liberadronecore.formation.nodes.transition.fn_transitionbase import FN_TransitionBase


class FN_SplitTransitionNode(Node, FN_Node, FN_TransitionBase):
    bl_idname = "FN_SplitTransitionNode"
    bl_label = "Split Transition"
    bl_icon = "DECORATE_KEYFRAME"
    
    computed_start_frame: IntProperty(name="Computed Start", default=-1, options={'SKIP_SAVE'})

    def init(self, context):
        self.inputs.new("FN_SocketFlow", "In")
        num = self.inputs.new("FN_SocketInt", "Num")
        num.value = 2
        duration = self.inputs.new("FN_SocketFloat", "Duration")
        duration.value = 1.0
        self._update_dynamic_sockets()

    def _get_num_value(self) -> int:
        sock = self.inputs.get("Num")
        if sock and hasattr(sock, "value"):
            return int(sock.value)
        return 1

    def _update_dynamic_sockets(self):
        desired_out = max(1, self._get_num_value())
        flow_outputs = [s for s in self.outputs if s.bl_idname == "FN_SocketFlow"]
        while len(flow_outputs) > desired_out:
            sock = flow_outputs.pop()
            self.outputs.remove(sock)
        for idx in range(len(flow_outputs), desired_out):
            self.outputs.new("FN_SocketFlow", str(idx + 1))

    def update(self):
        self._update_dynamic_sockets()
