import bpy
from liberadronecore.ledeffects.le_nodecategory import LDLED_Register


class LDLEDEntrySocket(bpy.types.NodeSocket, LDLED_Register):
    bl_idname = "LDLEDEntrySocket"
    bl_label = "LED Entry"

    def draw(self, context, layout, node, text):
        layout.label(text=text if text else self.name)

    def draw_color(self, context, node):
        return (0.85, 0.35, 0.15, 1.0)
