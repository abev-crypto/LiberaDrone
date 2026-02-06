from __future__ import annotations

import bpy

from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.formation import fn_parse_pairing


_NAMED_ATTR_CACHE: dict[tuple[str, int, str], list[float]] = {}


def _cache_key(name: str) -> tuple[str, int, str]:
    scene = bpy.context.scene
    frame = le_meshinfo._LED_FRAME_CACHE.get("frame")
    if frame is None:
        frame = int(getattr(scene, "frame_current", 0)) if scene else 0
    return (scene.name if scene else "", int(frame), str(name))


def _build_named_attr_cache(name: str) -> list[float]:
    col = bpy.data.collections.get("Formation")
    if col is None:
        return []
    meshes = fn_parse_pairing._collect_mesh_objects(col)
    if not meshes:
        return []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    values: list[float] = []
    for obj in meshes:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            attr = eval_mesh.attributes.get(name)
            if (
                attr is None
                or attr.data_type != 'FLOAT'
                or attr.domain != 'POINT'
                or len(attr.data) != len(eval_mesh.vertices)
            ):
                attr = obj.data.attributes.get(name)
            if (
                attr is None
                or attr.data_type != 'FLOAT'
                or attr.domain != 'POINT'
                or len(attr.data) != len(eval_mesh.vertices)
            ):
                raise ValueError(f"Named attribute not found: {name}")
            vals = [0.0] * len(eval_mesh.vertices)
            attr.data.foreach_get("value", vals)
            values.extend(float(v) for v in vals)
        finally:
            eval_obj.to_mesh_clear()
    return values


def _get_named_attr_cache(name: str) -> list[float]:
    key = _cache_key(name)
    cached = _NAMED_ATTR_CACHE.get(key)
    if cached is not None:
        return cached
    values = _build_named_attr_cache(str(name))
    _NAMED_ATTR_CACHE[key] = values
    return values


@register_runtime_function
def _named_attr_cache(name: str) -> None:
    _get_named_attr_cache(str(name))


@register_runtime_function
def _named_attr_value(name: str, idx: int) -> float:
    values = _get_named_attr_cache(str(name))
    if not values:
        return 0.0
    idx_val = int(idx)
    src_idx = idx_val
    pair_ids = le_meshinfo._LED_FRAME_CACHE.get("pair_ids")
    if pair_ids and len(pair_ids) == len(values):
        inv = le_meshinfo._LED_FRAME_CACHE.get("pair_id_inv_map")
        if inv is None:
            inv = {}
            for src_idx_local, pid in enumerate(pair_ids):
                key = int(pid)
                if key in inv:
                    continue
                inv[key] = src_idx_local
            le_meshinfo._LED_FRAME_CACHE["pair_id_inv_map"] = inv
        src_idx = inv.get(idx_val, idx_val)
    if 0 <= src_idx < len(values):
        return float(values[src_idx])
    return 0.0
