from __future__ import annotations

from typing import Dict, Tuple

import bpy
import numpy as np
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.system.video.cvcache import FrameSampler


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


@register_runtime_function
def _sample_video(path: str, frame: float, u: float, v: float, loop: bool = False) -> Tuple[float, float, float, float]:
    sampler = _get_video_sampler(path)
    if sampler is None:
        return 0.0, 0.0, 0.0, 1.0
    try:
        frame_count = int(getattr(sampler, "frame_count", 0))
    except Exception:
        frame_count = 0
    frame_idx = int(frame)
    if frame_count > 0:
        if loop:
            frame_idx = frame_idx % frame_count
        else:
            frame_idx = max(0, min(frame_idx, frame_count - 1))
    else:
        frame_idx = max(0, frame_idx)
    if isinstance(u, np.ndarray) or isinstance(v, np.ndarray):
        frame_img = sampler.get_frame(frame_idx)
        if frame_img is None:
            return 0.0, 0.0, 0.0, 1.0
        height, width = frame_img.shape[0], frame_img.shape[1]
        u = np.clip(u, 0.0, 1.0)
        v = np.clip(v, 0.0, 1.0)
        x = (u * (width - 1)).astype(np.int64)
        y = (v * (height - 1)).astype(np.int64)
        return frame_img[y, x]

    rgba = sampler.sample_uv(frame_idx, float(u), float(v))
    if hasattr(rgba, "__len__") and len(rgba) >= 4:
        return float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3])
    return 0.0, 0.0, 0.0, 1.0


class LDLEDVideoSamplerNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Sample a video frame (uses image data for now) based on entry progress."""

    bl_idname = "LDLEDVideoSamplerNode"
    bl_label = "Video Sampler"
    bl_icon = "SEQUENCE"

    filepath: bpy.props.StringProperty(
        name="Video",
        subtype='FILE_PATH',
        default="",
        options={'LIBRARY_EDITABLE'},
    )

    loop: bpy.props.BoolProperty(
        name="Loop",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "U")
        self.inputs.new("NodeSocketFloat", "V")
        start_offset = self.inputs.new("NodeSocketInt", "Start Offset")
        speed = self.inputs.new("NodeSocketFloat", "Speed")
        start_offset.default_value = 0
        speed.default_value = 1.0
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "filepath")
        layout.prop(self, "loop")

    def build_code(self, inputs):
        u = inputs.get("U", "0.0")
        v = inputs.get("V", "0.0")
        start_offset = inputs.get("Start Offset", "0.0")
        speed = inputs.get("Speed", "1.0")
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Color")
        video_path = bpy.path.abspath(self.filepath) if self.filepath else ""
        vid_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_progress_{vid_id} = _entry_progress({entry}, frame)",
                f"_frame_{vid_id} = ({start_offset}) + (frame * ({speed}))",
                f"{out_var} = _sample_video({video_path!r}, _frame_{vid_id}, {u}, {v}, {bool(self.loop)!r}) if _progress_{vid_id} > 0.0 else (0.0, 0.0, 0.0, 1.0)",
            ]
        )
