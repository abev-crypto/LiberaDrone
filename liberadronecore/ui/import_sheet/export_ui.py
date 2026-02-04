import bpy
from PySide6 import QtCore, QtWidgets

from .sheetutils import (
    EXPORT_HEADERS,
    _collect_cut_map,
    _ensure_qapp,
    _export_cut_to_vat_cat,
    _fetch_csv,
    _parse_rows,
    _to_int,
)

class SheetExportWindow(QtWidgets.QMainWindow):
    _instance = None

    def __init__(self, sheet_url: str, export_dir: str = ""):
        super().__init__()
        self._sheet_url = sheet_url
        self._export_dir = export_dir
        self._rows: list[dict[str, object]] = []
        self.setWindowTitle("LiberaDrone Export Sheet")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        top_row = QtWidgets.QHBoxLayout()
        root.addLayout(top_row)
        top_row.addWidget(QtWidgets.QLabel("Sheet URL"))
        self.url_edit = QtWidgets.QLineEdit(self._sheet_url)
        top_row.addWidget(self.url_edit, 1)
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        top_row.addWidget(self.btn_refresh)

        folder_row = QtWidgets.QHBoxLayout()
        root.addLayout(folder_row)
        folder_row.addWidget(QtWidgets.QLabel("Export Folder"))
        self.folder_edit = QtWidgets.QLineEdit(self._export_dir)
        folder_row.addWidget(self.folder_edit, 1)

        self.status_label = QtWidgets.QLabel("")
        root.addWidget(self.status_label)

        self.table = QtWidgets.QTableWidget(0, len(EXPORT_HEADERS))
        self.table.setHorizontalHeaderLabels(EXPORT_HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        root.addWidget(self.table)

        bottom_row = QtWidgets.QHBoxLayout()
        root.addLayout(bottom_row)
        bottom_row.addStretch(1)
        self.btn_export = QtWidgets.QPushButton("Export Selected")
        bottom_row.addWidget(self.btn_export)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_export.clicked.connect(self.export_selected)
        self.refresh()

    def refresh(self):
        url = self.url_edit.text().strip()
        if not url:
            self.status_label.setText("Missing URL.")
            return
        text = _fetch_csv(url)
        rows = _parse_rows(text)

        cuts = _collect_cut_map(bpy.context, assign_pairs=False)
        if not cuts:
            self.status_label.setText("Formation nodes not available.")
            return

        display_rows: list[dict[str, object]] = []
        for row in rows:
            name = (row.get("name") or "").strip()
            if not name or name not in cuts:
                continue
            cut = cuts[name]
            duration_sheet = _to_int(row.get("duration_frame"))
            duration_calc = int(cut.get("duration", 0))
            status = "OK" if duration_sheet is not None and duration_sheet == duration_calc else "DurError"
            display_rows.append(
                {
                    "name": name,
                    "duration_sheet": duration_sheet,
                    "duration_calc": duration_calc,
                    "status": status,
                    "cut": cut,
                }
            )

        self._rows = display_rows
        self.table.setRowCount(len(display_rows))
        for row_idx, row in enumerate(display_rows):
            check_item = QtWidgets.QTableWidgetItem()
            check_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            check_item.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row_idx, 0, check_item)
            values = (
                row.get("name", ""),
                str(row.get("duration_sheet") or ""),
                str(row.get("duration_calc") or ""),
                row.get("status", ""),
            )
            for col_idx, value in enumerate(values, start=1):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                self.table.setItem(row_idx, col_idx, item)
        self.status_label.setText(f"Loaded: {len(display_rows)} rows")

    def _checked_rows(self) -> list[dict[str, object]]:
        selected: list[dict[str, object]] = []
        for row_idx, row in enumerate(self._rows):
            item = self.table.item(row_idx, 0)
            if item is None:
                continue
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(row)
        return selected

    def export_selected(self):
        selected = self._checked_rows()
        if not selected:
            self.status_label.setText("No rows selected.")
            return

        export_dir = self.folder_edit.text().strip()
        if not export_dir:
            self.status_label.setText("Missing export folder.")
            return

        for row in selected:
            if row.get("status") != "OK":
                self.status_label.setText("Duration mismatch found.")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Export Error",
                    "Duration mismatch detected in selected rows.",
                )
                return

        export_cuts = _collect_cut_map(bpy.context, assign_pairs=True)
        for row in selected:
            name = row.get("name", "")
            cut = export_cuts.get(name) or row.get("cut") or {}
            ok, message = _export_cut_to_vat_cat(bpy.context, cut, export_dir)
            if not ok:
                self.status_label.setText(message)
                QtWidgets.QMessageBox.warning(self, "Export Error", message)
                return

        self.status_label.setText(f"Exported: {len(selected)} cuts")

    @staticmethod
    def show_window(sheet_url: str, export_dir: str = ""):
        _ensure_qapp()
        if SheetExportWindow._instance is not None:
            SheetExportWindow._instance.close()
        SheetExportWindow._instance = SheetExportWindow(sheet_url, export_dir)
        SheetExportWindow._instance.resize(900, 500)
        SheetExportWindow._instance.show()
        return SheetExportWindow._instance
