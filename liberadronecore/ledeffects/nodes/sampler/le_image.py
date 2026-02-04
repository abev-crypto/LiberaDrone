from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.ledeffects.nodes.util.le_math import _clamp


_IMAGE_CACHE: Dict[int, Tuple[int, int, List[float]]] = {}
_IMAGE_NAME_CACHE: Dict[str, bpy.types.Image] = {}


def _cache_static_image(image: Optional[bpy.types.Image]) -> None:
    if image is None:
        raise ValueError("Image cache requires a valid image")
    source = getattr(image, "source", "")
    if source in {"MOVIE", "SEQUENCE", "VIEWER", "COMPOSITED"}:
        return
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("Image has invalid size")
    key = int(image.as_pointer())
    cached = _IMAGE_CACHE.get(key)
    if cached is not None and cached[0] == width and cached[1] == height:
        return
    pixels = list(image.pixels)
    _IMAGE_CACHE[key] = (width, height, pixels)
    _IMAGE_NAME_CACHE[image.name] = image


def _prewarm_tree_images(tree: Optional[bpy.types.NodeTree]) -> None:
    for node in tree.nodes:
        if not hasattr(node, "image"):
            continue
        image = node.image
        if isinstance(image, bpy.types.Image):
            _cache_static_image(image)


def _get_image_pixels(image: bpy.types.Image) -> Tuple[int, int, List[float]]:
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("Image has invalid size")
    pixels = None
    source = getattr(image, "source", "")
    if source not in {"MOVIE", "SEQUENCE", "VIEWER", "COMPOSITED"}:
        key = int(image.as_pointer())
        cached = _IMAGE_CACHE.get(key)
        if cached is not None and cached[0] == width and cached[1] == height:
            pixels = cached[2]
        else:
            pixels = list(image.pixels)
            _IMAGE_CACHE[key] = (width, height, pixels)
    if pixels is None:
        pixels = image.pixels
    return width, height, pixels


@register_runtime_function
def _get_image_cached(image_name):
    name = image_name if isinstance(image_name, str) else str(image_name)
    cached = _IMAGE_NAME_CACHE.get(name)
    if cached is not None and cached.name == name:
        return cached
    image = bpy.data.images[name]
    _IMAGE_NAME_CACHE[name] = image
    return image


@register_runtime_function
def _sample_image(image_name, uv: Tuple[float, float]) -> Tuple[float, float, float, float]:
    image = image_name if isinstance(image_name, bpy.types.Image) else _get_image_cached(image_name)
    width, height, pixels = _get_image_pixels(image)
    u = _clamp(float(uv[0]), 0.0, 1.0)
    v = _clamp(float(uv[1]), 0.0, 1.0)
    x = int(u * (width - 1))
    y = int(v * (height - 1))
    idx = (y * width + x) * 4
    return float(pixels[idx]), float(pixels[idx + 1]), float(pixels[idx + 2]), float(pixels[idx + 3])


@register_runtime_function
def _sample_image_index(
    image_name,
    x_idx: int,
    y_idx: int,
) -> Tuple[float, float, float, float]:
    image = image_name if isinstance(image_name, bpy.types.Image) else _get_image_cached(image_name)
    width, height, pixels = _get_image_pixels(image)
    x = int(x_idx)
    y = int(y_idx)
    idx = (y * width + x) * 4
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
        if image_socket is not None:
            row.template_ID(image_socket, "default_value", open="image.open")

    def build_code(self, inputs):
        u = inputs.get("U", "0.0")
        v = inputs.get("V", "0.0")
        out_var = self.output_var("Color")
        image_val = inputs.get("Image", "None")
        return f"{out_var} = _sample_image({image_val}, ({u}, {v}))"
