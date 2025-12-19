import bpy
from bpy.props import FloatProperty, BoolProperty, IntProperty, PointerProperty
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
        label = text if text else self.name
        if self.is_output or self.is_linked:
            layout.label(text=label)
        else:
            layout.prop(self, "value", text=label)

    def draw_color(self, context, node):
        return (0.2, 0.8, 0.2, 1.0)

class FN_SocketCollection(bpy.types.NodeSocket, FN_Register):
    """Collection socket"""
    bl_idname = "FN_SocketCollection"
    bl_label = "Collection"

    collection: PointerProperty(type=bpy.types.Collection)

    def draw(self, context, layout, node, text):
        label = text if text else self.name
        if self.is_output or self.is_linked:
            layout.label(text=label)
        else:
            layout.prop(self, "collection", text=label)

    def draw_color(self, context, node):
        return (0.4, 0.6, 1.0, 1.0)
    
class FN_SocketFloat(bpy.types.NodeSocket, FN_Register):
    """Boolean socket (for conditions)"""
    bl_idname = "FN_SocketFloat"
    bl_label = "Float"

    value: FloatProperty(name="Value", default=0.0)

    def draw(self, context, layout, node, text):
        label = text if text else self.name
        if self.is_output or self.is_linked:
            layout.label(text=label)
        else:
            layout.prop(self, "value", text=label)

    def draw_color(self, context, node):
        return (0.2, 0.8, 0.2, 1.0)
    
class FN_SocketInt(bpy.types.NodeSocket, FN_Register):
    """Boolean socket (for conditions)"""
    bl_idname = "FN_SocketInt"
    bl_label = "Int"

    value: IntProperty(name="Value", default=0)

    def draw(self, context, layout, node, text):
        label = text if text else self.name
        if self.is_output or self.is_linked:
            layout.label(text=label)
        else:
            layout.prop(self, "value", text=label)

    def draw_color(self, context, node):
        return (0.2, 0.8, 0.2, 1.0)
