import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDFormationEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Entry based on formation schedule."""

    bl_idname = "LDLEDFormationEntryNode"
    bl_label = "LED Formation Entry"
    bl_icon = "OUTLINER_COLLECTION"

    formation_name: bpy.props.StringProperty(
        name="Formation",
        default="",
    )
    duration: bpy.props.IntProperty(
        name="Duration",
        default=0,
        min=0,
    )
    from_end: bpy.props.BoolProperty(
        name="From End",
        default=False,
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        layout.prop(self, "formation_name")
        layout.prop(self, "duration")
        layout.prop(self, "from_end")

    def build_code(self, inputs):
        out_var = self.output_var("Entry")
        entry_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return f"{out_var} = _entry_from_formation({entry_key!r}, {self.formation_name!r}, {int(self.duration)}, {bool(self.from_end)!r})"
