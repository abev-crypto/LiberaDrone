import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.ledeffects.nodes.util import le_particlebase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.util import formation_positions


@register_runtime_function
def _cat_row_index(idx: int, height: int) -> int:
    try:
        height_val = int(height)
    except (TypeError, ValueError):
        height_val = 0
    try:
        idx_val = int(idx)
    except (TypeError, ValueError):
        idx_val = 0
    cache = le_meshinfo._LED_FRAME_CACHE
    inv = cache.get("formation_id_inv_map")
    if not isinstance(inv, dict):
        mapping = le_particlebase._formation_id_map()
        inv = {}
        if isinstance(mapping, dict):
            for fid, rid in mapping.items():
                try:
                    rid_val = int(rid)
                except (TypeError, ValueError):
                    continue
                if rid_val in inv:
                    continue
                inv[rid_val] = fid
        cache["formation_id_inv_map"] = inv
    row_val = idx_val
    if isinstance(inv, dict):
        try:
            row_val = int(inv.get(idx_val, idx_val))
        except (TypeError, ValueError):
            row_val = idx_val
    if height_val > 0:
        if row_val < 0:
            row_val = 0
        elif row_val >= height_val:
            row_val = height_val - 1
    return row_val


_REF_FORMATION_INV_CACHE: dict[tuple[str, int], dict[int, int]] = {}


def _build_reference_inv_map(frame: int) -> dict[int, int]:
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return {}
    key = (scene.name, int(frame))
    cached = _REF_FORMATION_INV_CACHE.get(key)
    if isinstance(cached, dict):
        return cached

    original_frame = int(getattr(scene, "frame_current", 0))
    view_layer = getattr(bpy.context, "view_layer", None)
    suspended = False
    try:
        if int(frame) != original_frame:
            try:
                from liberadronecore.tasks import ledeffects_task
                ledeffects_task.suspend_led_effects(True)
                suspended = True
            except Exception:
                suspended = False
            try:
                scene.frame_set(int(frame))
            except Exception:
                pass
            if view_layer is not None:
                try:
                    view_layer.update()
                except Exception:
                    pass

        depsgraph = bpy.context.evaluated_depsgraph_get()
        _positions, pair_ids, formation_ids, _sig = (
            formation_positions.collect_formation_positions_with_form_ids(
                scene,
                depsgraph,
                collection_name="Formation",
                sort_by_pair_id=False,
                include_signature=False,
                as_numpy=False,
            )
        )
    finally:
        if int(frame) != original_frame:
            try:
                scene.frame_set(original_frame)
            except Exception:
                pass
            if view_layer is not None:
                try:
                    view_layer.update()
                except Exception:
                    pass
            if suspended:
                try:
                    from liberadronecore.tasks import ledeffects_task
                    ledeffects_task.suspend_led_effects(False)
                except Exception:
                    pass

    mapping: dict[int, int] = {}
    if formation_ids is None:
        _REF_FORMATION_INV_CACHE[key] = mapping
        return mapping

    use_pair_ids = False
    if pair_ids is not None and len(pair_ids) == len(formation_ids):
        seen = set()
        use_pair_ids = True
        for pid in pair_ids:
            try:
                key_pid = int(pid)
            except (TypeError, ValueError):
                use_pair_ids = False
                break
            if key_pid < 0 or key_pid >= len(formation_ids) or key_pid in seen:
                use_pair_ids = False
                break
            seen.add(key_pid)

    for src_idx, fid in enumerate(formation_ids):
        try:
            fid_val = int(fid)
        except (TypeError, ValueError):
            continue
        runtime_idx = src_idx
        if use_pair_ids and pair_ids is not None:
            try:
                runtime_idx = int(pair_ids[src_idx])
            except (TypeError, ValueError):
                runtime_idx = src_idx
        if runtime_idx in mapping:
            continue
        mapping[runtime_idx] = fid_val

    _REF_FORMATION_INV_CACHE[key] = mapping
    return mapping


@register_runtime_function
def _cat_row_index_at_frame(idx: int, frame: int, height: int) -> int:
    try:
        idx_val = int(idx)
    except (TypeError, ValueError):
        idx_val = 0
    try:
        height_val = int(height)
    except (TypeError, ValueError):
        height_val = 0
    try:
        frame_val = int(frame)
    except (TypeError, ValueError):
        frame_val = 0

    mapping = _build_reference_inv_map(frame_val)
    try:
        row_val = int(mapping.get(idx_val, idx_val))
    except (TypeError, ValueError):
        row_val = idx_val

    if height_val > 0:
        if row_val < 0:
            row_val = 0
        elif row_val >= height_val:
            row_val = height_val - 1
    return row_val


class LDLEDCatSamplerNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Sample an image using frame progress and formation id."""

    bl_idname = "LDLEDCatSamplerNode"
    bl_label = "CAT Sampler"
    bl_icon = "IMAGE_ZDEPTH"

    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
        options={'LIBRARY_EDITABLE'},
    )
    use_formation_id: bpy.props.BoolProperty(
        name="Use Formation ID",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )
    remap_rows: bpy.props.BoolProperty(
        name="Remap Rows",
        description="Remap CAT rows to match the current drone index",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )
    remap_frame: bpy.props.IntProperty(
        name="Remap Frame",
        description="Use formation IDs from this frame when remapping rows",
        default=-1,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "image")
        layout.prop(self, "use_formation_id")
        row = layout.row()
        row.enabled = not self.use_formation_id
        row.prop(self, "remap_rows")
        row = layout.row()
        row.enabled = (not self.use_formation_id) and self.remap_rows
        row.prop(self, "remap_frame")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Color")
        image_name = self.image.name if self.image else ""
        cat_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        use_remap = bool(self.remap_rows) and not self.use_formation_id
        idx_expr = "_formation_id()" if self.use_formation_id else "idx"
        if use_remap:
            if int(self.remap_frame) >= 0:
                idx_expr = f"_cat_row_index_at_frame(idx, {int(self.remap_frame)}, _im_{cat_id}.size[1])"
            else:
                idx_expr = f"_cat_row_index(idx, _im_{cat_id}.size[1])"
        return "\n".join(
            [
                f"_active_{cat_id} = _entry_active_count({entry}, frame)",
                f"if _entry_is_empty({entry}):",
                f"    _active_{cat_id} = 1",
                f"_progress_{cat_id} = _entry_progress({entry}, frame)",
                f"_img_{cat_id} = {image_name!r}",
                f"_v_{cat_id} = 0.0",
                f"if _img_{cat_id}:",
                f"    _im_{cat_id} = bpy.data.images.get(_img_{cat_id})",
                f"    if _im_{cat_id} and _im_{cat_id}.size[1] > 1:",
                f"        _v_{cat_id} = _clamp({idx_expr} / float(_im_{cat_id}.size[1] - 1), 0.0, 1.0)",
                f"{out_var} = _sample_image(_img_{cat_id}, (_progress_{cat_id}, _v_{cat_id})) if _active_{cat_id} > 0 else (0.0, 0.0, 0.0, 1.0)",
            ]
        )
