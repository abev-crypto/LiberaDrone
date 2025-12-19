import bpy
from bpy.types import NodeTree, Node, NodeSocket, Operator, Panel
from bpy.props import IntProperty, EnumProperty, StringProperty
from liberadronecore.formation.fn_nodecategory import FN_Node, FN_Register


class FN_OT_apply_split_mode(bpy.types.Operator, FN_Register):
    bl_idname = "fn.apply_split_mode"
    bl_label = "Apply Split Mode"
    node_name: StringProperty()

    def execute(self, context):
        tree = context.space_data.edit_tree if context.space_data else None
        if not tree:
            return {'CANCELLED'}
        node = tree.nodes.get(self.node_name) if self.node_name else context.active_node
        if node:
            self.report({'INFO'}, f"Applied mode {getattr(node, 'mode', '')} for {node.name}")
        return {'FINISHED'}


class FN_SplitTransitionNode(Node, FN_Node):
    bl_idname = "FN_SplitTransitionNode"
    bl_label = "Split Transition"
    bl_icon = "DECORATE_KEYFRAME"

    mode: EnumProperty(
        name="Mode",
        items=[
            ("DEFAULT", "Default", "Default split behavior"),
            ("RANDOM", "Random", "Randomize split routes"),
            ("SEQUENTIAL", "Sequential", "Sequential assignment"),
        ],
        default="DEFAULT",
    )
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
            try:
                return int(sock.value)
            except Exception:
                return 1
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

    def draw_buttons(self, context, layout):
        if self.computed_start_frame >= 0:
            row = layout.row()
            row.alignment = 'RIGHT'
            row.label(text=f"start:{self.computed_start_frame}f")
        layout.prop(self, "mode")
        op = layout.operator("fn.apply_split_mode", text="Apply Mode")
        op.node_name = self.name
