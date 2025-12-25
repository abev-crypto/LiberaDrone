import bpy

# -----------------------------------------
# Matplotlib backend: Qt6(Pyside6) 対忁E
# -----------------------------------------
import matplotlib
matplotlib.use("QtAgg")  # Qt5/Qt6 backend
from matplotlib import style
style.use("dark_background")

from PySide6 import QtWidgets

from matplotlib.figure import Figure
from matplotlib import patches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar


# =========================
# ���[�U�[��?E
# =========================
BIN_FRAMES = 4
COLOR_BY = "high"            # "high" or "close" (�F?E??�Ɏg��E??�\�l)
TARGET_OBJ_NAME = "ProxyPoints"

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
        # Blender冁E��Qtイベントループが無ぁE��ース用
        app = QtWidgets.QApplication([])
    return app


def _get_attr(mesh, name: str):
    attr = mesh.attributes.get(name)
    return attr if attr is not None else None


def _get_attr_values(attr) -> list[float]:
    values: list[float] = []
    if attr is None:
        return values
    for data in attr.data:
        val = getattr(data, "value", 0.0)
        try:
            values.append(float(val))
        except Exception:
            values.append(0.0)
    return values


def _get_frame_metrics(scene):
    obj = bpy.data.objects.get(TARGET_OBJ_NAME)
    if obj is None:
        return None

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = getattr(eval_obj, "data", None)
    if mesh is None:
        return None

    speed_vert = _get_attr_values(_get_attr(mesh, "speed_vert"))
    speed_horiz = _get_attr_values(_get_attr(mesh, "speed_horiz"))
    acc = _get_attr_values(_get_attr(mesh, "acc"))
    min_dist = _get_attr_values(_get_attr(mesh, "min_distance"))

    max_up = max([v for v in speed_vert if v > 0.0] or [0.0])
    max_down = abs(min([v for v in speed_vert if v < 0.0] or [0.0]))
    max_horiz = max(speed_horiz or [0.0])
    max_acc = max(acc or [0.0])
    min_distance = min(min_dist or [0.0])

    return {
        "speed_up": max_up,
        "speed_down": max_down,
        "speed_horiz": max_horiz,
        "acc": max_acc,
        "min_distance": min_distance,
    }


def _sample_metric_series(scene):
    f0, f1 = scene.frame_start, scene.frame_end
    frames = list(range(f0, f1 + 1))

    series = {
        "speed_up": [],
        "speed_down": [],
        "speed_horiz": [],
        "acc": [],
        "min_distance": [],
    }
    for f in frames:
        scene.frame_set(f)
        metrics = _get_frame_metrics(scene)
        if metrics is None:
            for key in series:
                series[key].append(0.0)
            continue
        for key in series:
            series[key].append(metrics.get(key, 0.0))

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

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        top_row = QtWidgets.QHBoxLayout()
        root.addLayout(top_row)
        top_row.addWidget(QtWidgets.QLabel(f"Target: {TARGET_OBJ_NAME}"))

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

        self.btn_refresh.clicked.connect(self.resample_and_redraw)\n        self.spin_bin.valueChanged.connect(self.resample_and_redraw)

        self.resample_and_redraw()

    def resample_and_redraw(self):
        scene = bpy.context.scene
        obj = bpy.data.objects.get(TARGET_OBJ_NAME)
        if obj is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Target object not found")
            return

        frames, series = _sample_metric_series(scene)\n        bin_frames = int(self.spin_bin.value())\n        self.frames = frames\n        self.ohlc = {key: _to_ohlc(frames, series[key], bin_frames) for key in series}

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

        bin_frames = int(self.spin_bin.value())\n        candle_width = max(1.0, bin_frames * 0.6)

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

if __name__ == "__main__":\n    VelocityCandleWindow.show_window()\n

