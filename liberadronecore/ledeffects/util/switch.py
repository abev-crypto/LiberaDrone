from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from liberadronecore.ledeffects.runtime_registry import register_runtime_function


def _entry_spans(entry) -> List[Tuple[float, float]]:
    spans: List[Tuple[float, float]] = []
    if not entry:
        return spans
    for span_list in entry.values():
        for start, end in span_list:
            spans.append((float(start), float(end)))
    spans.sort(key=lambda item: (item[0], item[1]))
    return spans


def _entry_active_span(spans: List[Tuple[float, float]], frame: float) -> Optional[Tuple[float, float]]:
    fr = float(frame)
    for start, end in spans:
        if start <= fr < end:
            return start, end
    return None


def _clamp01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


@register_runtime_function
def _switch_eval_fade(
    entry,
    frame: float,
    step_frames: int,
    count: int,
    fade_mode: str = "NONE",
    fade_frames: float = 0.0,
) -> Tuple[int, float]:
    count_val = max(1, int(count))
    spans = _entry_spans(entry)
    if not spans:
        return 0, 0.0
    span = _entry_active_span(spans, frame)
    if span is None:
        last_start, last_end = spans[-1]
        if float(frame) >= float(last_end):
            active_elapsed = sum(end - start for start, end in spans)
            hold_after = True
        else:
            return 0, 0.0
    else:
        active_elapsed = 0.0
        for start, end in spans:
            if span[0] == start and span[1] == end:
                active_elapsed += float(frame) - float(start)
                break
            active_elapsed += float(end) - float(start)
        hold_after = False

    step = max(1.0, float(step_frames))
    idx_cur = int(active_elapsed / step) % count_val
    local = active_elapsed - (float(int(active_elapsed / step)) * step)
    if hold_after:
        return idx_cur, 1.0

    mode = (fade_mode or "NONE").upper()
    fade = max(0.0, float(fade_frames))
    if fade <= 0.0 or mode == "NONE":
        return idx_cur, 1.0

    fade = min(fade, step)
    fade_in = 1.0
    fade_out = 1.0
    if mode in {"IN", "IN_OUT"} and local <= fade:
        fade_in = local / fade if fade > 0.0 else 1.0
    if mode in {"OUT", "IN_OUT"} and local >= (step - fade):
        fade_out = (step - local) / fade if fade > 0.0 else 1.0
    fade_val = _clamp01(min(fade_in, fade_out))
    return idx_cur, fade_val
