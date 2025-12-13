class LD_SocketFlow(bpy.types.NodeSocket):
    bl_idname = "LD_SocketFlow"
    bl_label  = "Flow"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.1, 1.0)  # オレンジ系
