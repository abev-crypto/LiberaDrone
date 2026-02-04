"""
TODO LedEffectsをドローンへ反映するタスク
何らかの方法でフォーメーションマッピングを跨げる仕組みが必要
フォーメーションマップに従ったCATデコードは正しいが
フォーメーションを跨げない　正しく跨ぐには、、、
"""

import bpy
from bpy.app.handlers import persistent

from liberadronecore.ledeffects import led_codegen_runtime as le_codegen
from liberadronecore.util import formation_positions
import numpy as np


_color_column_cache: dict[int, list[list[float]]] = {}
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

def _write_column_to_cache(column: int, colors) -> None:
    _color_column_cache[column] = [list(color) for color in colors]


def _write_led_color_attribute(colors, pair_ids=None) -> None:
    system_obj = bpy.data.objects["ColorVerts"]
    if system_obj.type != 'MESH':
        raise TypeError("ColorVerts must be a mesh object")

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
        raise ValueError("ColorVerts has no vertex colors")
    if colors is None:
        raise ValueError("LED colors are missing")

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

    if pair_ids is not None:
        if len(pair_ids) != arr.shape[0]:
            raise ValueError("pair_ids length mismatch for colors")
        if expected != arr.shape[0]:
            raise ValueError("ColorVerts length mismatch for colors")
        mapped = np.zeros((expected, 4), dtype=arr.dtype)
        src_count = arr.shape[0]
        for dst_idx, pid in enumerate(pair_ids):
            src_idx = int(pid)
            if src_idx < 0 or src_idx >= src_count:
                raise ValueError("pair_id out of range for colors")
            mapped[dst_idx] = arr[src_idx]
        arr = mapped
    else:
        arr = arr[:expected]
        if arr.shape[0] < expected:
            pad = np.zeros((expected - arr.shape[0], 4), dtype=arr.dtype)
            arr = np.concatenate([arr, pad], axis=0)

    arr = np.clip(arr, 0.0, 1.0)
    attr.data.foreach_set("color", arr.reshape(-1).tolist())

    #mesh.update()


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


def _order_positions_by_pair_id(
    positions: list[tuple[float, float, float]],
    pair_ids: list[int] | None,
) -> tuple[list[tuple[float, float, float]], list[int] | None]:
    if not pair_ids or len(pair_ids) != len(positions):
        return positions, pair_ids
    indexed: list[tuple[int, int, tuple[float, float, float]]] = []
    for idx, pid in enumerate(pair_ids):
        key = int(pid)
        indexed.append((key, idx, positions[idx]))
    if not indexed:
        return positions, pair_ids
    indexed.sort(key=lambda item: (item[0], item[1]))
    ordered_positions = [pos for _key, _idx, pos in indexed]
    ordered_pair_ids = [pair_ids[idx] for _key, idx, _pos in indexed]
    return ordered_positions, ordered_pair_ids


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
    frame_start = scene.frame_start

    positions, pair_ids, formation_ids = _collect_formation_positions(scene)
    if positions is None or len(positions) == 0:
        return
    positions_cache = [tuple(float(v) for v in pos) for pos in positions]
    if pair_ids is not None:
        if len(pair_ids) != len(positions_cache):
            raise ValueError("pair_ids length mismatch for positions")
        ordered: list[tuple[float, float, float] | None] = [None] * len(positions_cache)
        for src_idx, pid in enumerate(pair_ids):
            key = int(pid)
            if key < 0 or key >= len(positions_cache):
                raise ValueError("pair_id out of range for positions")
            if ordered[key] is not None:
                raise ValueError("duplicate pair_id in positions")
            ordered[key] = positions_cache[src_idx]
        positions_cache = [item for item in ordered]

    le_codegen.begin_led_frame_cache(
        frame,
        positions_cache,
        formation_ids=formation_ids,
        pair_ids=pair_ids,
    )
    colors = np.zeros((len(positions), 4), dtype=np.float32)
    for idx, pos in enumerate(positions):
        runtime_idx = idx
        if pair_ids is not None:
            runtime_idx = int(pair_ids[idx])
        le_codegen.set_led_source_index(idx)
        le_codegen.set_led_runtime_index(runtime_idx)
        color = effect_fn(runtime_idx, pos, frame)
        if not color:
            continue
        for chan in range(min(4, len(color))):
            colors[idx, chan] = float(color[chan])
    le_codegen.set_led_runtime_index(None)
    le_codegen.set_led_source_index(None)
    le_codegen.end_led_frame_cache()

    #_write_column_to_cache(frame - frame_start, colors)
    _write_led_color_attribute(colors, pair_ids)


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
