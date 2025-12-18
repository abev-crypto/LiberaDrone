import bpy
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty, IntProperty
from liberadronecore.formation.fn_nodecategory import FN_Register

class FN_SocketFlow(bpy.types.NodeSocket, FN_Register):
    bl_idname = "FN_SocketFlow"
    bl_label  = "Flow"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.1, 1.0)  # オレンジ系

class FN_SocketBool(bpy.types.NodeSocket, FN_Register):
    """Boolean socket (for conditions)"""
    bl_idname = "FN_SocketBool"
    bl_label = "Bool"

    value: BoolProperty(name="Value", default=False)

    def draw(self, context, layout, node, text):
        layout.prop(self, "value", text=text if text else self.name)

    def draw_color(self, context, node):
        return (0.2, 0.8, 0.2, 1.0)
    
class FN_SocketFloat(bpy.types.NodeSocket, FN_Register):
    """Boolean socket (for conditions)"""
    bl_idname = "FN_SocketFloat"
    bl_label = "Float"

    value: FloatProperty(name="Value", default=0.0)

    def draw(self, context, layout, node, text):
        layout.prop(self, "value", text=text if text else self.name)

    def draw_color(self, context, node):
        return (0.2, 0.8, 0.2, 1.0)
    
class FN_SocketInt(bpy.types.NodeSocket, FN_Register):
    """Boolean socket (for conditions)"""
    bl_idname = "FN_SocketInt"
    bl_label = "Int"

    value: IntProperty(name="Value", default=0)

    def draw(self, context, layout, node, text):
        layout.prop(self, "value", text=text if text else self.name)

    def draw_color(self, context, node):
        return (0.2, 0.8, 0.2, 1.0)