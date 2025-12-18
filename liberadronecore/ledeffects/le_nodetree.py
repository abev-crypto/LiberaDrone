import bpy
from liberadronecore.ledeffects.le_nodecategory import LDLED_Register


class LD_LedEffectsTree(bpy.types.NodeTree, LDLED_Register):
    """Node tree to host LED effect nodes."""

    bl_idname = "LD_LedEffectsTree"
    bl_label = "LD LED Effects"
    bl_icon = 'LIGHT'
    bl_use_link_search = True

    @classmethod
    def poll(cls, context):
        return True
