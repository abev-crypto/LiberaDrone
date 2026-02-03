import os

import bpy
import numpy as np

from liberadronecore.util import image_util


# Settings
HEIGHT = 500
WIDTH = 1
COLORSPACE = "Non-Color"  # Use "sRGB" if you want to test color-managed output.
OUTPUT_PATH = ""  # Set to an explicit path to override.
LOAD_IMAGE = True


def _default_output_path() -> str:
    scene = getattr(bpy.context, "scene", None)
    path = image_util.scene_cache_path("CAT_Test_500", "PNG", scene=scene, create=True)
    if path:
        return path
    base_dir = bpy.path.abspath("//")
    if not base_dir:
        base_dir = os.path.expanduser("~")
    return os.path.join(base_dir, "CAT_Test_500.png")


def _id_to_color(idx: int) -> tuple[float, float, float, float]:
    r = (idx & 0xFF) / 255.0
    g = ((idx >> 8) & 0xFF) / 255.0
    b = ((idx >> 16) & 0xFF) / 255.0
    return r, g, b, 1.0


def main() -> None:
    height = max(1, int(HEIGHT))
    width = max(1, int(WIDTH))
    data = np.zeros((height, width, 4), dtype=np.float32)
    for y in range(height):
        data[y, :, :] = _id_to_color(y)

    path = OUTPUT_PATH or _default_output_path()
    ok = image_util.write_png_rgba(path, data, colorspace=COLORSPACE)
    if not ok:
        raise RuntimeError(f"Failed to write PNG: {path}")
    print(f"[CAT Test] Wrote {path} ({width}x{height}) colorspace={COLORSPACE}")

    if LOAD_IMAGE:
        abs_path = bpy.path.abspath(path)
        img = bpy.data.images.load(abs_path, check_existing=True)
        if COLORSPACE:
            try:
                img.colorspace_settings.name = COLORSPACE
            except Exception:
                pass
        print(f"[CAT Test] Loaded image: {img.name}")


if __name__ == "__main__":
    main()
