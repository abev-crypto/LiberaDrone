from __future__ import annotations

from typing import Optional, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Vector

from liberadronecore.system.transition import transition_apply


def _order_by_pair_ids(
    positions: Sequence,
    pair_ids: Optional[Sequence[int]],
):
    if not pair_ids or len(pair_ids) != len(positions):
        return positions, pair_ids, False

    paired = []
    fallback = []
    for idx, pid in enumerate(pair_ids):
        try:
            key = int(pid)
        except (TypeError, ValueError):
            key = None
        if key is None:
            fallback.append(idx)
        else:
            paired.append((key, idx))

    if not paired:
        return positions, pair_ids, False

    paired.sort(key=lambda item: (item[0], item[1]))
    indices = [idx for _key, idx in paired] + fallback

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
        signature = (
            ("__scene__", scene.name if scene else ""),
            ("__vert_count__", len(positions)),
            ("__pair_sort__", 1 if pair_sort else 0),
        )

    return positions, pair_ids, signature
