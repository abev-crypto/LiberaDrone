import bpy
import math
from typing import Dict, List, Optional, Sequence, Tuple

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp01
from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.ledeffects.nodes.util import le_particlebase


_CHAIN_CACHE: Dict[str, Dict[str, object]] = {}
_NEIGHBOR_COUNT = 8


def _seed_from_key(key: str) -> int:
    seed = 0
    for ch in str(key or ""):
        seed = (seed * 131 + ord(ch)) & 0xFFFFFFFF
    return seed or 1


def _rand01(state: Dict[str, object]) -> float:
    value = int(state.get("rng", 1))
    value = (value * 1664525 + 1013904223) & 0xFFFFFFFF
    state["rng"] = value
    return value / 4294967296.0


def _entry_active_span(entry, frame: float) -> Optional[Tuple[int, float, float]]:
    if not entry:
        return None
    spans: List[Tuple[float, float]] = []
    for span_list in entry.values():
        for start, end in span_list:
            spans.append((float(start), float(end)))
    if not spans:
        return None
    spans.sort(key=lambda item: (item[0], item[1]))
    fr = float(frame)
    for idx, (start, end) in enumerate(spans):
        if start <= fr < end:
            return idx, start, end
    return None


def _direction_vector(angle: float) -> Tuple[float, float]:
    rad = math.radians(float(angle))
    return math.cos(rad), math.sin(rad)


def _pick_neighbor(
    positions: List[Tuple[float, float, float]],
    current_idx: int,
    prev_idx: int,
    state: Dict[str, object],
    move_mode: str,
    angle: float,
    center: Tuple[float, float, float],
    allowed_indices: Sequence[int],
    neighbor_map: Optional[Sequence[Sequence[int]]] = None,
) -> int:
    count = len(positions)
    if count <= 1:
        return current_idx
    if current_idx < 0 or current_idx >= count:
        return current_idx
    if not allowed_indices:
        return current_idx
    cx, cy, cz = positions[current_idx]
    if neighbor_map is not None and current_idx < len(neighbor_map):
        top = [idx for idx in neighbor_map[current_idx] if idx != prev_idx]
        if not top:
            return current_idx
    else:
        dists: List[Tuple[float, int, float, float, float]] = []
        for idx in allowed_indices:
            if idx < 0 or idx >= count:
                continue
            pos = positions[idx]
            if idx == current_idx or idx == prev_idx:
                continue
            dx = pos[0] - cx
            dy = pos[1] - cy
            dz = pos[2] - cz
            dists.append((dx * dx + dy * dy + dz * dz, idx, dx, dy, dz))
        if not dists:
            return current_idx
        dists.sort(key=lambda item: item[0])
        top = [item[1] for item in dists[: min(_NEIGHBOR_COUNT, len(dists))]]

    mode = (move_mode or "RANDOM").upper()
    if mode == "DIRECTION":
        dir_x, dir_y = _direction_vector(angle)
        best_idx = None
        best_dot = -1.0e9
        for idx in top:
            dx = positions[idx][0] - cx
            dy = positions[idx][1] - cy
            length = math.hypot(dx, dy)
            if length <= 1e-6:
                continue
            dot = (dx * dir_x + dy * dir_y) / length
            if dot > best_dot:
                best_dot = dot
                best_idx = idx
        if best_idx is not None:
            return best_idx
    elif mode in {"RADIAL", "SPIRAL"}:
        rx = cx - center[0]
        ry = cy - center[1]
        rlen = math.hypot(rx, ry)
        if rlen > 1e-6:
            rx /= rlen
            ry /= rlen
            if mode == "SPIRAL":
                rx, ry = -ry, rx
            best_idx = None
            best_dot = -1.0e9
            for idx in top:
                dx = positions[idx][0] - cx
                dy = positions[idx][1] - cy
                length = math.hypot(dx, dy)
                if length <= 1e-6:
                    continue
                dot = (dx * rx + dy * ry) / length
                if dot > best_dot:
                    best_dot = dot
                    best_idx = idx
            if best_idx is not None:
                return best_idx

    pick = int(_rand01(state) * len(top))
    return top[pick]


def _init_chain_state(key: str, count: int) -> Dict[str, object]:
    return {
        "frame": None,
        "count": int(count),
        "values": [0.0] * int(count),
        "particles": [],
        "spawn_acc": 0.0,
        "spawned_spans": set(),
        "route_sig": None,
        "rng": _seed_from_key(key),
    }


def _spawn_particle(
    state: Dict[str, object],
    positions: List[Tuple[float, float, float]],
    life_frames: int,
    frame: int,
    speed_frames: int,
    allowed_indices: Sequence[int],
) -> None:
    count = len(positions)
    if count <= 0:
        return
    if allowed_indices:
        idx = allowed_indices[int(_rand01(state) * len(allowed_indices))]
    else:
        return
    particles = state.get("particles", [])
    particles.append(
        {
            "idx": idx,
            "prev": -1,
            "next_move": int(frame) + int(speed_frames),
            "life": int(life_frames),
        }
    )
    state["particles"] = particles
    values = state.get("values", [])
    if 0 <= idx < len(values):
        values[idx] = 1.0


def _advance_chain_state(
    state: Dict[str, object],
    positions: List[Tuple[float, float, float]],
    frame: int,
    entry,
    mode: str,
    spawn: float,
    speed: float,
    decay: float,
    move_mode: str,
    angle: float,
    allowed_indices: Sequence[int],
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
    decay_val = max(0.0, float(decay))
    current_frame = int(frame)
    last_frame = state.get("frame")
    if last_frame is None:
        last_frame = current_frame - 1
    if current_frame - int(last_frame) > 1000:
        state.update(_init_chain_state(state.get("key", ""), count))
        last_frame = current_frame - 1
    if allowed_indices:
        cx = sum(positions[idx][0] for idx in allowed_indices) / len(allowed_indices)
        cy = sum(positions[idx][1] for idx in allowed_indices) / len(allowed_indices)
        cz = sum(positions[idx][2] for idx in allowed_indices) / len(allowed_indices)
    else:
        cx = sum(pos[0] for pos in positions) / count
        cy = sum(pos[1] for pos in positions) / count
        cz = sum(pos[2] for pos in positions) / count
    center = (cx, cy, cz)
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

        active_span = _entry_active_span(entry, step_frame)
        if active_span is None:
            state["spawn_acc"] = 0.0
        else:
            span_idx, start, end = active_span
            life_frames = max(1, int(round(end - start)))
            if (mode or "SINGLE").upper() == "SINGLE":
                spawned = state.get("spawned_spans", set())
                if span_idx not in spawned:
                    spawn_count = max(0, int(round(float(spawn))))
                    for _ in range(spawn_count):
                        _spawn_particle(state, positions, life_frames, step_frame, speed_frames, allowed_indices)
                    spawned.add(span_idx)
                    state["spawned_spans"] = spawned
            else:
                rate = max(0.0, float(spawn))
                acc = float(state.get("spawn_acc", 0.0))
                if rate > 0.0 and fps > 0.0:
                    acc += rate / fps
                elif rate <= 0.0:
                    acc = 0.0
                while acc >= 1.0:
                    _spawn_particle(state, positions, life_frames, step_frame, speed_frames, allowed_indices)
                    acc -= 1.0
                state["spawn_acc"] = acc

        particles = state.get("particles", [])
        new_particles = []
        for particle in particles:
            life = int(particle.get("life", 0)) - 1
            if life <= 0:
                continue
            idx = int(particle.get("idx", 0))
            prev = int(particle.get("prev", -1))
            next_move = int(particle.get("next_move", step_frame))
            if step_frame >= next_move:
                new_idx = _pick_neighbor(
                    positions,
                    idx,
                    prev,
                    state,
                    move_mode,
                    angle,
                    center,
                    allowed_indices,
                    neighbor_map,
                )
                if new_idx != idx:
                    prev = idx
                    idx = new_idx
                next_move = step_frame + speed_frames
            new_particles.append(
                {
                    "idx": idx,
                    "prev": prev,
                    "next_move": next_move,
                    "life": life,
                }
            )
        state["particles"] = new_particles
        values = state.get("values", [])
        active = {int(p["idx"]) for p in new_particles}
        for idx in active:
            if 0 <= idx < len(values) and (not mask_enabled or (allowed_set and idx in allowed_set)):
                values[idx] = 1.0
        state["values"] = values

    state["frame"] = current_frame


@register_runtime_function
def _chain_mask(
    key: str,
    idx: int,
    frame: float,
    entry,
    mode: str,
    spawn: float,
    speed: float,
    decay: float,
    move_mode: str,
    angle: float,
    allowed_ids: Sequence[int],
) -> float:
    positions = le_meshinfo._LED_FRAME_CACHE.get("positions") or []
    count = len(positions)
    if count <= 0:
        return 0.0
    if not isinstance(allowed_ids, (list, tuple, set)):
        allowed_ids = []
    allowed_ids = list(allowed_ids)
    cache_key = str(key or "")
    route_sig = (tuple(allowed_ids),)
    state = _CHAIN_CACHE.get(cache_key)
    if (
        state is None
        or int(state.get("count", -1)) != count
        or frame < float(state.get("frame") or -1)
        or state.get("route_sig") != route_sig
    ):
        state = _init_chain_state(cache_key, count)
        state["key"] = cache_key
        state["route_sig"] = route_sig
        _CHAIN_CACHE[cache_key] = state
    frame_i = int(frame)
    prep_frame = state.get("prep_frame")
    prep_sig = state.get("prep_sig")
    if prep_frame != frame_i or prep_sig != route_sig:
        mapping = le_particlebase._formation_id_map()
        if allowed_ids:
            allowed_indices = le_particlebase._map_allowed_indices(allowed_ids, count, mapping)
            mask_enabled = True
        else:
            allowed_indices = list(range(count))
            mask_enabled = False
        allowed_set = set(allowed_indices) if mask_enabled else None
        state["prep_frame"] = frame_i
        state["prep_sig"] = route_sig
        state["prep_allowed_indices"] = allowed_indices
        state["prep_allowed_set"] = allowed_set
        state["prep_mask_enabled"] = mask_enabled
    else:
        allowed_indices = state.get("prep_allowed_indices") or list(range(count))
        allowed_set = state.get("prep_allowed_set")
        mask_enabled = bool(state.get("prep_mask_enabled"))
    if int(state.get("frame") or -1) != frame_i:
        _advance_chain_state(
            state,
            positions,
            frame_i,
            entry,
            mode,
            spawn,
            speed,
            decay,
            move_mode,
            angle,
            allowed_indices,
            mask_enabled,
            allowed_set,
        )
    values = state.get("values", [])
    if idx < 0 or idx >= len(values):
        return 0.0
    if mask_enabled and (not allowed_set or idx not in allowed_set):
        return 0.0
    return _clamp01(float(values[idx]))


class LDLEDChainNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Spawn-and-hop chain mask."""

    NODE_CATEGORY_ID = "LD_LED_SIMULATE"
    NODE_CATEGORY_LABEL = "Simulate"

    bl_idname = "LDLEDChainNode"
    bl_label = "Chain"
    bl_icon = "MOD_PARTICLES"

    mode_items = [
        ("SINGLE", "Single", "Spawn once on entry start"),
        ("CONSTANT", "Constant", "Spawn continuously while entry is active"),
    ]

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="SINGLE",
        options={'LIBRARY_EDITABLE'},
    )
    move_items = [
        ("RANDOM", "Random", "Pick a random nearby target"),
        ("DIRECTION", "Direction", "Move toward the given angle"),
        ("SPIRAL", "Spiral", "Swirl around the formation center"),
        ("RADIAL", "Radial", "Move outward from the formation center"),
    ]
    move_mode: bpy.props.EnumProperty(
        name="Move",
        items=move_items,
        default="RANDOM",
        options={'LIBRARY_EDITABLE'},
    )
    seed: bpy.props.IntProperty(
        name="Seed",
        default=0,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDIDSocket", "IDs")
        self.inputs.new("LDLEDEntrySocket", "Entry")
        spawn = self.inputs.new("NodeSocketFloat", "Spawn")
        spawn.default_value = 1.0
        speed = self.inputs.new("NodeSocketFloat", "Speed")
        speed.default_value = 5.0
        decay = self.inputs.new("NodeSocketFloat", "Decay")
        decay.default_value = 0.1
        angle = self.inputs.new("NodeSocketFloat", "Angle")
        angle.default_value = 0.0
        self.outputs.new("NodeSocketFloat", "Mask")

    def draw_buttons(self, context, layout):
        layout.label(text="Spawn/Speed are per second")
        layout.prop(self, "mode", text="")
        layout.prop(self, "move_mode", text="")
        layout.prop(self, "seed")

    def build_code(self, inputs):
        ids = inputs.get("IDs", "None")
        entry = inputs.get("Entry", "_entry_empty()")
        spawn = inputs.get("Spawn", "1.0")
        speed = inputs.get("Speed", "1.0")
        decay = inputs.get("Decay", "0.0")
        angle = inputs.get("Angle", "0.0")
        out_var = self.output_var("Mask")
        cache_key = f"{self.name}_{int(self.seed)}"
        return (
            f"{out_var} = _chain_mask({cache_key!r}, idx, frame, {entry}, "
            f"{self.mode!r}, {spawn}, {speed}, {decay}, {self.move_mode!r}, {angle}, {ids})"
        )
