from .base_reg import RegisterBase

import bpy
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

from liberadronecore.ledeffects.le_nodetree import LD_LedEffectsTree
from liberadronecore.ledeffects.nodes.le_blend import LDLEDBlendNode
from liberadronecore.ledeffects.nodes.le_catcache import LDLEDCatCacheNode
from liberadronecore.ledeffects.nodes.le_collectioninfo import LDLEDCollectionInfoNode
from liberadronecore.ledeffects.nodes.le_effect import LDLEDEffectNode
from liberadronecore.ledeffects.nodes.le_math import LDLEDMathNode
from liberadronecore.ledeffects.nodes.le_meshinfo import LDLEDMeshInfoNode
from liberadronecore.ledeffects.nodes.le_output import LDLEDOutputNode
from liberadronecore.ledeffects.nodes.le_value import LDLEDValueNode


classes = (
    LD_LedEffectsTree,
    LDLEDValueNode,
    LDLEDOutputNode,
    LDLEDBlendNode,
    LDLEDMathNode,
    LDLEDEffectNode,
    LDLEDCatCacheNode,
    LDLEDCollectionInfoNode,
    LDLEDMeshInfoNode,
)


def _is_led_tree(context):
    tree_type = getattr(getattr(context, "space_data", None), "tree_type", "")
    return tree_type == LD_LedEffectsTree.bl_idname


node_categories = [
    NodeCategory(
        identifier="LD_LED_EFFECTS",
        name="LD LED Effects",
        items=[
            NodeItem(LDLEDValueNode.bl_idname),
            NodeItem(LDLEDOutputNode.bl_idname),
            NodeItem(LDLEDBlendNode.bl_idname),
            NodeItem(LDLEDMathNode.bl_idname),
            NodeItem(LDLEDEffectNode.bl_idname),
            NodeItem(LDLEDCatCacheNode.bl_idname),
            NodeItem(LDLEDCollectionInfoNode.bl_idname),
            NodeItem(LDLEDMeshInfoNode.bl_idname),
        ],
        poll=_is_led_tree,
    ),
]


class LedEffectsRegister(RegisterBase):
    """Register/unregister LED effect related Blender classes."""

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
