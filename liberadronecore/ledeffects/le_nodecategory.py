from liberadronecore.reg.autoreg import AutoNode, AutoRegister, Registry
from nodeitems_utils import NodeCategory


class LDLED_NodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space is not None) and (getattr(space, "tree_type", None) == "LD_LedEffectsTree")


class LDLED_RegisterBase(Registry[LDLED_NodeCategory]):
    node_root_id = "LD_LED_NODE_CATEGORIES"
    nc = LDLED_NodeCategory


class LDLED_Register(AutoRegister[LDLED_RegisterBase]):
    registry = LDLED_RegisterBase


class LDLED_Node(AutoNode[LDLED_RegisterBase]):
    registry = LDLED_RegisterBase
    NODE_CATEGORY_ID: str = "LD_LED_NODES"
    NODE_CATEGORY_LABEL: str = "LD LED Effects"
