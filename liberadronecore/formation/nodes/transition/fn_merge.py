import bpy
from bpy.types import NodeTree, Node, NodeSocket, Operator, Panel
from bpy.props import IntProperty, EnumProperty, StringProperty
from liberadronecore.formation.fn_nodecategory import FN_Node, FN_Register

class FN_OT_apply_merge_mode(bpy.types.Operator, FN_Register):
    bl_idname = "fn.apply_merge_mode"
    bl_label = "Apply Merge Mode"
    node_name: StringProperty()

    def execute(self, context):
        tree = context.space_data.edit_tree if context.space_data else None
        if not tree:
            return {'CANCELLED'}
        node = tree.nodes.get(self.node_name) if self.node_name else context.active_node
        if node:
            self.report({'INFO'}, f"Applied mode {getattr(node, 'mode', '')} for {node.name}")
        return {'FINISHED'}


class FN_MergeTransitionNode(Node, FN_Node):
    bl_idname = "FN_MergeTransitionNode"
    bl_label = "Merge Transition"
    bl_icon = "DECORATE_KEYFRAME"

    mode: EnumProperty(
        name="Mode",
        items=[
            ("DEFAULT", "Default", "Default merge behavior"),
            ("PRIORITY", "Priority", "Priority-based merge"),
            ("ROUNDROBIN", "Round Robin", "Round robin merge"),
        ],
        default="DEFAULT",
    )
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
            try:
                return int(sock.value)
            except Exception:
                return 1
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

    def draw_buttons(self, context, layout):
        if self.computed_start_frame >= 0:
            row = layout.row()
            row.alignment = 'RIGHT'
            row.label(text=f"start:{self.computed_start_frame}f")
        layout.prop(self, "mode")
        op = layout.operator("fn.apply_merge_mode", text="Apply Mode")
        op.node_name = self.name
