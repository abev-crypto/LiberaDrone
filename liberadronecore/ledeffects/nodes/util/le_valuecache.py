import bpy

from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase
from liberadronecore.ledeffects.util import valuecache as valuecache_util


class LDLEDValueCacheNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Cache a float value for reuse."""

    bl_idname = "LDLEDValueCacheNode"
    bl_label = "Value Cache"
    bl_icon = "FILE_CACHE"
    NODE_CATEGORY_ID = "LD_LED_CACHE"
    NODE_CATEGORY_LABEL = "Cache"

    mode_items = [
        ("SINGLE", "Single Frame", "Cache a single frame"),
        ("ENTRY", "Entry", "Cache across entry duration"),
    ]

    cache_mode: bpy.props.EnumProperty(
        name="Mode",
        items=mode_items,
        default="SINGLE",
        update=lambda self, _context: self._sync_inputs(),
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.inputs.new("LDLEDEntrySocket", "Entry")
        value = self.inputs.new("NodeSocketFloat", "Value")
        value.default_value = 0.0
        self.outputs.new("NodeSocketFloat", "Value")
        self._sync_inputs()

    def update(self):
        self._sync_inputs()

    def _sync_inputs(self):
        entry = self.inputs.get("Entry")
        if entry is None:
            entry = self.inputs.new("LDLEDEntrySocket", "Entry")
        is_entry_mode = self.cache_mode == "ENTRY"
        entry.hide = not is_entry_mode
        entry.enabled = is_entry_mode

    def draw_buttons(self, context, layout):
        layout.prop(self, "cache_mode", text="")
        op = layout.operator("ldled.value_cache_bake", text="Cache")
        op.node_tree_name = self.id_data.name
        op.node_name = self.name

    def build_code(self, inputs):
        out_var = self.output_var("Value")
        value_in = inputs.get("Value", "0.0")
        return f"{out_var} = {value_in}"
