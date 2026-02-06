import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDPaintCacheNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Bake colors into a UV texture and sample by Allow IDs."""

    bl_idname = "LDLEDPaintCacheNode"
    bl_label = "Paint Cache"
    bl_icon = "FILE_CACHE"
    NODE_CATEGORY_ID = "LD_LED_CACHE"
    NODE_CATEGORY_LABEL = "Cache"

    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.inputs.new("LDLEDIDSocket", "AllowIDs")
        self.inputs.new("NodeSocketFloat", "U")
        self.inputs.new("NodeSocketFloat", "V")
        self.outputs.new("NodeSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "image")
        op = layout.operator("ldled.paint_cache_bake", text="Cache")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

    def build_code(self, inputs):
        out_color = self.output_var("Color")
        color_in = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        allow_ids = inputs.get("AllowIDs", "None")
        u = inputs.get("U", "0.0")
        v = inputs.get("V", "0.0")
        image_name = self.image.name if self.image else ""
        if not image_name:
            return f"{out_color} = {color_in}"
        cache_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return "\n".join(
            [
                f"_img_{cache_id} = {image_name!r}",
                f"_allow_{cache_id} = {allow_ids}",
                f"_fid_{cache_id} = _formation_id(idx)",
                f"_use_{cache_id} = (_allow_{cache_id} is None) or (_fid_{cache_id} in _allow_{cache_id})",
                f"if _img_{cache_id} and _use_{cache_id}:",
                f"    _im_{cache_id} = _get_image_cached(_img_{cache_id})",
                f"    {out_color} = _sample_image(_im_{cache_id}, ({u}, {v}))",
                f"else:",
                f"    {out_color} = {color_in}",
            ]
        )
