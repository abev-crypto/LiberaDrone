import os

import bpy
import numpy as np



def create_image(name: str, width: int, height: int, fb: bool):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    return bpy.data.images.new(name=name, width=width, height=height, float_buffer=fb)


def sanitize_filename(name: str) -> str:
    safe = []
    for ch in name or "":
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch in {"_", "-"}:
            safe.append(ch)
        else:
            safe.append("_")
    result = "".join(safe).strip("_")
    return result or "image"

def get_scene_cache_dir(scene=None, *, create: bool = True) -> str | None:
    filepath = getattr(bpy.data, "filepath", "")
    if not filepath:
        return None
    dirpath = os.path.dirname(filepath)
    if not dirpath:
        return None
    blend_name = os.path.splitext(os.path.basename(filepath))[0]
    base_name = sanitize_filename(blend_name) or "Scene"
    cache_dir = os.path.join(dirpath, f"{base_name}_Cache")
    if create:
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            return None
    return cache_dir


def file_format_extension(file_format: str) -> str:
    fmt = (file_format or "").upper()
    if fmt in {"OPEN_EXR", "EXR"}:
        return ".exr"
    if fmt == "PNG":
        return ".png"
    return ".png"


def scene_cache_path(name: str, file_format: str, scene=None, *, create: bool = True) -> str | None:
    cache_dir = get_scene_cache_dir(scene, create=create)
    if not cache_dir:
        return None
    filename = sanitize_filename(name)
    return os.path.join(cache_dir, f"{filename}{file_format_extension(file_format)}")


def _apply_image_format(
    image,
    file_format: str,
    *,
    use_float: bool | None = None,
    colorspace: str | None = None,
) -> None:
    if image is None:
        return
    fmt = (file_format or "").upper()
    if fmt:
        image.file_format = fmt
    if colorspace:
        image.colorspace_settings.name = colorspace
    #if use_float and fmt in {"OPEN_EXR", "EXR"}:
    #    image.use_half_precision = False
    #    image.use_generated_float = True


def set_image_pixels(image, pixels) -> None:
    if image is None or pixels is None:
        return
    flat = pixels
    try:
        flat = np.asarray(pixels, dtype=np.float32).ravel()
    except Exception:
        pass
    image.pixels.foreach_set(flat)
    image.update()


def _image_pixels_to_rgba(image) -> np.ndarray | None:
    if image is None:
        return None
    width, height = image.size
    if width <= 0 or height <= 0:
        return None
    channels = getattr(image, "channels", 4) or 4
    expected = width * height * channels
    try:
        flat = np.asarray(image.pixels, dtype=np.float32)
    except Exception:
        return None
    if flat.size < expected:
        return None
    flat = flat[:expected]
    data = flat.reshape((height, width, channels))
    if channels > 4:
        data = data[:, :, :4]
    elif channels == 3:
        alpha = np.ones((height, width, 1), dtype=np.float32)
        data = np.concatenate([data, alpha], axis=2)
    return data


def save_image(image, filepath, file_format, *, use_float: bool | None = None, colorspace: str | None = None):
    #_apply_image_format(image, file_format, use_float=use_float, colorspace=colorspace)
    image.filepath_raw = filepath
    image.save()


def link_image_to_file(
    image,
    filepath,
    file_format,
    *,
    use_float: bool | None = None,
    colorspace: str | None = None,
):
    """Save ``image`` to ``filepath`` and keep it linked to the file."""

    save_image(image, filepath, file_format, use_float=use_float, colorspace=colorspace)
    image.filepath = filepath
    image.source = 'FILE'
    image.reload()

def default_image_extension(image):
    name = image.name.upper()
    file_format = getattr(image, "file_format", "").upper()
    if "P" in name or file_format == "OPEN_EXR":
        return ".exr"
    if file_format == "PNG":
        return ".png"
    return ".png"

def format_bounds_suffix(pos_min, pos_max):
    def _fmt(value: float) -> str:
        return (f"{value:.3f}").rstrip("0").rstrip(".")

    return (
        f"S_{_fmt(pos_min[0])}_{_fmt(pos_min[1])}_{_fmt(pos_min[2])}_"
        f"E_{_fmt(pos_max[0])}_{_fmt(pos_max[1])}_{_fmt(pos_max[2])}"
    )


def save_image_to_scene_cache(
    image,
    name: str,
    file_format: str,
    *,
    scene=None,
    use_float: bool | None = None,
    colorspace: str | None = None,
    link: bool = True,
) -> str | None:
    path = scene_cache_path(name, file_format, scene, create=True)
    if not path:
        return None
    fmt = (file_format or "").upper()
    if fmt in {"OPEN_EXR", "EXR"}:
        pixels = _image_pixels_to_rgba(image)
        if pixels is None or not write_exr_rgba(path, pixels):
            raise RuntimeError(f"Failed to write EXR: {path}")
        if link:
            link_image_to_existing_file(
                image,
                path,
                file_format,
                use_float=use_float,
                colorspace=colorspace,
                reload=True,
            )
    elif link:
        link_image_to_file(image, path, file_format, use_float=use_float, colorspace=colorspace)
    else:
        save_image(image, path, file_format, use_float=use_float, colorspace=colorspace)
    return path


def link_image_to_existing_file(
    image,
    filepath,
    file_format,
    *,
    use_float: bool | None = None,
    colorspace: str | None = None,
    reload: bool = True,
) -> None:
    if image is None:
        return
    image.filepath_raw = filepath
    _apply_image_format(image, file_format, use_float=use_float, colorspace=colorspace)
    image.filepath = filepath
    image.source = 'FILE'
    if reload:
        image.reload()


def write_png_rgba(path: str, pixels: np.ndarray) -> bool:
    if pixels is None:
        return False
    data = np.asarray(pixels, dtype=np.float32)
    if data.ndim != 3 or data.shape[2] < 3:
        return False
    height, width, channels = data.shape
    if width <= 0 or height <= 0:
        return False
    if channels > 4:
        data = data[:, :, :4]
    has_alpha = data.shape[2] == 4
    base_name = sanitize_filename(os.path.splitext(os.path.basename(path))[0]) or "PNG_Write"
    image_name = f"{base_name}_PNG_Write"
    existing = bpy.data.images.get(image_name)
    if existing is not None:
        try:
            bpy.data.images.remove(existing)
        except Exception:
            pass
    img = None
    try:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        img = bpy.data.images.new(
            name=image_name,
            width=width,
            height=height,
            alpha=has_alpha,
            float_buffer=False,
        )
        expected_channels = getattr(img, "channels", 4 if has_alpha else 3)
        if data.shape[2] != expected_channels:
            if data.shape[2] == 3 and expected_channels == 4:
                alpha = np.ones((height, width, 1), dtype=np.float32)
                data = np.concatenate([data, alpha], axis=2)
            elif data.shape[2] == 4 and expected_channels == 3:
                data = data[:, :, :3]
            else:
                return False
        set_image_pixels(img, data)
        try:
            img.update()
        except Exception:
            pass
        save_image(img, path, "PNG", use_float=False)
    except Exception:
        return False
    finally:
        if img is not None:
            try:
                bpy.data.images.remove(img)
            except Exception:
                pass
    return True


def write_exr_rgba(path: str, pixels: np.ndarray) -> bool:
    if pixels is None:
        return False
    data = np.asarray(pixels, dtype=np.float32)
    if data.ndim != 3 or data.shape[2] < 3:
        return False
    height, width, channels = data.shape
    if width <= 0 or height <= 0:
        return False
    base_name = sanitize_filename(os.path.splitext(os.path.basename(path))[0]) or "EXR_Write"
    image_name = f"{base_name}_EXR_Write"
    existing = bpy.data.images.get(image_name)
    if existing is not None:
        bpy.data.images.remove(existing)
    img = None
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    img = bpy.data.images.new(
        name=image_name,
        width=width,
        height=height,
        alpha=True,
        float_buffer=True,
    )
    _apply_image_format(img, "OPEN_EXR", use_float=True)
    img.filepath_raw = path
    expected_channels = getattr(img, "channels", 4 if True else 3)
    if data.shape[2] != expected_channels:
        if data.shape[2] == 3 and expected_channels == 4:
            alpha = np.ones((height, width, 1), dtype=np.float32)
            data = np.concatenate([data, alpha], axis=2)
        elif data.shape[2] == 4 and expected_channels == 3:
            data = data[:, :, :3]
        else:
            return False
    set_image_pixels(img, data)
    img.save()
    return True
