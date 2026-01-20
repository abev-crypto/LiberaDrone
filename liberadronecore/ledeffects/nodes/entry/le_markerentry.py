import bpy
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


class LDLEDMarkerEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Entry based on a timeline marker."""

    bl_idname = "LDLEDMarkerEntryNode"
    bl_label = "Marker Entry"
    bl_icon = "MARKER"

    marker_name: bpy.props.StringProperty(
        name="Marker",
        default="",
        options={'LIBRARY_EDITABLE'},
    )
    offset: bpy.props.IntProperty(
        name="Offset",
        default=0,
        options={'LIBRARY_EDITABLE'},
    )
    duration: bpy.props.IntProperty(
        name="Duration",
        default=0,
        min=0,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        layout.prop(self, "marker_name")
        layout.prop(self, "offset")
        layout.prop(self, "duration")

    def build_code(self, inputs):
        out_var = self.output_var("Entry")
        entry_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return f"{out_var} = _entry_from_marker({entry_key!r}, {self.marker_name!r}, {int(self.offset)}, {int(self.duration)})"
