import bpy
import numpy as np

try:
    from scipy.optimize import linear_sum_assignment
except ImportError as e:
    raise ImportError(
        "SciPy が見つかりませんでした。Blender の Python に scipy を入れてください。"
    ) from e


def get_two_selected_mesh_objects():
    objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(objs) != 2:
        raise RuntimeError("メッシュをちょうど2つ選択してください。")

    active = bpy.context.view_layer.objects.active
    if active in objs:
        A = active
        B = objs[0] if objs[1] == active else objs[1]
    else:
        A, B = objs[0], objs[1]
    return A, B


def get_world_vertex_array(obj):
    me = obj.data
    mat = obj.matrix_world
    return np.array([mat @ v.co for v in me.vertices], dtype=np.float64)


def compute_relative_coords(points):
    pts = np.asarray(points, dtype=np.float64)
    mn = pts.min(axis=0)
    mx = pts.max(axis=0)
    size = mx - mn
    size[size == 0.0] = 1.0
    return (pts - mn) / size


def compute_pair_id_hungarian_y_priority(relA, relB,
                                        W_NEG=1e6, W_POS=1e3, W_OTHER=1.0, W_TIE=1e-3):
    """
    コスト優先: Y- -> Y+ -> その他
    dy = B.y - A.y
    dy_neg = max(-dy, 0)  # 下方向移動量
    dy_pos = max(dy, 0)   # 上方向移動量
    cost = W_NEG*dy_neg + W_POS*dy_pos + W_OTHER*(|dx|+|dz|) + W_TIE*(dx^2+dy^2+dz^2)
    """
    if relA.shape != relB.shape:
        raise RuntimeError("A/B の頂点数が一致しません。")

    diff = relA[:, None, :] - relB[None, :, :]   # (N,N,3) = A - B
    dx = diff[:, :, 0]
    dy = (relB[None, :, 1] - relA[:, None, 1])   # (N,N) = B.y - A.y（移動方向）
    dz = diff[:, :, 2]

    dy_neg = np.maximum(-dy, 0.0)
    dy_pos = np.maximum(dy, 0.0)

    other = np.abs(dx) + np.abs(dz)
    tie = dx*dx + dy*dy + dz*dz

    cost = (W_NEG * dy_neg) + (W_POS * dy_pos) + (W_OTHER * other) + (W_TIE * tie)

    row_ind, col_ind = linear_sum_assignment(cost)

    N = relA.shape[0]
    pair_A_to_B = np.empty(N, dtype=np.int32)
    pair_B_to_A = np.empty(N, dtype=np.int32)
    pair_A_to_B[row_ind] = col_ind
    pair_B_to_A[col_ind] = row_ind
    return pair_A_to_B, pair_B_to_A


def write_int_point_attribute(obj, values, name="pair_id"):
    me = obj.data
    if len(me.vertices) != len(values):
        raise RuntimeError("頂点数と values 長が一致しません。")

    attr = me.attributes.get(name)
    if attr is None or attr.data_type != 'INT' or attr.domain != 'POINT':
        if attr is not None:
            me.attributes.remove(attr)
        attr = me.attributes.new(name=name, type='INT', domain='POINT')

    for i, d in enumerate(attr.data):
        d.value = int(values[i])

    me.update()


def main():
    objA, objB = get_two_selected_mesh_objects()
    ptsA = get_world_vertex_array(objA)
    ptsB = get_world_vertex_array(objB)

    if len(ptsA) != len(ptsB):
        raise RuntimeError("A/Bの頂点数が違います。")

    relA = compute_relative_coords(ptsA)
    relB = compute_relative_coords(ptsB)

    print("Hungarian: computing pair_id with Y- -> Y+ priority...")
    pairA, pairB = compute_pair_id_hungarian_y_priority(relA, relB)

    # 両方のメッシュに同じ名前 pair_id で書く（中身は「相手側のindex」）
    write_int_point_attribute(objA, pairA, name="pair_id")  # Aのpair_id = Bのindex
    write_int_point_attribute(objB, pairB, name="pair_id")  # Bのpair_id = Aのindex

    print(f"[OK] Wrote 'pair_id' on both: {objA.name} and {objB.name}")


if __name__ == "__main__":
    main()
