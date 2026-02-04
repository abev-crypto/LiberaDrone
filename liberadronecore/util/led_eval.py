import bpy
import numpy as np

from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.util import pair_id


def order_positions_cache_by_pair_ids(positions, pair_ids):
    inv_map = pair_id.build_inverse_map(pair_ids, len(positions))
    ordered = [positions[src_idx] for src_idx in inv_map]
    return ordered, inv_map


def eval_effect_colors_by_map(
    positions,
    pair_ids,
    dst_indices,
    effect_fn,
    frame: float,
):
    colors = np.zeros((len(positions), 4), dtype=np.float32)
    for src_idx, pos in enumerate(positions):
        runtime_idx = int(pair_ids[src_idx])
        dst_idx = int(dst_indices[src_idx])
        color = effect_fn(runtime_idx, pos, frame)
        if not color:
            continue
        for chan in range(min(4, len(color))):
            colors[dst_idx, chan] = float(color[chan])
    return colors


def evaluate_led_colors(effect_fn, positions, pair_ids, formation_ids, frame):
    positions_list = [tuple(float(v) for v in pos) for pos in positions]
    positions_cache, _inv_map = order_positions_cache_by_pair_ids(positions_list, pair_ids)
    le_meshinfo.begin_led_frame_cache(
        frame,
        positions_cache,
        formation_ids=formation_ids,
        pair_ids=pair_ids,
    )
    try:
        colors = eval_effect_colors_by_map(
            positions_list,
            pair_ids,
            range(len(positions_list)),
            effect_fn,
            frame,
        )
    finally:
        le_meshinfo.end_led_frame_cache()
    np.clip(colors, 0.0, 1.0, out=colors)

    return colors, positions


def read_color_verts() -> tuple[list[tuple[float, float, float, float]], list[int] | None] | None:
    obj = bpy.data.objects.get("ColorVerts")
    if obj is None or obj.type != "MESH":
        return None
    mesh = obj.data
    attr = None
    if hasattr(mesh, "color_attributes"):
        attr = mesh.color_attributes.get("color")
    if attr is None and hasattr(mesh, "attributes"):
        attr = mesh.attributes.get("color")
    if attr is None or len(attr.data) != len(mesh.vertices):
        return None
    flat = [0.0] * (len(attr.data) * 4)
    try:
        attr.data.foreach_get("color", flat)
    except Exception:
        return None
    colors = [tuple(flat[i:i + 4]) for i in range(0, len(flat), 4)]
    pair_ids = None
    if hasattr(mesh, "attributes"):
        pair_attr = mesh.attributes.get("pair_id")
        if (
            pair_attr is not None
            and pair_attr.data_type == "INT"
            and pair_attr.domain == "POINT"
            and len(pair_attr.data) == len(mesh.vertices)
        ):
            vals = [0] * len(mesh.vertices)
            pair_attr.data.foreach_get("value", vals)
            pair_ids = vals
    return colors, pair_ids
