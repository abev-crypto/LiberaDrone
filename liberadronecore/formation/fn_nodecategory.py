from liberadronecore.formation.fn_nodetree import FN_FormationTree
from liberadronecore.formation.fn_soket import FN_SocketBool, FN_SocketFlow
from liberadronecore.formation.nodes.fn_split import FN_SplitNode
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

class FN_NodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space is not None) and (getattr(space, "tree_type", None) == "FN_FormationTree")


FN_NODE_CATEGORIES = [
    FN_NodeCategory("FN_STORYBOARD_NODES", "FN Storyboard", items=[
        NodeItem("FN_StartNode"),
        NodeItem("FN_ActionNode"),
        NodeItem("FN_WaitNode"),
        NodeItem("FN_BranchNode"),
        NodeItem("FN_MergeNode"),
    ]),
]


classes = (
    FN_FormationTree,
    FN_SocketFlow,
    FN_SocketBool,
    FN_StartNode,
    FN_ActionNode,
    FN_WaitNode,
    FN_SplitNode,
    FN_MergeNode,
)