import csv
import io
import os
import re
import sys
import urllib.parse
import urllib.request

import bpy
from PySide6 import QtCore, QtWidgets

from liberadronecore.system.transition import vat_gn


SHEET_URL_DEFAULT = (
    "https://docs.google.com/spreadsheets/d/"
    "1EbPM3lqhiVnR1ZgmwEZoooDo7JqmlJyqLl51QKSAZhI/edit?gid=0#gid=0"
)

HEADERS = ("Use", "Name", "Attr", "Start(F)", "Duration(F)", "States")


def _ensure_qapp():
    _install_qt_message_handler()
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


_QT_HANDLER_INSTALLED = False
_QT_PREV_HANDLER = None


def _install_qt_message_handler() -> None:
    global _QT_HANDLER_INSTALLED, _QT_PREV_HANDLER
    if _QT_HANDLER_INSTALLED:
        return

    def _handler(mode, context, message):
        if "SetProcessDpiAwarenessContext() failed" in message:
            return
        if _QT_PREV_HANDLER is not None:
            _QT_PREV_HANDLER(mode, context, message)
            return
        try:
            sys.stderr.write(message + "\n")
        except Exception:
            pass

    _QT_PREV_HANDLER = QtCore.qInstallMessageHandler(_handler)
    _QT_HANDLER_INSTALLED = True


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


def _parse_rows(text: str) -> list[dict[str, str]]:
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) <= 3:
        return []
    data_rows = rows[3:]
    parsed: list[dict[str, str]] = []
    for row in data_rows:
        padded = list(row) + ["", "", "", "", "", "", ""]
        name = (padded[0] or "").strip()
        if not name:
            continue
        parsed.append(
            {
                "name": name,
                "attr": (padded[1] or "").strip(),
                "start_frame": (padded[3] or "").strip(),
                "duration_frame": (padded[5] or "").strip(),
                "states": (padded[6] or "").strip(),
            }
        )
    return parsed


def _map_show_neighbors(rows: list[dict[str, str]]) -> None:
    prev_show_idx = None
    for idx, row in enumerate(rows):
        if row.get("attr") == "Show":
            prev_show_idx = idx
        row["prev_show_idx"] = prev_show_idx
    next_show_idx = None
    for idx in range(len(rows) - 1, -1, -1):
        if rows[idx].get("attr") == "Show":
            next_show_idx = idx
        rows[idx]["next_show_idx"] = next_show_idx


def _filter_transition_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    _map_show_neighbors(rows)
    filtered: list[dict[str, str]] = []
    for idx, row in enumerate(rows):
        if row.get("states") != "完了":
            continue
        if row.get("attr") != "Transition":
            continue
        if row.get("prev_show_idx") is None or row.get("next_show_idx") is None:
            continue
        row["row_index"] = idx
        filtered.append(row)
    return filtered


def _ensure_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
    elif col.name not in scene.collection.children:
        scene.collection.children.link(col)
    return col


def _load_image(path: str) -> bpy.types.Image | None:
    if not path or not os.path.isfile(path):
        return None
    abs_path = os.path.abspath(path)
    for img in bpy.data.images:
        try:
            if os.path.abspath(bpy.path.abspath(img.filepath)) == abs_path:
                return img
        except Exception:
            continue
    try:
        return bpy.data.images.load(abs_path)
    except Exception:
        return None


def _parse_bounds_from_name(filename: str) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    pattern = r"S_(-?\\d+(?:\\.\\d+)?)_(-?\\d+(?:\\.\\d+)?)_(-?\\d+(?:\\.\\d+)?)_E_(-?\\d+(?:\\.\\d+)?)_(-?\\d+(?:\\.\\d+)?)_(-?\\d+(?:\\.\\d+)?)"
    match = re.search(pattern, filename)
    if not match:
        return None
    values = [float(match.group(i)) for i in range(1, 7)]
    return (values[0], values[1], values[2]), (values[3], values[4], values[5])


def _find_vat_cat_files(folder: str) -> tuple[str | None, str | None]:
    if not folder or not os.path.isdir(folder):
        return None, None
    pos_path = None
    color_path = None
    for entry in os.listdir(folder):
        path = os.path.join(folder, entry)
        if not os.path.isfile(path):
            continue
        low = entry.lower()
        if pos_path is None and low.endswith(".exr") and "vat" in low:
            pos_path = path
            continue
        if color_path is None and low.endswith(".png") and ("color" in low or "cat" in low):
            color_path = path
            continue
    return pos_path, color_path


def _create_point_object(name: str, count: int, collection: bpy.types.Collection) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    mesh = None
    if obj is None:
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
    else:
        mesh = obj.data
        if obj.name not in collection.objects:
            collection.objects.link(obj)
    if mesh is None:
        return obj
    count = max(1, int(count))
    mesh.clear_geometry()
    mesh.vertices.add(count)
    mesh.update()
    return obj


def _apply_vat_to_object(
    obj: bpy.types.Object,
    pos_img: bpy.types.Image,
    *,
    pos_min: tuple[float, float, float],
    pos_max: tuple[float, float, float],
    start_frame: int | None,
) -> None:
    if pos_img is None:
        return
    frame_count = max(1, int(pos_img.size[0]))
    drone_count = max(1, int(pos_img.size[1]))
    group = vat_gn._create_gn_vat_group(
        pos_img,
        pos_min,
        pos_max,
        frame_count,
        drone_count,
        start_frame=start_frame,
        base_name=obj.name,
    )
    vat_gn._apply_gn_to_object(obj, group)


def _ensure_formation_tree(context) -> bpy.types.NodeTree | None:
    tree = None
    space = getattr(context, "space_data", None)
    if space and getattr(space, "edit_tree", None):
        tree = space.edit_tree
    if tree is None or getattr(tree, "bl_idname", "") != "FN_FormationTree":
        tree = next((ng for ng in bpy.data.node_groups if getattr(ng, "bl_idname", "") == "FN_FormationTree"), None)
    if tree is None:
        tree = bpy.data.node_groups.new("FormationTree", "FN_FormationTree")
        if space and getattr(space, "type", "") == "NODE_EDITOR":
            try:
                space.tree_type = "FN_FormationTree"
                space.node_tree = tree
            except Exception:
                pass
    return tree


def _first_flow_out(node):
    for sock in getattr(node, "outputs", []):
        if getattr(sock, "bl_idname", "") == "FN_SocketFlow":
            return sock
    return None


def _first_flow_in(node):
    for sock in getattr(node, "inputs", []):
        if getattr(sock, "bl_idname", "") == "FN_SocketFlow":
            return sock
    return None


def _link_flow(tree, from_node, to_node):
    out_sock = _first_flow_out(from_node)
    in_sock = _first_flow_in(to_node)
    if out_sock and in_sock and not in_sock.is_linked:
        try:
            tree.links.new(out_sock, in_sock)
        except Exception:
            pass


def _set_socket_value(node, name: str, value) -> None:
    sock = node.inputs.get(name) if hasattr(node, "inputs") else None
    if sock is None:
        return
    if hasattr(sock, "value"):
        try:
            sock.value = value
        except Exception:
            pass


def _set_socket_collection(node, name: str, collection: bpy.types.Collection) -> None:
    sock = node.inputs.get(name) if hasattr(node, "inputs") else None
    if sock is None:
        return
    if hasattr(sock, "collection"):
        try:
            sock.collection = collection
        except Exception:
            pass


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


class SheetImportWindow(QtWidgets.QMainWindow):
    _instance = None

    def __init__(self, sheet_url: str, vat_dir: str = ""):
        super().__init__()
        self._sheet_url = sheet_url
        self._vat_dir = vat_dir
        self._rows_all: list[dict[str, str]] = []
        self._rows: list[dict[str, str]] = []
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

        folder_row = QtWidgets.QHBoxLayout()
        root.addLayout(folder_row)
        folder_row.addWidget(QtWidgets.QLabel("VAT/CAT Folder"))
        self.folder_edit = QtWidgets.QLineEdit(self._vat_dir)
        folder_row.addWidget(self.folder_edit, 1)

        self.status_label = QtWidgets.QLabel("")
        root.addWidget(self.status_label)

        self.table = QtWidgets.QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        root.addWidget(self.table)

        bottom_row = QtWidgets.QHBoxLayout()
        root.addLayout(bottom_row)
        bottom_row.addStretch(1)
        self.btn_import = QtWidgets.QPushButton("Import Selected")
        bottom_row.addWidget(self.btn_import)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_import.clicked.connect(self.import_selected)
        self.refresh()

    def refresh(self):
        url = self.url_edit.text().strip()
        if not url:
            self.status_label.setText("Missing URL.")
            return
        try:
            text = _fetch_csv(url)
            rows = _parse_rows(text)
            self._rows_all = rows
            display_rows = _filter_transition_rows(rows)
        except Exception as exc:
            self.status_label.setText(f"Failed to load: {exc}")
            QtWidgets.QMessageBox.warning(self, "Import Error", str(exc))
            return

        self._rows = display_rows
        self.table.setRowCount(len(display_rows))
        for row_idx, row in enumerate(display_rows):
            check_item = QtWidgets.QTableWidgetItem()
            check_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            check_item.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row_idx, 0, check_item)
            values = (
                row.get("name", ""),
                row.get("attr", ""),
                row.get("start_frame", ""),
                row.get("duration_frame", ""),
                row.get("states", ""),
            )
            for col_idx, value in enumerate(values, start=1):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                self.table.setItem(row_idx, col_idx, item)
        self.status_label.setText(f"Loaded: {len(display_rows)} rows")

    def _checked_rows(self) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        for row_idx, row in enumerate(self._rows):
            item = self.table.item(row_idx, 0)
            if item is None:
                continue
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(row)
        return selected

    def import_selected(self):
        selected = self._checked_rows()
        if not selected:
            self.status_label.setText("No rows selected.")
            return

        scene = getattr(bpy.context, "scene", None)
        if scene is None:
            self.status_label.setText("No active scene.")
            return

        base_dir = self.folder_edit.text().strip()
        if not base_dir:
            self.status_label.setText("Missing VAT/CAT folder.")
            return

        tree = _ensure_formation_tree(bpy.context)
        if tree is None:
            self.status_label.setText("Formation tree not available.")
            return

        node_map: dict[str, bpy.types.Node] = {}
        for node in tree.nodes:
            key = node.label or node.name
            node_map[key] = node

        if hasattr(scene, "ld_import_items"):
            scene.ld_import_items.clear()
            for row in selected:
                item = scene.ld_import_items.add()
                item.name = row.get("name", "")

        start_node = next((n for n in tree.nodes if n.bl_idname == "FN_StartNode"), None)
        if start_node is None:
            start_node = tree.nodes.new("FN_StartNode")
            start_node.location = (-300, 0)

        created = 0
        for row in selected:
            idx = row.get("row_index")
            if idx is None:
                continue
            prev_idx = self._rows_all[idx].get("prev_show_idx")
            next_idx = self._rows_all[idx].get("next_show_idx")
            prev_row = self._rows_all[prev_idx] if prev_idx is not None else None
            next_row = self._rows_all[next_idx] if next_idx is not None else None

            for show_row in (prev_row, next_row):
                if not show_row:
                    continue
                name = show_row.get("name", "")
                if not name:
                    continue
                if name in node_map and node_map[name].bl_idname == "FN_ShowNode":
                    continue
                col = _ensure_collection(scene, name)
                folder = os.path.join(base_dir, name)
                pos_path, _color_path = _find_vat_cat_files(folder)
                pos_img = _load_image(pos_path) if pos_path else None
                bounds = _parse_bounds_from_name(os.path.basename(pos_path)) if pos_path else None
                pos_min, pos_max = bounds if bounds else ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
                start_frame = _to_int(show_row.get("start_frame"))
                obj = _create_point_object(f"{name}_VAT", pos_img.size[1] if pos_img else 1, col)
                if pos_img is not None:
                    try:
                        pos_img.colorspace_settings.name = "Non-Color"
                    except Exception:
                        pass
                    _apply_vat_to_object(obj, pos_img, pos_min=pos_min, pos_max=pos_max, start_frame=start_frame)

                show_node = tree.nodes.new("FN_ShowNode")
                show_node.label = name
                show_node.location = (0, 0)
                _set_socket_collection(show_node, "Collection", col)
                duration = _to_float(show_row.get("duration_frame"))
                if duration is not None:
                    _set_socket_value(show_node, "Duration", duration)
                node_map[name] = show_node
                created += 1

            transition_name = row.get("name", "")
            if transition_name:
                if transition_name in node_map and node_map[transition_name].bl_idname == "FN_TransitionNode":
                    transition_node = node_map[transition_name]
                else:
                    transition_node = tree.nodes.new("FN_TransitionNode")
                    transition_node.label = transition_name
                    transition_node.location = (200, 0)
                    duration = _to_float(row.get("duration_frame"))
                    if duration is not None:
                        _set_socket_value(transition_node, "Duration", duration)
                    node_map[transition_name] = transition_node
                    created += 1
                col = _ensure_collection(scene, transition_name)
                folder = os.path.join(base_dir, transition_name)
                pos_path, _color_path = _find_vat_cat_files(folder)
                pos_img = _load_image(pos_path) if pos_path else None
                bounds = _parse_bounds_from_name(os.path.basename(pos_path)) if pos_path else None
                pos_min, pos_max = bounds if bounds else ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
                start_frame = _to_int(row.get("start_frame"))
                obj = _create_point_object(f"{transition_name}_VAT", pos_img.size[1] if pos_img else 1, col)
                if pos_img is not None:
                    try:
                        pos_img.colorspace_settings.name = "Non-Color"
                    except Exception:
                        pass
                    _apply_vat_to_object(obj, pos_img, pos_min=pos_min, pos_max=pos_max, start_frame=start_frame)
                if hasattr(transition_node, "collection"):
                    try:
                        transition_node.collection = col
                    except Exception:
                        pass
            else:
                transition_node = None

            if prev_row and transition_node:
                prev_node = node_map.get(prev_row.get("name", ""))
                if prev_node:
                    _link_flow(tree, start_node, prev_node)
                    _link_flow(tree, prev_node, transition_node)
            if next_row and transition_node:
                next_node = node_map.get(next_row.get("name", ""))
                if next_node:
                    _link_flow(tree, transition_node, next_node)

        if created:
            self.status_label.setText(f"Imported: {created} nodes")
        else:
            self.status_label.setText("No nodes created.")

    @staticmethod
    def show_window(sheet_url: str, vat_dir: str = ""):
        _ensure_qapp()
        if SheetImportWindow._instance is not None:
            try:
                SheetImportWindow._instance.close()
            except Exception:
                pass
        SheetImportWindow._instance = SheetImportWindow(sheet_url, vat_dir)
        SheetImportWindow._instance.resize(900, 500)
        SheetImportWindow._instance.show()
        return SheetImportWindow._instance
