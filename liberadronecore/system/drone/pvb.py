bl_info = {
    "name": "Pseudo Vertex Brush (EditMode, Panel start)",
    "author": "chatgpt",
    "version": (0, 1, 0),
    "blender": (4, 3, 0),
    "category": "3D View",
}

import bpy
import math
import gpu
import bmesh
from mathutils import Vector
from mathutils.kdtree import KDTree
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader


# -------------------------
# Settings (Scene props)
# -------------------------

def ensure_scene_props():
    Scene = bpy.types.Scene
    if not hasattr(Scene, "pvb_radius_px"):
        Scene.pvb_radius_px = bpy.props.FloatProperty(
            name="Radius (px)", default=40.0, min=1.0, soft_max=500.0
        )
    if not hasattr(Scene, "pvb_falloff_power"):
        Scene.pvb_falloff_power = bpy.props.FloatProperty(
            name="Falloff Power", default=2.0, min=0.1, soft_max=8.0,
            description="w = (1 - d/r)^power"
        )
    if not hasattr(Scene, "pvb_only_selected"):
        Scene.pvb_only_selected = bpy.props.BoolProperty(
            name="Only Selected", default=True,
            description="Affect only selected vertices (Edit Mode)"
        )
    if not hasattr(Scene, "pvb_color"):
        Scene.pvb_color = bpy.props.FloatVectorProperty(
            name="Color", subtype='COLOR', size=4,
            default=(1.0, 1.0, 1.0, 1.0), min=0.0, max=1.0
        )


# -------------------------
# Draw (Blender 4.3 builtin)
# -------------------------

def _draw_circle_2d(center, radius_px, segments=64):
    if center is None or radius_px is None or radius_px <= 0.5:
        return
    cx, cy = center
    verts = []
    for i in range(segments + 1):
        t = (i / segments) * math.tau
        verts.append((cx + math.cos(t) * radius_px, cy + math.sin(t) * radius_px, 0.0))

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINE_STRIP", {"pos": verts})

    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(2.0)
    shader.bind()
    shader.uniform_float("color", (1.0, 1.0, 1.0, 0.9))
    batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


def draw_callback_px(self, _context):
    _draw_circle_2d(self._brush_center_2d, self._brush_radius_px)


# -------------------------
# Cache (2D projection KDTree)
# -------------------------

def view_signature(region, rv3d):
    vm = rv3d.view_matrix
    pm = rv3d.perspective_matrix
    return (
        region.width, region.height,
        rv3d.is_perspective,
        round(vm[0][0], 6), round(vm[0][1], 6), round(vm[0][2], 6), round(vm[0][3], 6),
        round(vm[1][0], 6), round(vm[1][1], 6), round(vm[1][2], 6), round(vm[1][3], 6),
        round(vm[2][0], 6), round(vm[2][1], 6), round(vm[2][2], 6), round(vm[2][3], 6),
        round(pm[0][0], 6), round(pm[1][1], 6), round(pm[2][2], 6), round(pm[3][2], 6),
    )

def obj_matrix_sig(obj):
    mw = obj.matrix_world
    return tuple(round(mw[i][j], 6) for i in range(3) for j in range(4))

def selection_sig(bm):
    # 選択変更を雑に検知（選択頂点数 + 先頭数個のindex）
    sel = [v.index for v in bm.verts if v.select]
    sel_count = len(sel)
    head = tuple(sel[:16])
    return (sel_count, head)

def build_screen_kdtree(context, obj, only_selected):
    region = context.region
    rv3d = context.region_data

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    pts2d = []
    vidx_list = []

    mw = obj.matrix_world
    for v in bm.verts:
        if only_selected and (not v.select):
            continue
        wco = mw @ v.co
        p2d = view3d_utils.location_3d_to_region_2d(region, rv3d, wco)
        if p2d is None:
            continue
        pts2d.append((float(p2d.x), float(p2d.y), 0.0))
        vidx_list.append(v.index)

    kd = KDTree(len(pts2d))
    for i, p in enumerate(pts2d):
        kd.insert(Vector(p), i)
    kd.balance()

    return kd, vidx_list, len(pts2d)

def find_range_with_weights(kd, vidx_list, mouse_xy, radius_px, power):
    mx, my = mouse_xy
    center = Vector((mx, my, 0.0))

    hits = []
    for (co, k_i, dist) in kd.find_range(center, radius_px):
        t = max(0.0, 1.0 - (dist / radius_px))
        w = (t ** power) if power != 1.0 else t
        hits.append((vidx_list[k_i], float(dist), float(w)))

    # dist昇順
    hits.sort(key=lambda x: x[1])
    return hits


# -------------------------
# Paint / Eyedropper
# -------------------------

def ensure_color_attribute(obj, name="color"):
    me = obj.data
    ca = me.color_attributes.get(name)
    if ca is None:
        ca = me.color_attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
    return ca

def apply_color_to_verts(obj, vert_hits, color_rgba):
    """
    vert_hits: [(vidx, dist_px, weight), ...]
    weightでブレンド（既存色と lerp）
    """
    ca = ensure_color_attribute(obj, "color")
    layer = ca.data  # POINTなので頂点数と同じ

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # 既存色へブレンド
    r, g, b, a = color_rgba
    for vidx, _d, w in vert_hits:
        i = int(vidx)
        cur = layer[i].color  # (r,g,b,a)
        # lerp(cur, target, w)
        layer[i].color = (
            cur[0] + (r - cur[0]) * w,
            cur[1] + (g - cur[1]) * w,
            cur[2] + (b - cur[2]) * w,
            cur[3] + (a - cur[3]) * w,
        )

    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)

def eyedrop_color_from_verts(obj, vert_hits):
    """
    半径内の加重平均色（weight合計で正規化）
    """
    me = obj.data
    ca = me.color_attributes.get("color")
    if ca is None:
        return None

    layer = ca.data
    total = 0.0
    acc = Vector((0.0, 0.0, 0.0, 0.0))
    for vidx, _d, w in vert_hits:
        c = layer[int(vidx)].color
        acc += Vector((c[0], c[1], c[2], c[3])) * w
        total += w
    if total <= 1e-8:
        return None
    out = acc / total
    return (float(out[0]), float(out[1]), float(out[2]), float(out[3]))


# -------------------------
# Modal Operator
# -------------------------

class VIEW3D_OT_pvb_modal(bpy.types.Operator):
    bl_idname = "view3d.pvb_modal"
    bl_label = "Pseudo Vertex Brush (Modal)"
    bl_options = {'REGISTER'}

    _draw_handle = None
    _brush_center_2d = None
    _brush_radius_px = None

    _painting = False
    _last_primary = None

    # cache
    _kd = None
    _vidx_list = None
    _proj_count = 0
    _view_sig = None
    _obj_name = None
    _obj_mw_sig = None
    _sel_sig = None

    def invoke(self, context, event):
        ensure_scene_props()

        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Run in a 3D View")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Active object must be a mesh")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Switch to Edit Mode first")
            return {'CANCELLED'}

        # draw handler
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL'
        )

        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("PVB: LMB drag=apply | Shift+RMB=eyedrop | RMB/ESC=exit | [ ] radius")
        print("[PVB] start")
        return {'RUNNING_MODAL'}

    def finish(self, context):
        if self._draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
        if context.area:
            context.area.header_text_set(None)
        self._kd = None
        self._vidx_list = None
        print("[PVB] end")

    def _update_brush_draw(self, context, event):
        sc = context.scene
        self._brush_center_2d = (event.mouse_region_x, event.mouse_region_y)
        self._brush_radius_px = sc.pvb_radius_px
        if context.area:
            context.area.tag_redraw()

    def _rebuild_cache(self, context):
        obj = context.active_object
        sc = context.scene

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        self._kd, self._vidx_list, self._proj_count = build_screen_kdtree(context, obj, sc.pvb_only_selected)
        self._view_sig = view_signature(context.region, context.region_data)
        self._obj_name = obj.name
        self._obj_mw_sig = obj_matrix_sig(obj)
        self._sel_sig = selection_sig(bm)
        self._last_primary = None
        print(f"[PVB] cache rebuilt (projected={self._proj_count})")

    def _ensure_cache_valid_on_press(self, context):
        """LMB PRESS時にだけ呼ぶ（軽量化の本丸）"""
        obj = context.active_object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            return False

        sc = context.scene
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        need = False
        if self._kd is None:
            need = True
        if obj.name != self._obj_name:
            need = True
        if obj_matrix_sig(obj) != self._obj_mw_sig:
            need = True
        if view_signature(context.region, context.region_data) != self._view_sig:
            need = True
        if sc.pvb_only_selected:
            if selection_sig(bm) != self._sel_sig:
                need = True

        if need:
            self._rebuild_cache(context)

        return True

    def _compute_hits(self, context, event):
        sc = context.scene
        if self._kd is None or self._proj_count == 0:
            return []
        mx, my = event.mouse_region_x, event.mouse_region_y
        return find_range_with_weights(
            self._kd, self._vidx_list, (mx, my), sc.pvb_radius_px, sc.pvb_falloff_power
        )

    def modal(self, context, event):
        # ナビは通す（Panel起動でもカメラ操作できる）
        if event.type in {
            'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE'
        } or event.alt:
            return {'PASS_THROUGH'}

        # 終了
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS' and (not event.shift):
            self.finish(context)
            return {'CANCELLED'}
        if event.type == 'ESC':
            self.finish(context)
            return {'CANCELLED'}

        # スポイト（Shift+RMB）
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS' and event.shift:
            if self._ensure_cache_valid_on_press(context):
                hits = self._compute_hits(context, event)
                if hits:
                    col = eyedrop_color_from_verts(context.active_object, hits)
                    if col is not None:
                        context.scene.pvb_color = col
                        print(f"[Eyedrop] color={tuple(round(x,4) for x in col)}  hits={len(hits)}")
            return {'RUNNING_MODAL'}

        # 半径変更（描画即更新）
        if event.type == 'LEFT_BRACKET' and event.value == 'PRESS':
            context.scene.pvb_radius_px = max(1.0, context.scene.pvb_radius_px / 1.1)
            self._brush_radius_px = context.scene.pvb_radius_px
            if context.area:
                context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type == 'RIGHT_BRACKET' and event.value == 'PRESS':
            context.scene.pvb_radius_px = min(5000.0, context.scene.pvb_radius_px * 1.1)
            self._brush_radius_px = context.scene.pvb_radius_px
            if context.area:
                context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        # ブラシ円は常時表示
        if event.type in {'MOUSEMOVE', 'LEFTMOUSE'}:
            self._update_brush_draw(context, event)

        # ドラッグ中のみ計算＆適用
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if not self._ensure_cache_valid_on_press(context):
                return {'RUNNING_MODAL'}
            self._painting = True

            hits = self._compute_hits(context, event)
            if hits:
                apply_color_to_verts(context.active_object, hits, context.scene.pvb_color)
                # primary（最寄り）だけprint（大量spam防止）
                primary = hits[0][0]
                if primary != self._last_primary:
                    self._last_primary = primary
                    print(f"[Apply] primary_vert={primary} hits={len(hits)}")
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._painting = False
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE' and self._painting:
            hits = self._compute_hits(context, event)
            if hits:
                apply_color_to_verts(context.active_object, hits, context.scene.pvb_color)
                primary = hits[0][0]
                if primary != self._last_primary:
                    self._last_primary = primary
                    print(f"[Apply] primary_vert={primary} hits={len(hits)}")
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}


# -------------------------
# Panel + Stop operator
# -------------------------

class VIEW3D_OT_pvb_stop(bpy.types.Operator):
    bl_idname = "view3d.pvb_stop"
    bl_label = "Stop PVB"

    def execute(self, context):
        # 走ってるモーダルを強制停止は難しいので「ユーザーにRMB/ESCで終わらせてね」が基本。
        # ただし、モーダルが1つだけなら Esc を投げる等のhackが必要になるのでここは素直に。
        self.report({'INFO'}, "Use RMB or ESC in the viewport to exit the brush.")
        return {'FINISHED'}


class VIEW3D_PT_pvb_panel(bpy.types.Panel):
    bl_label = "Pseudo Vertex Brush"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PVB"

    def draw(self, context):
        ensure_scene_props()
        sc = context.scene
        layout = self.layout

        col = layout.column(align=True)
        col.operator("view3d.pvb_modal", text="Start Brush", icon='BRUSH_DATA')
        col.operator("view3d.pvb_stop", text="How to Stop", icon='INFO')

        layout.separator()
        layout.prop(sc, "pvb_radius_px")
        layout.prop(sc, "pvb_falloff_power")
        layout.prop(sc, "pvb_only_selected")
        layout.prop(sc, "pvb_color")


# -------------------------
# Register
# -------------------------

classes = (
    VIEW3D_OT_pvb_modal,
    VIEW3D_OT_pvb_stop,
    VIEW3D_PT_pvb_panel,
)

def register():
    ensure_scene_props()
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()