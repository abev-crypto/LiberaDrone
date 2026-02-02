import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.ledeffects.nodes.util import le_particlebase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function
from liberadronecore.util import formation_positions


@register_runtime_function
def _cat_row_index(idx: int, height: int, mode: str = "PAIR_TO_FORM") -> int:
    return _cat_row_index_mode(idx, height, mode)


@register_runtime_function
def _cat_row_index_mode(idx: int, height: int, mode: str = "PAIR_TO_FORM") -> int:
    try:
        height_val = int(height)
    except (TypeError, ValueError):
        height_val = 0
    try:
        idx_val = int(idx)
    except (TypeError, ValueError):
        idx_val = 0
    if str(mode) == "REF_TO_REF":
        fid_val = int(le_meshinfo._formation_id())
        mapping = le_particlebase._formation_id_map()
        try:
            row_val = int(mapping.get(fid_val, fid_val))
        except (TypeError, ValueError):
            row_val = fid_val
    else:
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


_REF_FORMATION_MAP_CACHE: dict[tuple[str, int], dict[str, dict[int, int]]] = {}


def _build_reference_maps(frame: int) -> tuple[dict[int, int], dict[int, int]]:
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return {}, {}
    key = (scene.name, int(frame))
    cached = _REF_FORMATION_MAP_CACHE.get(key)
    if isinstance(cached, dict):
        pair_to_form = cached.get("pair_to_form")
        form_to_pair = cached.get("form_to_pair")
        if isinstance(pair_to_form, dict) and isinstance(form_to_pair, dict):
            return pair_to_form, form_to_pair

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

    pair_to_form: dict[int, int] = {}
    form_to_pair: dict[int, int] = {}
    if formation_ids is None:
        _REF_FORMATION_MAP_CACHE[key] = {"pair_to_form": pair_to_form, "form_to_pair": form_to_pair}
        return pair_to_form, form_to_pair

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
        if runtime_idx not in pair_to_form:
            pair_to_form[runtime_idx] = fid_val
        if fid_val not in form_to_pair:
            form_to_pair[fid_val] = runtime_idx

    _REF_FORMATION_MAP_CACHE[key] = {"pair_to_form": pair_to_form, "form_to_pair": form_to_pair}
    return pair_to_form, form_to_pair


@register_runtime_function
def _cat_ref_fid_locked(idx: int, frame: int, ref_frame: int) -> int:
    try:
        idx_val = int(idx)
    except (TypeError, ValueError):
        idx_val = 0
    try:
        frame_val = int(frame)
    except (TypeError, ValueError):
        frame_val = 0
    try:
        ref_val = int(ref_frame)
    except (TypeError, ValueError):
        ref_val = -1

    if ref_val < 0:
        return _cat_ref_fid(idx_val)

    if frame_val <= ref_val:
        pair_to_form, _form_to_pair = _build_reference_maps(ref_val)
        try:
            return int(pair_to_form.get(idx_val, idx_val))
        except (TypeError, ValueError):
            return idx_val
    return idx_val


@register_runtime_function
def _cat_row_index_locked(idx: int, frame: int, ref_frame: int, height: int) -> int:
    try:
        height_val = int(height)
    except (TypeError, ValueError):
        height_val = 0
    row_val = _cat_ref_fid_locked(idx, frame, ref_frame)
    try:
        row_val = int(row_val)
    except (TypeError, ValueError):
        row_val = 0
    if height_val > 0:
        if row_val < 0:
            row_val = 0
        elif row_val >= height_val:
            row_val = height_val - 1
    return row_val


@register_runtime_function
def _cat_ref_fid(idx: int, mode: str = "PAIR_TO_FORM") -> int:
    try:
        idx_val = int(idx)
    except (TypeError, ValueError):
        idx_val = 0
    if str(mode) == "REF_TO_REF":
        return int(le_meshinfo._formation_id())
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
    try:
        return int(inv.get(idx_val, idx_val))
    except (TypeError, ValueError):
        return idx_val


@register_runtime_function
def _cat_ref_fid_at_frame(idx: int, frame: int, mode: str = "PAIR_TO_FORM") -> int:
    try:
        idx_val = int(idx)
    except (TypeError, ValueError):
        idx_val = 0
    if str(mode) == "REF_TO_REF":
        return int(le_meshinfo._formation_id())
    pair_to_form, _form_to_pair = _build_reference_maps(frame)
    try:
        return int(pair_to_form.get(idx_val, idx_val))
    except (TypeError, ValueError):
        return idx_val


@register_runtime_function
def _cat_row_index_at_frame(
    idx: int,
    frame: int,
    height: int,
    mode: str = "PAIR_TO_FORM",
) -> int:
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

    pair_to_form, form_to_pair = _build_reference_maps(frame_val)
    if str(mode) == "REF_TO_REF":
        fid_val = int(le_meshinfo._formation_id())
        try:
            row_val = int(form_to_pair.get(fid_val, fid_val))
        except (TypeError, ValueError):
            row_val = fid_val
    else:
        try:
            row_val = int(pair_to_form.get(idx_val, idx_val))
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
        row = layout.row(align=True)
        row.enabled = (not self.use_formation_id) and self.remap_rows
        row.prop(self, "remap_frame")
        op = row.operator("ldled.remapframe_fill_current", text="Now")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Color")
        image_name = self.image.name if self.image else ""
        cat_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        use_remap = bool(self.remap_rows) and not self.use_formation_id
        idx_expr = "_formation_id()" if self.use_formation_id else "idx"
        if use_remap:
            if int(self.remap_frame) >= 0:
                idx_expr = (
                    f"_cat_row_index_locked(idx, frame, {int(self.remap_frame)}, "
                    f"_im_{cat_id}.size[1])"
                )
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
