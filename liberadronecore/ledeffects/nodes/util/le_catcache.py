import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDCatCacheNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Cache LED colors by name."""

    bl_idname = "LDLEDCatCacheNode"
    bl_label = "Category Cache"
    bl_icon = "FILE_CACHE"

    cache_modes = [
        ("WRITE", "Write", "Store incoming data to a named cache"),
        ("READ", "Read", "Read data from a named cache"),
    ]

    cache_mode: bpy.props.EnumProperty(
        name="Mode",
        items=cache_modes,
        default="WRITE",
    )

    cache_name: bpy.props.StringProperty(
        name="Cache Name",
        default="Default",
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("NodeSocketColor", "Color")
        self.inputs.new("NodeSocketFloat", "Intensity")
        self.outputs.new("NodeSocketColor", "Color")
        self.outputs.new("NodeSocketFloat", "Intensity")

    def draw_buttons(self, context, layout):
        layout.prop(self, "cache_mode", text="")
        layout.prop(self, "cache_name")

    def build_code(self, inputs):
        color = inputs.get("Color", "(0.0, 0.0, 0.0, 1.0)")
        intensity = inputs.get("Intensity", "0.0")
        out_color = self.output_var("Color")
        out_intensity = self.output_var("Intensity")
        cache_name = self.cache_name
        cache_id = f"{self.codegen_id()}_{int(self.as_pointer())}"
        if self.cache_mode == "READ":
            return "\n".join(
                [
                    f"_cat_color_{cache_id}, _cat_intensity_{cache_id} = _cat_cache_read({cache_name!r})",
                    f"{out_color} = _cat_color_{cache_id}",
                    f"{out_intensity} = _cat_intensity_{cache_id}",
                ]
            )
        return "\n".join(
            [
                f"_cat_cache_write({cache_name!r}, {color}, {intensity})",
                f"{out_color} = {color}",
                f"{out_intensity} = {intensity}",
            ]
        )
