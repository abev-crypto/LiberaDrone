from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import bpy
import math
import mathutils
from liberadronecore.formation import fn_parse_pairing
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp


_LED_FRAME_CACHE: Dict[str, Any] = {"frame": None, "mesh": {}, "collection": {}, "collection_ids": {}, "bbox": {}}
_LED_CURRENT_INDEX: Optional[int] = None
_FORMATION_BBOX_CACHE: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = {}


def begin_led_frame_cache(frame: float, positions: List[Tuple[float, float, float]]) -> None:
    _LED_FRAME_CACHE["frame"] = float(frame)
    _LED_FRAME_CACHE["mesh"] = {}
    _LED_FRAME_CACHE["collection"] = {}
    _LED_FRAME_CACHE["collection_ids"] = {}
    _LED_FRAME_CACHE["bbox"] = {}


def end_led_frame_cache() -> None:
    _LED_FRAME_CACHE["frame"] = None
    _LED_FRAME_CACHE["mesh"] = {}
    _LED_FRAME_CACHE["collection"] = {}
    _LED_FRAME_CACHE["collection_ids"] = {}
    _LED_FRAME_CACHE["bbox"] = {}


def set_led_runtime_index(idx: Optional[int]) -> None:
    global _LED_CURRENT_INDEX
    _LED_CURRENT_INDEX = None if idx is None else int(idx)


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
def _distance_to_mesh_bbox(obj_name: str, pos: Tuple[float, float, float]) -> float:
    obj = _get_object(obj_name)
    bounds = _object_world_bbox(obj)
    if not bounds:
        return 0.0
    return _distance_to_bbox(pos, bounds)


@register_runtime_function
def _point_in_mesh_bbox(obj_name: str, pos: Tuple[float, float, float]) -> bool:
    obj = _get_object(obj_name)
    bounds = _object_world_bbox(obj)
    if not bounds:
        return False
    return _point_in_bbox(pos, bounds)


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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


def _get_formation_bbox(cache_key: Optional[str] = None, static: bool = False):
    if static and cache_key:
        cached = _FORMATION_BBOX_CACHE.get(cache_key)
        if cached is not None:
            return cached
    bounds = _collection_world_bbox("Formation", use_children=True)
    if static and cache_key and bounds:
        _FORMATION_BBOX_CACHE[cache_key] = bounds
    return bounds


@register_runtime_function
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


@register_runtime_function
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


def _mesh_formation_ids(mesh: Optional[bpy.types.Mesh]) -> List[int]:
    if mesh is None:
        return []
    attr = mesh.attributes.get(fn_parse_pairing.FORMATION_ATTR_NAME)
    if (
        attr is None
        or attr.domain != 'POINT'
        or attr.data_type != 'INT'
        or len(attr.data) != len(mesh.vertices)
    ):
        attr = mesh.attributes.get(fn_parse_pairing.FORMATION_ID_ATTR)
    if (
        attr is None
        or attr.domain != 'POINT'
        or attr.data_type != 'INT'
        or len(attr.data) != len(mesh.vertices)
    ):
        return list(range(len(mesh.vertices)))

    values = [0] * len(mesh.vertices)
    attr.data.foreach_get("value", values)
    return values


@register_runtime_function
def _collection_formation_ids(
    collection_name: str,
    use_children: bool = True,
) -> set[int]:
    collection_name = _collection_name(collection_name)
    if not collection_name:
        return set()
    key = (collection_name, bool(use_children))
    if _LED_FRAME_CACHE.get("frame") is not None:
        cached = _LED_FRAME_CACHE["collection_ids"].get(key)
        if cached is not None:
            return cached

    ids: set[int] = set()
    names = _get_collection_cache(collection_name, use_children, build_mesh_cache=False)
    if names is not None:
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj is None or obj.type != 'MESH':
                continue
            ids.update(_mesh_formation_ids(obj.data))
    else:
        col = _get_collection(collection_name)
        if col is None:
            if _LED_FRAME_CACHE.get("frame") is not None:
                _LED_FRAME_CACHE["collection_ids"][key] = ids
            return ids
        stack = [col]
        while stack:
            current = stack.pop()
            for obj in current.objects:
                if obj.type != 'MESH':
                    continue
                ids.update(_mesh_formation_ids(obj.data))
            if use_children:
                stack.extend(list(current.children))

    if _LED_FRAME_CACHE.get("frame") is not None:
        _LED_FRAME_CACHE["collection_ids"][key] = ids
    return ids


class LDLEDMeshInfoNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Expose a mesh object for LED sampling."""

    bl_idname = "LDLEDMeshInfoNode"
    bl_label = "Mesh Info"
    bl_icon = "MESH_DATA"

    target_object: bpy.props.PointerProperty(
        name="Mesh",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("NodeSocketObject", "Mesh")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target_object")

    def build_code(self, inputs):
        out_mesh = self.output_var("Mesh")
        obj_name = self.target_object.name if self.target_object else ""
        return f"{out_mesh} = bpy.data.objects.get({obj_name!r}) if {obj_name!r} else None"
