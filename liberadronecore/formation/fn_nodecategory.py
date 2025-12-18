from liberadronecore.reg.autoreg import AutoNode, AutoRegister, Registry
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

class FN_NodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space is not None) and (getattr(space, "tree_type", None) == "FN_FormationTree")

class FN_RegisterBase(Registry[FN_NodeCategory]):
    nc = FN_NodeCategory

class FN_Register(AutoRegister[FN_RegisterBase]):
    registry = FN_RegisterBase

class FN_Node(AutoNode[FN_RegisterBase]):
    registry = FN_RegisterBase
    NODE_CATEGORY_ID: str = "FN_STORYBOARD_NODES"
    NODE_CATEGORY_LABEL: str = "FN Storyboard"
