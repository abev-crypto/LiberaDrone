import bpy
from liberadronecore.formation.fn_nodecategory import FN_Node


class FN_ShowNode(bpy.types.Node, FN_Node):
    bl_idname = "FN_ShowNode"
    bl_label = "Show"
    bl_icon = "ACTION"

    computed_start_frame: bpy.props.IntProperty(name="Computed Start", default=-1, options={'SKIP_SAVE'})
    collection_vertex_count: bpy.props.IntProperty(name="Collection Vertices", default=-1, options={'SKIP_SAVE'})

    def init(self, context):
        self.inputs.new("FN_SocketFlow", "In")
        self.inputs.new("FN_SocketCollection", "Collection")
        duration = self.inputs.new("FN_SocketFloat", "Duration")
        duration.value = 480.0
        self.outputs.new("FN_SocketFlow", "Next")

    def draw_buttons(self, context, layout):
        if self.collection_vertex_count >= 0:
            layout.label(text=f"Verts: {self.collection_vertex_count}")
        if self.computed_start_frame >= 0:
            row = layout.row()
            row.alignment = 'RIGHT'
            row.label(text=f"start:{self.computed_start_frame}f")
