from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Type, Optional, TypeVar, Generic
import bpy
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories
from .base_reg import RegisterBase


T = TypeVar('T')


class Registry(RegisterBase, Generic[T]):
    nc : Optional[Type[T]] = None
    classes: List[Type] = []
    _class_set = set()

    # cat_id -> [node_bl_idname...]
    node_items: Dict[str, List[str]] = defaultdict(list)
    node_labels: Dict[str, str] = {}

    # register_node_categories に渡す “ルートID”
    node_root_id: str = "FN_NODE_CATEGORIES"
    _built_categories: List[T] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Ensure per-registry storage to avoid cross-registry duplicates.
        cls.classes = []
        cls._class_set = set()
        cls.node_items = defaultdict(list)
        cls.node_labels = {}
        cls._built_categories = []

    @classmethod
    def add_class(cls, c: Type):
        if not issubclass(c, bpy.types.bpy_struct):
            return
        if c in cls._class_set:
            return
        cls._class_set.add(c)
        cls.classes.append(c)

    @classmethod
    def add_node(cls, node_bl_idname: str, catid: str, label: str, order: int = 0):
        cls.node_labels[catid] = label
        # order で並び制御したいなら (order, idname) のタプルで保持して後でソートしてもOK
        if node_bl_idname not in cls.node_items[catid]:
            cls.node_items[catid].append(node_bl_idname)

    @classmethod
    def build_node_categories(cls) -> List[T]:
        cats: List[T] = []
        ncat = getattr(cls, "nc", None)
        for cat_id, items in cls.node_items.items():
            label = cls.node_labels.get(cat_id, cat_id)
            cats.append(ncat(cat_id, label, items=[NodeItem(x) for x in items]))
        # 必要ならカテゴリ順制御
        cats.sort(key=lambda c: c.identifier)
        return cats

    @classmethod
    def register(cls):
        # class register
        for c in cls.classes:
            bpy.utils.register_class(c)

        # node categories register
        cls._built_categories = cls.build_node_categories()
        if cls._built_categories:
            register_node_categories(cls.node_root_id, cls._built_categories)

    @classmethod
    def unregister(cls):
        if cls._built_categories:
            unregister_node_categories(cls.node_root_id)

        # class unregister
        for c in reversed(cls.classes):
            bpy.utils.unregister_class(c)


class AutoRegister(Generic[T]):
    """継承した瞬間に、Blender登録対象に積む"""
    registry : Optional[Type[T]] = None
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        reg = getattr(cls, "registry", None)
        reg.add_class(cls)


class AutoNode(Generic[T]):
    """Node 継承した瞬間に NodeItem も積む（カテゴリ指定がある場合）"""
    NODE_CATEGORY_ID: Optional[str] = None
    NODE_CATEGORY_LABEL: str = ""
    registry : Optional[Type[T]] = None
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        reg = getattr(cls, "registry", None)
        reg.add_class(cls)
        cat_id = getattr(cls, "NODE_CATEGORY_ID", None)

        bl_idname = getattr(cls, "bl_idname", None)

        label = getattr(cls, "NODE_CATEGORY_LABEL", "") or cat_id
        if cat_id and bl_idname:
            reg.add_node(bl_idname, cat_id, label)
