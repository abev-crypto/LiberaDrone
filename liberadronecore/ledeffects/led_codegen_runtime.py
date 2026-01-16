from __future__ import annotations

import colorsys
import math
import mathutils
from typing import Callable, Dict, List, Optional, Tuple, Any

import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.system.video.cvcache import FrameSampler
from liberadronecore.formation import fn_parse
import numpy as np

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
    if getattr(socket, "bl_idname", "") == "NodeSocketObject":
        return "None"
    if getattr(socket, "bl_idname", "") == "NodeSocketCollection":
        return "None"
    if getattr(socket, "bl_idname", "") == "LDLEDEntrySocket":
        return "_entry_empty()"
    return "0.0"


def _default_for_input(socket: bpy.types.NodeSocket) -> str:
    if hasattr(socket, "default_value"):
        value = socket.default_value
        if isinstance(value, bpy.types.Object):
            return repr(value.name)
        if isinstance(value, bpy.types.Collection):
            return repr(value.name)
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


def _fract(x: float) -> float:
    return x - math.floor(x)


def _loop_factor(value: float, mode: str = "REPEAT") -> float:
    mode = (mode or "REPEAT").upper()
    frac = _fract(float(value))
    if mode in {"PINGPONG", "PING_PONG", "PING-PONG"}:
        return 1.0 - abs(2.0 * frac - 1.0)
    return frac


def _alpha_over(dst: List[float], src: List[float], alpha: float) -> List[float]:
    inv = 1.0 - alpha
    return [
        src[0] * alpha + dst[0] * inv,
        src[1] * alpha + dst[1] * inv,
        src[2] * alpha + dst[2] * inv,
        1.0,
    ]


def _blend_over(dst: List[float], src: List[float], alpha: float, mode: str) -> List[float]:
    alpha = _clamp01(float(alpha))
    if alpha <= 0.0:
        return [dst[0], dst[1], dst[2], 1.0]
    mode = (mode or "MIX").upper()
    if mode == "MIX":
        return _alpha_over(dst, src, alpha)

    def blend_channel(a: float, b: float) -> float:
        if mode == "ADD":
            return a + b
        if mode == "MULTIPLY":
            return a * b
        if mode == "SCREEN":
            return 1.0 - (1.0 - a) * (1.0 - b)
        if mode == "OVERLAY":
            return (2.0 * a * b) if (a < 0.5) else (1.0 - 2.0 * (1.0 - a) * (1.0 - b))
        if mode == "HARD_LIGHT":
            return (2.0 * a * b) if (b < 0.5) else (1.0 - 2.0 * (1.0 - a) * (1.0 - b))
        if mode == "SOFT_LIGHT":
            return (a - (1.0 - 2.0 * b) * a * (1.0 - a)) if (b < 0.5) else (
                a + (2.0 * b - 1.0) * (_clamp01(a) ** 0.5 - a)
            )
        if mode == "BURN":
            return _clamp01(1.0 - (1.0 - a) / (b if b > 0.0 else 1e-5))
        if mode == "SUBTRACT":
            return a - b
        if mode == "MAX":
            return a if a > b else b
        return b

    inv = 1.0 - alpha
    r = dst[0] * inv + blend_channel(dst[0], src[0]) * alpha
    g = dst[1] * inv + blend_channel(dst[1], src[1]) * alpha
    b = dst[2] * inv + blend_channel(dst[2], src[2]) * alpha
    return [r, g, b, 1.0]


def _clamp(x: float, low: float, high: float) -> float:
    if x < low:
        return low
    if x > high:
        return high
    return x


def _rand01(idx: int, frame: float, seed: float) -> float:
    value = math.sin(idx * 12.9898 + frame * 78.233 + seed * 37.719)
    return value - math.floor(value)


def _rand01_static(idx: int, seed: float) -> float:
    value = math.sin(idx * 12.9898 + seed * 78.233)
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


def _hue_lerp(h0: float, h1: float, t: float) -> float:
    delta = (h1 - h0) % 1.0
    if delta > 0.5:
        delta -= 1.0
    return (h0 + delta * t) % 1.0


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c0: Tuple[float, float, float, float], c1: Tuple[float, float, float, float], t: float, mode: str):
    mode = (mode or "RGB").upper()
    if mode == "HSV":
        h0, s0, v0 = colorsys.rgb_to_hsv(c0[0], c0[1], c0[2])
        h1, s1, v1 = colorsys.rgb_to_hsv(c1[0], c1[1], c1[2])
        h = _hue_lerp(h0, h1, t)
        s = _lerp(s0, s1, t)
        v = _lerp(v0, v1, t)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return r, g, b, _lerp(c0[3], c1[3], t)
    if mode == "HSL":
        h0, l0, s0 = colorsys.rgb_to_hls(c0[0], c0[1], c0[2])
        h1, l1, s1 = colorsys.rgb_to_hls(c1[0], c1[1], c1[2])
        h = _hue_lerp(h0, h1, t)
        l = _lerp(l0, l1, t)
        s = _lerp(s0, s1, t)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return r, g, b, _lerp(c0[3], c1[3], t)
    return (
        _lerp(c0[0], c1[0], t),
        _lerp(c0[1], c1[1], t),
        _lerp(c0[2], c1[2], t),
        _lerp(c0[3], c1[3], t),
    )


def _ease(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _ease_in(t: float) -> float:
    t = _clamp01(t)
    return t * t


def _ease_out(t: float) -> float:
    t = _clamp01(t)
    inv = 1.0 - t
    return 1.0 - inv * inv


def _ease_in_out(t: float) -> float:
    t = _clamp01(t)
    return _ease(t)


def _apply_ease(t: float, mode: str) -> float:
    mode = (mode or "LINEAR").upper()
    if mode in {"EASEIN", "EASE_IN"}:
        return _ease_in(t)
    if mode in {"EASEOUT", "EASE_OUT"}:
        return _ease_out(t)
    if mode in {"EASEINOUT", "EASE_IN_OUT"}:
        return _ease_in_out(t)
    return _clamp01(t)

def _color_ramp_eval(
    elements: List[Tuple[float, Tuple[float, float, float, float]]],
    interpolation: str,
    color_mode: str,
    factor: float,
) -> Tuple[float, float, float, float]:
    if not elements:
        return 0.0, 0.0, 0.0, 1.0
    t = _clamp01(float(factor))
    elements = sorted(elements, key=lambda e: e[0])
    if t <= elements[0][0]:
        return tuple(elements[0][1])
    if t >= elements[-1][0]:
        return tuple(elements[-1][1])
    interp = (interpolation or "LINEAR").upper()
    for idx in range(len(elements) - 1):
        p0, c0 = elements[idx]
        p1, c1 = elements[idx + 1]
        if p0 <= t <= p1:
            if p1 <= p0:
                return tuple(c1)
            local_t = (t - p0) / (p1 - p0)
            if interp == "CONSTANT":
                return tuple(c0)
            if interp in {"EASE", "CARDINAL", "B_SPLINE"}:
                local_t = _ease(local_t)
            return _lerp_color(tuple(c0), tuple(c1), local_t, color_mode)
    return tuple(elements[-1][1])


def _get_object(value) -> Optional[bpy.types.Object]:
    if value is None:
        return None
    if isinstance(value, bpy.types.Object):
        return value
    if isinstance(value, str):
        if not value:
            return None
        return bpy.data.objects.get(value)
    return None


def _collection_name(value) -> str:
    if isinstance(value, bpy.types.Collection):
        return value.name
    if isinstance(value, str):
        return value
    return ""


def _get_collection(value) -> Optional[bpy.types.Collection]:
    if value is None:
        return None
    if isinstance(value, bpy.types.Collection):
        return value
    if isinstance(value, str):
        if not value:
            return None
        return bpy.data.collections.get(value)
    return None


def _object_world_bbox(obj: bpy.types.Object) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
    if obj is None:
        return None
    if _LED_FRAME_CACHE.get("frame") is not None:
        cached = _LED_FRAME_CACHE["bbox"].get(obj.name)
        if cached is not None:
            return cached
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
    bounds = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
    if _LED_FRAME_CACHE.get("frame") is not None:
        _LED_FRAME_CACHE["bbox"][obj.name] = bounds
    return bounds


def _collection_world_bbox(
    collection_name: str,
    *,
    use_children: bool = True,
) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
    collection_name = _collection_name(collection_name)
    if not collection_name:
        return None
    names = _get_collection_cache(collection_name, use_children, build_mesh_cache=False)
    if names is None:
        col = _get_collection(collection_name)
        if col is None:
            return None
        candidates: List[bpy.types.Object] = []
        stack = [col]
        while stack:
            current = stack.pop()
            candidates.extend([obj for obj in current.objects if obj.type == 'MESH'])
            if use_children:
                stack.extend(list(current.children))
        names = [obj.name for obj in candidates]
    min_v = None
    max_v = None
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH':
            continue
        bounds = _object_world_bbox(obj)
        if not bounds:
            continue
        (min_x, min_y, min_z), (max_x, max_y, max_z) = bounds
        if min_v is None:
            min_v = [min_x, min_y, min_z]
            max_v = [max_x, max_y, max_z]
        else:
            min_v[0] = min(min_v[0], min_x)
            min_v[1] = min(min_v[1], min_y)
            min_v[2] = min(min_v[2], min_z)
            max_v[0] = max(max_v[0], max_x)
            max_v[1] = max(max_v[1], max_y)
            max_v[2] = max(max_v[2], max_z)
    if min_v is None or max_v is None:
        return None
    return (min_v[0], min_v[1], min_v[2]), (max_v[0], max_v[1], max_v[2])


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


_LED_FRAME_CACHE: Dict[str, Any] = {"frame": None, "mesh": {}, "collection": {}, "bbox": {}}
_LED_CURRENT_INDEX: Optional[int] = None


def begin_led_frame_cache(frame: float, positions: List[Tuple[float, float, float]]) -> None:
    _LED_FRAME_CACHE["frame"] = float(frame)
    _LED_FRAME_CACHE["mesh"] = {}
    _LED_FRAME_CACHE["collection"] = {}
    _LED_FRAME_CACHE["bbox"] = {}


def end_led_frame_cache() -> None:
    _LED_FRAME_CACHE["frame"] = None
    _LED_FRAME_CACHE["mesh"] = {}
    _LED_FRAME_CACHE["collection"] = {}
    _LED_FRAME_CACHE["bbox"] = {}


def set_led_runtime_index(idx: Optional[int]) -> None:
    global _LED_CURRENT_INDEX
    _LED_CURRENT_INDEX = None if idx is None else int(idx)


def _build_mesh_cache(obj: bpy.types.Object) -> Optional[Dict[str, Any]]:
    if obj is None or obj.type != 'MESH':
        return None
    mesh = obj.data
    if not mesh.vertices:
        return None
    mw = obj.matrix_world
    positions: List[Tuple[float, float, float]] = []
    for v in mesh.vertices:
        world = mw @ v.co
        positions.append((float(world.x), float(world.y), float(world.z)))

    uv_by_vertex: List[Optional[Tuple[float, float]]] = [None] * len(mesh.vertices)
    if mesh.uv_layers:
        uv_layer = mesh.uv_layers.active or mesh.uv_layers[0]
        for loop in mesh.loops:
            v_idx = loop.vertex_index
            if uv_by_vertex[v_idx] is None:
                uv = uv_layer.data[loop.index].uv
                uv_by_vertex[v_idx] = (float(uv[0]), float(uv[1]))

    color_by_vertex: List[Optional[Tuple[float, float, float, float]]] = [None] * len(mesh.vertices)
    attr = None
    if hasattr(mesh, "color_attributes"):
        attrs = list(mesh.color_attributes)
        if attrs:
            color_attrs = [
                a for a in attrs
                if getattr(a, "data_type", "") in {"BYTE_COLOR", "FLOAT_COLOR"}
            ]
            if color_attrs:
                active = mesh.color_attributes.active
                attr = active if active in color_attrs else color_attrs[0]
    if attr is not None:
        if attr.domain == 'POINT':
            for idx in range(len(mesh.vertices)):
                try:
                    color = attr.data[idx].color
                except Exception:
                    continue
                color_by_vertex[idx] = (float(color[0]), float(color[1]), float(color[2]), float(color[3]))
        elif attr.domain == 'CORNER':
            for loop in mesh.loops:
                v_idx = loop.vertex_index
                if color_by_vertex[v_idx] is None:
                    try:
                        color = attr.data[loop.index].color
                    except Exception:
                        continue
                    color_by_vertex[v_idx] = (float(color[0]), float(color[1]), float(color[2]), float(color[3]))

    available_uv = list(range(len(mesh.vertices)))

    return {
        "positions": positions,
        "uvs": uv_by_vertex,
        "colors": color_by_vertex,
        "available_uv_indices": available_uv,
        "assigned_uv": {},
        "assigned_uv_dist": {},
        "assigned_color": {},
    }


def _get_mesh_cache(obj: bpy.types.Object) -> Optional[Dict[str, Any]]:
    if _LED_FRAME_CACHE.get("frame") is None:
        return None
    if obj is None or obj.type != 'MESH':
        return None
    cache = _LED_FRAME_CACHE["mesh"].get(obj.name)
    if cache is None:
        cache = _build_mesh_cache(obj)
        if cache is None:
            return None
        _LED_FRAME_CACHE["mesh"][obj.name] = cache
    return cache


def _get_collection_cache(
    collection_name: str,
    use_children: bool,
    build_mesh_cache: bool = True,
) -> Optional[List[str]]:
    if _LED_FRAME_CACHE.get("frame") is None:
        return None
    collection_name = _collection_name(collection_name)
    if not collection_name:
        return []
    key = (collection_name, bool(use_children))
    cached = _LED_FRAME_CACHE["collection"].get(key)
    if cached is not None:
        if build_mesh_cache:
            for name in cached:
                obj = bpy.data.objects.get(name)
                if obj is not None and obj.type == 'MESH':
                    _get_mesh_cache(obj)
        return cached
    col = _get_collection(collection_name)
    if col is None:
        _LED_FRAME_CACHE["collection"][key] = []
        return []
    candidates: List[bpy.types.Object] = []
    stack = [col]
    while stack:
        current = stack.pop()
        candidates.extend([obj for obj in current.objects if obj.type == 'MESH'])
        if use_children:
            stack.extend(list(current.children))
    names = [obj.name for obj in candidates]
    if build_mesh_cache:
        for obj in candidates:
            _get_mesh_cache(obj)
    _LED_FRAME_CACHE["collection"][key] = names
    return names


def _nearest_vertex_color(obj_name: str, pos: Tuple[float, float, float]) -> Tuple[float, float, float, float]:
    obj = _get_object(obj_name)
    if obj is None or obj.type != 'MESH':
        return 0.0, 0.0, 0.0, 1.0
    mesh = obj.data
    if not mesh.vertices:
        return 0.0, 0.0, 0.0, 1.0
    cache = _get_mesh_cache(obj)
    if cache is not None:
        assigned = cache["assigned_color"].get(_LED_CURRENT_INDEX)
        if assigned is not None:
            return assigned
        positions = cache["positions"]
        colors = cache["colors"]
        best_idx = None
        best_dist = 1e30
        for idx, world in enumerate(positions):
            dx = world[0] - pos[0]
            dy = world[1] - pos[1]
            dz = world[2] - pos[2]
            dist = dx * dx + dy * dy + dz * dz
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        if best_idx is None:
            return 0.0, 0.0, 0.0, 1.0
        color = colors[best_idx]
        if color is None:
            return 0.0, 0.0, 0.0, 1.0
        if _LED_CURRENT_INDEX is not None:
            cache["assigned_color"][_LED_CURRENT_INDEX] = color
        return color
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
    cache = _get_mesh_cache(obj)
    if cache is not None:
        assigned = cache["assigned_uv"].get(_LED_CURRENT_INDEX)
        if assigned is not None:
            return assigned
        positions = cache["positions"]
        uvs = cache["uvs"]
        available = cache["available_uv_indices"]
        best_list_idx = None
        best_idx = None
        best_dist = 1e30
        if _LED_CURRENT_INDEX is not None:
            indices = available
        else:
            indices = range(len(positions))
        for list_idx, v_idx in enumerate(indices):
            world = positions[v_idx]
            dx = world[0] - pos[0]
            dy = world[1] - pos[1]
            dz = world[2] - pos[2]
            dist = dx * dx + dy * dy + dz * dz
            if dist < best_dist:
                best_dist = dist
                best_idx = v_idx
                best_list_idx = list_idx
        if best_idx is None:
            return 0.0, 0.0
        uv = uvs[best_idx]
        if uv is None:
            return 0.0, 0.0
        if _LED_CURRENT_INDEX is not None and best_list_idx is not None:
            available[best_list_idx] = available[-1]
            available.pop()
            cache["assigned_uv"][_LED_CURRENT_INDEX] = uv
        return uv
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
    obj: bpy.types.Object, pos: Tuple[float, float, float], consume: bool = True
) -> Tuple[Tuple[float, float], float]:
    if obj is None or obj.type != 'MESH':
        return (0.0, 0.0), 1e30
    mesh = obj.data
    if not mesh.vertices or not mesh.uv_layers:
        return (0.0, 0.0), 1e30
    cache = _get_mesh_cache(obj)
    if cache is not None:
        assigned = cache["assigned_uv_dist"].get(_LED_CURRENT_INDEX)
        if assigned is not None:
            return assigned
        positions = cache["positions"]
        uvs = cache["uvs"]
        available = cache["available_uv_indices"]
        best_list_idx = None
        best_idx = None
        best_dist = 1e30
        if _LED_CURRENT_INDEX is not None and consume:
            indices = available
        else:
            indices = range(len(positions))
        for list_idx, v_idx in enumerate(indices):
            world = positions[v_idx]
            dx = world[0] - pos[0]
            dy = world[1] - pos[1]
            dz = world[2] - pos[2]
            dist = dx * dx + dy * dy + dz * dz
            if dist < best_dist:
                best_dist = dist
                best_idx = v_idx
                best_list_idx = list_idx
        if best_idx is None:
            return (0.0, 0.0), 1e30
        uv = uvs[best_idx]
        if uv is None:
            return (0.0, 0.0), 1e30
        if _LED_CURRENT_INDEX is not None and consume and best_list_idx is not None:
            available[best_list_idx] = available[-1]
            available.pop()
            cache["assigned_uv"][_LED_CURRENT_INDEX] = uv
            cache["assigned_uv_dist"][_LED_CURRENT_INDEX] = (uv, best_dist)
        return uv, best_dist
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


def _collection_nearest_uv(
    collection_name: str,
    pos: Tuple[float, float, float],
    use_children: bool,
) -> Tuple[float, float]:
    collection_name = _collection_name(collection_name)
    candidates: List[bpy.types.Object] = []
    cached = _get_collection_cache(collection_name, use_children, build_mesh_cache=True)
    if cached is not None:
        for name in cached:
            obj = bpy.data.objects.get(name)
            if obj is not None and obj.type == 'MESH':
                candidates.append(obj)
    else:
        col = _get_collection(collection_name)
        if col is None:
            return 0.0, 0.0
        stack = [col]
        while stack:
            current = stack.pop()
            candidates.extend([obj for obj in current.objects if obj.type == 'MESH'])
            if use_children:
                stack.extend(list(current.children))
    best_uv = (0.0, 0.0)
    best_dist = 1e30
    best_obj: Optional[bpy.types.Object] = None
    for obj in candidates:
        uv, dist = _nearest_vertex_uv_with_dist(obj, pos, consume=False)
        if dist < best_dist:
            best_dist = dist
            best_uv = uv
            best_obj = obj
    if best_obj is not None:
        best_uv, best_dist = _nearest_vertex_uv_with_dist(best_obj, pos, consume=True)
    return best_uv


_FORMATION_BBOX_CACHE: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = {}


def _get_formation_bbox(cache_key: Optional[str] = None, static: bool = False):
    if static and cache_key:
        cached = _FORMATION_BBOX_CACHE.get(cache_key)
        if cached is not None:
            return cached
    bounds = _collection_world_bbox("Formation", use_children=True)
    if static and cache_key and bounds:
        _FORMATION_BBOX_CACHE[cache_key] = bounds
    return bounds


def _formation_bbox_uv(
    pos: Tuple[float, float, float],
    cache_key: Optional[str] = None,
    static: bool = False,
) -> Tuple[float, float]:
    bounds = _get_formation_bbox(cache_key, static)
    if not bounds:
        return 0.0, 0.0
    (min_x, min_y, min_z), (max_x, max_y, max_z) = bounds
    span_x = max(0.0001, max_x - min_x)
    span_z = max(0.0001, max_z - min_z)
    u = _clamp((pos[0] - min_x) / span_x, 0.0, 1.0)
    v = _clamp((pos[2] - min_z) / span_z, 0.0, 1.0)
    return u, v


def _formation_bbox_relpos(
    pos: Tuple[float, float, float],
    cache_key: Optional[str] = None,
    static: bool = False,
) -> Tuple[float, float, float]:
    bounds = _get_formation_bbox(cache_key, static)
    if not bounds:
        return 0.0, 0.0, 0.0
    (min_x, min_y, min_z), (max_x, max_y, max_z) = bounds
    span_x = max(0.0001, max_x - min_x)
    span_y = max(0.0001, max_y - min_y)
    span_z = max(0.0001, max_z - min_z)
    rel_x = _clamp((pos[0] - min_x) / span_x, 0.0, 1.0)
    rel_y = _clamp((pos[1] - min_y) / span_y, 0.0, 1.0)
    rel_z = _clamp((pos[2] - min_z) / span_z, 0.0, 1.0)
    return rel_x, rel_y, rel_z


_IMAGE_CACHE: Dict[int, Tuple[int, int, List[float]]] = {}

def _cache_static_image(image: Optional[bpy.types.Image]) -> None:
    if image is None:
        return
    source = getattr(image, "source", "")
    if source in {"MOVIE", "SEQUENCE", "VIEWER", "COMPOSITED"}:
        return
    width, height = image.size
    if width <= 0 or height <= 0:
        return
    key = int(image.as_pointer())
    cached = _IMAGE_CACHE.get(key)
    if cached is not None and cached[0] == width and cached[1] == height:
        return
    try:
        pixels = list(image.pixels)
    except Exception:
        return
    _IMAGE_CACHE[key] = (width, height, pixels)


def _prewarm_tree_images(tree: Optional[bpy.types.NodeTree]) -> None:
    if tree is None:
        return
    for node in getattr(tree, "nodes", []):
        image = getattr(node, "image", None)
        if isinstance(image, bpy.types.Image):
            _cache_static_image(image)


def _sample_image(image_name, uv: Tuple[float, float]) -> Tuple[float, float, float, float]:
    if not image_name:
        return 0.0, 0.0, 0.0, 1.0
    image = image_name if isinstance(image_name, bpy.types.Image) else bpy.data.images.get(image_name)
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
    pixels = None
    source = getattr(image, "source", "")
    if source not in {"MOVIE", "SEQUENCE", "VIEWER", "COMPOSITED"}:
        key = int(image.as_pointer())
        cached = _IMAGE_CACHE.get(key)
        if cached is not None and cached[0] == width and cached[1] == height:
            pixels = cached[2]
        else:
            try:
                pixels = list(image.pixels)
            except Exception:
                pixels = None
            if pixels is not None:
                _IMAGE_CACHE[key] = (width, height, pixels)
    if pixels is None:
        pixels = image.pixels
    if idx + 3 >= len(pixels):
        return 0.0, 0.0, 0.0, 1.0
    return float(pixels[idx]), float(pixels[idx + 1]), float(pixels[idx + 2]), float(pixels[idx + 3])


_VIDEO_CACHE: Dict[str, object] = {}


def _get_video_sampler(path: str):
    if not path:
        return None
    full_path = bpy.path.abspath(path)
    sampler = _VIDEO_CACHE.get(full_path)
    if sampler is not None:
        return sampler
    sampler = FrameSampler(
        path=full_path,
        cache_mode="lru",
        lru_max=64,
        resize_to=None,
        output_dtype=np.float32,
        store_rgba=True,
    )
    _VIDEO_CACHE[full_path] = sampler
    return sampler


def _sample_video(path: str, frame: float, u: float, v: float) -> Tuple[float, float, float, float]:
    sampler = _get_video_sampler(path)
    if sampler is None:
        return 0.0, 0.0, 0.0, 1.0
    rgba = sampler.sample_uv(int(frame), float(u), float(v))
    if hasattr(rgba, "__len__") and len(rgba) >= 4:
        return float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3])
    return 0.0, 0.0, 0.0, 1.0


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


def _entry_scale_duration(
    entry: Optional[Dict[str, List[Tuple[float, float]]]],
    speed: float,
) -> Dict[str, List[Tuple[float, float]]]:
    if not entry:
        return {}
    scale = float(speed)
    if scale <= 0.0:
        return {}
    result: Dict[str, List[Tuple[float, float]]] = {}
    for key, spans in entry.items():
        new_spans = []
        for start, end in spans:
            start = float(start)
            duration = max(0.0, float(end) - start)
            new_spans.append((start, start + duration * scale))
        result[key] = new_spans
    return result


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


def _entry_progress(
    entry: Optional[Dict[str, List[Tuple[float, float]]]],
    frame: float,
    mode: str = "LINEAR",
) -> float:
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
    return _apply_ease(best, mode)


def _entry_fade(
    entry: Optional[Dict[str, List[Tuple[float, float]]]],
    frame: float,
    duration: float,
    ease_mode: str = "LINEAR",
    fade_mode: str = "IN",
) -> float:
    if not entry:
        return 0.0
    fr = float(frame)
    dur = max(0.0, float(duration))
    fade_mode = (fade_mode or "IN").upper()
    best = 0.0
    for spans in entry.values():
        for start, end in spans:
            start_f = float(start)
            end_f = float(end)
            if end_f <= start_f:
                continue
            if fr < start_f or fr >= end_f:
                continue
            if dur <= 0.0:
                val = 1.0
            elif fade_mode == "OUT":
                fade_start = end_f - dur
                if fr <= fade_start:
                    val = 1.0
                else:
                    t = (fr - fade_start) / dur
                    val = 1.0 - _apply_ease(t, ease_mode)
            else:
                if fr >= start_f + dur:
                    in_val = 1.0
                else:
                    t = (fr - start_f) / dur
                    in_val = _apply_ease(t, ease_mode)
                if fade_mode == "IN_OUT":
                    fade_start = end_f - dur
                    if fr <= fade_start:
                        out_val = 1.0
                    else:
                        t = (fr - fade_start) / dur
                        out_val = 1.0 - _apply_ease(t, ease_mode)
                    val = min(in_val, out_val)
                else:
                    val = in_val
            if val > best:
                best = val
    return _clamp01(best)


def _entry_active_index(
    entry: Optional[Dict[str, List[Tuple[float, float]]]],
    frame: float,
) -> int:
    if not entry:
        return -1
    spans: List[Tuple[float, float]] = []
    for span_list in entry.values():
        for start, end in span_list:
            spans.append((float(start), float(end)))
    if not spans:
        return -1
    spans.sort(key=lambda item: (item[0], item[1]))
    fr = float(frame)
    active = -1
    for idx, (start, end) in enumerate(spans):
        if start <= fr < end:
            active = idx
    return active


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


def _output_seed(name: str) -> float:
    seed = 0
    for ch in name or "":
        seed = (seed * 131 + ord(ch)) % 100000
    return float(seed)


def compile_led_effect(tree: bpy.types.NodeTree) -> Optional[Callable]:
    outputs = _collect_outputs(tree)
    if not outputs:
        return None

    output_counts: Dict[int, int] = {}
    for output in outputs:
        priority = int(getattr(output, "priority", 0))
        output_counts[priority] = output_counts.get(priority, 0) + 1
    output_indices = {priority: 0 for priority in output_counts}

    lines: List[str] = []

    def emit_node(
        node: bpy.types.Node,
        target_lines: List[str],
        emitted_nodes: set[int],
        *,
        fallback_entry: Optional[str] = None,
        allow_entry_fallback: bool = True,
    ) -> None:
        if node.as_pointer() in emitted_nodes:
            return
        if not isinstance(node, LDLED_CodeNodeBase):
            return

        inputs: Dict[str, str] = {}
        allowed_inputs = None
        try:
            allowed_inputs = set(node.code_inputs())
        except Exception:
            allowed_inputs = None
        for sock in getattr(node, "inputs", []):
            if allowed_inputs is not None and sock.name not in allowed_inputs:
                continue
            inputs[sock.name] = resolve_input(
                sock,
                target_lines,
                emitted_nodes,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )

        output_vars = {
            sock.name: f"{node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(node, "outputs", [])
        }
        node._set_codegen_output_vars(output_vars)

        snippet = node.build_code(inputs) or ""
        for line in snippet.splitlines():
            target_lines.append(line)
        emitted_nodes.add(node.as_pointer())

    def resolve_input(
        socket: Optional[bpy.types.NodeSocket],
        target_lines: List[str],
        emitted_nodes: set[int],
        *,
        fallback_entry: Optional[str] = None,
        allow_entry_fallback: bool = True,
    ) -> str:
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
                emit_node(
                    from_node,
                    target_lines,
                    emitted_nodes,
                    fallback_entry=fallback_entry,
                    allow_entry_fallback=allow_entry_fallback,
                )
                if isinstance(from_node, LDLED_CodeNodeBase):
                    entry_vars.append(_get_output_var(from_node, from_socket))
            if not entry_vars:
                return "_entry_empty()"
            if len(entry_vars) == 1:
                return entry_vars[0]
            merge_var = f"_entry_merge_{len(target_lines)}"
            target_lines.append(f"{merge_var} = _entry_empty()")
            for entry_var in entry_vars:
                target_lines.append(f"{merge_var} = _entry_merge({merge_var}, {entry_var})")
            return merge_var
        if socket.is_linked and socket.links:
            link = socket.links[0]
            if not getattr(link, "is_valid", True):
                return _default_for_input(socket)
            from_node = link.from_node
            from_socket = link.from_socket
            emit_node(
                from_node,
                target_lines,
                emitted_nodes,
                fallback_entry=fallback_entry,
                allow_entry_fallback=allow_entry_fallback,
            )
            if isinstance(from_node, LDLED_CodeNodeBase):
                return _get_output_var(from_node, from_socket)
            return _default_for_socket(from_socket)
        if is_entry:
            if allow_entry_fallback and fallback_entry is not None:
                return fallback_entry
            return "_entry_empty()"
        return _default_for_input(socket)

    output_meta_blocks: Dict[str, List[str]] = {}
    output_color_blocks: Dict[str, List[str]] = {}

    for output in outputs:
        out_key = output.name
        meta_lines: List[str] = []
        meta_emitted: set[int] = set()
        entry_in = resolve_input(
            output.inputs.get("Entry"),
            meta_lines,
            meta_emitted,
            allow_entry_fallback=False,
        )
        intensity_in = resolve_input(
            output.inputs.get("Intensity"),
            meta_lines,
            meta_emitted,
            fallback_entry=entry_in,
        )
        alpha_in = resolve_input(
            output.inputs.get("Alpha"),
            meta_lines,
            meta_emitted,
            fallback_entry=entry_in,
        )
        meta_lines.append(f"_intensity = {intensity_in}")
        meta_lines.append(f"_alpha = {alpha_in}")
        meta_lines.append(f"_entry = {entry_in}")
        output_meta_blocks[out_key] = meta_lines

        color_lines: List[str] = []
        color_emitted: set[int] = set()
        color_in = resolve_input(
            output.inputs.get("Color"),
            color_lines,
            color_emitted,
            fallback_entry="_entry",
        )
        color_lines.append(f"_color = {color_in}")
        output_color_blocks[out_key] = color_lines

    lines.append("_output_items = []")

    for output in outputs:
        out_key = output.name
        priority = int(getattr(output, "priority", 0))
        group_index = output_indices[priority]
        group_size = output_counts[priority]
        output_indices[priority] = group_index + 1
        blend_mode = getattr(output, "blend_mode", "MIX") or "MIX"
        try:
            random_weight = float(getattr(output, "random", 0.0))
        except Exception:
            random_weight = 0.0
        random_weight = max(0.0, min(1.0, random_weight))
        seed = _output_seed(output.name)
        lines.append(
            "_output_items.append(({0}, {1}, {2}, {3}, {4}, {5}, {6}))"
            .format(
                priority,
                group_index,
                group_size,
                repr(random_weight),
                repr(blend_mode),
                repr(seed),
                repr(out_key),
            )
        )

    lines.append("_ordered_outputs = []")
    lines.append("for _prio, _group_idx, _group_size, _rand, _blend, _seed, _out_id in _output_items:")
    lines.append("    _order = _group_idx")
    lines.append("    if _rand > 0.0:")
    lines.append("        _roll = _rand01_static(idx, _seed)")
    lines.append("        if _roll < _rand:")
    lines.append("            _order = _rand01_static(idx, _seed + 1.0) * _group_size")
    lines.append("    _ordered_outputs.append((_prio, _order, _group_idx, _blend, _out_id))")
    lines.append("_ordered_outputs.sort(key=lambda item: (item[0], item[1], item[2]))")
    lines.append("_meta = {}")
    lines.append("_max_opaque_prio = None")
    lines.append("for _prio, _order, _group_idx, _blend, _out_id in _ordered_outputs:")
    first = True
    for out_key, meta_lines in output_meta_blocks.items():
        keyword = "if" if first else "elif"
        lines.append(f"    {keyword} _out_id == {out_key!r}:")
        for line in meta_lines:
            lines.append(f"        {line}")
        first = False
    lines.append("    else:")
    lines.append("        _intensity = 0.0")
    lines.append("        _alpha = 0.0")
    lines.append("        _entry = _entry_empty()")
    lines.append("    _entry_count = _entry_active_count(_entry, frame)")
    lines.append("    if _entry_is_empty(_entry):")
    lines.append("        _entry_count = 1")
    lines.append("    _meta[_out_id] = (_intensity, _alpha, _entry, _entry_count)")
    lines.append("    if _blend == \"MIX\" and _entry_count > 0 and _intensity >= 1.0 and _alpha >= 1.0:")
    lines.append("        if _max_opaque_prio is None or _prio > _max_opaque_prio:")
    lines.append("            _max_opaque_prio = _prio")

    lines.append("for _prio, _order, _group_idx, _blend, _out_id in _ordered_outputs:")
    lines.append("    if _max_opaque_prio is not None and _prio < _max_opaque_prio:")
    lines.append("        continue")
    lines.append("    _meta_vals = _meta.get(_out_id)")
    lines.append("    if _meta_vals is None:")
    lines.append("        continue")
    lines.append("    _intensity, _alpha, _entry, _entry_count = _meta_vals")
    lines.append("    if _entry_count <= 0 or _intensity <= 0.0 or _alpha <= 0.0:")
    lines.append("        continue")
    first = True
    for out_key, color_lines in output_color_blocks.items():
        keyword = "if" if first else "elif"
        lines.append(f"    {keyword} _out_id == {out_key!r}:")
        for line in color_lines:
            lines.append(f"        {line}")
        first = False
    lines.append("    else:")
    lines.append("        _color = (0.0, 0.0, 0.0, 1.0)")
    lines.append("    _src_alpha = _clamp01(_alpha * (_color[3] if len(_color) > 3 else 1.0))")
    lines.append("    if _src_alpha <= 0.0:")
    lines.append("        continue")
    lines.append("    _src_color = [_color[0] * _intensity, _color[1] * _intensity, _color[2] * _intensity, 1.0]")
    lines.append("    for _ in range(int(_entry_count)):")
    lines.append("        color = _blend_over(color, _src_color, _src_alpha, _blend)")

    body = ["def _led_effect(idx, pos, frame):", "    color = [0.0, 0.0, 0.0, 1.0]"]
    body.extend([f"    {line}" for line in lines])
    body.append("    return color")

    code = "\n".join(body)
    env = {
        "_clamp": _clamp,
        "_clamp01": _clamp01,
        "_loop_factor": _loop_factor,
        "_alpha_over": _alpha_over,
        "_blend_over": _blend_over,
        "_rand01": _rand01,
        "_rand01_static": _rand01_static,
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
        "_formation_bbox_relpos": _formation_bbox_relpos,
        "_sample_image": _sample_image,
        "_sample_video": _sample_video,
        "_color_ramp_eval": _color_ramp_eval,
        "_cat_cache_write": _cat_cache_write,
        "_cat_cache_read": _cat_cache_read,
        "_entry_empty": _entry_empty,
        "_rand01_static": _rand01_static,
        "_entry_is_empty": _entry_is_empty,
        "_entry_merge": _entry_merge,
        "_entry_from_range": _entry_from_range,
        "_entry_from_marker": _entry_from_marker,
        "_entry_from_formation": _entry_from_formation,
        "_entry_shift": _entry_shift,
        "_entry_scale_duration": _entry_scale_duration,
        "_entry_loop": _entry_loop,
        "_entry_active_count": _entry_active_count,
        "_entry_progress": _entry_progress,
        "_entry_fade": _entry_fade,
        "_entry_active_index": _entry_active_index,
        "bpy": bpy,
        "math": math,
        "mathutils": mathutils,
    }
    exec(code, env)
    _prewarm_tree_images(tree)
    return env["_led_effect"]


def compile_led_socket(
    tree: bpy.types.NodeTree,
    node: bpy.types.Node,
    socket_name: str,
    *,
    force_inputs: bool = False,
) -> Optional[Callable]:
    if tree is None or node is None or not socket_name:
        return None
    _prewarm_tree_images(tree)
    socket = node.inputs.get(socket_name) if hasattr(node, "inputs") else None
    if socket is None:
        return None

    lines: List[str] = []
    emitted: set[int] = set()

    def emit_node(
        dep_node: bpy.types.Node,
        target_lines: List[str],
        emitted_nodes: set[int],
    ) -> None:
        if dep_node.as_pointer() in emitted_nodes:
            return
        if not isinstance(dep_node, LDLED_CodeNodeBase):
            return

        inputs: Dict[str, str] = {}
        allowed_inputs = None
        if not force_inputs:
            try:
                allowed_inputs = set(dep_node.code_inputs())
            except Exception:
                allowed_inputs = None
        for sock in getattr(dep_node, "inputs", []):
            if allowed_inputs is not None and sock.name not in allowed_inputs:
                continue
            inputs[sock.name] = resolve_input(sock, target_lines, emitted_nodes)

        output_vars = {
            sock.name: f"{dep_node.codegen_id()}_{_sanitize_identifier(sock.name)}"
            for sock in getattr(dep_node, "outputs", [])
        }
        dep_node._set_codegen_output_vars(output_vars)

        snippet = dep_node.build_code(inputs) or ""
        for line in snippet.splitlines():
            target_lines.append(line)
        emitted_nodes.add(dep_node.as_pointer())

    def resolve_input(
        dep_socket: Optional[bpy.types.NodeSocket],
        target_lines: List[str],
        emitted_nodes: set[int],
    ) -> str:
        if dep_socket is None:
            return "0.0"
        is_entry = getattr(dep_socket, "bl_idname", "") == "LDLEDEntrySocket"
        if is_entry and dep_socket.is_linked and dep_socket.links:
            entry_vars: List[str] = []
            for link in dep_socket.links:
                if not getattr(link, "is_valid", True):
                    continue
                from_node = link.from_node
                from_socket = link.from_socket
                emit_node(from_node, target_lines, emitted_nodes)
                if isinstance(from_node, LDLED_CodeNodeBase):
                    entry_vars.append(_get_output_var(from_node, from_socket))
            if not entry_vars:
                return "_entry_empty()"
            if len(entry_vars) == 1:
                return entry_vars[0]
            merge_var = f"_entry_merge_{len(target_lines)}"
            target_lines.append(f"{merge_var} = _entry_empty()")
            for entry_var in entry_vars:
                target_lines.append(f"{merge_var} = _entry_merge({merge_var}, {entry_var})")
            return merge_var
        if dep_socket.is_linked and dep_socket.links:
            link = dep_socket.links[0]
            if not getattr(link, "is_valid", True):
                return _default_for_input(dep_socket)
            from_node = link.from_node
            from_socket = link.from_socket
            emit_node(from_node, target_lines, emitted_nodes)
            if isinstance(from_node, LDLED_CodeNodeBase):
                return _get_output_var(from_node, from_socket)
            return _default_for_socket(from_socket)
        if is_entry:
            return "_entry_empty()"
        return _default_for_input(dep_socket)

    value_expr = resolve_input(socket, lines, emitted)
    lines.append(f"_value = {value_expr}")

    body = ["def _led_socket(idx, pos, frame):"]
    body.extend([f"    {line}" for line in lines])
    body.append("    return _value")

    code = "\n".join(body)
    env = {
        "_clamp": _clamp,
        "_clamp01": _clamp01,
        "_loop_factor": _loop_factor,
        "_alpha_over": _alpha_over,
        "_blend_over": _blend_over,
        "_rand01": _rand01,
        "_rand01_static": _rand01_static,
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
        "_formation_bbox_relpos": _formation_bbox_relpos,
        "_sample_image": _sample_image,
        "_sample_video": _sample_video,
        "_color_ramp_eval": _color_ramp_eval,
        "_cat_cache_write": _cat_cache_write,
        "_cat_cache_read": _cat_cache_read,
        "_entry_empty": _entry_empty,
        "_entry_is_empty": _entry_is_empty,
        "_entry_merge": _entry_merge,
        "_entry_from_range": _entry_from_range,
        "_entry_from_marker": _entry_from_marker,
        "_entry_from_formation": _entry_from_formation,
        "_entry_shift": _entry_shift,
        "_entry_scale_duration": _entry_scale_duration,
        "_entry_loop": _entry_loop,
        "_entry_active_count": _entry_active_count,
        "_entry_progress": _entry_progress,
        "_entry_fade": _entry_fade,
        "_entry_active_index": _entry_active_index,
        "bpy": bpy,
        "math": math,
        "mathutils": mathutils,
    }
    exec(code, env)
    return env["_led_socket"]


def get_output_activity(tree: bpy.types.NodeTree, frame: float) -> Dict[str, bool]:
    outputs = _collect_outputs(tree)
    if not outputs:
        return {}

    emitted: set[int] = set()
    lines: List[str] = []

    def emit_node(node: bpy.types.Node) -> None:
        if node.as_pointer() in emitted:
            return
        if not isinstance(node, LDLED_CodeNodeBase):
            return

        inputs: Dict[str, str] = {}
        allowed_inputs = None
        try:
            allowed_inputs = set(node.code_inputs())
        except Exception:
            allowed_inputs = None
        for sock in getattr(node, "inputs", []):
            if allowed_inputs is not None and sock.name not in allowed_inputs:
                continue
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
        entry_in = resolve_input(output.inputs.get("Entry"))
        out_id = _sanitize_identifier(output.name)
        lines.append(f"_entry_{out_id} = {entry_in}")
        lines.append(f"_entry_count_{out_id} = _entry_active_count(_entry_{out_id}, frame)")
        lines.append(f"if _entry_is_empty(_entry_{out_id}):")
        lines.append(f"    _entry_count_{out_id} = 1")
        lines.append(f"result[{output.name!r}] = int(_entry_count_{out_id})")

    body = ["def _led_output_activity(frame):", "    result = {}"]
    body.extend([f"    {line}" for line in lines])
    body.append("    return result")

    code = "\n".join(body)
    env = {
        "_entry_empty": _entry_empty,
        "_entry_is_empty": _entry_is_empty,
        "_entry_merge": _entry_merge,
        "_entry_from_range": _entry_from_range,
        "_entry_from_marker": _entry_from_marker,
        "_entry_from_formation": _entry_from_formation,
        "_entry_shift": _entry_shift,
        "_entry_scale_duration": _entry_scale_duration,
        "_entry_loop": _entry_loop,
        "_entry_active_count": _entry_active_count,
        "_entry_progress": _entry_progress,
        "_entry_fade": _entry_fade,
        "_entry_active_index": _entry_active_index,
        "bpy": bpy,
        "math": math,
        "mathutils": mathutils,
    }
    exec(code, env)
    counts = env["_led_output_activity"](float(frame))
    return {name: bool(count) for name, count in counts.items()}


_TREE_CACHE: Dict[int, Tuple[Callable, Any]] = {}


def _to_hashable(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bpy.types.ID):
        return value.name
    if isinstance(value, (list, tuple, mathutils.Vector, mathutils.Color)):
        return tuple(_to_hashable(v) for v in value)
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        try:
            return tuple(_to_hashable(v) for v in value)
        except Exception:
            return repr(value)
    return repr(value)


def _node_signature(node: bpy.types.Node):
    props = []
    for prop in node.bl_rna.properties:
        ident = prop.identifier
        if ident == "rna_type":
            continue
        try:
            val = getattr(node, ident)
        except Exception:
            continue
        props.append((ident, _to_hashable(val)))
    inputs = []
    for sock in getattr(node, "inputs", []):
        try:
            val = sock.default_value if hasattr(sock, "default_value") else None
        except Exception:
            val = None
        inputs.append((sock.name, getattr(sock, "bl_idname", ""), _to_hashable(val)))
    return (node.bl_idname, node.name, node.label, tuple(props), tuple(inputs))


def _tree_signature(tree: bpy.types.NodeTree):
    nodes = sorted(getattr(tree, "nodes", []), key=lambda n: n.name)
    links = []
    for link in getattr(tree, "links", []):
        if not getattr(link, "is_valid", True):
            continue
        from_node = getattr(link, "from_node", None)
        to_node = getattr(link, "to_node", None)
        from_socket = getattr(link, "from_socket", None)
        to_socket = getattr(link, "to_socket", None)
        if not (from_node and to_node and from_socket and to_socket):
            continue
        links.append((from_node.name, from_socket.name, to_node.name, to_socket.name))
    links.sort()
    return (tuple(_node_signature(n) for n in nodes), tuple(links))


def get_compiled_effect(tree: bpy.types.NodeTree) -> Optional[Callable]:
    key = tree.as_pointer()
    sig = _tree_signature(tree)
    cached = _TREE_CACHE.get(key)
    if cached and cached[1] == sig:
        return cached[0]
    compiled = compile_led_effect(tree)
    if compiled is not None:
        _TREE_CACHE[key] = (compiled, sig)
    return compiled


def get_active_tree(scene: bpy.types.Scene) -> Optional[bpy.types.NodeTree]:
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", "") == "LD_LedEffectsTree":
            return tree
    return None
