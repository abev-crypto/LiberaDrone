import bpy
from liberadronecore.ledeffects.le_nodecategory import LDLED_Register


class LDLEDEntrySocket(bpy.types.NodeSocket, LDLED_Register):
    bl_idname = "LDLEDEntrySocket"
    bl_label = "LED Entry"

    def draw(self, context, layout, node, text):
        layout.label(text=text if text else self.name)

    def draw_color(self, context, node):
        return (0.85, 0.35, 0.15, 1.0)


class LDLEDIDSocket(bpy.types.NodeSocket, LDLED_Register):
    bl_idname = "LDLEDIDSocket"
    bl_label = "ID List"

    def draw(self, context, layout, node, text):
        layout.label(text=text if text else self.name)

    def draw_color(self, context, node):
        return (0.25, 0.65, 0.9, 1.0)
