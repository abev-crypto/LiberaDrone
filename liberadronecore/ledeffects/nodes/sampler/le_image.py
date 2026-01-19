from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp


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


@register_runtime_function
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


class LDLEDImageSamplerNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Sample a Blender image by UV."""

    bl_idname = "LDLEDImageSamplerNode"
    bl_label = "Image Sampler"
    bl_icon = "IMAGE_DATA"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        image = self.inputs.new("NodeSocketImage", "Image")
        self.inputs.new("NodeSocketFloat", "U")
        self.inputs.new("NodeSocketFloat", "V")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        image_socket = self.inputs.get("Image")
        row = layout.row()
        row.enabled = not (image_socket and image_socket.is_linked)
        row.prop(self, "image")

    def build_code(self, inputs):
        u = inputs.get("U", "0.0")
        v = inputs.get("V", "0.0")
        out_var = self.output_var("Color")
        image_val = inputs.get("Image", "None")
        return f"{out_var} = _sample_image({image_val}, ({u}, {v}))"
