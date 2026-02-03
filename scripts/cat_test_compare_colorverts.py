import os

import bpy

from liberadronecore.ledeffects.nodes.sampler import le_image


# Settings
IMAGE_NAME_OR_PATH = ""  # Set to image name in Blender or an absolute path.
U_VALUE = 0.0
TOL = 1e-4
MAX_REPORT = 20
DECODE_ID = True


def _get_image():
    if IMAGE_NAME_OR_PATH:
        if os.path.isfile(IMAGE_NAME_OR_PATH):
            return bpy.data.images.load(IMAGE_NAME_OR_PATH, check_existing=True)
        img = bpy.data.images.get(IMAGE_NAME_OR_PATH)
        if img is not None:
            return img

    for img in bpy.data.images:
        try:
            if img.name.startswith("CAT_Test_500"):
                return img
            path = bpy.path.abspath(img.filepath)
            if path and path.lower().endswith("cat_test_500.png"):
                return img
        except Exception:
            continue
    return None


def _read_colorverts():
    obj = bpy.data.objects.get("ColorVerts")
    if obj is None or obj.type != "MESH":
        return None
    mesh = obj.data
    attr = None
    if hasattr(mesh, "color_attributes"):
        attr = mesh.color_attributes.get("color")
    if attr is None and hasattr(mesh, "attributes"):
        attr = mesh.attributes.get("color")
    if attr is None or len(attr.data) != len(mesh.vertices):
        return None
    flat = [0.0] * (len(attr.data) * 4)
    try:
        attr.data.foreach_get("color", flat)
    except Exception:
        return None
    return [tuple(flat[i:i + 4]) for i in range(0, len(flat), 4)]


def _sample_row(img, row_idx: int) -> tuple[float, float, float, float]:
    height = img.size[1]
    if height <= 1:
        v = 0.0
    else:
        v = float(row_idx) / float(height - 1)
    return le_image._sample_image(img, (float(U_VALUE), v))


def _color_to_id(color) -> int:
    r = int(round(float(color[0]) * 255.0)) if len(color) > 0 else 0
    g = int(round(float(color[1]) * 255.0)) if len(color) > 1 else 0
    b = int(round(float(color[2]) * 255.0)) if len(color) > 2 else 0
    return (r & 0xFF) | ((g & 0xFF) << 8) | ((b & 0xFF) << 16)


def main() -> None:
    img = _get_image()
    if img is None:
        raise RuntimeError("Test image not found. Set IMAGE_NAME_OR_PATH.")

    colors = _read_colorverts()
    if colors is None:
        raise RuntimeError("ColorVerts not available or color attribute mismatch.")

    height = int(img.size[1])
    compare_count = min(len(colors), height)
    mismatches = []

    for idx in range(compare_count):
        expected = _sample_row(img, idx)
        actual = colors[idx]
        delta = max(abs(actual[i] - expected[i]) for i in range(4))
        if delta > TOL:
            mismatches.append((idx, actual, expected, delta))

    print(
        f"[CAT Test] ColorVerts={len(colors)} image_height={height} "
        f"compared={compare_count} mismatches={len(mismatches)}"
    )

    if mismatches:
        for idx, actual, expected, delta in mismatches[:MAX_REPORT]:
            if DECODE_ID:
                actual_id = _color_to_id(actual)
                expected_id = _color_to_id(expected)
                print(
                    f"[CAT Test] idx={idx} actual_id={actual_id} expected_id={expected_id} "
                    f"delta={delta:.6f}"
                )
            else:
                print(
                    f"[CAT Test] idx={idx} actual={actual} expected={expected} delta={delta:.6f}"
                )


if __name__ == "__main__":
    main()
