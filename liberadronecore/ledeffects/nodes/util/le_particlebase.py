from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import bpy

from liberadronecore.ledeffects.nodes.util import le_meshinfo


def _particle_fps() -> float:
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return 24.0
    fps = float(getattr(scene.render, "fps", 24.0))
    base = float(getattr(scene.render, "fps_base", 1.0) or 1.0)
    if fps <= 0.0:
        fps = 24.0
    if base <= 0.0:
        base = 1.0
    return fps / base


def _formation_id_map() -> Dict[int, int]:
    cache = le_meshinfo._LED_FRAME_CACHE
    cached = cache.get("formation_id_map")
    if isinstance(cached, dict):
        return cached
    mapping: Dict[int, int] = {}
    ids = cache.get("formation_ids")
    if ids is None:
        ids = []
    pair_ids = cache.get("pair_ids")
    positions = cache.get("positions") or []
    use_pair_ids = False
    if pair_ids is not None and len(pair_ids) == len(positions):
        seen = set()
        use_pair_ids = True
        for pid in pair_ids:
            try:
                key = int(pid)
            except (TypeError, ValueError):
                use_pair_ids = False
                break
            if key < 0 or key >= len(positions) or key in seen:
                use_pair_ids = False
                break
            seen.add(key)
    for src_idx, fid in enumerate(ids):
        try:
            key = int(fid)
        except (TypeError, ValueError):
            continue
        if key in mapping:
            continue
        runtime_idx = src_idx
        if use_pair_ids and src_idx < len(pair_ids):
            try:
                runtime_idx = int(pair_ids[src_idx])
            except (TypeError, ValueError):
                runtime_idx = src_idx
        mapping[key] = runtime_idx
    cache["formation_id_map"] = mapping
    return mapping


def _resolve_runtime_index(value, count: int, mapping: Dict[int, int]) -> Optional[int]:
    idx = None
    if mapping:
        try:
            key = int(value)
        except (TypeError, ValueError):
            key = None
        if key is not None:
            idx = mapping.get(key)
            if idx is not None and (idx < 0 or idx >= count):
                idx = None
    if idx is None:
        try:
            idx = int(value)
        except (TypeError, ValueError):
            return None
    try:
        idx = int(idx)
    except (TypeError, ValueError):
        return None
    if 0 <= idx < count:
        return idx
    return None


def _map_allowed_indices(
    allowed_ids: Sequence[int],
    count: int,
    mapping: Dict[int, int],
) -> List[int]:
    allowed_set: set[int] = set()
    allowed_list: List[int] = []
    for value in allowed_ids:
        idx = _resolve_runtime_index(value, count, mapping)
        if idx is None or idx in allowed_set:
            continue
        allowed_set.add(idx)
        allowed_list.append(idx)
    return allowed_list


def _mask_key(mask_mesh) -> str:
    if isinstance(mask_mesh, str):
        return mask_mesh
    mask_obj = le_meshinfo._get_object(mask_mesh)
    if mask_obj is not None:
        return mask_obj.name
    return ""


def _resolve_mask_context(
    state: Dict[str, object],
    mask_mesh,
    count: int,
    mapping: Dict[int, int],
    *,
    mask_key: Optional[str] = None,
) -> Tuple[bool, str, List[int], Optional[set[int]]]:
    if mask_key is None:
        mask_key = _mask_key(mask_mesh)
    mask_obj = le_meshinfo._get_object(mask_mesh)
    mask_enabled = mask_obj is not None and mask_obj.type == 'MESH'
    if not mask_enabled:
        return False, mask_key, list(range(count)), None

    mask_sig = (mask_obj.name, len(mask_obj.data.vertices))
    cached_sig = state.get("mask_sig")
    cached_ids = state.get("mask_ids")
    if cached_sig == mask_sig and isinstance(cached_ids, list):
        mask_ids = cached_ids
    else:
        values = le_meshinfo._mesh_formation_ids(mask_obj.data)
        seen: set[int] = set()
        unique: List[int] = []
        for value in values:
            try:
                val = int(value)
            except (TypeError, ValueError):
                continue
            if val in seen:
                continue
            seen.add(val)
            unique.append(val)
        mask_ids = unique
        state["mask_sig"] = mask_sig
        state["mask_ids"] = unique

    allowed_indices = _map_allowed_indices(mask_ids, count, mapping)
    allowed_set = set(allowed_indices) if allowed_indices else set()
    return True, mask_key, allowed_indices, allowed_set


def _neighbor_map(
    state: Dict[str, object],
    positions: List[Tuple[float, float, float]],
    allowed_indices: Sequence[int],
    neighbor_count: int,
    *,
    frame: Optional[int] = None,
) -> List[List[int]]:
    sig = (int(frame) if frame is not None else None, state.get("route_sig"), int(neighbor_count))
    cached_sig = state.get("neighbor_sig")
    cached = state.get("neighbor_map")
    if cached_sig == sig and isinstance(cached, list):
        return cached
    count = len(positions)
    neighbors: List[List[int]] = [[] for _ in range(count)]
    allowed = [idx for idx in allowed_indices if 0 <= idx < count]
    if allowed:
        for idx in allowed:
            cx, cy, cz = positions[idx]
            dists: List[Tuple[float, int]] = []
            for other in allowed:
                if other == idx:
                    continue
                px, py, pz = positions[other]
                dx = px - cx
                dy = py - cy
                dz = pz - cz
                dists.append((dx * dx + dy * dy + dz * dz, other))
            if dists:
                dists.sort(key=lambda item: item[0])
                neighbors[idx] = [item[1] for item in dists[: min(neighbor_count, len(dists))]]
    state["neighbor_sig"] = sig
    state["neighbor_map"] = neighbors
    return neighbors
