from .base_reg import RegisterBase

import bpy
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

from ledeffects.le_nodetree import LD_LedEffectsTree
from ledeffects.nodes.le_value import LDLEDValueNode


classes = (
    LD_LedEffectsTree,
    LDLEDValueNode,
)


def _is_led_tree(context):
    tree_type = getattr(getattr(context, "space_data", None), "tree_type", "")
    return tree_type == LD_LedEffectsTree.bl_idname


node_categories = [
    NodeCategory(
        identifier="LD_LED_EFFECTS",
        name="LD LED Effects",
        items=[NodeItem(LDLEDValueNode.bl_idname)],
        poll=_is_led_tree,
    ),
]

class LedEffectsRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        for cls in classes:
            bpy.utils.register_class(cls)
        register_node_categories("LD_LED_EFFECTS_NODES", node_categories)

    @classmethod
    def unregister(cls) -> None:
        unregister_node_categories("LD_LED_EFFECTS_NODES")
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)