import bpy
import numpy as np

from liberadronecore.ledeffects import led_codegen_runtime as le_codegen
from liberadronecore.util import pair_id


def evaluate_led_colors(effect_fn, positions, pair_ids, formation_ids, frame):
    if effect_fn is None or positions is None:
        return None
    positions_list = [tuple(float(v) for v in pos) for pos in positions]
    positions_cache = positions_list
    if pair_ids is not None and len(pair_ids) == len(positions_list):
        positions_cache = pair_id.order_by_pair_id(positions_list, pair_ids)
    le_codegen.begin_led_frame_cache(
        frame,
        positions_cache,
        formation_ids=formation_ids,
        pair_ids=pair_ids,
    )
    colors = np.zeros((len(positions_list), 4), dtype=np.float32)
    try:
        for idx, pos in enumerate(positions_list):
            runtime_idx = idx
            if pair_ids is not None and idx < len(pair_ids):
                pid = pair_ids[idx]
                if pid is not None:
                    try:
                        runtime_idx = int(pid)
                    except (TypeError, ValueError):
                        runtime_idx = idx
            le_codegen.set_led_source_index(idx)
            le_codegen.set_led_runtime_index(runtime_idx)
            color = effect_fn(runtime_idx, pos, frame)
            if not color:
                continue
            for chan in range(min(4, len(color))):
                colors[idx, chan] = float(color[chan])
    finally:
        le_codegen.set_led_runtime_index(None)
        le_codegen.set_led_source_index(None)
        le_codegen.end_led_frame_cache()
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
