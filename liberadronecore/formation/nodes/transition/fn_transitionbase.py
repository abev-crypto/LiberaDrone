import bpy
from bpy.props import IntProperty, EnumProperty, StringProperty, FloatProperty, PointerProperty
from liberadronecore.formation.fn_nodecategory import FN_Node


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
    handle_frames: FloatProperty(
        name="Handle Frames",
        default=2.0,
        min=0.0,
        description="Handle offset in frames for CopyLoc influence curves",
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
            layout.prop(self, "handle_frames")
            op = layout.operator("fn.shape_copyloc_influence", text="Shape CopyLoc Influence")
            op.node_name = self.name
            op.handle_frames = self.handle_frames
        layout.prop(self, "collection")
        op = layout.operator("fn.apply_transition", text="Transition")
        op.node_name = self.name
        
    
