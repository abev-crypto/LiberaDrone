import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

# =========================================================
# ユーザー設定
# =========================================================
V_MAX = 2.0        # 最大速度 (m/s)
A_MAX = 8.0        # 最大加速度 (m/s^2)
J_MAX = 60.0       # 最大ジャーク (m/s^3)  小さいほど滑らか

D_MIN = 0.30       # 最小距離 (m)

# =========================================================
# Limits from ProxyPoints (scene)
# =========================================================
def _max_positive(values, default):
    vals = [v for v in values if v > 0.0]
    return max(vals) if vals else default


def _limit_positive(value, default):
    return value if value > 0.0 else default


def _get_proxy_limits(scene):
    if scene is None:
        return V_MAX, V_MAX, V_MAX, V_MAX, A_MAX, J_MAX, D_MIN
    max_up = float(getattr(scene, "ld_proxy_max_speed_up", 0.0))
    max_down = float(getattr(scene, "ld_proxy_max_speed_down", 0.0))
    max_horiz = float(getattr(scene, "ld_proxy_max_speed_horiz", 0.0))
    max_acc = float(getattr(scene, "ld_proxy_max_acc_vert", 0.0))
    min_dist = float(getattr(scene, "ld_proxy_min_distance", 0.0))
    v_max_up = _limit_positive(max_up, V_MAX)
    v_max_down = _limit_positive(max_down, V_MAX)
    v_max_horiz = _limit_positive(max_horiz, V_MAX)
    v_max = _max_positive([v_max_up, v_max_down, v_max_horiz], V_MAX)
    a_max = _limit_positive(max_acc, A_MAX)
    d_min = _limit_positive(min_dist, D_MIN)
    return v_max_up, v_max_down, v_max_horiz, v_max, a_max, J_MAX, d_min


def _expand_distance_limit(value: float, scale: float) -> float:
    return value * scale if value > 0.0 else value


def _get_scene_setting(scene, name: str, default, cast):
    if scene is None:
        return default
    try:
        return cast(getattr(scene, name, default))
    except Exception:
        return default


def _get_transition_settings(scene):
    max_subdiv = max(0, _get_scene_setting(scene, "ld_bakedt_max_subdiv", MAX_SUBDIV, int))
    check_relax_iters = max(0, _get_scene_setting(scene, "ld_bakedt_check_relax_iters", CHECK_RELAX_ITERS, int))
    pre_relax_iters = max(0, _get_scene_setting(scene, "ld_bakedt_pre_relax_iters", PRE_RELAX_ITERS, int))
    exp_distance = max(0.0, _get_scene_setting(scene, "ld_bakedt_exp_distance", EXP_DISTANCE, float))
    relax_dmin_scale = max(0.0, _get_scene_setting(scene, "ld_bakedt_relax_dmin_scale", RELAX_DMIN_SCALE, float))
    relax_edge_frames = max(0, _get_scene_setting(scene, "ld_bakedt_relax_edge_frames", RELAX_EDGE_FRAMES, int))
    relax_edge_ratio = max(0.0, _get_scene_setting(scene, "ld_bakedt_relax_edge_ratio", RELAX_EDGE_RATIO, float))
    speed_acc_margin = _get_scene_setting(scene, "ld_bakedt_speed_acc_margin", SPEED_ACC_MARGIN, float)
    speed_acc_margin = max(0.0, min(1.0, speed_acc_margin))
    max_neighbors = max(1, _get_scene_setting(scene, "ld_bakedt_max_neighbors", MAX_NEIGHBORS, int))
    return {
        "max_subdiv": max_subdiv,
        "check_relax_iters": check_relax_iters,
        "pre_relax_iters": pre_relax_iters,
        "exp_distance": exp_distance,
        "relax_dmin_scale": relax_dmin_scale,
        "relax_edge_frames": relax_edge_frames,
        "relax_edge_ratio": relax_edge_ratio,
        "speed_acc_margin": speed_acc_margin,
        "max_neighbors": max_neighbors,
    }


def _clamp_velocity(v: Vector, *, v_max: float, v_max_up: float, v_max_down: float, v_max_horiz: float) -> Vector:
    if v.length > 1e-12 and v.length > v_max:
        v = v * (v_max / v.length)
    if v.z > v_max_up:
        v.z = v_max_up
    elif v.z < -v_max_down:
        v.z = -v_max_down
    horiz_len = (v.x * v.x + v.y * v.y) ** 0.5
    if horiz_len > 1e-12 and horiz_len > v_max_horiz:
        scale = v_max_horiz / horiz_len
        v.x *= scale
        v.y *= scale
    return v


def _clamp_velocity_array(
    v: np.ndarray,
    *,
    v_max: float,
    v_max_up: float,
    v_max_down: float,
    v_max_horiz: float,
) -> np.ndarray:
    if v.size == 0:
        return v
    speed = np.linalg.norm(v, axis=1)
    mask = speed > v_max
    if np.any(mask):
        scale = np.ones_like(speed)
        scale[mask] = v_max / speed[mask]
        v = v * scale[:, None]

    v[:, 2] = np.clip(v[:, 2], -v_max_down, v_max_up)

    horiz = np.linalg.norm(v[:, :2], axis=1)
    mask = horiz > v_max_horiz
    if np.any(mask):
        scale = np.ones_like(horiz)
        scale[mask] = v_max_horiz / horiz[mask]
        v[:, 0] *= scale
        v[:, 1] *= scale
    return v

# 仮想ポーズ（適応分割）
MAX_SUBDIV = 3               # 再帰分割の最大深さ
SAMPLES_IN_INTERVAL = 2      # 区間チェックのサンプル数（1/3,2/3…）
CHECK_RELAX_ITERS = 4        # 判定用の軽いリラックス反復
PRE_RELAX_ITERS = 12         # 仮想ポーズ生成時の本気リラックス反復
EXP_DISTANCE = 1.25          # 距離制限緩和倍率

# 仮想ポーズの直線からの逸脱を抑える（前処理）
TETHER_PRE = 0.35            # 0..1 直線位置(base)へ戻す強さ
MAX_SHIFT_PER_POSE = 0.25    # baseから許容する最大ずれ (m)

# 本番（フレームごと）
RUN_RELAX_ITERS = 6          # 本番近接解消反復
TETHER_RUN = 0.1            # 本番は弱め（強すぎると離れない）
MAX_SHIFT_RUN = None         # Noneなら D_MIN*0.75 を使用
MAX_SHIFT_RUN_RATIO = 0.85
JERK_SCALE = 0.6             # Start/Endの急加速を緩める
RELAX_DMIN_SCALE = 1.06      # Relax d_min scale at full strength
RELAX_EDGE_FRAMES = 24       # Frames to ramp up from 1.0 at start/end
RELAX_EDGE_RATIO = 0.21875   # Ratio of transition frames (105/480)
SPEED_ACC_MARGIN = 0.995     # Safety margin for speed/acc limits

MAX_NEIGHBORS = 25           # KDTreeで見る近傍数

END_POS_TOLERANCE = 0.01     # Max allowed end position error before correction
END_CORRECTION_FRAMES = 6    # Frames used to blend into end target when off

# Bake先
COLLECTION_NAME = "Drones_Empties"
NAME_PREFIX = "DroneNull_"
EMPTY_SIZE = 0.05
CLEAR_OLD = True

# =========================================================
# Sカーブ台形（ジャーク制限）: 数値積分テーブル
# =========================================================
def build_scurve_table(L, T_total, v_max, a_max, j_max, samples=2048):
    if L <= 1e-12 or T_total <= 1e-12:
        return {"T": T_total, "ts": [0.0], "ss": [0.0], "vs": [0.0]}

    dt = T_total / (samples - 1)

    tJ = a_max / max(j_max, 1e-12)
    tJ = min(tJ, T_total * 0.25)

    # v_maxに到達する目安の加速時間
    t_acc_nom = v_max / max(a_max, 1e-12)
    tA_hold = max(0.0, t_acc_nom - 2.0 * tJ)

    t_acc = 2.0 * tJ + tA_hold
    t_cruise = max(0.0, T_total - 2.0 * t_acc)

    if T_total < 2.0 * t_acc:
        tA_hold = max(0.0, (T_total / 2.0) - 2.0 * tJ)
        t_acc = 2.0 * tJ + tA_hold
        t_cruise = 0.0

    def accel_at_time(t):
        t0 = 0.0
        t1 = t0 + tJ
        t2 = t1 + tA_hold
        t3 = t2 + tJ
        t4 = t3 + t_cruise

        if t < t0:
            return 0.0
        if t < t1:
            return j_max * (t - t0)
        if t < t2:
            return a_max
        if t < t3:
            return a_max - j_max * (t - t2)
        if t < t4:
            return 0.0

        tr = T_total - t
        if tr < t1:
            return -(j_max * (tr - t0))
        if tr < t2:
            return -a_max
        if tr < t3:
            return -(a_max - j_max * (tr - t2))
        return 0.0

    ts = [0.0]
    vs = [0.0]
    ss = [0.0]
    v = 0.0
    s = 0.0

    for n in range(1, samples):
        t_prev = (n - 1) * dt
        t = n * dt

        a0 = accel_at_time(t_prev)
        a1 = accel_at_time(t)
        a = 0.5 * (a0 + a1)

        v = v + a * dt
        if v > v_max:
            v = v_max
        if v < 0.0:
            v = 0.0

        s = s + v * dt

        ts.append(t)
        vs.append(v)
        ss.append(s)

    # 距離を L に合わせてスケール
    if ss[-1] > 1e-12:
        scale = L / ss[-1]
    else:
        scale = 1.0
    ss = [x * scale for x in ss]
    vs = [x * scale for x in vs]

    return {"T": T_total, "ts": ts, "ss": ss, "vs": vs}

def table_lookup(table, t, key="s"):
    T = table["T"]
    if t <= 0.0:
        return table["ss"][0] if key == "s" else table["vs"][0]
    if t >= T:
        return table["ss"][-1] if key == "s" else table["vs"][-1]

    ts = table["ts"]
    arr = table["ss"] if key == "s" else table["vs"]

    u = t / T
    idx = int(u * (len(ts) - 1))
    idx = max(0, min(len(ts) - 2, idx))

    t0, t1 = ts[idx], ts[idx + 1]
    a0, a1 = arr[idx], arr[idx + 1]
    if t1 - t0 <= 1e-12:
        return a0
    w = (t - t0) / (t1 - t0)
    return a0 + (a1 - a0) * w

# =========================================================
# KDTree：距離違反チェック
# =========================================================
def has_min_dist_violation(pos_list, d_min, max_neighbors=12):
    N = len(pos_list)
    if N < 2:
        return False
    d2 = d_min * d_min

    kd = KDTree(N)
    for i, p in enumerate(pos_list):
        kd.insert(p, i)
    kd.balance()

    for i, p in enumerate(pos_list):
        for (q, j, dist) in kd.find_n(p, max_neighbors + 1):
            if j == i:
                continue
            if dist * dist < d2:
                return True
    return False

# =========================================================
# 近接押し離し + tether + shift clamp
# =========================================================
def relax_pose(pos, base, d_min, iters, max_neighbors, tether, max_shift):
    N = len(pos)
    if N < 2:
        return
    d2_min = d_min * d_min

    for _ in range(iters):
        kd = KDTree(N)
        for i, p in enumerate(pos):
            kd.insert(p, i)
        kd.balance()

        moved = [Vector((0,0,0)) for _ in range(N)]

        for i, p in enumerate(pos):
            for (q, j, dist) in kd.find_n(p, max_neighbors + 1):
                if j == i:
                    continue
                if dist <= 1e-12:
                    push = Vector((d_min * 0.5, 0, 0))
                    moved[i] += push
                    moved[j] -= push
                    continue
                if dist * dist < d2_min:
                    dirv = (p - q) / dist
                    delta = (d_min - dist) * 0.5
                    moved[i] += dirv * delta
                    moved[j] -= dirv * delta

        for i in range(N):
            p = pos[i] + moved[i]
            # tether
            if tether > 0.0:
                p = p.lerp(base[i], tether)
            # clamp shift
            if max_shift is not None:
                off = p - base[i]
                L = off.length
                if L > max_shift and L > 1e-12:
                    p = base[i] + off * (max_shift / L)
            pos[i] = p

# =========================================================
# 適応仮想ポーズ生成（時間中間→リラックス→必要なら再帰分割）
# =========================================================
def base_pose_at_time(Aw, Ew, L_base, table, t):
    s = table_lookup(table, t, key="s")
    u = 0.0 if L_base <= 1e-12 else min(1.0, max(0.0, s / L_base))
    return [Aw[i].lerp(Ew[i], u) for i in range(len(Aw))]

def interval_needs_split(
    Aw, Ew, L_base, table,
    t0, t1,
    d_min,
    tether, max_shift,
    check_relax_iters=4,
    samples_in_interval=2,
    max_neighbors=12
):
    if t1 - t0 <= 1e-8:
        return False

    for sidx in range(1, samples_in_interval + 1):
        w = sidx / (samples_in_interval + 1)
        ts = t0 + (t1 - t0) * w

        base = base_pose_at_time(Aw, Ew, L_base, table, ts)
        test = [p.copy() for p in base]

        relax_pose(
            test, base,
            d_min=d_min,
            iters=check_relax_iters,
            max_neighbors=max_neighbors,
            tether=tether,
            max_shift=max_shift
        )

        if has_min_dist_violation(test, d_min, max_neighbors=max_neighbors):
            return True

    return False

def build_adaptive_poses(
    Aw, Ew, L_base, table,
    t0, t1,
    d_min,
    pre_iters,
    tether,
    max_shift,
    max_subdiv,
    max_neighbors=12,
    check_relax_iters=4,
    samples_in_interval=2,
    relax_endpoints=True
):
    base0 = base_pose_at_time(Aw, Ew, L_base, table, t0)
    base1 = base_pose_at_time(Aw, Ew, L_base, table, t1)
    pose0 = [p.copy() for p in base0]
    pose1 = [p.copy() for p in base1]

    # 端点の距離制限を無視する場合はリラックスしない
    if relax_endpoints:
        relax_pose(pose0, base0, d_min, pre_iters, max_neighbors, tether, max_shift)
        relax_pose(pose1, base1, d_min, pre_iters, max_neighbors, tether, max_shift)

    poses = [(t0, pose0), (t1, pose1)]

    def rec(tL, pL, tR, pR, depth):
        if depth >= max_subdiv:
            return

        if not interval_needs_split(
            Aw, Ew, L_base, table,
            tL, tR,
            d_min=d_min,
            tether=tether,
            max_shift=max_shift,
            check_relax_iters=check_relax_iters,
            samples_in_interval=samples_in_interval,
            max_neighbors=max_neighbors
        ):
            return

        tM = 0.5 * (tL + tR)
        baseM = base_pose_at_time(Aw, Ew, L_base, table, tM)
        pM = [p.copy() for p in baseM]
        relax_pose(pM, baseM, d_min, pre_iters, max_neighbors, tether, max_shift)

        poses.append((tM, pM))
        rec(tL, pL, tM, pM, depth + 1)
        rec(tM, pM, tR, pR, depth + 1)

    rec(t0, pose0, t1, pose1, 0)
    poses.sort(key=lambda x: x[0])
    return poses  # [(t, pose[N]), ...]

# =========================================================
# 折れ線補間（距離sで進む）
# =========================================================
def position_along_polyline(points, seglens, s):
    if s <= 0.0:
        return points[0]
    Ltot = sum(seglens)
    if s >= Ltot:
        return points[-1]

    remain = s
    for k in range(len(points)-1):
        L = seglens[k]
        a = points[k]
        b = points[k+1]
        if L <= 1e-12:
            continue
        if remain <= L:
            t = remain / L
            return a.lerp(b, t)
        remain -= L
    return points[-1]

# =========================================================
# Blender util
# =========================================================
def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col

def clear_empties_in_collection(col):
    for obj in list(col.objects):
        if obj.type == 'EMPTY':
            bpy.data.objects.remove(obj, do_unlink=True)

def set_action_fcurves_linear(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
            kp.handle_left_type = 'VECTOR'
            kp.handle_right_type = 'VECTOR'

def get_two_selected_mesh_objects():
    meshes = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(meshes) != 2:
        raise RuntimeError("メッシュをちょうど2つ選択してください（アクティブがA、もう一つがEnd）。")
    A = bpy.context.view_layer.objects.active
    if A not in meshes:
        A = meshes[0]
    End = meshes[0] if meshes[1] == A else meshes[1]
    return A, End

# =========================================================
# Bake util for VAT tracks
# =========================================================
def build_tracks_from_positions(
    start_positions,
    end_positions,
    frame_start: int,
    frame_end: int,
    fps: float,
    *,
    scene=None,
):
    if fps <= 0.0:
        raise RuntimeError("Invalid FPS")
    if len(start_positions) != len(end_positions):
        raise RuntimeError("Start/End vertex counts do not match")

    if scene is None:
        scene = getattr(bpy, "context", None).scene if getattr(bpy, "context", None) else None
    settings = _get_transition_settings(scene)
    v_max_up, v_max_down, v_max_horiz, v_max, a_max, j_max, d_min = _get_proxy_limits(scene)
    j_max = max(1e-6, j_max * JERK_SCALE)
    d_min_relax = _expand_distance_limit(d_min, settings["exp_distance"])
    speed_margin = settings["speed_acc_margin"]
    v_max_up_run = v_max_up * speed_margin
    v_max_down_run = v_max_down * speed_margin
    v_max_horiz_run = v_max_horiz * speed_margin
    a_max_run = a_max * speed_margin
    max_neighbors = settings["max_neighbors"]
    max_subdiv = settings["max_subdiv"]
    check_relax_iters = settings["check_relax_iters"]
    pre_relax_iters = settings["pre_relax_iters"]
    relax_dmin_scale = settings["relax_dmin_scale"]
    relax_edge_frames = settings["relax_edge_frames"]
    relax_edge_ratio = settings["relax_edge_ratio"]

    start_f = int(frame_start)
    end_f = int(frame_end)
    if end_f < start_f:
        raise RuntimeError("Invalid frame range")

    frames = end_f - start_f
    if frames <= 0:
        tracks = []
        for i, pos in enumerate(start_positions):
            tracks.append(
                {
                    "name": f"Drone_{i:04d}",
                    "data": [
                        {
                            "frame": float(start_f),
                            "x": float(pos.x),
                            "y": float(pos.y),
                            "z": float(pos.z),
                            "r": 255,
                            "g": 255,
                            "b": 255,
                        }
                    ],
                }
            )
        return tracks

    T_total = frames / fps

    Aw = list(start_positions)
    Ew = list(end_positions)
    N = len(Aw)

    dists = [(Ew[i] - Aw[i]).length for i in range(N)]
    L_base = max(dists) if N else 0.0

    table = build_scurve_table(L_base, T_total, v_max, a_max, j_max, samples=2048)

    poses_t = build_adaptive_poses(
        Aw, Ew, L_base, table,
        t0=0.0, t1=T_total,
        d_min=d_min_relax,
        pre_iters=pre_relax_iters,
        tether=TETHER_PRE,
        max_shift=MAX_SHIFT_PER_POSE,
        max_subdiv=max_subdiv,
        max_neighbors=max_neighbors,
        check_relax_iters=check_relax_iters,
        samples_in_interval=SAMPLES_IN_INTERVAL,
        relax_endpoints=False
    )

    K = len(poses_t)
    poses = [pose for (t, pose) in poses_t]
    pose_times_np = np.asarray([t for (t, pose) in poses_t], dtype=np.float64)
    pose_s_np = np.asarray([table_lookup(table, t, key="s") for t in pose_times_np], dtype=np.float64)

    poses_np = np.asarray(
        [[(p.x, p.y, p.z) for p in pose] for pose in poses],
        dtype=np.float64,
    ) if N else np.zeros((0, 0, 3), dtype=np.float64)

    cur_pos_np = np.asarray(
        [[p.x, p.y, p.z] for p in poses[0]],
        dtype=np.float64,
    ) if N else np.zeros((0, 3), dtype=np.float64)
    prev_vel_np = np.zeros_like(cur_pos_np)
    dt = 1.0 / fps

    max_shift_run = (d_min_relax * MAX_SHIFT_RUN_RATIO) if (MAX_SHIFT_RUN is None) else MAX_SHIFT_RUN

    end_np = np.asarray(
        [[p.x, p.y, p.z] for p in Ew],
        dtype=np.float64,
    ) if N else np.zeros((0, 3), dtype=np.float64)
    a_max_run_base = a_max * speed_margin

    def _simulate_tracks():
        cur_pos_np = np.asarray(
            [[p.x, p.y, p.z] for p in poses[0]],
            dtype=np.float64,
        ) if N else np.zeros((0, 3), dtype=np.float64)
        prev_vel_np = np.zeros_like(cur_pos_np)
        tracks = [{"name": f"Drone_{i:04d}", "data": []} for i in range(N)]
        a_max_run = a_max_run_base

        for f in range(start_f, end_f + 1):
            t = (f - start_f) / fps

            s_base = table_lookup(table, t, key="s")
            v_allow = table_lookup(table, t, key="v")
            if K <= 1:
                target_np = poses_np[0] if K else np.zeros((0, 3), dtype=np.float64)
            else:
                seg_idx = np.searchsorted(pose_times_np, t, side="right") - 1
                seg_idx = int(np.clip(seg_idx, 0, K - 2))
                s0 = pose_s_np[seg_idx]
                s1 = pose_s_np[seg_idx + 1]
                denom = s1 - s0
                if abs(denom) <= 1e-12:
                    t0 = pose_times_np[seg_idx]
                    t1 = pose_times_np[seg_idx + 1]
                    denom_t = t1 - t0
                    alpha = (t - t0) / denom_t if denom_t > 1e-12 else 0.0
                else:
                    alpha = (s_base - s0) / denom
                if alpha < 0.0:
                    alpha = 0.0
                elif alpha > 1.0:
                    alpha = 1.0
                p0 = poses_np[seg_idx]
                p1 = poses_np[seg_idx + 1]
                target_np = p0 + (p1 - p0) * alpha

            target = [Vector((float(x), float(y), float(z))) for x, y, z in target_np]
            next_pos = [p.copy() for p in target]

            if relax_edge_ratio > 0.0:
                edge_frames = int(round(frames * relax_edge_ratio))
            else:
                edge_frames = int(relax_edge_frames)
            edge_frames = max(1, edge_frames)
            edge_dist = min(f - start_f, end_f - f)
            if edge_dist <= 0:
                d_min_scale = 1.0
            else:
                ramp = edge_dist / edge_frames
                if ramp > 1.0:
                    ramp = 1.0
                d_min_scale = 1.0 + (relax_dmin_scale - 1.0) * ramp
            d_min_run = d_min * d_min_scale

            relax_pose(
                next_pos,
                base=target,
                d_min=d_min_run,
                iters=RUN_RELAX_ITERS,
                max_neighbors=max_neighbors,
                tether=TETHER_RUN,
                max_shift=max_shift_run,
            )

            v_allow = min(v_max, max(0.0, v_allow)) * speed_margin

            next_pos_np = np.asarray(
                [[p.x, p.y, p.z] for p in next_pos],
                dtype=np.float64,
            ) if N else np.zeros((0, 3), dtype=np.float64)

            v = (next_pos_np - cur_pos_np) / dt
            v = _clamp_velocity_array(
                v,
                v_max=v_allow,
                v_max_up=v_max_up_run,
                v_max_down=v_max_down_run,
                v_max_horiz=v_max_horiz_run,
            )
            next_pos_np = cur_pos_np + v * dt

            dv = v - prev_vel_np
            acc = np.linalg.norm(dv, axis=1) / dt
            acc_limit = max(a_max_run, 1e-12)
            acc_mask = acc > acc_limit
            if np.any(acc_mask):
                scale = np.ones_like(acc)
                scale[acc_mask] = a_max_run / acc[acc_mask]
                dv = dv * scale[:, None]
                v2 = prev_vel_np + dv
                spd2 = np.linalg.norm(v2, axis=1)
                spd_mask = (spd2 > v_allow) & (spd2 > 1e-12)
                if np.any(spd_mask):
                    scale2 = np.ones_like(spd2)
                    scale2[spd_mask] = v_allow / spd2[spd_mask]
                    v2 = v2 * scale2[:, None]
                v = v2
                next_pos_np = cur_pos_np + v * dt

            prev_vel_np = v

            cur_pos_np = next_pos_np
            for i in range(N):
                pos = next_pos_np[i]
                tracks[i]["data"].append(
                    {
                        "frame": float(f),
                        "x": float(pos[0]),
                        "y": float(pos[1]),
                        "z": float(pos[2]),
                        "r": 255,
                        "g": 255,
                        "b": 255,
                    }
                )

        return tracks, cur_pos_np

    tracks, final_np = _simulate_tracks()
    if N <= 0:
        return tracks

    diff = final_np - end_np
    max_err = float(np.linalg.norm(diff, axis=1).max()) if diff.size else 0.0
    if max_err <= END_POS_TOLERANCE:
        return tracks

    if tracks and END_CORRECTION_FRAMES > 0:
        for i in range(N):
            if np.linalg.norm(diff[i]) <= END_POS_TOLERANCE:
                continue
            data = tracks[i].get("data") or []
            if not data:
                continue
            start_idx = max(0, len(data) - int(END_CORRECTION_FRAMES))
            span = max(1, len(data) - start_idx)
            target = end_np[i]
            for local_idx, idx in enumerate(range(start_idx, len(data))):
                t = (local_idx + 1) / span
                row = data[idx]
                row["x"] = float(row["x"] + (target[0] - row["x"]) * t)
                row["y"] = float(row["y"] + (target[1] - row["y"]) * t)
                row["z"] = float(row["z"] + (target[2] - row["z"]) * t)

    return tracks

# =========================================================
# main
# =========================================================
def main():
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    dt = 1.0 / fps
    v_max_up, v_max_down, v_max_horiz, v_max, a_max, j_max, d_min = _get_proxy_limits(scene)
    j_max = max(1e-6, j_max * JERK_SCALE)
    d_min_relax = _expand_distance_limit(d_min, 1.15)

    start_f = scene.frame_start
    end_f = scene.frame_end
    frames = end_f - start_f
    if frames <= 0:
        raise RuntimeError("フレーム範囲が不正です。")
    T_total = frames / fps

    A, End = get_two_selected_mesh_objects()
    if len(A.data.vertices) != len(End.data.vertices):
        raise RuntimeError("AとEndの頂点数が一致しません。")

    N = len(A.data.vertices)
    Aw = [A.matrix_world @ v.co for v in A.data.vertices]
    Ew = [End.matrix_world @ v.co for v in End.data.vertices]

    # 代表距離（台形になりやすいようmax）
    dists = [(Ew[i] - Aw[i]).length for i in range(N)]
    L_base = max(dists) if N else 0.0

    # 速度テーブル（Sカーブ）
    table = build_scurve_table(L_base, T_total, v_max, a_max, j_max, samples=2048)

    # 適応仮想ポーズ生成
    poses_t = build_adaptive_poses(
        Aw, Ew, L_base, table,
        t0=0.0, t1=T_total,
        d_min=d_min_relax,
        pre_iters=PRE_RELAX_ITERS,
        tether=TETHER_PRE,
        max_shift=MAX_SHIFT_PER_POSE,
        max_subdiv=MAX_SUBDIV,
        max_neighbors=MAX_NEIGHBORS,
        check_relax_iters=CHECK_RELAX_ITERS,
        samples_in_interval=SAMPLES_IN_INTERVAL
    )

    # pose点列（K点）
    K = len(poses_t)
    poses = [pose for (t, pose) in poses_t]
    pose_times = [t for (t, pose) in poses_t]

    # 各ドローンの折れ線パス長
    seglens = [[0.0]*(K-1) for _ in range(N)]
    total_len = [0.0]*N
    for i in range(N):
        L = 0.0
        for k in range(K-1):
            d = (poses[k+1][i] - poses[k][i]).length
            seglens[i][k] = d
            L += d
        total_len[i] = L

    # Empties
    col = ensure_collection(COLLECTION_NAME)
    if CLEAR_OLD:
        clear_empties_in_collection(col)

    empties = []
    for i in range(N):
        e = bpy.data.objects.new(f"{NAME_PREFIX}{i:05d}", None)
        e.empty_display_type = 'PLAIN_AXES'
        e.empty_display_size = EMPTY_SIZE
        e.location = poses[0][i]
        col.objects.link(e)
        empties.append(e)

    cur_pos = [poses[0][i].copy() for i in range(N)]
    prev_vel = [Vector((0.0,0.0,0.0)) for _ in range(N)]

    max_shift_run = (d_min_relax * MAX_SHIFT_RUN_RATIO) if (MAX_SHIFT_RUN is None) else MAX_SHIFT_RUN

    # Bake
    for f in range(start_f, end_f + 1):
        t = (f - start_f) / fps

        s_base = table_lookup(table, t, key="s")
        v_allow = table_lookup(table, t, key="v")  # Sカーブ速度そのもの
        u = 0.0 if L_base <= 1e-12 else min(1.0, max(0.0, s_base / L_base))

        # 目標位置（各ドローンは自分のパス長に比例して進む）
        target = [None]*N
        for i in range(N):
            Li = total_len[i]
            si = u * Li
            per_points = [poses[k][i] for k in range(K)]
            target[i] = position_along_polyline(per_points, seglens[i], si)

        next_pos = [p.copy() for p in target]

        # 本番近接解消（目標へ引き戻しつつ）
        relax_pose(
            next_pos,
            base=target,
            d_min=d_min_relax,
            iters=RUN_RELAX_ITERS,
            max_neighbors=MAX_NEIGHBORS,
            tether=TETHER_RUN,
            max_shift=max_shift_run
        )

        # 速度・加速度制限（暴れ止め）
        v_allow = min(v_max, max(0.0, v_allow))

        for i in range(N):
            dp = next_pos[i] - cur_pos[i]
            v = dp / dt

            v = _clamp_velocity(
                v,
                v_max=v_allow,
                v_max_up=v_max_up,
                v_max_down=v_max_down,
                v_max_horiz=v_max_horiz,
            )
            next_pos[i] = cur_pos[i] + v * dt

            dv = v - prev_vel[i]
            acc = dv.length / dt
            if acc > 1e-12 and acc > a_max:
                dv = dv * (a_max / acc)
                v2 = prev_vel[i] + dv
                spd2 = v2.length
                if spd2 > 1e-12 and spd2 > v_allow:
                    v2 = v2 * (v_allow / spd2)
                next_pos[i] = cur_pos[i] + v2 * dt
                v = v2

            prev_vel[i] = v

        # キー
        for i, e in enumerate(empties):
            cur_pos[i] = next_pos[i]
            e.location = cur_pos[i]
            e.keyframe_insert(data_path="location", frame=f)

    for e in empties:
        set_action_fcurves_linear(e)

    print(f"Done: N={N}, adaptive_poses={K}, MAX_SUBDIV={MAX_SUBDIV}, frames=[{start_f}-{end_f}]")


if __name__ == "__main__":
    main()

