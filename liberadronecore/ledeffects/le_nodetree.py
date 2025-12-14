import bpy


class LD_LedEffectsTree(bpy.types.NodeTree):
    """Node tree to host LED effect nodes."""

    bl_idname = "LD_LedEffectsTree"
    bl_label = "LD LED Effects"
    bl_icon = 'LIGHT'

    @classmethod
    def poll(cls, context):
        return True
