import bpy
from PySide6 import QtCore, QtGui, QtWidgets

from liberadronecore.ledeffects.util import paint as paint_util
from liberadronecore.overlay import paint_preview


def _ensure_qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class PaintControlWindow(QtWidgets.QMainWindow):
    _instance = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LED Paint")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self._updating = False

        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)

        self.node_label = QtWidgets.QLabel("Node: -")
        root.addWidget(self.node_label)

        color_row = QtWidgets.QHBoxLayout()
        color_row.addWidget(QtWidgets.QLabel("Color"))
        self.color_btn = QtWidgets.QPushButton()
        self.color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self.color_btn)
        root.addLayout(color_row)

        strength_row = QtWidgets.QHBoxLayout()
        strength_row.addWidget(QtWidgets.QLabel("Strength"))
        self.alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alpha_slider.setRange(0, 1000)
        self.alpha_slider.valueChanged.connect(self._on_alpha_changed)
        strength_row.addWidget(self.alpha_slider)
        self.alpha_value = QtWidgets.QLabel("0.00")
        strength_row.addWidget(self.alpha_value)
        root.addLayout(strength_row)

        radius_row = QtWidgets.QHBoxLayout()
        radius_row.addWidget(QtWidgets.QLabel("Radius"))
        self.radius_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.radius_slider.setRange(1, 5000)
        self.radius_slider.valueChanged.connect(self._on_radius_changed)
        radius_row.addWidget(self.radius_slider)
        self.radius_value = QtWidgets.QLabel("1")
        radius_row.addWidget(self.radius_value)
        root.addLayout(radius_row)

        blend_row = QtWidgets.QHBoxLayout()
        blend_row.addWidget(QtWidgets.QLabel("Blend"))
        self.blend_combo = QtWidgets.QComboBox()
        for value, label, _desc in paint_util.PAINT_BLEND_MODES:
            self.blend_combo.addItem(label, userData=value)
        self.blend_combo.currentIndexChanged.connect(self._on_blend_changed)
        blend_row.addWidget(self.blend_combo)
        root.addLayout(blend_row)

        brush_row = QtWidgets.QHBoxLayout()
        brush_row.addWidget(QtWidgets.QLabel("Hard Brush"))
        self.hard_brush_check = QtWidgets.QCheckBox()
        self.hard_brush_check.toggled.connect(self._on_hard_brush_toggled)
        brush_row.addWidget(self.hard_brush_check)
        brush_row.addWidget(QtWidgets.QLabel("Eraser"))
        self.eraser_check = QtWidgets.QCheckBox()
        self.eraser_check.toggled.connect(self._on_eraser_toggled)
        brush_row.addWidget(self.eraser_check)
        root.addLayout(brush_row)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(self.btn_apply)
        self.btn_vertex = QtWidgets.QPushButton("Vertex")
        self.btn_vertex.clicked.connect(self._on_vertex)
        btn_row.addWidget(self.btn_vertex)
        self.btn_screen = QtWidgets.QPushButton("Screen")
        self.btn_screen.clicked.connect(self._on_screen)
        btn_row.addWidget(self.btn_screen)
        root.addLayout(btn_row)

        self.overlay_check = QtWidgets.QCheckBox("Overlay")
        self.overlay_check.toggled.connect(self._on_overlay_toggled)
        root.addWidget(self.overlay_check)

        overlay_row = QtWidgets.QHBoxLayout()
        overlay_row.addWidget(QtWidgets.QLabel("Overlay Size"))
        self.overlay_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.overlay_slider.setRange(1, 30)
        self.overlay_slider.valueChanged.connect(self._on_overlay_size_changed)
        overlay_row.addWidget(self.overlay_slider)
        self.overlay_value = QtWidgets.QLabel("6")
        overlay_row.addWidget(self.overlay_value)
        root.addLayout(overlay_row)

        self.setCentralWidget(central)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._refresh_from_node)
        self._timer.start()

        self._refresh_from_node()
        size = int(round(paint_preview.get_point_size()))
        self.overlay_slider.setValue(size)
        self.overlay_value.setText(str(size))

    @classmethod
    def show_window(cls):
        _ensure_qapp()
        if cls._instance is None:
            cls._instance = PaintControlWindow()
        cls._instance.show()
        cls._instance.raise_()
        cls._instance.activateWindow()

    def _set_controls_enabled(self, enabled: bool):
        self.color_btn.setEnabled(enabled)
        self.alpha_slider.setEnabled(enabled)
        self.radius_slider.setEnabled(enabled)
        self.blend_combo.setEnabled(enabled)
        self.hard_brush_check.setEnabled(enabled)
        self.eraser_check.setEnabled(enabled)
        self.btn_apply.setEnabled(enabled)
        self.btn_vertex.setEnabled(enabled)
        self.btn_screen.setEnabled(enabled)
        self.overlay_check.setEnabled(True)

    def _set_color_button(self, r: float, g: float, b: float):
        color = QtGui.QColor(int(r * 255), int(g * 255), int(b * 255))
        self.color_btn.setStyleSheet(f"background-color: {color.name()};")

    def _node(self):
        return paint_util.active_node()

    def _refresh_from_node(self):
        node = self._node()
        if node is None:
            self.node_label.setText("Node: -")
            self._set_controls_enabled(False)
            return

        self._set_controls_enabled(True)
        self.node_label.setText(f"Node: {node.name}")

        self._updating = True
        try:
            r, g, b = node.paint_color
            self._set_color_button(r, g, b)
            alpha = float(node.paint_alpha)
            self.alpha_slider.setValue(int(round(alpha * 1000.0)))
            self.alpha_value.setText(f"{alpha:.2f}")
            radius = float(node.paint_radius)
            self.radius_slider.setValue(int(round(radius)))
            self.radius_value.setText(f"{radius:.0f}")
            blend_value = str(node.blend_mode)
            for i in range(self.blend_combo.count()):
                if self.blend_combo.itemData(i) == blend_value:
                    self.blend_combo.setCurrentIndex(i)
                    break
            self.hard_brush_check.setChecked(bool(node.paint_hard_brush))
            self.eraser_check.setChecked(bool(node.paint_erase))
        finally:
            self._updating = False

    def _pick_color(self):
        node = self._node()
        if node is None:
            return
        r, g, b = node.paint_color
        color = QtGui.QColor(int(r * 255), int(g * 255), int(b * 255))
        picked = QtWidgets.QColorDialog.getColor(color, self, "Pick Color")
        if not picked.isValid():
            return
        node.paint_color = (
            picked.red() / 255.0,
            picked.green() / 255.0,
            picked.blue() / 255.0,
        )
        self._set_color_button(*node.paint_color)

    def _on_alpha_changed(self, value):
        if self._updating:
            return
        node = self._node()
        if node is None:
            return
        alpha = float(value) / 1000.0
        node.paint_alpha = alpha
        self.alpha_value.setText(f"{alpha:.2f}")

    def _on_radius_changed(self, value):
        if self._updating:
            return
        node = self._node()
        if node is None:
            return
        radius = float(value)
        node.paint_radius = radius
        self.radius_value.setText(f"{radius:.0f}")

    def _on_blend_changed(self, index):
        if self._updating:
            return
        node = self._node()
        if node is None:
            return
        value = self.blend_combo.itemData(index)
        node.blend_mode = str(value)

    def _on_hard_brush_toggled(self, checked):
        if self._updating:
            return
        node = self._node()
        if node is None:
            return
        node.paint_hard_brush = bool(checked)

    def _on_eraser_toggled(self, checked):
        if self._updating:
            return
        node = self._node()
        if node is None:
            return
        node.paint_erase = bool(checked)

    def _on_apply(self):
        override = self._view_override()
        with bpy.context.temp_override(**override):
            bpy.ops.ldled.paint_apply_selection()

    def _on_vertex(self):
        override = self._view_override()
        with bpy.context.temp_override(**override):
            bpy.ops.ldled.paint_eyedrop_vertex()

    def _on_screen(self):
        override = self._view_override()
        with bpy.context.temp_override(**override):
            bpy.ops.ldled.paint_eyedrop_screen()

    def _on_overlay_size_changed(self, value):
        size = max(1.0, float(value))
        paint_preview.set_point_size(size)
        self.overlay_value.setText(f"{size:.0f}")

    def _on_overlay_toggled(self, checked):
        paint_preview.set_enabled(bool(checked))

    def closeEvent(self, event):
        paint_preview.set_enabled(False)
        PaintControlWindow._instance = None
        super().closeEvent(event)

    def _view_override(self) -> dict:
        wm = bpy.context.window_manager
        if wm is None:
            raise RuntimeError("No window manager")
        windows = []
        if bpy.context.window is not None:
            windows.append(bpy.context.window)
        for win in wm.windows:
            if win not in windows:
                windows.append(win)
        for window in windows:
            if window.screen is None:
                continue
            area = next((a for a in window.screen.areas if a.type == 'VIEW_3D'), None)
            if area is None:
                continue
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region is None:
                continue
            return {
                "window": window,
                "screen": window.screen,
                "area": area,
                "region": region,
                "scene": bpy.context.scene,
            }
        raise RuntimeError("3D View not found")


def show_window():
    PaintControlWindow.show_window()
