import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


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

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "image")

    def build_code(self, inputs):
        entry = inputs.get("Entry", "_entry_empty()")
        out_var = self.output_var("Color")
        image_name = self.image.name if self.image else ""
        cat_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
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
                f"        _v_{cat_id} = max(0.0, min(1.0, idx / float(_im_{cat_id}.size[1] - 1)))",
                f"{out_var} = _sample_image(_img_{cat_id}, (_progress_{cat_id}, _v_{cat_id})) if _active_{cat_id} > 0 else (0.0, 0.0, 0.0, 1.0)",
            ]
        )
