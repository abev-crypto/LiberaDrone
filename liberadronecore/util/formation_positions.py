from __future__ import annotations

from typing import Optional, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Vector

from liberadronecore.system.transition import transition_apply
from liberadronecore.util import pair_id


def _pair_ids_hash(pair_ids: Optional[Sequence[int]]) -> int:
    if not pair_ids:
        return 0
    h = 1469598103934665603
    for pid in pair_ids:
        try:
            val = int(pid)
        except (TypeError, ValueError):
            val = 0
        h ^= val & 0xFFFFFFFFFFFFFFFF
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def _order_by_pair_ids(
    positions: Sequence,
    pair_ids: Optional[Sequence[int]],
):
    if not pair_ids or len(pair_ids) != len(positions):
        return positions, pair_ids, False

    indices, ok = pair_id.order_indices_by_pair_id(pair_ids)
    if not ok:
        return positions, pair_ids, False

    if isinstance(positions, np.ndarray):
        ordered_positions = positions[np.asarray(indices, dtype=np.int64)]
    else:
        ordered_positions = [positions[idx] for idx in indices]
    ordered_pair_ids = [pair_ids[idx] for idx in indices]
    return ordered_positions, ordered_pair_ids, True


def collect_formation_positions(
    scene: bpy.types.Scene,
    depsgraph: bpy.types.Depsgraph,
    *,
    collection_name: str = "Formation",
    sort_by_pair_id: bool = False,
    include_signature: bool = False,
    as_numpy: bool = False,
):
    col = bpy.data.collections.get(collection_name)
    if col is None:
        positions = np.empty((0, 3), dtype=np.float32) if as_numpy else []
        signature = None
        if include_signature:
            signature = (
                ("__scene__", scene.name if scene else ""),
                ("__vert_count__", 0),
                ("__pair_sort__", 0),
            )
        return positions, None, signature

    frame = int(getattr(scene, "frame_current", 0)) if scene else 0
    positions, pair_ids, _ = transition_apply._collect_positions_for_collection(
        col,
        frame,
        depsgraph,
        as_numpy=as_numpy,
    )

    if positions is None or len(positions) == 0:
        positions = np.empty((0, 3), dtype=np.float32) if as_numpy else []
        signature = None
        if include_signature:
            signature = (
                ("__scene__", scene.name if scene else ""),
                ("__vert_count__", 0),
                ("__pair_sort__", 0),
            )
        return positions, None, signature

    pair_sort = False
    if sort_by_pair_id:
        positions, pair_ids, pair_sort = _order_by_pair_ids(positions, pair_ids)

    signature = None
    if include_signature:
        pair_hash = _pair_ids_hash(pair_ids)
        signature = (
            ("__scene__", scene.name if scene else ""),
            ("__vert_count__", len(positions)),
            ("__pair_sort__", 1 if pair_sort else 0),
            ("__pair_hash__", pair_hash),
        )

    return positions, pair_ids, signature


def collect_formation_positions_with_form_ids(
    scene: bpy.types.Scene,
    depsgraph: bpy.types.Depsgraph,
    *,
    collection_name: str = "Formation",
    sort_by_pair_id: bool = False,
    include_signature: bool = False,
    as_numpy: bool = False,
):
    col = bpy.data.collections.get(collection_name)
    if col is None:
        positions = np.empty((0, 3), dtype=np.float32) if as_numpy else []
        signature = None
        if include_signature:
            signature = (
                ("__scene__", scene.name if scene else ""),
                ("__vert_count__", 0),
                ("__pair_sort__", 0),
            )
        return positions, None, None, signature

    frame = int(getattr(scene, "frame_current", 0)) if scene else 0
    positions, pair_ids, form_ids = transition_apply._collect_positions_for_collection(
        col,
        frame,
        depsgraph,
        collect_form_ids=True,
        as_numpy=as_numpy,
    )

    if positions is None or len(positions) == 0:
        positions = np.empty((0, 3), dtype=np.float32) if as_numpy else []
        signature = None
        if include_signature:
            signature = (
                ("__scene__", scene.name if scene else ""),
                ("__vert_count__", 0),
                ("__pair_sort__", 0),
            )
        return positions, None, None, signature

    pair_sort = False
    if sort_by_pair_id:
        indices, ok = pair_id.order_indices_by_pair_id(pair_ids)
        if ok:
            if isinstance(positions, np.ndarray):
                positions = positions[np.asarray(indices, dtype=np.int64)]
            else:
                positions = [positions[idx] for idx in indices]
            pair_ids = [pair_ids[idx] for idx in indices] if pair_ids else pair_ids
            if form_ids:
                form_ids = [form_ids[idx] for idx in indices]
            pair_sort = True

    signature = None
    if include_signature:
        pair_hash = _pair_ids_hash(pair_ids)
        signature = (
            ("__scene__", scene.name if scene else ""),
            ("__vert_count__", len(positions)),
            ("__pair_sort__", 1 if pair_sort else 0),
            ("__pair_hash__", pair_hash),
        )

    return positions, pair_ids, form_ids, signature
