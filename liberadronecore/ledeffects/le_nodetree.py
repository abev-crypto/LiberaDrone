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

    def update(self):
        try:
            from liberadronecore.tasks import ledeffects_task
        except Exception:
            return
        scene = getattr(bpy.context, "scene", None)
        if scene is None:
            return
        scheduler = getattr(ledeffects_task, "schedule_led_effects_update", None)
        if scheduler is None:
            ledeffects_task.update_led_effects(scene)
        else:
            scheduler(scene)
