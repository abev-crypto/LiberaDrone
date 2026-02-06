from __future__ import annotations

from typing import Dict, List, Tuple

import bpy

from liberadronecore.ledeffects.runtime_registry import register_runtime_function


_VALUE_CACHE: Dict[str, Dict[str, object]] = {}


def clear_value_cache(key: str) -> None:
    _VALUE_CACHE.pop(str(key), None)


def set_value_cache_single(key: str, values: List[float]) -> None:
    _VALUE_CACHE[str(key)] = {
        "mode": "SINGLE",
        "values": [float(v) for v in values],
    }


def set_value_cache_entry(key: str, frames: List[List[float]], start: int, end: int) -> None:
    frame_size = max((len(frame) for frame in frames), default=0)
    flat: List[float] = []
    for frame in frames:
        if len(frame) < frame_size:
            frame = list(frame) + [0.0] * (frame_size - len(frame))
        flat.extend(float(v) for v in frame)
    _VALUE_CACHE[str(key)] = {
        "mode": "ENTRY",
        "values": flat,
        "frame_size": int(frame_size),
        "frame_count": int(len(frames)),
        "start": int(start),
        "end": int(end),
    }


@register_runtime_function
def _value_cache_has(key: str) -> bool:
    key = str(key)
    if key in _VALUE_CACHE:
        return True
    tree_name, node_name = _split_key(key)
    node = _find_node(tree_name, node_name)
    if node is None:
        return False
    return _load_from_node(key, node) is not None


@register_runtime_function
def _value_cache_read(key: str, fid: int) -> float:
    cache = _ensure_cache(str(key))
    if not cache or cache.get("mode") != "SINGLE":
        return 0.0
    values = cache.get("values")
    if not isinstance(values, list):
        return 0.0
    idx = int(fid)
    if idx < 0 or idx >= len(values):
        return 0.0
    return float(values[idx])


@register_runtime_function
def _value_cache_read_entry(key: str, fid: int, progress: float) -> float:
    cache = _ensure_cache(str(key))
    if not cache or cache.get("mode") != "ENTRY":
        return 0.0
    values = cache.get("values")
    frame_size = cache.get("frame_size")
    frame_count = cache.get("frame_count")
    if not isinstance(values, list):
        return 0.0
    if not isinstance(frame_size, int) or not isinstance(frame_count, int):
        return 0.0
    if frame_size <= 0 or frame_count <= 0:
        return 0.0
    if frame_count <= 1:
        frame_idx = 0
    else:
        t = float(progress)
        if t < 0.0:
            t = 0.0
        if t > 1.0:
            t = 1.0
        frame_idx = int(t * float(frame_count - 1))
    idx = int(fid)
    if idx < 0 or idx >= frame_size:
        return 0.0
    flat_idx = frame_idx * frame_size + idx
    if flat_idx < 0 or flat_idx >= len(values):
        return 0.0
    return float(values[flat_idx])


def _split_key(key: str) -> tuple[str, str]:
    key = str(key)
    if "::" not in key:
        return key, ""
    tree_name, node_name = key.split("::", 1)
    return tree_name, node_name


def _find_node(tree_name: str, node_name: str) -> bpy.types.Node | None:
    tree = bpy.data.node_groups.get(tree_name)
    if tree is None:
        return None
    return tree.nodes.get(node_name)


def _load_from_node(key: str, node: bpy.types.Node) -> Dict[str, object] | None:
    payload = node.get("ld_value_cache")
    if payload is None or not hasattr(payload, "get"):
        return None
    cache = {"mode": payload.get("mode")}
    if cache["mode"] == "SINGLE":
        values = payload.get("values")
        if values is None:
            return None
        cache["values"] = [float(v) for v in list(values)]
    elif cache["mode"] == "ENTRY":
        values = payload.get("values")
        frame_size = payload.get("frame_size")
        frame_count = payload.get("frame_count")
        if values is None:
            return None
        if not isinstance(frame_size, int) or not isinstance(frame_count, int):
            return None
        cache["values"] = [float(v) for v in list(values)]
        cache["frame_size"] = int(frame_size)
        cache["frame_count"] = int(frame_count)
        cache["start"] = int(payload.get("start", 0))
        cache["end"] = int(payload.get("end", 0))
    else:
        return None
    _VALUE_CACHE[str(key)] = cache
    return cache


def _ensure_cache(key: str) -> Dict[str, object] | None:
    cached = _VALUE_CACHE.get(str(key))
    if cached is not None:
        return cached
    tree_name, node_name = _split_key(str(key))
    node = _find_node(tree_name, node_name)
    if node is None:
        return None
    return _load_from_node(str(key), node)
