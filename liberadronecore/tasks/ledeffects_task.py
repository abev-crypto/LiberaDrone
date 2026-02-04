"""
TODO LedEffectsをドローンへ反映するタスク
何らかの方法でフォーメーションマッピングを跨げる仕組みが必要
フォーメーションマップに従ったCATデコードは正しいが
フォーメーションを跨げない　正しく跨ぐには、、、
"""

import bpy
from bpy.app.handlers import persistent

from liberadronecore.ledeffects import led_codegen_runtime as le_codegen
from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.util import formation_positions
from liberadronecore.util import led_eval
import numpy as np


_UNDO_DEPTH = 0
_SUSPEND_LED_EFFECTS = 0
_LED_UPDATE_PENDING = False


def _set_undo_block(active: bool) -> None:
    global _UNDO_DEPTH
    if active:
        _UNDO_DEPTH += 1
    else:
        _UNDO_DEPTH = max(0, _UNDO_DEPTH - 1)


def _on_undo_pre(*_args, **_kwargs) -> None:
    _set_undo_block(True)


def _on_undo_post(*_args, **_kwargs) -> None:
    _set_undo_block(False)


def _on_redo_pre(*_args, **_kwargs) -> None:
    _set_undo_block(True)


def _on_redo_post(*_args, **_kwargs) -> None:
    _set_undo_block(False)


def _is_undo_running() -> bool:
    return _UNDO_DEPTH > 0


def suspend_led_effects(active: bool) -> None:
    global _SUSPEND_LED_EFFECTS
    if active:
        _SUSPEND_LED_EFFECTS += 1
    else:
        _SUSPEND_LED_EFFECTS = max(0, _SUSPEND_LED_EFFECTS - 1)


def _is_led_suspended() -> bool:
    return _SUSPEND_LED_EFFECTS > 0


def schedule_led_effects_update(scene: bpy.types.Scene) -> None:
    global _LED_UPDATE_PENDING
    if _LED_UPDATE_PENDING:
        return
    scene_name = scene.name

    def _do_update():
        global _LED_UPDATE_PENDING
        if _is_undo_running():
            return 0.1
        _LED_UPDATE_PENDING = False
        scn = bpy.data.scenes[scene_name]
        update_led_effects(scn)
        return None

    _LED_UPDATE_PENDING = True
    bpy.app.timers.register(_do_update, first_interval=0.0)


def _is_any_viewport_wireframe() -> bool:
    wm = bpy.context.window_manager
    for window in wm.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for space in area.spaces:
                if space.type != 'VIEW_3D':
                    continue
                shading = space.shading
                if shading.type == 'WIREFRAME':
                    return True
    return False


def _write_led_color_attribute(colors) -> None:
    mesh = bpy.data.objects["ColorVerts"].data
    attr = mesh.color_attributes.get("color")
    if attr is None or attr.domain != 'POINT' or attr.data_type != 'BYTE_COLOR':
        if attr is not None:
            mesh.color_attributes.remove(attr)
        attr = mesh.color_attributes.new(
            name="color", domain='POINT', type='BYTE_COLOR'
        )

    expected = len(attr.data)

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
    attr.data.foreach_set("color", arr.reshape(-1).tolist())


def _collect_formation_positions(scene):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    positions, pair_ids, formation_ids, _signature = (
        formation_positions.collect_formation_positions_with_form_ids(
            scene,
            depsgraph,
            collection_name="Formation",
            sort_by_pair_id=False,
            include_signature=False,
            as_numpy=True,
        )
    )
    if positions is None or len(positions) == 0:
        return np.empty((0, 3), dtype=np.float32), None, None
    if not pair_ids or len(pair_ids) != len(positions):
        pair_ids = None
    if not formation_ids or len(formation_ids) != len(positions):
        formation_ids = None
    return positions, pair_ids, formation_ids


@persistent
def update_led_effects(scene):
    if _is_undo_running():
        return

    if _is_led_suspended():
        return

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

    positions, pair_ids, formation_ids = _collect_formation_positions(scene)
    if positions is None or len(positions) == 0:
        return
    positions_cache, inv_map = led_eval.order_positions_cache_by_pair_ids(positions, pair_ids)

    le_meshinfo.begin_led_frame_cache(
        frame,
        positions_cache,
        formation_ids=formation_ids,
        pair_ids=pair_ids,
    )
    colors = led_eval.eval_effect_colors_by_map(
        positions,
        pair_ids,
        inv_map,
        effect_fn,
        frame,
    )
    le_meshinfo.end_led_frame_cache()

    _write_led_color_attribute(colors)


def register():
    if update_led_effects not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(update_led_effects)
    if _on_undo_pre not in bpy.app.handlers.undo_pre:
        bpy.app.handlers.undo_pre.append(_on_undo_pre)
    if _on_undo_post not in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.append(_on_undo_post)
    if _on_redo_pre not in bpy.app.handlers.redo_pre:
        bpy.app.handlers.redo_pre.append(_on_redo_pre)
    if _on_redo_post not in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.append(_on_redo_post)


def unregister():
    if update_led_effects in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(update_led_effects)
    if _on_undo_pre in bpy.app.handlers.undo_pre:
        bpy.app.handlers.undo_pre.remove(_on_undo_pre)
    if _on_undo_post in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(_on_undo_post)
    if _on_redo_pre in bpy.app.handlers.redo_pre:
        bpy.app.handlers.redo_pre.remove(_on_redo_pre)
    if _on_redo_post in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.remove(_on_redo_post)
