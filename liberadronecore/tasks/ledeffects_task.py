"""
TODO LedEffectsをドローンへ反映するタスク
何らかの方法でフォーメーションマッピングを跨げる仕組みが必要
フォーメーションマップに従ったCATデコードは正しいが
フォーメーションを跨げない　正しく跨ぐには、、、
"""

import liberadronecore.util.droneutil as du

from typing import MutableSequence
import bpy
from bpy.app.handlers import persistent



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
    global _base_color_cache

    if _is_any_viewport_wireframe():
        return

    if not getattr(scene, "update_led_effects", True):
        return


    frame = scene.frame_current
    frame_start = scene.frame_start

    drones = du.get_all_drones_in_scene(scene)
    mapping = scene.skybrush.storyboard.get_mapping_at_frame(frame)
    height = len(mapping) if mapping is not None else len(drones)

    if not drones or height == 0:
        return

    colors: list[MutableSequence[float]] | None = None
    positions = None
    random_seq = scene.skybrush.settings.random_sequence_root

    for effect in light_effects.iter_active_effects_in_frame(frame):
        if colors is None:
            positions = [du.get_position_of_object(drone) for drone in drones]
            colors = [[0.0, 0.0, 0.0, 0.0] for _ in drones]

        effect.apply_on_colors(
            drones=drones,
            colors=colors,
            positions=positions,
            mapping=mapping,
            frame=frame,
            random_seq=random_seq,
        )
    if colors:
        _write_column_to_cache(frame - frame_start, colors)
        _write_led_color_attribute(colors)
    else:
        _write_led_color_attribute(cached)