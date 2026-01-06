from liberadronecore.reg.autoreg import AutoNode, AutoRegister, Registry
from nodeitems_utils import NodeCategory, NodeItemCustom


def _led_layout_tools_draw(_self, layout, _context):
    layout.operator("ldled.add_frame", text="Frame")
    layout.operator("ldled.add_reroute", text="Reroute")
    layout.operator("ldled.group_selected", text="Group")
    layout.separator()


class LDLED_NodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space is not None) and (getattr(space, "tree_type", None) == "LD_LedEffectsTree")


class LDLED_RegisterBase(Registry[LDLED_NodeCategory]):
    node_root_id = "LD_LED_NODE_CATEGORIES"
    nc = LDLED_NodeCategory

    @classmethod
    def build_node_categories(cls) -> list[LDLED_NodeCategory]:
        cats = super().build_node_categories()
        layout_items = [NodeItemCustom(draw=_led_layout_tools_draw)]
        cats.append(LDLED_NodeCategory("LD_LED_LAYOUT", "Layout", items=layout_items))
        cats.sort(key=lambda c: c.identifier)
        return cats


class LDLED_Register(AutoRegister[LDLED_RegisterBase]):
    registry = LDLED_RegisterBase


class LDLED_Node(AutoNode[LDLED_RegisterBase]):
    registry = LDLED_RegisterBase
    NODE_CATEGORY_ID: str = "LD_LED_NODES"
    NODE_CATEGORY_LABEL: str = "LD LED Effects"

    def __init_subclass__(cls, **kwargs):
        if getattr(cls, "NODE_CATEGORY_ID", None) in (None, "LD_LED_NODES"):
            module = getattr(cls, "__module__", "")
            if ".nodes.effect" in module:
                cls.NODE_CATEGORY_ID = "LD_LED_EFFECT"
                cls.NODE_CATEGORY_LABEL = "Effect"
            elif ".nodes.entry" in module:
                cls.NODE_CATEGORY_ID = "LD_LED_ENTRY"
                cls.NODE_CATEGORY_LABEL = "Entry"
            elif ".nodes.mask" in module:
                cls.NODE_CATEGORY_ID = "LD_LED_MASK"
                cls.NODE_CATEGORY_LABEL = "Mask"
            elif ".nodes.position" in module:
                cls.NODE_CATEGORY_ID = "LD_LED_POSITION"
                cls.NODE_CATEGORY_LABEL = "Position"
            elif ".nodes.sampler" in module:
                cls.NODE_CATEGORY_ID = "LD_LED_SAMPLER"
                cls.NODE_CATEGORY_LABEL = "Sampler"
            elif ".nodes.util" in module:
                cls.NODE_CATEGORY_ID = "LD_LED_UTIL"
                cls.NODE_CATEGORY_LABEL = "Utility"
            elif module.endswith(".nodes.le_output"):
                cls.NODE_CATEGORY_ID = "LD_LED_OUTPUT"
                cls.NODE_CATEGORY_LABEL = "Output"
        super().__init_subclass__(**kwargs)
