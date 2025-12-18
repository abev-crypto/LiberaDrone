""""
Docstring for liberadronecore.overlay.checker
頂点属性に基づいて、チェックマークを3Dビューに描画するオーバーレイ
TODO 横速度 上速度 下速度 加速度 距離制限の各オーバーレイを作成
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

# === 設定項目 ===
TARGET_OBJ_NAME = "Cube"   # GN で頂点属性を書き込んでいるオブジェクト名
ATTR_NAME = "err_close"         # 頂点の Bool 属性名

_handler = None  # draw handler のハンドル


def draw_gn_vertex_markers():
    """GN で書き込んだ頂点属性を見て、その頂点位置にポイント描画"""

    obj = bpy.data.objects.get(TARGET_OBJ_NAME)

    # 評価済みオブジェクトを取得（GN モディファイアの結果を反映）
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)

    mesh = getattr(eval_obj, "data", None)

    attr = mesh.attributes.get(ATTR_NAME)


    coords = []

    # 頂点ごとに属性をチェック
    for i, v in enumerate(mesh.vertices):
        if i >= len(attr.data):
            break

        data = attr.data[i]

        # 属性の data_type に応じて True/False 判定
        val = getattr(data, "value", None)

        # BOOLEAN や FLOAT(0/1)どちらでも動くようにゆるく判定しておく
        if isinstance(val, bool):
            flag = val
        else:
            flag = float(val) > 0.5

        if flag:
            # ワールド座標に変換して保存
            world_co = eval_obj.matrix_world @ v.co
            coords.append(world_co)

    if not coords:
        return

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": coords})

    # ---- ココから描画設定 ----
    gpu.state.blend_set('ALPHA')

    # 一番上に描画したいので、デプステストを無効化
    gpu.state.depth_test_set('NONE')
    # 必要なら深度書き込みも止める（なくてもOKだけど安全）
    gpu.state.depth_mask_set(False)

    gpu.state.point_size_set(6.0)

    shader.bind()
    shader.uniform_float("color", (0.1, 0.8, 1.0, 1.0))
    batch.draw(shader)

    # 状態戻す（お好みで）
    gpu.state.depth_mask_set(True)
    gpu.state.depth_test_set('LESS_EQUAL')


class VIEW3D_OT_draw_gn_vertex_markers(bpy.types.Operator):
    """Toggle drawing GN vertex markers in viewport"""
    bl_idname = "view3d.draw_gn_vertex_markers"
    bl_label = "Toggle GN Vertex Markers"

    def execute(self, context):
        global _handler

        if _handler is None:
            _handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_gn_vertex_markers,
                (),
                'WINDOW',
                'POST_VIEW'
            )
            self.report({'INFO'}, "GN vertex markers: ON")
        else:
            bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
            _handler = None
            self.report({'INFO'}, "GN vertex markers: OFF")

        # 再描画
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(
        VIEW3D_OT_draw_gn_vertex_markers.bl_idname,
        text="Toggle GN Vertex Markers"
    )


classes = (
    VIEW3D_OT_draw_gn_vertex_markers,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_view.append(menu_func)


def unregister():
    global _handler
    if _handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
        _handler = None

    bpy.types.VIEW3D_MT_view.remove(menu_func)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
