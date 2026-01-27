import bpy
from liberadronecore.formation import fn_parse
from liberadronecore.ledeffects.le_codegen_base import LDLED_CodeNodeBase


def _formation_entry_items(self, context):
    items = [("CUSTOM", "Custom", "Use manual formation name")]
    scene = None
    if context and getattr(context, "scene", None):
        scene = context.scene
    else:
        try:
            scene = bpy.context.scene
        except Exception:
            scene = None
    schedule = fn_parse.get_cached_schedule(scene) if scene else []
    seen = set()
    for entry in schedule:
        value = entry.node_name or ""
        if not value and entry.collection:
            value = entry.collection.name
        if not value:
            value = entry.tree_name or ""
        if not value or value in seen:
            continue
        seen.add(value)
        label = value
        if entry.tree_name and entry.tree_name not in label:
            label = f"{entry.tree_name}: {label}"
        tooltip = f"{entry.start}-{entry.end}"
        items.append((value, label, tooltip))
    return items


def _formation_choice_update(self, context):
    choice = getattr(self, "formation_choice", "CUSTOM")
    if choice and choice != "CUSTOM":
        self.formation_name = choice


class LDLEDFormationEntryNode(bpy.types.Node, LDLED_CodeNodeBase):
    """Entry based on formation schedule."""

    bl_idname = "LDLEDFormationEntryNode"
    bl_label = "Formation Entry"
    bl_icon = "OUTLINER_COLLECTION"

    formation_name: bpy.props.StringProperty(
        name="Formation",
        default="",
        options={'LIBRARY_EDITABLE'},
    )
    formation_choice: bpy.props.EnumProperty(
        name="Formation",
        items=_formation_entry_items,
        update=_formation_choice_update,
        default=0,
        options={'LIBRARY_EDITABLE'},
    )
    duration: bpy.props.IntProperty(
        name="Duration",
        default=0,
        min=0,
        options={'LIBRARY_EDITABLE'},
    )
    from_end: bpy.props.BoolProperty(
        name="From End",
        default=False,
        options={'LIBRARY_EDITABLE'},
    )

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "LD_LedEffectsTree"

    def init(self, context):
        self.outputs.new("LDLEDEntrySocket", "Entry")

    def draw_buttons(self, context, layout):
        layout.prop(self, "formation_choice", text="Formation")
        layout.prop(self, "formation_name")
        layout.prop(self, "duration")
        layout.prop(self, "from_end")

    def build_code(self, inputs):
        out_var = self.output_var("Entry")
        entry_key = f"{self.codegen_id()}_{int(self.as_pointer())}"
        return f"{out_var} = _entry_from_formation({entry_key!r}, {self.formation_name!r}, {int(self.duration)}, {bool(self.from_end)!r})"
