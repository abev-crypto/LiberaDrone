from typing import Iterable, Sequence
import os

import numpy as np

import bpy


def ms_to_frame(ms: float, fps: float) -> float:
    return (ms / 1000.0) * fps


def _create_image(
    name: str,
    width: int,
    height: int,
    use_float: bool,
    *,
    recreate: bool,
) -> bpy.types.Image:
    img = bpy.data.images.get(name)
    if img is not None and recreate:
        try:
            bpy.data.images.remove(img, do_unlink=True)
        except TypeError:
            try:
                bpy.data.images.remove(img)
            except Exception:
                pass
        img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.new(name=name, width=width, height=height, alpha=True, float_buffer=use_float)
    else:
        img.scale(width, height)
        if hasattr(img, "alpha_mode"):
            img.alpha_mode = 'STRAIGHT'
        if hasattr(img, "use_alpha"):
            img.use_alpha = True
        try:
            img.use_float = use_float
        except Exception:
            pass
    return img


def _save_image_to_blend_dir(img: bpy.types.Image) -> None:
    filepath = getattr(bpy.data, "filepath", "")
    if not filepath:
        return
    dirpath = os.path.dirname(filepath)
    if not dirpath:
        return
    is_pos = img.name.endswith("_Pos")
    filename = f"{img.name}.exr" if is_pos else f"{img.name}.png"
    path = os.path.join(dirpath, filename)
    try:
        img.filepath_raw = path
        if is_pos:
            img.file_format = "OPEN_EXR"
            if hasattr(img, "use_float"):
                img.use_float = True
        else:
            img.file_format = "PNG"
        img.save()
    except Exception:
        pass

def _row_frame(row: dict, fps: float) -> float:
    if "frame" in row:
        try:
            return float(row.get("frame", 0.0))
        except Exception:
            return 0.0
    try:
        return ms_to_frame(float(row.get("t_ms", 0.0)), fps)
    except Exception:
        return 0.0

def _gather_samples(
    tracks: Sequence[dict], fps: float, frame_count: int
) -> list[dict[str, np.ndarray]]:
    target_frames = np.arange(frame_count, dtype=np.float32)
    samples: list[dict[str, np.ndarray]] = []

    for track in tracks:
        data = track.get("data") or []
        if not data:
            zeros = np.zeros(frame_count, dtype=np.float32)
            samples.append({key: zeros for key in ("x", "y", "z", "r", "g", "b")})
            continue

        times = np.array([_row_frame(row, fps) for row in data], dtype=np.float32)

        def _interp(values: np.ndarray) -> np.ndarray:
            return np.interp(
                target_frames, times, values, left=values[0], right=values[-1]
            )

        samples.append(
            {
                key: _interp(
                    np.array([row.get(key, 0.0) for row in data], dtype=np.float32)
                )
                for key in ("x", "y", "z", "r", "g", "b")
            }
        )

    return samples


def _determine_bounds(samples: Iterable[dict[str, np.ndarray]]):
    arrays = list(samples)
    if not arrays:
        return (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)

    xs = np.concatenate([track["x"] for track in arrays])
    ys = np.concatenate([track["y"] for track in arrays])
    zs = np.concatenate([track["z"] for track in arrays])

    return (
        float(xs.min(initial=0.0)),
        float(ys.min(initial=0.0)),
        float(zs.min(initial=0.0)),
    ), (
        float(xs.max(initial=1.0)),
        float(ys.max(initial=1.0)),
        float(zs.max(initial=1.0)),
    )

def build_vat_images_from_tracks(
    tracks: Sequence[dict],
    fps: float,
    *,
    image_name_prefix: str = "VAT",
    recreate_images: bool = False,
):
    if not tracks:
        raise RuntimeError("No CSV tracks supplied for VAT generation")

    # Normalize frames to start at the earliest sample so VAT starts at the render range
    min_frame = min(
        (_row_frame(tr["data"][0], fps) for tr in tracks if tr.get("data")),
        default=0.0,
    )
    adjusted_tracks = []
    for tr in tracks:
        data = tr.get("data") or []
        if not data:
            adjusted_tracks.append({"name": tr.get("name", ""), "data": []})
            continue
        adjusted = []
        for row in data:
            frame = _row_frame(row, fps) - float(min_frame)
            adjusted.append({**row, "frame": frame})
        adjusted_tracks.append({"name": tr.get("name", ""), "data": adjusted})

    max_frame = max(
        (tr["data"][-1]["frame"] for tr in adjusted_tracks if tr["data"]),
        default=0.0,
    )
    duration = int(max_frame)
    frame_count = max(duration + 1, 1)
    samples = _gather_samples(adjusted_tracks, fps, frame_count)
    pos_min, pos_max = _determine_bounds(samples)

    drone_count = len(tracks)
    prefix = image_name_prefix or "VAT"
    pos_img = _create_image(
        f"{prefix}_Pos",
        frame_count,
        drone_count,
        True,
        recreate=recreate_images,
    )
    col_img = _create_image(
        f"{prefix}_Color",
        frame_count,
        drone_count,
        False,
        recreate=recreate_images,
    )
    pos_img.colorspace_settings.name = "Non-Color"
    
    rx = (pos_max[0] - pos_min[0]) or 1.0
    ry = (pos_max[1] - pos_min[1]) or 1.0
    rz = (pos_max[2] - pos_min[2]) or 1.0

    pos_pixels = np.empty((drone_count, frame_count, 4), dtype=np.float32)
    col_pixels = np.empty((drone_count, frame_count, 4), dtype=np.float32)

    pos_pixels[:, :, 3] = 1.0
    col_pixels[:, :, 3] = 1.0

    for drone_idx, track in enumerate(samples):
        pos_pixels[drone_idx, :, 0] = (track["x"] - pos_min[0]) / rx
        pos_pixels[drone_idx, :, 1] = (track["y"] - pos_min[1]) / ry
        pos_pixels[drone_idx, :, 2] = (track["z"] - pos_min[2]) / rz

        col_pixels[drone_idx, :, 0] = (track["r"])/ 255.0
        col_pixels[drone_idx, :, 1] = (track["g"])/ 255.0
        col_pixels[drone_idx, :, 2] = (track["b"])/ 255.0

    pos_img.pixels[:] = pos_pixels.ravel()
    col_img.pixels[:] = col_pixels.ravel()

    _save_image_to_blend_dir(pos_img)
    _save_image_to_blend_dir(col_img)

    return pos_img, col_img, pos_min, pos_max, duration, drone_count


def _build_tracks_from_scene(
    context,
    frame_start: int,
    frame_end: int,
    drones: Iterable,
    fps: float,
):
    scene = context.scene
    view_layer = context.view_layer
    original_frame = scene.frame_current
    drones = list(drones)
    tracks = [{"name": obj.name, "data": []} for obj in drones]

    for frame, time_sec in each_frame_in(
        range(frame_start, frame_end + 1), context=context, redraw=True
    ):
        scene.frame_set(frame)
        if view_layer is not None:
            view_layer.update()

        # Use absolute frame counts so VAT starts at the render range start, not frame 0
        frame_value = float(frame)
        if time_sec is not None:
            frame_value = float(time_sec) * fps

        for idx, obj in enumerate(drones):
            location = obj.matrix_world.translation
            color = _color_to_255(_get_emission_color(obj))
            tracks[idx]["data"].append(
                {
                    "frame": frame_value,
                    "x": float(location.x),
                    "y": float(location.y),
                    "z": float(location.z),
                    "r": color[0],
                    "g": color[1],
                    "b": color[2],
                }
            )

    scene.frame_set(original_frame)
    if view_layer is not None:
        view_layer.update()

    return tracks

def _export_vat_cat(
    context,
    name: str,
    frame_start: int,
    frame_end: int,
    export_dir: str,
):
    collection = _find_drone_collection()
    drones = _gather_drone_objects_for_export(collection)
    if not drones:
        return False, "No drone meshes found for VAT/CAT export"

    fps = 24.0
    tracks = _build_tracks_from_scene(context, frame_start, frame_end, drones, fps)
    if not any(tr["data"] for tr in tracks):
        return False, "No animation data captured for VAT/CAT export"

    pos_img, vat_color_img, pos_min, pos_max, _duration, _drone_count = (
        build_vat_images_from_tracks(tracks, fps, image_name_prefix=f"{name}_VAT")
    )

    bounds_suffix = CSV2Vertex._format_bounds_suffix(pos_min, pos_max)
    short_name = name[:7]
    vat_base = f"{short_name}_VAT_{bounds_suffix}"

    pos_img.name = f"{vat_base}"
    vat_color_img.name = f"{short_name}_Color"

    pos_path = os.path.join(export_dir, f"{pos_img.name}.exr")
    vat_color_path = os.path.join(export_dir, f"{vat_color_img.name}.png")

    CSV2Vertex._save_image(pos_img, pos_path, "OPEN_EXR")
    CSV2Vertex._save_image(vat_color_img, vat_color_path, "PNG")

    return True, f"VAT: {os.path.basename(pos_path)}, {os.path.basename(vat_color_path)}"
