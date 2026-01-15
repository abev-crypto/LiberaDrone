import bpy

from liberadronecore.formation.fn_nodecategory import FN_Register
from liberadronecore.ui import fn_parse_ui


class FN_OT_add_frame(bpy.types.Operator, FN_Register):
    bl_idname = "fn.add_frame"
    bl_label = "Frame"
    bl_description = "Wrap selected Formation nodes in a frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        tree = fn_parse_ui._get_formation_tree(context)
        if tree is None:
            self.report({'ERROR'}, "Formation tree not available")
            return {'CANCELLED'}
        selected = [n for n in tree.nodes if n.select]
        frame = tree.nodes.new("NodeFrame")
        frame.label = "Frame"
        frame.shrink = True
        if selected:
            xs = [float(n.location.x) for n in selected if hasattr(n, "location")]
            ys = [float(n.location.y) for n in selected if hasattr(n, "location")]
            if xs and ys:
                frame.location = (min(xs) - 60.0, max(ys) + 60.0)
            for node in selected:
                if node == frame:
                    continue
                node.parent = frame
        else:
            frame.location = fn_parse_ui._node_editor_cursor(context)
        for node in tree.nodes:
            node.select = False
        frame.select = True
        tree.nodes.active = frame
        return {'FINISHED'}
