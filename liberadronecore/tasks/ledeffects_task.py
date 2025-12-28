"""
TODO LedEffectsをドローンへ反映するタスク
何らかの方法でフォーメーションマッピングを跨げる仕組みが必要
フォーメーションマップに従ったCATデコードは正しいが
フォーメーションを跨げない　正しく跨ぐには、、、
"""

import bpy
from bpy.app.handlers import persistent

import liberadronecore.util.droneutil as du
from liberadronecore.ledeffects import led_codegen_runtime as le_codegen
import numpy as np


_color_column_cache: dict[int, list[list[float]]] = {}

def _is_any_viewport_wireframe() -> bool:
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return False

    for window in wm.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for space in area.spaces:
                if space.type != 'VIEW_3D':
                    continue
                shading = getattr(space, "shading", None)
                if shading and getattr(shading, "type", None) == 'WIREFRAME':
                    return True
    return False

def _write_column_to_cache(column: int, colors) -> None:
    _color_column_cache[column] = [list(color) for color in colors]


def _write_led_color_attribute(colors) -> None:
    system_obj = bpy.data.objects.get("ColorVerts")
    if system_obj is None or system_obj.type != 'MESH':
        return

    mesh = system_obj.data
    attr = mesh.color_attributes.get("color")
    if attr is None or attr.domain != 'POINT' or attr.data_type != 'BYTE_COLOR':
        if attr is not None:
            mesh.color_attributes.remove(attr)
        attr = mesh.color_attributes.new(
            name="color", domain='POINT', type='BYTE_COLOR'
        )

    expected = len(attr.data)
    if expected <= 0:
        return

    flat: list[float]

    if hasattr(colors, "shape"):
        arr = np.asarray(colors, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape((-1, 4))
        elif arr.ndim >= 2:
            arr = arr.reshape((-1, arr.shape[-1]))
        if arr.shape[1] < 4:
            pad = np.zeros((arr.shape[0], 4 - arr.shape[1]), dtype=arr.dtype)
            arr = np.concatenate([arr, pad], axis=1)
        elif arr.shape[1] > 4:
            arr = arr[:, :4]
        arr = arr[:expected]
        if arr.shape[0] < expected:
            pad = np.zeros((expected - arr.shape[0], 4), dtype=arr.dtype)
            arr = np.concatenate([arr, pad], axis=0)
        arr = np.clip(arr, 0.0, 1.0)
        flat = arr.reshape(-1).tolist()
        attr.data.foreach_set("color", flat)

    #mesh.update()


@persistent
def update_led_effects(scene):
    if _is_any_viewport_wireframe():
        return

    if not getattr(scene, "update_led_effects", True):
        return

    tree = le_codegen.get_active_tree(scene)
    if tree is None:
        return

    effect_fn = le_codegen.get_compiled_effect(tree)
    if effect_fn is None:
        return

    frame = scene.frame_current
    frame_start = scene.frame_start

    drones = du.get_all_drones_in_scene(scene)
    if not drones:
        return

    positions = [du.get_position_of_object(drone) for drone in drones]

    le_codegen.begin_led_frame_cache(frame, positions)
    colors = np.zeros((len(positions), 4), dtype=np.float32)
    try:
        for idx, pos in enumerate(positions):
            le_codegen.set_led_runtime_index(idx)
            color = effect_fn(idx, pos, frame)
            if not color:
                continue
            for chan in range(min(4, len(color))):
                colors[idx, chan] = float(color[chan])
    finally:
        le_codegen.set_led_runtime_index(None)
        le_codegen.end_led_frame_cache()

    #_write_column_to_cache(frame - frame_start, colors)
    _write_led_color_attribute(colors)


def register():
    if update_led_effects not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(update_led_effects)


def unregister():
    if update_led_effects in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(update_led_effects)
