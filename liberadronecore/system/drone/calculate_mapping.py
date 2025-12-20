import bpy
import numpy as np

from scipy.optimize import linear_sum_assignment

# =========================
# 設定
# =========================
USE_WORLD_COORDS = True
PAIR_ATTR_NAME = "pair_id"

# =========================
# ユーティリティ
# =========================
def get_two_selected_mesh_objects():
    objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(objs) != 2:
        raise RuntimeError("メッシュオブジェクトをちょうど2つ選択してください。")

    active = bpy.context.view_layer.objects.active
    if active not in objs:
        A, B = objs[0], objs[1]
    else:
        A = active
        B = objs[0] if objs[1] == active else objs[1]
    return A, B


def get_world_vertex_array(obj, use_world=True):
    me = obj.data
    mat = obj.matrix_world
    if use_world:
        coords = np.array([mat @ v.co for v in me.vertices], dtype=np.float64)
    else:
        coords = np.array([v.co for v in me.vertices], dtype=np.float64)
    return coords

def hungarian_from_points(P, Q):
    """P,Q: (N,3)。距離二乗でハンガリアン。"""
    diff = P[:, None, :] - Q[None, :, :]
    d2 = np.sum(diff * diff, axis=2)
    r, c = linear_sum_assignment(d2)

    N = P.shape[0]
    p2q = np.empty(N, dtype=np.int32)
    q2p = np.empty(N, dtype=np.int32)
    p2q[r] = c
    q2p[c] = r
    return p2q, q2p


def ensure_int_point_attr(mesh, name):
    attr = mesh.attributes.get(name)
    if attr is None:
        attr = mesh.attributes.new(name=name, type='INT', domain='POINT')
    else:
        if attr.data_type != 'INT' or attr.domain != 'POINT':
            mesh.attributes.remove(attr)
            attr = mesh.attributes.new(name=name, type='INT', domain='POINT')
    return attr

# =========================
# メイン
# =========================
def main():
    objA, objB = get_two_selected_mesh_objects()
    print(f"A: {objA.name}, B: {objB.name}")

    ptsA = get_world_vertex_array(objA, USE_WORLD_COORDS)
    ptsB = get_world_vertex_array(objB, USE_WORLD_COORDS)

    if ptsA.shape[0] != ptsB.shape[0]:
        raise RuntimeError("A/B の頂点数が一致していません。")

    # 3) リラックス空間で Hungarian
    print("[match] Hungarian on relaxed coords ...")
    pairA, pairB = hungarian_from_points(ptsA, ptsB)

    # 4) pair_id 属性として書き込み
    meshA = objA.data
    meshB = objB.data

    attrB = ensure_int_point_attr(meshB, PAIR_ATTR_NAME)

    # B側は「対応するAのindex」
    attrB.data.foreach_set("value", pairB.astype(np.int32))

    meshA.update()
    meshB.update()

if __name__ == "__main__":
    main()
