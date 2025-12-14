bl_info = {
    "name": "LiberaDrone LED Effects",
    "author": "LiberaDrone",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "Node Editor > Add menu",
    "description": "Prototype LED effects node tree with a sample node",
    "category": "Node",
}

import bpy
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

from .le_nodetree import LD_LedEffectsTree
from .nodes.le_value import LDLEDValueNode

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


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_node_categories("LD_LED_EFFECTS_NODES", node_categories)


def unregister():
    unregister_node_categories("LD_LED_EFFECTS_NODES")
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

