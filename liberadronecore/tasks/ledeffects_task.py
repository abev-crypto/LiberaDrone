"""
TODO LedEffectsをドローンへ反映するタスク
何らかの方法でフォーメーションマッピングを跨げる仕組みが必要
フォーメーションマップに従ったCATデコードは正しいが
フォーメーションを跨げない　正しく跨ぐには、、、
"""

from typing import MutableSequence

import bpy
from bpy.app.handlers import persistent

import liberadronecore.util.droneutil as du
from liberadronecore.ledeffects import led_codegen_runtime as le_codegen



_color_column_cache: dict[int, list[MutableSequence[float]]] = {}

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

def _write_column_to_cache(column: int, colors: list[MutableSequence[float]]) -> None:
    _color_column_cache[column] = [list(color) for color in colors]


def _write_led_color_attribute(colors: list[MutableSequence[float]]) -> None:
    system_obj = bpy.data.objects.get("DroneSystem")
    if system_obj is None or system_obj.type != 'MESH':
        return

    mesh = system_obj.data
    if mesh is None:
        return

    point_count = len(colors)

    if len(mesh.vertices) != point_count:
        mesh.clear_geometry()
        mesh.vertices.add(point_count)

    attr = mesh.color_attributes.get("LEDColor")
    if attr is None or attr.domain != 'POINT' or attr.data_type != 'BYTE_COLOR':
        if attr is not None:
            mesh.color_attributes.remove(attr)
        attr = mesh.color_attributes.new(
            name="LEDColor", domain='POINT', type='BYTE_COLOR'
        )

    for idx, color in enumerate(colors):
        if idx >= len(attr.data):
            break
        attr.data[idx].color = color

    mesh.update()


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
    random_seq = getattr(scene.skybrush.settings, "random_sequence_root", None)

    colors: list[MutableSequence[float]] = []
    for idx, pos in enumerate(positions):
        color = effect_fn(idx, pos, frame, random_seq)
        if not color:
            color = [0.0, 0.0, 0.0, 1.0]
        elif len(color) < 4:
            color = list(color) + [1.0] * (4 - len(color))
        colors.append(color)

    _write_column_to_cache(frame - frame_start, colors)
    _write_led_color_attribute(colors)


def register():
    if update_led_effects not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(update_led_effects)


def unregister():
    if update_led_effects in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(update_led_effects)
