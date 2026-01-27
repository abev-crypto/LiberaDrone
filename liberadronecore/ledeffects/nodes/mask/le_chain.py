import bpy
import math
from typing import Dict, List, Optional, Tuple

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp01
from liberadronecore.ledeffects.nodes.util import le_meshinfo


_CHAIN_CACHE: Dict[str, Dict[str, object]] = {}
_NEIGHBOR_COUNT = 8


def _chain_fps() -> float:
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
) -> int:
    count = len(positions)
    if count <= 1:
        return current_idx
    if current_idx < 0 or current_idx >= count:
        return current_idx
    cx, cy, cz = positions[current_idx]
    dists: List[Tuple[float, int, float, float, float]] = []
    for idx, pos in enumerate(positions):
        if idx == current_idx or idx == prev_idx:
            continue
        dx = pos[0] - cx
        dy = pos[1] - cy
        dz = pos[2] - cz
        dists.append((dx * dx + dy * dy + dz * dz, idx, dx, dy, dz))
    if not dists:
        return current_idx
    dists.sort(key=lambda item: item[0])
    top = dists[: min(_NEIGHBOR_COUNT, len(dists))]

    mode = (move_mode or "RANDOM").upper()
    if mode == "DIRECTION":
        dir_x, dir_y = _direction_vector(angle)
        best_idx = None
        best_dot = -1.0e9
        for _dist, idx, dx, dy, _dz in top:
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
            for _dist, idx, dx, dy, _dz in top:
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
    return top[pick][1]


def _init_chain_state(key: str, count: int) -> Dict[str, object]:
    return {
        "frame": None,
        "count": int(count),
        "values": [0.0] * int(count),
        "particles": [],
        "spawn_acc": 0.0,
        "spawned_spans": set(),
        "rng": _seed_from_key(key),
    }


def _spawn_particle(
    state: Dict[str, object],
    positions: List[Tuple[float, float, float]],
    life_frames: int,
    frame: int,
    speed_frames: int,
) -> None:
    count = len(positions)
    if count <= 0:
        return
    idx = int(_rand01(state) * count)
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
) -> None:
    count = len(positions)
    if count <= 0:
        return
    speed_frames = max(1, int(round(float(speed))))
    decay_val = max(0.0, float(decay))
    current_frame = int(frame)
    last_frame = state.get("frame")
    if last_frame is None:
        last_frame = current_frame - 1
    if current_frame - int(last_frame) > 1000:
        state.update(_init_chain_state(state.get("key", ""), count))
        last_frame = current_frame - 1
    cx = sum(pos[0] for pos in positions) / count
    cy = sum(pos[1] for pos in positions) / count
    cz = sum(pos[2] for pos in positions) / count
    center = (cx, cy, cz)

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
                        _spawn_particle(state, positions, life_frames, step_frame, speed_frames)
                    spawned.add(span_idx)
                    state["spawned_spans"] = spawned
            else:
                fps = _chain_fps()
                rate = max(0.0, float(spawn))
                acc = float(state.get("spawn_acc", 0.0))
                acc += rate / fps if fps > 0.0 else 0.0
                while acc >= 1.0:
                    _spawn_particle(state, positions, life_frames, step_frame, speed_frames)
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
            if 0 <= idx < len(values):
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
) -> float:
    positions = le_meshinfo._LED_FRAME_CACHE.get("positions") or []
    count = len(positions)
    if count <= 0:
        return 0.0
    cache_key = str(key or "")
    state = _CHAIN_CACHE.get(cache_key)
    if state is None or int(state.get("count", -1)) != count or frame < float(state.get("frame") or -1):
        state = _init_chain_state(cache_key, count)
        state["key"] = cache_key
        _CHAIN_CACHE[cache_key] = state
    if int(state.get("frame") or -1) != int(frame):
        _advance_chain_state(
            state,
            positions,
            int(frame),
            entry,
            mode,
            spawn,
            speed,
            decay,
            move_mode,
            angle,
        )
    values = state.get("values", [])
    if idx < 0 or idx >= len(values):
        return 0.0
    return _clamp01(float(values[idx]))


class LDLEDChainNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Spawn-and-hop chain mask."""

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

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
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
        layout.prop(self, "mode", text="")
        layout.prop(self, "move_mode", text="")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        spawn = inputs.get("Spawn", "1.0")
        speed = inputs.get("Speed", "1.0")
        decay = inputs.get("Decay", "0.0")
        angle = inputs.get("Angle", "0.0")
        out_var = self.output_var("Mask")
        cache_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return (
            f"{out_var} = _chain_mask({cache_key!r}, idx, frame, {entry}, "
            f"{self.mode!r}, {spawn}, {speed}, {decay}, {self.move_mode!r}, {angle})"
        )
