import bpy
from typing import Dict, List, Optional, Sequence, Tuple

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp01
from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.ledeffects.nodes.util import le_particlebase


_TRAIL_CACHE: Dict[str, Dict[str, object]] = {}
_NEIGHBOR_COUNT = 8


def _map_transit_ids(
    transit_ids: Sequence[int],
    count: int,
    mapping: Dict[int, int],
) -> List[int]:
    mapped: List[int] = []
    for value in transit_ids:
        idx = le_particlebase._resolve_runtime_index(value, count, mapping)
        if idx is None:
            continue
        mapped.append(idx)
    return mapped


def _pick_trail_neighbor(
    positions: List[Tuple[float, float, float]],
    current_idx: int,
    target_idx: int,
    allowed_indices: Sequence[int],
    neighbor_map: Optional[Sequence[Sequence[int]]] = None,
) -> int:
    if current_idx == target_idx:
        return current_idx
    count = len(positions)
    if count <= 1:
        return current_idx
    if current_idx < 0 or current_idx >= count:
        return current_idx
    if target_idx < 0 or target_idx >= count:
        return current_idx
    cx, cy, cz = positions[current_idx]
    tx, ty, tz = positions[target_idx]
    if neighbor_map is not None and current_idx < len(neighbor_map):
        top = list(neighbor_map[current_idx])
        if not top:
            return current_idx
    else:
        dists: List[Tuple[float, int]] = []
        for idx in allowed_indices:
            if idx == current_idx:
                continue
            if idx < 0 or idx >= count:
                continue
            px, py, pz = positions[idx]
            dx = px - cx
            dy = py - cy
            dz = pz - cz
            dists.append((dx * dx + dy * dy + dz * dz, idx))
        if not dists:
            return current_idx
        dists.sort(key=lambda item: item[0])
        top = [item[1] for item in dists[: min(_NEIGHBOR_COUNT, len(dists))]]
    best_idx = None
    best_dist = None
    for idx in top:
        px, py, pz = positions[idx]
        dx = px - tx
        dy = py - ty
        dz = pz - tz
        tdist = dx * dx + dy * dy + dz * dz
        if best_dist is None or tdist < best_dist:
            best_dist = tdist
            best_idx = idx
    return current_idx if best_idx is None else best_idx


def _init_trail_state(key: str, count: int) -> Dict[str, object]:
    return {
        "frame": None,
        "count": int(count),
        "values": [0.0] * int(count),
        "particles": [],
        "spawn_acc": 0.0,
        "route_sig": None,
        "key": key,
    }


def _spawn_trail_particle(
    state: Dict[str, object],
    start_idx: Optional[int],
    targets: Sequence[int],
    frame: int,
    speed_frames: int,
) -> None:
    if start_idx is None:
        return
    particle = {
        "idx": int(start_idx),
        "route_index": 0,
        "targets": list(targets),
        "next_move": int(frame) + int(speed_frames),
    }
    particles = state.get("particles", [])
    particles.append(particle)
    state["particles"] = particles
    values = state.get("values", [])
    if 0 <= start_idx < len(values):
        values[start_idx] = 1.0


def _advance_trail_state(
    state: Dict[str, object],
    positions: List[Tuple[float, float, float]],
    frame: int,
    start_idx: Optional[int],
    spawn: float,
    speed: float,
    decay: float,
    allowed_indices: Sequence[int],
    targets: Sequence[int],
    mask_enabled: bool,
    allowed_set: Optional[set[int]],
) -> None:
    count = len(positions)
    if count <= 0:
        return
    fps = le_particlebase._particle_fps()
    speed_rate = max(0.0, float(speed))
    if speed_rate > 0.0:
        speed_frames = max(1, int(round(fps / speed_rate)))
    else:
        speed_frames = max(1, int(round(fps)))
    spawn_rate = max(0.0, float(spawn))
    decay_val = max(0.0, float(decay))
    current_frame = int(frame)
    last_frame = state.get("frame")
    if last_frame is None:
        last_frame = current_frame - 1
    if current_frame - int(last_frame) > 1000:
        state.update(_init_trail_state(state.get("key", ""), count))
        last_frame = current_frame - 1
    allowed_count = len(allowed_indices)
    particle_count = len(state.get("particles", []))
    move_rate = max(1, int(speed_frames))
    expected_moves = particle_count / float(move_rate) if move_rate > 0 else float(particle_count)
    neighbor_map = None
    if allowed_count and (allowed_count <= 96 or expected_moves >= allowed_count):
        neighbor_map = le_particlebase._neighbor_map(
            state,
            positions,
            allowed_indices,
            _NEIGHBOR_COUNT,
            frame=current_frame,
        )
    for step_frame in range(int(last_frame) + 1, current_frame + 1):
        if decay_val > 0.0:
            values = state.get("values", [])
            for idx in range(len(values)):
                if values[idx] > 0.0:
                    values[idx] = max(0.0, values[idx] - decay_val)

        acc = float(state.get("spawn_acc", 0.0))
        if spawn_rate > 0.0 and fps > 0.0:
            acc += spawn_rate / fps
        elif spawn_rate <= 0.0:
            acc = 0.0
        while acc >= 1.0:
            if not mask_enabled or (start_idx is not None and allowed_set and start_idx in allowed_set):
                _spawn_trail_particle(state, start_idx, targets, step_frame, speed_frames)
            acc -= 1.0
        state["spawn_acc"] = acc

        particles = state.get("particles", [])
        new_particles = []
        active = set()
        for particle in particles:
            idx = int(particle.get("idx", -1))
            if idx < 0 or idx >= count:
                continue
            route_index = int(particle.get("route_index", 0))
            particle_targets = particle.get("targets", targets)
            if not isinstance(particle_targets, list):
                particle_targets = list(particle_targets) if particle_targets is not None else []
            next_move = int(particle.get("next_move", step_frame))

            target_idx = None
            while route_index < len(particle_targets):
                target = particle_targets[route_index]
                if target is None or target < 0 or target >= count:
                    route_index += 1
                    continue
                target_idx = int(target)
                break

            if target_idx is not None and idx == target_idx:
                route_index += 1
                target_idx = None
                while route_index < len(particle_targets):
                    target = particle_targets[route_index]
                    if target is None or target < 0 or target >= count:
                        route_index += 1
                        continue
                    target_idx = int(target)
                    break

            if target_idx is not None and step_frame >= next_move:
                idx = _pick_trail_neighbor(positions, idx, target_idx, allowed_indices, neighbor_map)
                next_move = step_frame + speed_frames
                if idx == target_idx:
                    route_index += 1
                    target_idx = None
                    while route_index < len(particle_targets):
                        target = particle_targets[route_index]
                        if target is None or target < 0 or target >= count:
                            route_index += 1
                            continue
                        target_idx = int(target)
                        break

            active.add(idx)

            if route_index < len(particle_targets) or target_idx is not None:
                new_particles.append(
                    {
                        "idx": idx,
                        "route_index": route_index,
                        "targets": particle_targets,
                        "next_move": next_move,
                    }
                )

        state["particles"] = new_particles
        values = state.get("values", [])
        for idx in active:
            if 0 <= idx < len(values) and (not mask_enabled or (allowed_set and idx in allowed_set)):
                values[idx] = 1.0
        state["values"] = values

    state["frame"] = current_frame


@register_runtime_function
def _trail_mask(
    key: str,
    idx: int,
    frame: float,
    start_id: float,
    spawn: float,
    speed: float,
    decay: float,
    allowed_ids: Sequence[int],
    transit_ids: Sequence[int],
    cycle: bool,
) -> float:
    positions = le_meshinfo._LED_FRAME_CACHE.get("positions") or []
    count = len(positions)
    if count <= 0:
        return 0.0
    if not isinstance(allowed_ids, (list, tuple, set)):
        allowed_ids = []
    allowed_ids = list(allowed_ids)
    cache_key = str(key or "")
    route_sig = (tuple(allowed_ids), tuple(transit_ids or ()), bool(cycle))
    state = _TRAIL_CACHE.get(cache_key)
    if (
        state is None
        or int(state.get("count", -1)) != count
        or frame < float(state.get("frame") or -1)
        or state.get("route_sig") != route_sig
    ):
        state = _init_trail_state(cache_key, count)
        state["route_sig"] = route_sig
        _TRAIL_CACHE[cache_key] = state

    frame_i = int(frame)
    prep_frame = state.get("prep_frame")
    prep_sig = state.get("prep_sig")
    if prep_frame != frame_i or prep_sig != route_sig:
        mapping = le_particlebase._formation_id_map()
        start_idx = le_particlebase._resolve_runtime_index(start_id, count, mapping)
        transit_indices = _map_transit_ids(transit_ids, count, mapping)
        if allowed_ids:
            allowed_indices = le_particlebase._map_allowed_indices(allowed_ids, count, mapping)
            mask_enabled = True
        else:
            allowed_indices = list(range(count))
            mask_enabled = False
        allowed_set = set(allowed_indices) if mask_enabled else None
        if mask_enabled:
            if allowed_set:
                transit_indices = [idx for idx in transit_indices if idx in allowed_set]
                if cycle and start_idx is not None and start_idx in allowed_set:
                    transit_indices = list(transit_indices) + [start_idx]
            else:
                transit_indices = []
        elif cycle and start_idx is not None:
            transit_indices = list(transit_indices) + [start_idx]
        state["prep_frame"] = frame_i
        state["prep_sig"] = route_sig
        state["prep_start_idx"] = start_idx
        state["prep_transit_indices"] = transit_indices
        state["prep_allowed_indices"] = allowed_indices
        state["prep_allowed_set"] = allowed_set
        state["prep_mask_enabled"] = mask_enabled
    else:
        start_idx = state.get("prep_start_idx")
        transit_indices = state.get("prep_transit_indices") or []
        allowed_indices = state.get("prep_allowed_indices") or list(range(count))
        allowed_set = state.get("prep_allowed_set")
        mask_enabled = bool(state.get("prep_mask_enabled"))

    if int(state.get("frame") or -1) != frame_i:
        _advance_trail_state(
            state,
            positions,
            frame_i,
            start_idx,
            spawn,
            speed,
            decay,
            allowed_indices,
            transit_indices,
            mask_enabled,
            allowed_set,
        )
    values = state.get("values", [])
    if idx < 0 or idx >= len(values):
        return 0.0
    if mask_enabled and (not allowed_set or idx not in allowed_set):
        return 0.0
    return _clamp01(float(values[idx]))


def _parse_ids(text: str, *, allow_duplicates: bool) -> List[int]:
    if not text:
        return []
    values: List[int] = []
    seen: set[int] = set()
    for part in text.replace(",", " ").replace(";", " ").split():
        try:
            val = int(part)
        except (TypeError, ValueError):
            continue
        if val < 0:
            continue
        if not allow_duplicates:
            if val in seen:
                continue
            seen.add(val)
        values.append(val)
    return values


class LDLEDTrailNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Spawn and move a particle along formation IDs."""

    NODE_CATEGORY_ID = "LD_LED_SIMULATE"
    NODE_CATEGORY_LABEL = "Simulate"

    bl_idname = "LDLEDTrailNode"
    bl_label = "Trail"
    bl_icon = "TRACKING"

    start_id: bpy.props.IntProperty(
        name="Start",
        default=-1,
        min=-1,
        options={'HIDDEN', 'LIBRARY_EDITABLE'},
    )
    transit_ids: bpy.props.StringProperty(
        name="Transit",
        default="",
        options={'HIDDEN', 'LIBRARY_EDITABLE'},
    )
    cycle: bpy.props.BoolProperty(
        name="Cycle",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDIDSocket", "IDs")
        spawn = self.inputs.new("NodeSocketFloat", "Spawn")
        spawn.default_value = 1.0
        speed = self.inputs.new("NodeSocketFloat", "Speed")
        speed.default_value = 5.0
        decay = self.inputs.new("NodeSocketFloat", "Decay")
        decay.default_value = 0.1
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        layout.label(text="Spawn/Speed are per second")
        start_label = "-" if int(self.start_id) < 0 else str(int(self.start_id))
        transit_list = _parse_ids(self.transit_ids, allow_duplicates=True)
        transit_label = ", ".join(str(i) for i in transit_list) if transit_list else "-"
        layout.label(text=f"Start: {start_label}")
        layout.label(text=f"Transit: {transit_label}")
        row = layout.row(align=True)
        op = row.operator("ldled.trail_set_start", text="Set Start")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        op = row.operator("ldled.trail_set_transit", text="Set Transit")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name
        layout.prop(self, "cycle")

    def build_code(self, inputs):
        ids = inputs.get("IDs", "None")
        spawn = inputs.get("Spawn", "1.0")
        speed = inputs.get("Speed", "1.0")
        decay = inputs.get("Decay", "0.0")
        out_var = self.output_var("Mask")
        cache_key = f"{self.name}"
        transit_ids = _parse_ids(self.transit_ids, allow_duplicates=True)
        return (
            f"{out_var} = _trail_mask({cache_key!r}, idx, frame, {int(self.start_id)}, {spawn}, "
            f"{speed}, {decay}, {ids}, {transit_ids!r}, {bool(self.cycle)!r})"
        )
