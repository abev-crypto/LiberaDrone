from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _apply_ease, _clamp01
from liberadronecore.formation import fn_parse


@register_runtime_function
def _entry_empty() -> Dict[str, List[Tuple[float, float]]]:
    return {}


@register_runtime_function
def _entry_is_empty(entry: Optional[Dict[str, List[Tuple[float, float]]]]) -> bool:
    return not entry


@register_runtime_function
def _entry_merge(
    left: Optional[Dict[str, List[Tuple[float, float]]]],
    right: Optional[Dict[str, List[Tuple[float, float]]]],
) -> Dict[str, List[Tuple[float, float]]]:
    merged: Dict[str, List[Tuple[float, float]]] = {}
    for source in (left or {}, right or {}):
        for key, spans in source.items():
            merged.setdefault(key, []).extend(list(spans))
    return merged


@register_runtime_function
def _entry_from_range(key: str, start: float, duration: float) -> Dict[str, List[Tuple[float, float]]]:
    dur = max(0.0, float(duration))
    if dur <= 0.0:
        return {}
    return {key: [(float(start), float(start) + dur)]}


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


@register_runtime_function
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


class LDLEDFrameEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Entry active between start and duration frames."""

    bl_idname = "LDLEDFrameEntryNode"
    bl_label = "Frame Entry"
    bl_icon = "TIME"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "Start")
        self.inputs.new("NodeSocketFloat", "Duration")
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def build_code(self, inputs):
        out_var = self.output_var("Entry")
        entry_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        start_val = inputs.get("Start", "0.0")
        duration_val = inputs.get("Duration", "0.0")
        return f"{out_var} = _entry_from_range({entry_key!r}, {start_val}, {duration_val})"
