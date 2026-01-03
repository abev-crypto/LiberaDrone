import csv
import io
import re
import urllib.parse
import urllib.request

from PySide6 import QtWidgets


SHEET_URL_DEFAULT = (
    "https://docs.google.com/spreadsheets/d/"
    "1EbPM3lqhiVnR1ZgmwEZoooDo7JqmlJyqLl51QKSAZhI/edit?gid=0#gid=0"
)

HEADERS = ("Name", "Attr", "Start(F)", "Duration(F)", "States")


def _ensure_qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def _parse_sheet_url(url: str) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    sheet_id = match.group(1) if match else None

    gid = None
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query or "")
    if "gid" in query and query["gid"]:
        gid = query["gid"][0]
    if gid is None and parsed.fragment:
        frag = urllib.parse.parse_qs(parsed.fragment)
        if "gid" in frag and frag["gid"]:
            gid = frag["gid"][0]
    return sheet_id, gid


def _sheet_export_url(url: str) -> str | None:
    sheet_id, gid = _parse_sheet_url(url)
    if not sheet_id:
        return None
    gid = gid or "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _fetch_csv(url: str) -> str:
    export_url = _sheet_export_url(url) or url
    with urllib.request.urlopen(export_url, timeout=10) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace")


def _parse_rows(text: str) -> list[tuple[str, str, str, str, str]]:
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) <= 3:
        return []
    data_rows = rows[3:]
    parsed: list[tuple[str, str, str, str, str]] = []
    for row in data_rows:
        padded = list(row) + ["", "", "", "", ""]
        name = (padded[0] or "").strip()
        if not name:
            continue
        parsed.append(
            (
                name,
                (padded[1] or "").strip(),
                (padded[2] or "").strip(),
                (padded[3] or "").strip(),
                (padded[4] or "").strip(),
            )
        )
    return parsed


class SheetImportWindow(QtWidgets.QMainWindow):
    _instance = None

    def __init__(self, sheet_url: str):
        super().__init__()
        self._sheet_url = sheet_url
        self.setWindowTitle("LiberaDrone Import Sheet")

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

        self.status_label = QtWidgets.QLabel("")
        root.addWidget(self.status_label)

        self.table = QtWidgets.QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        root.addWidget(self.table)

        self.btn_refresh.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self):
        url = self.url_edit.text().strip()
        if not url:
            self.status_label.setText("Missing URL.")
            return
        try:
            text = _fetch_csv(url)
            rows = _parse_rows(text)
        except Exception as exc:
            self.status_label.setText(f"Failed to load: {exc}")
            QtWidgets.QMessageBox.warning(self, "Import Error", str(exc))
            return

        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(value)
                self.table.setItem(row_idx, col_idx, item)
        self.status_label.setText(f"Loaded: {len(rows)} rows")

    @staticmethod
    def show_window(sheet_url: str):
        _ensure_qapp()
        if SheetImportWindow._instance is not None:
            try:
                SheetImportWindow._instance.close()
            except Exception:
                pass
        SheetImportWindow._instance = SheetImportWindow(sheet_url)
        SheetImportWindow._instance.resize(900, 500)
        SheetImportWindow._instance.show()
        return SheetImportWindow._instance
