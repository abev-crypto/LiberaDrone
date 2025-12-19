import bpy
from liberadronecore.formation.fn_nodecategory import FN_Node

class FN_CollectionNode(bpy.types.Node, FN_Node):
    bl_idname = "FN_CollectionNode"
    bl_label  = "Collection"
    bl_icon = "ACTION"

    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        description="Target collection",
    )
    collection_vertex_count: bpy.props.IntProperty(name="Collection Vertices", default=-1, options={'SKIP_SAVE'})

    def init(self, context):
        self.outputs.new("FN_SocketCollection", "Collection")

    def draw_buttons(self, context, layout):
        layout.prop(self, "collection")
        if self.collection_vertex_count >= 0:
            layout.label(text=f"Verts: {self.collection_vertex_count}")
