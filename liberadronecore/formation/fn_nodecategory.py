from liberadronecore.reg.autoreg import AutoNode, AutoRegister, Registry
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom, register_node_categories, unregister_node_categories


def _formation_layout_tools_draw(_self, layout, _context):
    layout.operator("fn.add_frame", text="Frame")
    layout.separator()

class FN_NodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space is not None) and (getattr(space, "tree_type", None) == "FN_FormationTree")

class FN_RegisterBase(Registry[FN_NodeCategory]):
    nc = FN_NodeCategory

    @classmethod
    def build_node_categories(cls) -> list[FN_NodeCategory]:
        cats = super().build_node_categories()
        layout_items = [NodeItemCustom(draw=_formation_layout_tools_draw)]
        cats.append(FN_NodeCategory("FN_LAYOUT", "Layout", items=layout_items))
        cats.sort(key=lambda c: c.identifier)
        return cats

class FN_Register(AutoRegister[FN_RegisterBase]):
    registry = FN_RegisterBase

class FN_Node(AutoNode[FN_RegisterBase]):
    registry = FN_RegisterBase
    NODE_CATEGORY_ID: str = "FN_STORYBOARD_NODES"
    NODE_CATEGORY_LABEL: str = "FN Storyboard"
