import bpy
from bpy.props import IntProperty, EnumProperty, StringProperty, FloatProperty, PointerProperty
from liberadronecore.formation import fn_parse
from liberadronecore.formation.fn_nodecategory import FN_Node


class FN_TransitionBase:
    mode: EnumProperty(
        name="Mode",
        items=[
            ("AUTO", "Auto", "Automatic transition behavior"),
            ("CONSTRUCTION", "Construction", "Staggered transition by travel distance"),
            ("COPYLOC", "Copy Location", "Copyloc transition behavior"),
        ],
        default="AUTO",
    )
    error_message: StringProperty(name="Error", default="", options={'SKIP_SAVE'})
    max_move_up: FloatProperty(name="Max Up", default=-1.0, options={'SKIP_SAVE'})
    max_move_down: FloatProperty(name="Max Down", default=-1.0, options={'SKIP_SAVE'})
    max_move_horiz: FloatProperty(name="Max Horiz", default=-1.0, options={'SKIP_SAVE'})
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
    construction_start_count: IntProperty(
        name="Start Per Frame",
        default=1,
        min=1,
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

    def _max_travel_distance(self, duration_frames: float, speed: float, accel: float, fps: float) -> float:
        try:
            frames = float(duration_frames)
        except Exception:
            return 0.0
        if fps <= 0.0:
            fps = 24.0
        t = frames / fps
        if t <= 0.0:
            return 0.0
        v = max(0.0, float(speed))
        if v <= 0.0:
            return 0.0
        a = max(0.0, float(accel))
        if a <= 0.0:
            return v * t
        t_ramp = v / a
        if t <= 2.0 * t_ramp:
            return a * (t * 0.5) ** 2
        return v * t - (v * v) / a

    def draw_buttons(self, context, layout):
        if self.computed_start_frame >= 0:
            row = layout.row()
            row.alignment = 'RIGHT'
            row.label(text=f"start:{self.computed_start_frame}f")
        if self.error_message:
            layout.label(text=self.error_message, icon='ERROR')
        if (
            self.max_move_up >= 0.0
            or self.max_move_down >= 0.0
            or self.max_move_horiz >= 0.0
        ):
            scene = context.scene if context else None
            fps = 0.0
            if scene is not None:
                fps = float(getattr(scene.render, "fps", 0.0))
                base = float(getattr(scene.render, "fps_base", 1.0) or 1.0)
                fps = fps / base if base > 0.0 else fps
            duration_value = fn_parse._resolve_input_value(self, "Duration", 0.0, "duration")
            duration_frames = fn_parse._duration_frames(duration_value)
            if scene is not None:
                acc = float(getattr(scene, "ld_proxy_max_acc_vert", 0.0))
                max_up = float(getattr(scene, "ld_proxy_max_speed_up", 0.0))
                max_down = float(getattr(scene, "ld_proxy_max_speed_down", 0.0))
                max_horiz = float(getattr(scene, "ld_proxy_max_speed_horiz", 0.0))
            else:
                acc = 0.0
                max_up = 0.0
                max_down = 0.0
                max_horiz = 0.0
            limit_up = self._max_travel_distance(duration_frames, max_up, acc, fps)
            limit_down = self._max_travel_distance(duration_frames, max_down, acc, fps)
            limit_horiz = self._max_travel_distance(duration_frames, max_horiz, acc, fps)
            eps = 1.0e-5
            if self.max_move_up >= 0.0:
                row = layout.row()
                row.alert = self.max_move_up > limit_up + eps
                row.label(text=f"Move Up: {self.max_move_up:.2f}m")
            if self.max_move_down >= 0.0:
                row = layout.row()
                row.alert = self.max_move_down > limit_down + eps
                row.label(text=f"Move Down: {self.max_move_down:.2f}m")
            if self.max_move_horiz >= 0.0:
                row = layout.row()
                row.alert = self.max_move_horiz > limit_horiz + eps
                row.label(text=f"Move Horiz: {self.max_move_horiz:.2f}m")
        layout.prop(self, "mode")
        if self.mode == "CONSTRUCTION":
            layout.prop(self, "construction_start_count")
        elif self.mode == "COPYLOC":
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
        
    
