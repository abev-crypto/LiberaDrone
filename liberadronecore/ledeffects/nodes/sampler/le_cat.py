import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.nodes.util import le_meshinfo
from liberadronecore.ledeffects.nodes.util import le_particlebase
from liberadronecore.ledeffects.runtime_registry import register_runtime_function


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
    if height_val <= 0:
        return idx_val
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

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Color")
        image_name = self.image.name if self.image else ""
        cat_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        use_remap = bool(self.remap_rows) and not self.use_formation_id
        idx_expr = "_formation_id()" if self.use_formation_id else "idx"
        if use_remap:
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
