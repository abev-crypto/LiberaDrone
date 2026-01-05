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

HEADERS = ("Use", "Name", "Attr", "Start(F)", "Duration(F)", "States", "FileCheck")


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
    if not rows:
        return []
    header_row = None
    header_idx = None
    for idx, row in enumerate(rows[:6]):
        if not row:
            continue
        has_name = any((cell or "").strip().lower() == "name" for cell in row)
        has_attr = any((cell or "").strip().lower() == "attr" for cell in row)
        if has_name and has_attr:
            header_row = row
            header_idx = idx
            break

    if header_row is not None:
        def _norm(label: str) -> str:
            return re.sub(r"[^a-z0-9]", "", label.lower())

        col_map = {_norm(cell): i for i, cell in enumerate(header_row) if cell}
        name_idx = col_map.get("name", 0)
        attr_idx = col_map.get("attr", 1)
        start_idx = col_map.get("startf", 3)
        duration_idx = col_map.get("durationf", 5)
        states_idx = col_map.get("states", 6)
        data_rows = rows[header_idx + 1:]
    else:
        name_idx, attr_idx, start_idx, duration_idx, states_idx = 0, 1, 3, 5, 6
        data_rows = rows[3:]
    parsed: list[dict[str, str]] = []
    for row in data_rows:
        padded = list(row)
        max_idx = max(name_idx, attr_idx, start_idx, duration_idx, states_idx)
        if len(padded) <= max_idx:
            padded += [""] * (max_idx + 1 - len(padded))
        name = (padded[name_idx] or "").strip()
        attr = (padded[attr_idx] or "").strip()
        start_frame = (padded[start_idx] or "").strip()
        duration_frame = (padded[duration_idx] or "").strip()
        states = (padded[states_idx] or "").strip()
        if not (name or attr or start_frame or duration_frame or states):
            continue
        parsed.append(
            {
                "name": name,
                "attr": attr,
                "start_frame": start_frame,
                "duration_frame": duration_frame,
                "states": states,
            }
        )
    for idx, row in enumerate(parsed):
        if row.get("attr") != "Transition":
            continue
        if row.get("name"):
            continue
        prev_name = ""
        for prev in range(idx - 1, -1, -1):
            prev_name = parsed[prev].get("name", "")
            if prev_name:
                break
        if prev_name:
            row["name"] = f"{prev_name}Transition"
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
    display_rows: list[dict[str, str]] = []
    for idx, row in enumerate(rows):
        attr = row.get("attr")
        if attr == "Show":
            row["row_index"] = idx
            display_rows.append(row)
            continue
        if attr != "Transition":
            continue
        prev_idx = row.get("prev_show_idx")
        next_idx = row.get("next_show_idx")
        if prev_idx is None or next_idx is None:
            continue
        prev_show = rows[prev_idx]
        next_show = rows[next_idx]
        if prev_show.get("states") != "完了" or next_show.get("states") != "完了":
            continue
        row["row_index"] = idx
        display_rows.append(row)
    return display_rows


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


def _get_image_width(path: str | None) -> int | None:
    if not path:
        return None
    img = _load_image(path)
    if img is None or not getattr(img, "size", None):
        return None
    return int(img.size[0])


def _calc_asset_status(base_dir: str, row: dict[str, str]) -> str:
    if not base_dir or not row.get("name"):
        return ""
    folder = os.path.join(base_dir, row.get("name", ""))
    pos_path, color_path = _find_vat_cat_files(folder)
    vat_width = _get_image_width(pos_path)
    cat_width = _get_image_width(color_path)
    vat_exists = vat_width is not None
    cat_exists = cat_width is not None
    if not vat_exists and not cat_exists:
        return "Missing"
    if not vat_exists:
        return "MissingVAT"
    if not cat_exists:
        return "MissingCAT"
    duration = _to_int(row.get("duration_frame"))
    if duration is None or duration <= 0:
        return "DurError"
    if vat_width != duration or cat_width != duration:
        return "DurError"
    return "OK"


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
        base_dir = self.folder_edit.text().strip()
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
            status = _calc_asset_status(base_dir, row)
            values = (
                row.get("name", ""),
                row.get("attr", ""),
                row.get("start_frame", ""),
                row.get("duration_frame", ""),
                row.get("states", ""),
                status,
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

        import_indices: set[int] = set()
        for row in selected:
            idx = row.get("row_index")
            if idx is None:
                continue
            import_indices.add(idx)
            if row.get("attr") == "Transition":
                prev_idx = self._rows_all[idx].get("prev_show_idx")
                next_idx = self._rows_all[idx].get("next_show_idx")
                if prev_idx is not None:
                    import_indices.add(prev_idx)
                if next_idx is not None:
                    import_indices.add(next_idx)

        if not import_indices:
            self.status_label.setText("No rows selected.")
            return

        rows_to_import: list[dict[str, str]] = []
        for idx in sorted(import_indices):
            row = dict(self._rows_all[idx])
            row["row_index"] = idx
            rows_to_import.append(row)

        status_map: dict[int, str] = {}
        for row in rows_to_import:
            status = _calc_asset_status(base_dir, row)
            status_map[row["row_index"]] = status
            if status == "DurError":
                name = row.get("name", "")
                self.status_label.setText(f"DurError: {name}")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Import Error",
                    f"Duration mismatch: {name}",
                )
                return

        def _should_create_vat(row, status: str, pos_img) -> bool:
            if pos_img is None:
                return False
            if status in ("Missing", "MissingVAT"):
                return False
            if row.get("attr") == "Transition" and status != "OK":
                return False
            return True

        assets: dict[int, dict[str, object]] = {}
        vat_heights: set[int] = set()
        for row in rows_to_import:
            idx = row["row_index"]
            name = row.get("name", "")
            pos_img = None
            pos_min, pos_max = (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
            if name:
                folder = os.path.join(base_dir, name)
                pos_path, _color_path = _find_vat_cat_files(folder)
                pos_img = _load_image(pos_path) if pos_path else None
                bounds = _parse_bounds_from_name(os.path.basename(pos_path)) if pos_path else None
                if bounds:
                    pos_min, pos_max = bounds
            assets[idx] = {
                "pos_img": pos_img,
                "pos_min": pos_min,
                "pos_max": pos_max,
            }
            status = status_map.get(idx, "")
            if _should_create_vat(row, status, pos_img):
                vat_heights.add(int(pos_img.size[1]))

        if len(vat_heights) > 1:
            self.status_label.setText("Error: Drone count mismatch.")
            QtWidgets.QMessageBox.warning(
                self,
                "Import Error",
                "Drone count mismatch between VAT images.",
            )
            return

        node_map: dict[str, bpy.types.Node] = {}
        for node in tree.nodes:
            key = node.label or node.name
            node_map[key] = node

        start_node = next((n for n in tree.nodes if n.bl_idname == "FN_StartNode"), None)
        if start_node is None:
            start_node = tree.nodes.new("FN_StartNode")
            start_node.location = (-300, 0)
        if vat_heights:
            start_node.drone_count = int(next(iter(vat_heights)))

        created = 0
        prev_node = start_node
        for order_idx, row in enumerate(rows_to_import):
            idx = row["row_index"]
            name = row.get("name", "")
            if not name:
                continue
            status = status_map.get(idx, "")
            attr = row.get("attr")
            pos_img = assets[idx]["pos_img"]
            pos_min = assets[idx]["pos_min"]
            pos_max = assets[idx]["pos_max"]
            duration = _to_float(row.get("duration_frame"))

            if attr == "Transition" and status == "OK":
                bl_idname = "FN_ShowNode"
            elif attr == "Transition":
                bl_idname = "FN_TransitionNode"
            else:
                bl_idname = "FN_ShowNode"

            node = node_map.get(name)
            if node is None or node.bl_idname != bl_idname:
                node = tree.nodes.new(bl_idname)
                node.label = name
                node.location = (200 * (order_idx + 1), 0)
                node_map[name] = node
                created += 1

            col = _ensure_collection(scene, name)
            if bl_idname == "FN_ShowNode":
                _set_socket_collection(node, "Collection", col)
            else:
                if hasattr(node, "collection"):
                    try:
                        node.collection = col
                    except Exception:
                        pass

            if duration is not None:
                _set_socket_value(node, "Duration", duration)

            if _should_create_vat(row, status, pos_img):
                obj = _create_point_object(f"{name}_VAT", pos_img.size[1] if pos_img else 1, col)
                if pos_img is not None:
                    try:
                        pos_img.colorspace_settings.name = "Non-Color"
                    except Exception:
                        pass
                    _apply_vat_to_object(obj, pos_img, pos_min=pos_min, pos_max=pos_max, start_frame=None)

            if prev_node:
                _link_flow(tree, prev_node, node)
            prev_node = node

        if created:
            self.status_label.setText(f"Imported: {created} nodes")
        else:
            self.status_label.setText("No nodes created.")
        try:
            SheetImportWindow._instance = None
            self.close()
        except Exception:
            pass

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



