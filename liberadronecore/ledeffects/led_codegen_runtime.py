from __future__ import annotations

import colorsys
import math
import mathutils
from typing import Callable, Dict, List, Optional, Tuple

import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


def _sanitize_identifier(text: str) -> str:
    safe = []
    for ch in text or "":
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch == "_":
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe) or "node"
    if result[0].isdigit():
        result = f"n_{result}"
    return result


def _default_for_socket(socket: bpy.types.NodeSocket) -> str:
    if getattr(socket, "bl_idname", "") == "NodeSocketColor":
        return "(0.0, 0.0, 0.0, 1.0)"
    if getattr(socket, "bl_idname", "") == "NodeSocketFloat":
        return "0.0"
    if getattr(socket, "bl_idname", "") == "NodeSocketVector":
        return "(0.0, 0.0, 0.0)"
    if getattr(socket, "bl_idname", "") == "NodeSocketString":
        return "''"
    if getattr(socket, "bl_idname", "") == "LDLEDEntrySocket":
        return "_entry_empty()"
    return "0.0"


def _default_for_input(socket: bpy.types.NodeSocket) -> str:
    if hasattr(socket, "default_value"):
        value = socket.default_value
        if isinstance(value, (float, int)):
            return repr(float(value))
        if isinstance(value, (list, tuple, mathutils.Vector)) or (
            hasattr(value, "__iter__") and not isinstance(value, (str, bytes))
        ):
            try:
                return repr(tuple(float(v) for v in value))
            except Exception:
                pass
    return _default_for_socket(socket)


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _alpha_over(dst: List[float], src: List[float], alpha: float) -> List[float]:
    inv = 1.0 - alpha
    return [
        src[0] * alpha + dst[0] * inv,
        src[1] * alpha + dst[1] * inv,
        src[2] * alpha + dst[2] * inv,
        1.0,
    ]


def _clamp(x: float, low: float, high: float) -> float:
    if x < low:
        return low
    if x > high:
        return high
    return x


def _rand01(idx: int, frame: float, seed: float) -> float:
    value = math.sin(idx * 12.9898 + frame * 78.233 + seed * 37.719)
    return value - math.floor(value)


def _rgb_to_hsv(color: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    r, g, b, a = color
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h, s, v, a


def _hsv_to_rgb(color: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    h, s, v, a = color
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return r, g, b, a


def _srgb_to_linear_channel(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb_channel(c: float) -> float:
    if c <= 0.0031308:
        return c * 12.92
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _srgb_to_linear(color: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    r, g, b, a = color
    return (
        _srgb_to_linear_channel(r),
        _srgb_to_linear_channel(g),
        _srgb_to_linear_channel(b),
        a,
    )


def _linear_to_srgb(color: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    r, g, b, a = color
    return (
        _linear_to_srgb_channel(r),
        _linear_to_srgb_channel(g),
        _linear_to_srgb_channel(b),
        a,
    )


def _to_grayscale(color: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    r, g, b, a = color
    gray = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return gray, gray, gray, a


def _get_object(name: str) -> Optional[bpy.types.Object]:
    if not name:
        return None
    return bpy.data.objects.get(name)


def _object_world_bbox(obj: bpy.types.Object) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
    if obj is None:
        return None
    bbox = obj.bound_box
    if not bbox:
        return None
    mw = obj.matrix_world
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    for co in bbox:
        world = mw @ mathutils.Vector(co)
        xs.append(world.x)
        ys.append(world.y)
        zs.append(world.z)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _point_in_bbox(pos: Tuple[float, float, float], bounds) -> bool:
    (min_x, min_y, min_z), (max_x, max_y, max_z) = bounds
    return min_x <= pos[0] <= max_x and min_y <= pos[1] <= max_y and min_z <= pos[2] <= max_z


def _distance_to_bbox(pos: Tuple[float, float, float], bounds) -> float:
    (min_x, min_y, min_z), (max_x, max_y, max_z) = bounds
    dx = max(min_x - pos[0], 0.0, pos[0] - max_x)
    dy = max(min_y - pos[1], 0.0, pos[1] - max_y)
    dz = max(min_z - pos[2], 0.0, pos[2] - max_z)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _project_bbox_uv(obj_name: str, pos: Tuple[float, float, float]) -> Tuple[float, float]:
    obj = _get_object(obj_name)
    bounds = _object_world_bbox(obj)
    if not bounds:
        return 0.0, 0.0
    (min_x, _, min_z), (max_x, _, max_z) = bounds
    span_x = max(0.0001, max_x - min_x)
    span_z = max(0.0001, max_z - min_z)
    u = _clamp((pos[0] - min_x) / span_x, 0.0, 1.0)
    v = _clamp((pos[2] - min_z) / span_z, 0.0, 1.0)
    return u, v


def _distance_to_mesh_bbox(obj_name: str, pos: Tuple[float, float, float]) -> float:
    obj = _get_object(obj_name)
    bounds = _object_world_bbox(obj)
    if not bounds:
        return 0.0
    return _distance_to_bbox(pos, bounds)


def _point_in_mesh_bbox(obj_name: str, pos: Tuple[float, float, float]) -> bool:
    obj = _get_object(obj_name)
    bounds = _object_world_bbox(obj)
    if not bounds:
        return False
    return _point_in_bbox(pos, bounds)


def _nearest_vertex_color(obj_name: str, pos: Tuple[float, float, float]) -> Tuple[float, float, float, float]:
    obj = _get_object(obj_name)
    if obj is None or obj.type != 'MESH':
        return 0.0, 0.0, 0.0, 1.0
    mesh = obj.data
    if not mesh.vertices:
        return 0.0, 0.0, 0.0, 1.0
    mw = obj.matrix_world
    best_idx = None
    best_dist = 1e30
    for v in mesh.vertices:
        world = mw @ v.co
        dx = world.x - pos[0]
        dy = world.y - pos[1]
        dz = world.z - pos[2]
        dist = dx * dx + dy * dy + dz * dz
        if dist < best_dist:
            best_dist = dist
            best_idx = v.index
    if best_idx is None:
        return 0.0, 0.0, 0.0, 1.0
    attr = mesh.color_attributes.active if hasattr(mesh, "color_attributes") else None
    if attr is None and hasattr(mesh, "color_attributes"):
        if mesh.color_attributes:
            attr = mesh.color_attributes[0]
    if attr is None:
        return 0.0, 0.0, 0.0, 1.0
    if attr.domain == 'POINT':
        color = attr.data[best_idx].color
        return color[0], color[1], color[2], color[3]
    if attr.domain == 'CORNER':
        for loop in mesh.loops:
            if loop.vertex_index == best_idx:
                color = attr.data[loop.index].color
                return color[0], color[1], color[2], color[3]
    return 0.0, 0.0, 0.0, 1.0


def _nearest_vertex_uv(obj_name: str, pos: Tuple[float, float, float]) -> Tuple[float, float]:
    obj = _get_object(obj_name)
    if obj is None or obj.type != 'MESH':
        return 0.0, 0.0
    mesh = obj.data
    if not mesh.vertices or not mesh.uv_layers:
        return 0.0, 0.0
    uv_layer = mesh.uv_layers.active or mesh.uv_layers[0]
    mw = obj.matrix_world
    best_idx = None
    best_dist = 1e30
    for v in mesh.vertices:
        world = mw @ v.co
        dx = world.x - pos[0]
        dy = world.y - pos[1]
        dz = world.z - pos[2]
        dist = dx * dx + dy * dy + dz * dz
        if dist < best_dist:
            best_dist = dist
            best_idx = v.index
    if best_idx is None:
        return 0.0, 0.0
    for loop in mesh.loops:
        if loop.vertex_index == best_idx:
            uv = uv_layer.data[loop.index].uv
            return float(uv[0]), float(uv[1])
    return 0.0, 0.0


def _nearest_vertex_uv_with_dist(
    obj: bpy.types.Object, pos: Tuple[float, float, float]
) -> Tuple[Tuple[float, float], float]:
    if obj is None or obj.type != 'MESH':
        return (0.0, 0.0), 1e30
    mesh = obj.data
    if not mesh.vertices or not mesh.uv_layers:
        return (0.0, 0.0), 1e30
    uv_layer = mesh.uv_layers.active or mesh.uv_layers[0]
    mw = obj.matrix_world
    best_idx = None
    best_dist = 1e30
    for v in mesh.vertices:
        world = mw @ v.co
        dx = world.x - pos[0]
        dy = world.y - pos[1]
        dz = world.z - pos[2]
        dist = dx * dx + dy * dy + dz * dz
        if dist < best_dist:
            best_dist = dist
            best_idx = v.index
    if best_idx is None:
        return (0.0, 0.0), 1e30
    for loop in mesh.loops:
        if loop.vertex_index == best_idx:
            uv = uv_layer.data[loop.index].uv
            return (float(uv[0]), float(uv[1])), best_dist
    return (0.0, 0.0), 1e30


def _collection_nearest_uv(collection_name: str, pos: Tuple[float, float, float], use_children: bool) -> Tuple[float, float]:
    col = bpy.data.collections.get(collection_name)
    if col is None:
        return 0.0, 0.0
    candidates: List[bpy.types.Object] = []
    stack = [col]
    while stack:
        current = stack.pop()
        candidates.extend([obj for obj in current.objects if obj.type == 'MESH'])
        if use_children:
            stack.extend(list(current.children))
    best_uv = (0.0, 0.0)
    best_dist = 1e30
    for obj in candidates:
        uv, dist = _nearest_vertex_uv_with_dist(obj, pos)
        if dist < best_dist:
            best_dist = dist
            best_uv = uv
    return best_uv


def _formation_bbox_uv(pos: Tuple[float, float, float]) -> Tuple[float, float]:
    obj = bpy.data.objects.get("DroneSystem")
    bounds = _object_world_bbox(obj) if obj else None
    if not bounds:
        return 0.0, 0.0
    (min_x, min_y, min_z), (max_x, max_y, max_z) = bounds
    span_x = max(0.0001, max_x - min_x)
    span_z = max(0.0001, max_z - min_z)
    u = _clamp((pos[0] - min_x) / span_x, 0.0, 1.0)
    v = _clamp((pos[2] - min_z) / span_z, 0.0, 1.0)
    return u, v


_IMAGE_CACHE: Dict[str, Tuple[int, int, List[float]]] = {}


def _sample_image(image_name: str, uv: Tuple[float, float]) -> Tuple[float, float, float, float]:
    if not image_name:
        return 0.0, 0.0, 0.0, 1.0
    image = bpy.data.images.get(image_name)
    if image is None:
        return 0.0, 0.0, 0.0, 1.0
    width, height = image.size
    if width <= 0 or height <= 0:
        return 0.0, 0.0, 0.0, 1.0
    u = _clamp(float(uv[0]), 0.0, 1.0)
    v = _clamp(float(uv[1]), 0.0, 1.0)
    x = int(u * (width - 1))
    y = int(v * (height - 1))
    idx = (y * width + x) * 4
    pixels = image.pixels
    if idx + 3 >= len(pixels):
        return 0.0, 0.0, 0.0, 1.0
    return float(pixels[idx]), float(pixels[idx + 1]), float(pixels[idx + 2]), float(pixels[idx + 3])


_CAT_CACHE: Dict[str, Tuple[Tuple[float, float, float, float], float]] = {}


def _cat_cache_write(name: str, color: Tuple[float, float, float, float], intensity: float) -> None:
    _CAT_CACHE[str(name)] = (tuple(color), float(intensity))


def _cat_cache_read(name: str) -> Tuple[Tuple[float, float, float, float], float]:
    return _CAT_CACHE.get(str(name), ((0.0, 0.0, 0.0, 1.0), 0.0))


def _entry_empty() -> Dict[str, List[Tuple[float, float]]]:
    return {}


def _entry_is_empty(entry: Optional[Dict[str, List[Tuple[float, float]]]]) -> bool:
    return not entry


def _entry_merge(
    left: Optional[Dict[str, List[Tuple[float, float]]]],
    right: Optional[Dict[str, List[Tuple[float, float]]]],
) -> Dict[str, List[Tuple[float, float]]]:
    merged: Dict[str, List[Tuple[float, float]]] = {}
    for source in (left or {}, right or {}):
        for key, spans in source.items():
            merged.setdefault(key, []).extend(list(spans))
    return merged


def _entry_from_range(key: str, start: float, duration: float) -> Dict[str, List[Tuple[float, float]]]:
    dur = max(0.0, float(duration))
    if dur <= 0.0:
        return {}
    return {key: [(float(start), float(start) + dur)]}


def _entry_from_marker(
    key: str,
    marker_name: str,
    offset: float,
    duration: float,
) -> Dict[str, List[Tuple[float, float]]]:
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return {}
    for marker in scene.timeline_markers:
        if marker.name == marker_name:
            start = float(marker.frame) + float(offset)
            return _entry_from_range(key, start, duration)
    return {}


def _entry_from_formation(
    key: str,
    formation_name: str,
    duration: float,
    from_end: bool,
) -> Dict[str, List[Tuple[float, float]]]:
    try:
        from liberadronecore.formation import fn_parse
    except Exception:
        return {}
    scene = getattr(bpy.context, "scene", None)
    schedule = fn_parse.get_cached_schedule(scene)
    spans: List[Tuple[float, float]] = []
    for entry in schedule:
        col = getattr(entry, "collection", None)
        col_name = getattr(col, "name", "") if col else ""
        if formation_name and formation_name not in {entry.node_name, col_name, entry.tree_name}:
            continue
        if from_end:
            end = float(entry.end)
            start = end - max(0.0, float(duration))
        else:
            start = float(entry.start)
            end = start + max(0.0, float(duration))
        spans.append((start, end))
    if not spans:
        return {}
    return {key: spans}


def _entry_shift(
    entry: Optional[Dict[str, List[Tuple[float, float]]]],
    start_offset: float,
    duration_offset: float,
) -> Dict[str, List[Tuple[float, float]]]:
    if not entry:
        return {}
    shifted: Dict[str, List[Tuple[float, float]]] = {}
    for key, spans in entry.items():
        new_spans = []
        for start, end in spans:
            start = float(start) + float(start_offset)
            duration = max(0.0, float(end - start) + float(duration_offset))
            new_spans.append((start, start + duration))
        shifted[key] = new_spans
    return shifted


def _entry_loop(
    entry: Optional[Dict[str, List[Tuple[float, float]]]],
    offset: float,
    loops: int,
) -> Dict[str, List[Tuple[float, float]]]:
    if not entry:
        return {}
    result: Dict[str, List[Tuple[float, float]]] = {}
    loop_count = max(0, int(loops))
    for key, spans in entry.items():
        out_spans = list(spans)
        for i in range(1, loop_count + 1):
            delta = float(offset) * i
            for start, end in spans:
                out_spans.append((float(start) + delta, float(end) + delta))
        result[key] = out_spans
    return result


def _entry_active_count(entry: Optional[Dict[str, List[Tuple[float, float]]]], frame: float) -> int:
    if not entry:
        return 0
    count = 0
    fr = float(frame)
    for spans in entry.values():
        for start, end in spans:
            if float(start) <= fr < float(end):
                count += 1
    return count


def _entry_progress(entry: Optional[Dict[str, List[Tuple[float, float]]]], frame: float) -> float:
    if not entry:
        return 0.0
    fr = float(frame)
    best = 0.0
    for spans in entry.values():
        for start, end in spans:
            start_f = float(start)
            end_f = float(end)
            if end_f <= start_f:
                continue
            if start_f <= fr < end_f:
                t = (fr - start_f) / (end_f - start_f)
                if t > best:
                    best = t
    return _clamp01(best)


def _get_output_var(node: bpy.types.Node, socket: bpy.types.NodeSocket) -> str:
    mapping = getattr(node, "_codegen_output_vars", {})
    if socket.name in mapping:
        return mapping[socket.name]
    node_id = _sanitize_identifier(getattr(node, "name", "") or node.bl_idname)
    return f"{node_id}_{_sanitize_identifier(socket.name)}"


def _collect_outputs(tree: bpy.types.NodeTree) -> List[bpy.types.Node]:
    outputs = [n for n in tree.nodes if n.bl_idname == "LDLEDOutputNode"]
    outputs.sort(key=lambda n: (getattr(n, "priority", 0), n.name))
    return outputs


def compile_led_effect(tree: bpy.types.NodeTree) -> Optional[Callable]:
    outputs = _collect_outputs(tree)
    if not outputs:
        return None

    emitted: set[int] = set()
    lines: List[str] = []

    def emit_node(node: bpy.types.Node) -> None:
        if node.as_pointer() in emitted:
            return
        if not isinstance(node, LDLED_CodeNodeBase):
            return

        inputs: Dict[str, str] = {}
        for sock in getattr(node, "inputs", []):
            inputs[sock.name] = resolve_input(sock)

        output_vars = {
            sock.name: f"{node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(node, "outputs", [])
        }
        node._set_codegen_output_vars(output_vars)

        snippet = node.build_code(inputs) or ""
        for line in snippet.splitlines():
            lines.append(line)
        emitted.add(node.as_pointer())

    def resolve_input(socket: Optional[bpy.types.NodeSocket]) -> str:
        if socket is None:
            return "0.0"
        is_entry = getattr(socket, "bl_idname", "") == "LDLEDEntrySocket"
        if is_entry and socket.is_linked and socket.links:
            entry_vars: List[str] = []
            for link in socket.links:
                if not getattr(link, "is_valid", True):
                    continue
                from_node = link.from_node
                from_socket = link.from_socket
                emit_node(from_node)
                if isinstance(from_node, LDLED_CodeNodeBase):
                    entry_vars.append(_get_output_var(from_node, from_socket))
            if not entry_vars:
                return "_entry_empty()"
            if len(entry_vars) == 1:
                return entry_vars[0]
            merge_var = f"_entry_merge_{len(lines)}"
            lines.append(f"{merge_var} = _entry_empty()")
            for entry_var in entry_vars:
                lines.append(f"{merge_var} = _entry_merge({merge_var}, {entry_var})")
            return merge_var
        if socket.is_linked and socket.links:
            link = socket.links[0]
            if not getattr(link, "is_valid", True):
                return _default_for_input(socket)
            from_node = link.from_node
            from_socket = link.from_socket
            emit_node(from_node)
            if isinstance(from_node, LDLED_CodeNodeBase):
                return _get_output_var(from_node, from_socket)
            return _default_for_socket(from_socket)
        if is_entry:
            return "_entry_empty()"
        return _default_for_input(socket)

    for output in outputs:
        color_in = resolve_input(output.inputs.get("Color"))
        intensity_in = resolve_input(output.inputs.get("Intensity"))
        alpha_in = resolve_input(output.inputs.get("Alpha"))
        entry_in = resolve_input(output.inputs.get("Entry"))
        out_id = _sanitize_identifier(output.name)
        lines.append(f"_color_{out_id} = {color_in}")
        lines.append(f"_intensity_{out_id} = {intensity_in}")
        lines.append(f"_alpha_{out_id} = {alpha_in}")
        lines.append(f"_entry_{out_id} = {entry_in}")
        lines.append(f"_entry_count_{out_id} = _entry_active_count(_entry_{out_id}, frame)")
        lines.append(f"if _entry_is_empty(_entry_{out_id}):")
        lines.append(f"    _entry_count_{out_id} = 1")
        lines.append(f"if _entry_count_{out_id} > 0:")
        lines.append(
            "    _src_alpha = _clamp01(_alpha_{0} * ("
            "_color_{0}[3] if len(_color_{0}) > 3 else 1.0))".format(out_id)
        )
        lines.append(
            "    _src_color = ["
            "_color_{0}[0] * _intensity_{0}, "
            "_color_{0}[1] * _intensity_{0}, "
            "_color_{0}[2] * _intensity_{0}, "
            "1.0]".format(out_id)
        )
        lines.append("    for _ in range(int(_entry_count_{0})):".format(out_id))
        lines.append("        color = _alpha_over(color, _src_color, _src_alpha)")

    body = ["def _led_effect(idx, pos, frame, random_seq):", "    color = [0.0, 0.0, 0.0, 1.0]"]
    body.extend([f"    {line}" for line in lines])
    body.append("    return color")

    code = "\n".join(body)
    env = {
        "_clamp": _clamp,
        "_clamp01": _clamp01,
        "_alpha_over": _alpha_over,
        "_rand01": _rand01,
        "_rgb_to_hsv": _rgb_to_hsv,
        "_hsv_to_rgb": _hsv_to_rgb,
        "_srgb_to_linear": _srgb_to_linear,
        "_linear_to_srgb": _linear_to_srgb,
        "_to_grayscale": _to_grayscale,
        "_get_object": _get_object,
        "_project_bbox_uv": _project_bbox_uv,
        "_distance_to_mesh_bbox": _distance_to_mesh_bbox,
        "_point_in_mesh_bbox": _point_in_mesh_bbox,
        "_nearest_vertex_color": _nearest_vertex_color,
        "_nearest_vertex_uv": _nearest_vertex_uv,
        "_collection_nearest_uv": _collection_nearest_uv,
        "_formation_bbox_uv": _formation_bbox_uv,
        "_sample_image": _sample_image,
        "_cat_cache_write": _cat_cache_write,
        "_cat_cache_read": _cat_cache_read,
        "_entry_empty": _entry_empty,
        "_entry_is_empty": _entry_is_empty,
        "_entry_merge": _entry_merge,
        "_entry_from_range": _entry_from_range,
        "_entry_from_marker": _entry_from_marker,
        "_entry_from_formation": _entry_from_formation,
        "_entry_shift": _entry_shift,
        "_entry_loop": _entry_loop,
        "_entry_active_count": _entry_active_count,
        "_entry_progress": _entry_progress,
        "bpy": bpy,
        "math": math,
        "mathutils": mathutils,
    }
    exec(code, env)
    return env["_led_effect"]


_TREE_CACHE: Dict[int, Callable] = {}


def get_compiled_effect(tree: bpy.types.NodeTree) -> Optional[Callable]:
    key = tree.as_pointer()
    if key in _TREE_CACHE and not tree.is_updated:
        return _TREE_CACHE[key]
    compiled = compile_led_effect(tree)
    if compiled is not None:
        _TREE_CACHE[key] = compiled
    return compiled


def get_active_tree(scene: bpy.types.Scene) -> Optional[bpy.types.NodeTree]:
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", "") == "LD_LedEffectsTree":
            return tree
    return None
