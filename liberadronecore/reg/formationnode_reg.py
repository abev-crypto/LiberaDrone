from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories
import liberadronecore.formation.fn_nodecategory as fn_nodecategory
from .base_reg import RegisterBase 
import bpy


class OverlayRegister(RegisterBase):
    """Register/unregister overlay related Blender classes."""

    @classmethod
    def register(cls) -> None:
        for c in fn_nodecategory.classes:
            bpy.utils.register_class(c)
        register_node_categories("FN_FORMATION_CATEGORIES", fn_nodecategory.FN_NODE_CATEGORIES)

    @classmethod
    def unregister(cls) -> None:
        unregister_node_categories("FN_FORMATION_CATEGORIES")
        for c in reversed(fn_nodecategory.classes):
            bpy.utils.unregister_class(c)
