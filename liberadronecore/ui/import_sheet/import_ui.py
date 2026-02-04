import os

import bpy
from PySide6 import QtCore, QtWidgets

from liberadronecore.ui import ledeffects_panel as led_panel

from .sheetutils import (
    HEADERS,
    _apply_import_settings,
    _apply_vat_to_object,
    _build_cat_led_graph,
    _calc_asset_status,
    _create_point_object,
    _ensure_collection,
    _ensure_formation_tree,
    _ensure_qapp,
    _fetch_csv,
    _filter_transition_rows,
    _find_vat_cat_files,
    _link_camera_blend_assets,
    _link_flow,
    _link_tree_to_workspace,
    _load_image,
    _parse_bounds_from_name,
    _parse_rows,
    _read_sheet_settings,
    _set_socket_collection,
    _set_socket_value,
    _set_world_surface_black,
    _to_float,
    _to_int,
)

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
        text = _fetch_csv(url)
        rows = _parse_rows(text)
        self._rows_all = rows
        display_rows = _filter_transition_rows(rows, base_dir)

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
        _set_world_surface_black(scene)

        base_dir = self.folder_edit.text().strip()
        if not base_dir:
            self.status_label.setText("Missing VAT/CAT folder.")
            return

        _linked_cameras, linked_area_obj = _link_camera_blend_assets(scene, base_dir)
        if linked_area_obj is not None:
            scene.ld_checker_range_object = linked_area_obj

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

        duration_frames: dict[int, int] = {}
        start_frames: dict[int, int] = {}
        cursor = 0
        for row in rows_to_import:
            idx = row["row_index"]
            duration_int = _to_int(row.get("duration_frame")) or 0
            duration_frames[idx] = duration_int
            start_frames[idx] = int(cursor)
            cursor += max(0, duration_int)

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

        settings, settings_source, settings_error = _read_sheet_settings(self.url_edit.text().strip())
        drone_num_setting = _to_int(settings.get("dronenum")) if settings else None
        glare_threshold = _to_float(settings.get("glarethreshold")) if settings else None

        if drone_num_setting and vat_heights:
            if any(height != drone_num_setting for height in vat_heights):
                self.status_label.setText("Error: Drone count mismatch.")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Import Error",
                    "Drone count mismatch between VAT images and sheet settings.",
                )
                return
        elif len(vat_heights) > 1:
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
        if settings:
            _apply_import_settings(scene, settings, start_node=start_node)
        if linked_area_obj is None and getattr(scene, "ld_checker_range_object", None) is None:
            bpy.ops.liberadrone.create_range_object()
        settings_note = ""
        if settings:
            parts = []
            for key in ("dronenum", "areawidth", "areaheight", "areadepth", "dronemodel"):
                if key in settings:
                    parts.append(f"{key}={settings[key]}")
            detail = ", ".join(parts) if parts else "loaded"
            src = settings_source or "sheet2"
            settings_note = f" (Settings {src}: {detail})"
        elif settings_error:
            settings_note = f" (Settings error: {settings_error})"
        if vat_heights and not (drone_num_setting and drone_num_setting > 0):
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
            duration_int = duration_frames.get(idx, 0)
            start_frame = start_frames.get(idx, 0)

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
                    node.collection = col

            if duration is not None:
                _set_socket_value(node, "Duration", duration)

            if _should_create_vat(row, status, pos_img):
                vat_count = drone_num_setting or (pos_img.size[1] if pos_img else 1)
                obj = _create_point_object(f"{name}_VAT", vat_count, col)
                if pos_img is not None:
                    pos_img.colorspace_settings.name = "Non-Color"
                    _apply_vat_to_object(
                        obj,
                        pos_img,
                        pos_min=pos_min,
                        pos_max=pos_max,
                        start_frame=start_frame,
                        frame_count=duration_int,
                        drone_count=vat_count,
                    )

            cat_img = None
            if name:
                folder = os.path.join(base_dir, name)
                _pos_path, cat_path = _find_vat_cat_files(folder)
                cat_img = _load_image(cat_path, colorspace="sRGB") if cat_path else None
            if cat_img is not None:
                _build_cat_led_graph(
                    bpy.context,
                    cut_name=name,
                    cat_image=cat_img,
                    start_frame=start_frame,
                    duration=duration_int or 0,
                )

            if prev_node:
                _link_flow(tree, prev_node, node)
            prev_node = node

        if created:
            self.status_label.setText(f"Imported: {created} nodes{settings_note}")
        else:
            self.status_label.setText(f"No nodes created.{settings_note}")
        bpy.ops.liberadrone.setup_all()
        _link_tree_to_workspace("Formation", tree, "FN_FormationTree")
        led_tree = led_panel._get_led_tree(bpy.context)
        if led_tree is not None:
            _link_tree_to_workspace("LED", led_tree, "LD_LedEffectsTree")
        if all(
            status_map.get(row["row_index"]) == "OK"
            for row in rows_to_import
            if row.get("name")
        ):
            bpy.ops.fn.calculate_schedule()
        from liberadronecore.util import view_setup
        view_setup.setup_glare_compositor(scene, glare_threshold=glare_threshold)
        SheetImportWindow._instance = None
        self.close()

    @staticmethod
    def show_window(sheet_url: str, vat_dir: str = ""):
        _ensure_qapp()
        if SheetImportWindow._instance is not None:
            SheetImportWindow._instance.close()
        SheetImportWindow._instance = SheetImportWindow(sheet_url, vat_dir)
        SheetImportWindow._instance.resize(900, 500)
        SheetImportWindow._instance.show()
        return SheetImportWindow._instance
