import bpy

# -----------------------------------------
# Matplotlib backend: Qt6 (PySide6)
# -----------------------------------------
import numpy as np
import matplotlib
matplotlib.use("QtAgg")  # Qt5/Qt6 backend
from matplotlib import style
style.use("dark_background")

from PySide6 import QtCore, QtWidgets

from liberadronecore.overlay import checker as overlay_checker

from matplotlib.figure import Figure
from matplotlib import patches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar


# =========================
# Settings
# =========================
BIN_FRAMES = 4
COLOR_BY = "high"            # "high" or "close" (value used for color)
TARGET_COLLECTION_NAME = "Formation"

COLOR_OK = "#2ecc71"
COLOR_WARN = "#e74c3c"
COLOR_NEUTRAL = "#7f8c8d"

METRICS = [
    ("speed_up", "Max Speed Up", "ld_proxy_max_speed_up", False),
    ("speed_down", "Max Speed Down", "ld_proxy_max_speed_down", False),
    ("speed_horiz", "Max Speed Horiz", "ld_proxy_max_speed_horiz", False),
    ("acc", "Max Acc", "ld_proxy_max_acc_vert", False),
    ("min_distance", "Min Distance", "ld_proxy_min_distance", True),
]

def _ensure_qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        # Blender may not have a Qt event loop running.
        app = QtWidgets.QApplication([])
    return app


def _get_fps(scene: bpy.types.Scene) -> float:
    fps = float(getattr(scene.render, "fps", 0.0))
    base = float(getattr(scene.render, "fps_base", 1.0) or 1.0)
    if base <= 0.0:
        base = 1.0
    if fps <= 0.0:
        fps = 24.0
    return fps / base


def _positions_to_numpy(positions):
    if not positions:
        return np.zeros((0, 3), dtype=np.float64)
    return np.asarray([[p.x, p.y, p.z] for p in positions], dtype=np.float64)


def _collect_positions(scene, depsgraph):
    positions, _signature = overlay_checker._collect_formation_positions(scene, depsgraph)
    return positions


def _sample_metric_series(scene):
    f0, f1 = scene.frame_start, scene.frame_end
    frames = list(range(f0, f1 + 1))
    fps = _get_fps(scene)

    series = {
        "speed_up": [],
        "speed_down": [],
        "speed_horiz": [],
        "acc": [],
        "min_distance": [],
    }
    prev_positions_np = None
    prev_vel_np = None
    prev_frame = None

    view_layer = bpy.context.view_layer

    suspend = None
    try:
        from liberadronecore.tasks import ledeffects_task
        suspend = getattr(ledeffects_task, "suspend_led_effects", None)
    except Exception:
        suspend = None

    if suspend is not None:
        suspend(True)
    try:
        for f in frames:
            scene.frame_set(f)
            if view_layer is not None:
                view_layer.update()

            depsgraph = bpy.context.evaluated_depsgraph_get()
            positions = _collect_positions(scene, depsgraph)
            if not positions:
                for key in series:
                    series[key].append(0.0)
                prev_positions_np = None
                prev_vel_np = None
                prev_frame = None
                continue

            positions_np = _positions_to_numpy(positions)
            if prev_positions_np is None or prev_positions_np.shape[0] != positions_np.shape[0] or prev_frame is None:
                speed_vert = [0.0] * len(positions)
                speed_horiz = [0.0] * len(positions)
                acc = [0.0] * len(positions)
                prev_vel_np = np.zeros_like(positions_np)
            else:
                frame_delta = f - prev_frame
                if frame_delta == 0:
                    frame_delta = 1
                dt = (frame_delta / fps) if fps > 0.0 else 1.0
                vel = (positions_np - prev_positions_np) / dt
                speed_vert = vel[:, 2].tolist()
                speed_horiz = np.linalg.norm(vel[:, :2], axis=1).tolist()
                if prev_vel_np is None or prev_vel_np.shape[0] != vel.shape[0]:
                    acc = [0.0] * len(positions)
                else:
                    acc_vec = (vel - prev_vel_np) / dt
                    acc = np.linalg.norm(acc_vec, axis=1).tolist()
                prev_vel_np = vel

            min_dist = overlay_checker._compute_min_distances(positions)

            max_up = max([v for v in speed_vert if v > 0.0] or [0.0])
            max_down = abs(min([v for v in speed_vert if v < 0.0] or [0.0]))
            max_horiz = max(speed_horiz or [0.0])
            max_acc = max(acc or [0.0])
            min_distance = min(min_dist or [0.0])

            series["speed_up"].append(max_up)
            series["speed_down"].append(max_down)
            series["speed_horiz"].append(max_horiz)
            series["acc"].append(max_acc)
            series["min_distance"].append(min_distance)

            prev_positions_np = positions_np
            prev_frame = f
    finally:
        if suspend is not None:
            suspend(False)

    return frames, series

def _to_ohlc(frames, values, bin_frames):
    # (x_center_frame, open, high, low, close)
    out = []
    n = len(values)
    for start in range(0, n, bin_frames):
        chunk = values[start:start + bin_frames]
        if not chunk:
            continue
        o = chunk[0]
        c = chunk[-1]
        h = max(chunk)
        l = min(chunk)

        center_idx = min(start + (len(chunk) // 2), len(frames) - 1)
        x = frames[center_idx]
        out.append((x, o, h, l, c))
    return out


def _pick_color(value: float, limit: float | None, invert: bool):
    if limit and limit > 0.0:
        is_error = value < limit if invert else value > limit
        return COLOR_WARN if is_error else COLOR_OK
    return COLOR_NEUTRAL

def _draw_candles(ax, ohlc, candle_width_frames: float, title: str, limit: float | None, invert: bool):
    ax.clear()
    ax.set_title(title)

    for x, o, h, l, c in ohlc:
        rep = h if COLOR_BY == "high" else c
        color = _pick_color(rep, limit, invert)

        ax.vlines(x, l, h, linewidth=1, color=color)

        y0 = min(o, c)
        height = abs(c - o)
        if height == 0:
            height = 1e-9

        rect = patches.Rectangle(
            (x - candle_width_frames / 2.0, y0),
            candle_width_frames,
            height,
            facecolor=color,
            edgecolor=color,
            linewidth=1,
            alpha=0.35,
        )
        ax.add_patch(rect)

    if limit and limit > 0.0:
        ax.axhline(limit, color=COLOR_WARN, linewidth=1, linestyle="--", alpha=0.6)

    ax.grid(True, color="#333333")

class VelocityCandleWindow(QtWidgets.QMainWindow):
    _instance = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LiberaDrone Check Graph (Candles)")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        top_row = QtWidgets.QHBoxLayout()
        root.addLayout(top_row)
        top_row.addWidget(QtWidgets.QLabel(f"Target: {TARGET_COLLECTION_NAME}"))

        top_row.addWidget(QtWidgets.QLabel("Bin Frames"))
        self.spin_bin = QtWidgets.QSpinBox()
        self.spin_bin.setRange(1, 600)
        self.spin_bin.setValue(BIN_FRAMES)
        self.spin_bin.setSingleStep(1)
        top_row.addWidget(self.spin_bin)

        self.btn_refresh = QtWidgets.QPushButton("Refresh (resample)")
        top_row.addWidget(self.btn_refresh)
        top_row.addStretch(1)

        grid = QtWidgets.QGridLayout()
        root.addLayout(grid)

        self.metric_checks = {}
        for idx, (key, label, _limit_prop, _invert) in enumerate(METRICS):
            cb = QtWidgets.QCheckBox(label)
            cb.setChecked(True)
            cb.stateChanged.connect(self.redraw)
            self.metric_checks[key] = cb
            row = idx // 3
            col = idx % 3
            grid.addWidget(cb, row, col)

        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        root.addWidget(self.toolbar)
        root.addWidget(self.canvas)

        self.frames = []
        self.ohlc = {}

        self.btn_refresh.clicked.connect(self.resample_and_redraw)
        self.spin_bin.valueChanged.connect(self.resample_and_redraw)

        self.resample_and_redraw()

    def resample_and_redraw(self):
        scene = bpy.context.scene
        col = bpy.data.collections.get(TARGET_COLLECTION_NAME)
        if col is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Formation collection not found")
            return

        frames, series = _sample_metric_series(scene)
        bin_frames = int(self.spin_bin.value())
        self.frames = frames
        self.ohlc = {key: _to_ohlc(frames, series[key], bin_frames) for key in series}

        self.redraw()

    def redraw(self):
        scene = bpy.context.scene
        targets = []
        for key, label, limit_prop, invert in METRICS:
            cb = self.metric_checks.get(key)
            if cb is not None and cb.isChecked():
                targets.append((key, label, limit_prop, invert))

        self.fig.clear()

        if not targets:
            ax = self.fig.add_subplot(1, 1, 1)
            ax.text(0.5, 0.5, "No metric selected", ha="center", va="center")
            ax.set_axis_off()
            self.canvas.draw_idle()
            return

        bin_frames = int(self.spin_bin.value())
        candle_width = max(1.0, bin_frames * 0.6)

        first_ax = None
        for i, (key, label, limit_prop, invert) in enumerate(targets, start=1):
            ax = self.fig.add_subplot(len(targets), 1, i, sharex=first_ax)
            if first_ax is None:
                first_ax = ax

            limit = float(getattr(scene, limit_prop, 0.0)) if scene else 0.0
            _draw_candles(ax, self.ohlc.get(key, []), candle_width, label, limit, invert)

            if i == len(targets):
                ax.set_xlabel("Frame (center of bin)")
            else:
                ax.tick_params(labelbottom=False)

        self.fig.suptitle("Green: within limit, Red: over limit", fontsize=9, color="#e0e0e0")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    @staticmethod
    def show_window():
        _ensure_qapp()

        if VelocityCandleWindow._instance is not None:
            try:
                VelocityCandleWindow._instance.close()
            except Exception:
                pass

        VelocityCandleWindow._instance = VelocityCandleWindow()
        VelocityCandleWindow._instance.resize(1100, 800)
        VelocityCandleWindow._instance.show()
        return VelocityCandleWindow._instance

if __name__ == "__main__":
    VelocityCandleWindow.show_window()



