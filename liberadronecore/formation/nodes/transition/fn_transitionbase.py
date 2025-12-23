import bpy
from bpy.props import IntProperty, EnumProperty, StringProperty, FloatProperty, PointerProperty
from liberadronecore.formation.fn_nodecategory import FN_Node, FN_Register
from liberadronecore.system.transition.transition_apply import apply_transition_by_node_name

class FN_OT_apply_transition(bpy.types.Operator, FN_Register):
    bl_idname = "fn.apply_transition"
    bl_label = "Apply Transition"
    node_name: StringProperty()

    def execute(self, context):
        ok, message = apply_transition_by_node_name(self.node_name, context)
        if ok:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        self.report({'ERROR'}, message)
        return {'CANCELLED'}

class FN_TransitionBase:
    mode: EnumProperty(
        name="Mode",
        items=[
            ("AUTO", "Auto", "Automatic transition behavior"),
            ("COPYLOC", "Copy Location", "Copyloc transition behavior"),
        ],
        default="AUTO",
    )
    error_message: StringProperty(name="Error", default="", options={'SKIP_SAVE'})
    copyloc_mode: EnumProperty(
        name="CopyLoc Mode",
        items=[
            ("NORMAL", "Normal", "Directly connect previous and next"),
            ("SPLIT", "Split", "Insert split meshes between"),
            ("GRID", "Grid", "Insert grid mesh between"),
        ],
        default="NORMAL",
    )
    split_count: IntProperty(
        name="Split Count",
        default=1,
        min=1,
    )
    grid_spacing: FloatProperty(
        name="Grid Spacing",
        default=0.5,
        min=0.01,
    )
    collection: PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        description="Transition output collection",
    )

    def draw_buttons(self, context, layout):
        if self.computed_start_frame >= 0:
            row = layout.row()
            row.alignment = 'RIGHT'
            row.label(text=f"start:{self.computed_start_frame}f")
        if self.error_message:
            layout.label(text=self.error_message, icon='ERROR')
        layout.prop(self, "mode")
        if self.mode == "COPYLOC":
            layout.prop(self, "copyloc_mode")
            if self.copyloc_mode == "SPLIT":
                layout.prop(self, "split_count")
            elif self.copyloc_mode == "GRID":
                layout.prop(self, "grid_spacing")
        layout.prop(self, "collection")
        op = layout.operator("fn.apply_transition", text="Transition")
        op.node_name = self.name
        
    
