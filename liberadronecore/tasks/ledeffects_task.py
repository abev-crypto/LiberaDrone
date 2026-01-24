"""
TODO LedEffectsをドローンへ反映するタスク
何らかの方法でフォーメーションマッピングを跨げる仕組みが必要
フォーメーションマップに従ったCATデコードは正しいが
フォーメーションを跨げない　正しく跨ぐには、、、
"""

import bpy
from bpy.app.handlers import persistent

from liberadronecore.ledeffects import led_codegen_runtime as le_codegen
from liberadronecore.system.transition import transition_apply
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
    if _UNDO_DEPTH > 0:
        return True
    checker = getattr(bpy.app, "is_job_running", None)
    if checker is None:
        return False
    try:
        return checker("UNDO") or checker("REDO")
    except Exception:
        return False


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
    scene_name = scene.name if scene else ""

    def _do_update():
        global _LED_UPDATE_PENDING
        if _is_undo_running():
            return 0.1
        _LED_UPDATE_PENDING = False
        if not scene_name:
            return None
        scn = bpy.data.scenes.get(scene_name)
        if scn is None:
            return None
        update_led_effects(scn)
        return None

    _LED_UPDATE_PENDING = True
    bpy.app.timers.register(_do_update, first_interval=0.0)

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


def _write_led_color_attribute(colors, pair_ids=None) -> None:
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

    if colors is None:
        return

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

    if pair_ids is not None and len(pair_ids) == arr.shape[0]:
        mapped = np.zeros((expected, 4), dtype=arr.dtype)
        src_count = arr.shape[0]
        for dst_idx, pid in enumerate(pair_ids):
            if pid is None:
                continue
            try:
                src_idx = int(pid)
            except (TypeError, ValueError):
                continue
            if 0 <= src_idx < src_count and 0 <= dst_idx < expected:
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


def _collect_formation_positions(scene) -> tuple[list[tuple[float, float, float]], list[int] | None]:
    col = bpy.data.collections.get("Formation")
    if col is None:
        return [], None
    depsgraph = bpy.context.evaluated_depsgraph_get()
    positions, pair_ids, _ = transition_apply._collect_positions_for_collection(
        col,
        int(getattr(scene, "frame_current", 0)),
        depsgraph,
    )
    if not positions:
        return [], None
    if not pair_ids or len(pair_ids) != len(positions):
        pair_ids = None
    return [(float(p.x), float(p.y), float(p.z)) for p in positions], pair_ids


def _order_positions_by_pair_id(
    positions: list[tuple[float, float, float]],
    pair_ids: list[int] | None,
) -> tuple[list[tuple[float, float, float]], list[int] | None]:
    if not pair_ids or len(pair_ids) != len(positions):
        return positions, pair_ids
    indexed: list[tuple[int, int, tuple[float, float, float]]] = []
    fallback: list[tuple[int, tuple[float, float, float], int | None]] = []
    for idx, pid in enumerate(pair_ids):
        try:
            key = int(pid)
        except (TypeError, ValueError):
            key = None
        if key is None:
            fallback.append((idx, positions[idx], pid))
        else:
            indexed.append((key, idx, positions[idx]))
    if not indexed:
        return positions, pair_ids
    indexed.sort(key=lambda item: (item[0], item[1]))
    ordered_positions = [pos for _key, _idx, pos in indexed]
    ordered_pair_ids = [pair_ids[idx] for _key, idx, _pos in indexed]
    if fallback:
        ordered_positions.extend([pos for _idx, pos, _pid in fallback])
        ordered_pair_ids.extend([pid for _idx, _pos, pid in fallback])
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
    effect_fn_bulk = le_codegen.get_compiled_effect_bulk(tree)
    if effect_fn is None and effect_fn_bulk is None:
        return

    frame = scene.frame_current
    frame_start = scene.frame_start

    positions, pair_ids = _collect_formation_positions(scene)
    if not positions:
        return

    runtime_indices = None
    if pair_ids is not None:
        runtime_indices = []
        for idx, pid in enumerate(pair_ids):
            runtime_idx = idx
            if pid is not None:
                try:
                    runtime_idx = int(pid)
                except (TypeError, ValueError):
                    runtime_idx = idx
            runtime_indices.append(runtime_idx)

    le_codegen.begin_led_frame_cache(frame, positions, runtime_indices)
    if effect_fn_bulk is not None:
        colors = None
        try:
            idx_array = np.asarray(
                runtime_indices if runtime_indices is not None else range(len(positions)),
                dtype=np.int64,
            )
            pos_array = np.asarray(positions, dtype=np.float32)
            if pos_array.ndim == 2 and pos_array.shape[1] >= 3:
                pos_tuple = (pos_array[:, 0], pos_array[:, 1], pos_array[:, 2])
            else:
                pos_tuple = (np.array([], dtype=np.float32),) * 3
            colors = effect_fn_bulk(idx_array, pos_tuple, frame)
        except Exception:
            colors = None
        finally:
            le_codegen.end_led_frame_cache()

        if colors is not None:
            _write_led_color_attribute(colors, pair_ids)
            return

    if effect_fn is None:
        return

    colors = np.zeros((len(positions), 4), dtype=np.float32)
    try:
        for idx, pos in enumerate(positions):
            runtime_idx = runtime_indices[idx] if runtime_indices is not None else idx
            le_codegen.set_led_runtime_index(runtime_idx)
            color = effect_fn(runtime_idx, pos, frame)
            if not color:
                continue
            for chan in range(min(4, len(color))):
                colors[idx, chan] = float(color[chan])
    finally:
        le_codegen.set_led_runtime_index(None)
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
