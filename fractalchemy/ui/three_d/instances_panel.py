"""The 3D Editor's Instances tab: mesh assets and the instancers that place them along a fractal (the Holon IFS).

Top: the **assets** (primitives, imported meshes, the Mesh tab's clean mesh saved as a PLY) with their detail and
normalisation. Middle: the **instancers** — which asset, which fractal (the scene's, or an own 3D IFS), chaos or
tree mode, depth, size rules, colour, material — and *Show the fractal itself*. Bottom, for an own IFS: the
**transform table**, one row per transform as a 3D affine map (position, rotation, scale, weight, colour),
with *Add* / *Remove* / *Starter IFS* / *Send to main window*. Everything goes through the `Scene3DDocument`.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QMenu, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
                               QToolButton, QVBoxLayout, QWidget)

from ...scene3d.model import Instancer, MeshAsset
from ...solid import holon
from ...solid.io import MESH_READ_FILTER
from ...widgets.silent import blocked, updating
from .document import Scene3DDocument
from .panels import _Panel

COLUMNS = ("weight", "x", "y", "z", "rot x", "rot y", "rot z", "scale", "colour")
COLUMN_KEYS = ("weight", "px", "py", "pz", "rx", "ry", "rz", "scale", "color")
COLUMN_RANGES = {"weight": (0.0, 100.0, 2), "px": (-50.0, 50.0, 3), "py": (-50.0, 50.0, 3), "pz": (-50.0, 50.0, 3), "rx": (-360.0, 360.0, 1),
                 "ry": (-360.0, 360.0, 1), "rz": (-360.0, 360.0, 1), "scale": (-10.0, 10.0, 3), "color": (0.0, 1.0, 3)}


def asset_folder() -> Path:
    """Where saved assets (the clean mesh as a PLY) go."""
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation) or str(Path.home() / ".fractalchemy")
    return Path(base) / "assets"


class InstancesPanel(_Panel):
    """Assets, instancers and the own-IFS transform table (see the module docstring).

    Signals:
        flame_sent(object): *Send own IFS to main window*: a `Flame`.
        status(str): A message for the status bar.
    """
    flame_sent = Signal(object)
    status = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_instancer = -1
        # assets
        self.asset_list = QListWidget(self)
        self.asset_list.setMaximumHeight(90)
        self.add_primitive_button = QToolButton(self)
        self.add_primitive_button.setText("Add primitive")
        self.add_primitive_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.add_primitive_button)
        for kind in holon.PRIMITIVES:
            menu.addAction(kind.capitalize(), lambda k=kind: self._add_primitive(k))
        self.add_primitive_button.setMenu(menu)
        self.import_button = QPushButton("Import mesh…", self)
        self.from_mesh_button = QPushButton("From the clean mesh", self)
        self.from_mesh_button.setToolTip("Save the Mesh tab's clean mesh as a PLY and use it as an asset")
        self.remove_asset_button = QPushButton("Remove", self)
        self.asset_name = QLineEdit(self)
        self.asset_detail = QSpinBox(self)
        self.asset_detail.setRange(0, 5)
        self.asset_detail.setToolTip("Subdivision level of a primitive")
        self.asset_normalize = QCheckBox("Centre and scale to unit size", self)
        self.asset_info = QLabel(self)
        self.asset_info.setStyleSheet("color: #808080;")
        # instancers
        self.show_fractal_check = QCheckBox("Show the fractal itself", self)
        self.show_fractal_check.setToolTip("Off: only the instances are drawn (a pure holon scene)")
        self.instancer_list = QListWidget(self)
        self.instancer_list.setMaximumHeight(90)
        self.add_instancer_button = QPushButton("Add instancer", self)
        self.remove_instancer_button = QPushButton("Remove", self)
        self.name = QLineEdit(self)
        self.asset_box = QComboBox(self)
        self.source_box = QComboBox(self)
        self.source_box.addItem("The scene's fractal", "main")
        self.source_box.addItem("Own 3D IFS (the table below)", "own")
        self.mode_box = QComboBox(self)
        self.mode_box.addItem("Chaos game (orbit samples)", "chaos")
        self.mode_box.addItem("Tree (every composition)", "tree")
        self.count = QSpinBox(self)
        self.count.setRange(1, 2_000_000)
        self.count.setSingleStep(500)
        self.count.setToolTip("Instances wanted (chaos game)")
        self.depth = QSpinBox(self)
        self.depth.setRange(1, 12)
        self.depth.setToolTip("Transforms composed per instance: the frames are those of depth-n holons (tree: the depth)")
        self.levels_box = QComboBox(self)
        self.levels_box.addItem("Every level", "all")
        self.levels_box.addItem("Deepest level only", "leaves")
        self.frame_box = QComboBox(self)
        self.frame_box.addItem("Turn and scale with the transforms", "jacobian")
        self.frame_box.addItem("Scale only (keep upright)", "translation")
        self.size = self._row("Size", 0.001, 2.0, 3, "Base size of an instance (its longest side, in flame units) before the orbit's scale",
                              self._inst_field("size"), "size")
        self.falloff = self._row("Size falloff", 0.0, 2.0, 2, "Exponent on the accumulated scale: 1 = exact, less flattens the size range",
                                 self._inst_field("size_falloff"), "size_falloff")
        self.min_size = self._row("Min size", 0.0, 0.2, 4, "Instances smaller than this are dropped", self._inst_field("min_size"), "min_size")
        self.max_instances = QSpinBox(self)
        self.max_instances.setRange(1, 2_000_000)
        self.max_instances.setSingleStep(1000)
        self.max_instances.setToolTip("Cap on the instances (the largest are kept)")
        self.color_box = QComboBox(self)
        self.color_box.addItem("Orbit colour (palette)", "palette")
        self.color_box.addItem("The asset's own colours", "asset")
        self.color_box.addItem("Fixed colour", "fixed")
        self.color = self._color("Instance colour", lambda c: self._material("color", color=c))
        self.specular = self._row("Specular", 0.0, 2.0, 2, "Highlight strength", self._mat_field("specular"), "specular")
        self.shininess = self._row("Shininess", 1.0, 200.0, 0, "Highlight tightness", self._mat_field("shininess"), "shininess")
        self.seed = QSpinBox(self)
        self.seed.setRange(1, 99999)
        self.visible_check = QCheckBox("Visible", self)
        # own IFS
        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(list(COLUMNS))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMaximumHeight(170)
        self.add_xform_button = QPushButton("Add transform", self)
        self.remove_xform_button = QPushButton("Remove", self)
        self.starter_button = QPushButton("Starter IFS", self)
        self.send_button = QPushButton("Send to main window", self)
        self.send_button.setToolTip("Show the own IFS as a fractal in the main window")
        self.own_group = QGroupBox("Own 3D IFS", self)
        self._build()
        self._connect()

    # --- construction -------------------------------------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        assets = QGroupBox("Assets", self)
        al = QVBoxLayout(assets)
        al.addWidget(self.asset_list)
        row = QHBoxLayout()
        for w in (self.add_primitive_button, self.import_button, self.from_mesh_button, self.remove_asset_button):
            row.addWidget(w)
        row.addStretch(1)
        al.addLayout(row)
        form = QFormLayout()
        form.addRow("Name", self.asset_name)
        form.addRow("Detail", self.asset_detail)
        form.addRow(self.asset_normalize)
        form.addRow(self.asset_info)
        al.addLayout(form)
        layout.addWidget(assets)
        instancers = QGroupBox("Instancers", self)
        il = QVBoxLayout(instancers)
        il.addWidget(self.show_fractal_check)
        il.addWidget(self.instancer_list)
        row = QHBoxLayout()
        row.addWidget(self.add_instancer_button)
        row.addWidget(self.remove_instancer_button)
        row.addStretch(1)
        row.addWidget(self.visible_check)
        il.addLayout(row)
        form = QFormLayout()
        form.addRow("Name", self.name)
        form.addRow("Asset", self.asset_box)
        form.addRow("Fractal", self.source_box)
        form.addRow("Mode", self.mode_box)
        form.addRow("Instances", self.count)
        form.addRow("Depth", self.depth)
        form.addRow("Levels", self.levels_box)
        form.addRow("Frames", self.frame_box)
        il.addLayout(form)
        il.addWidget(self.size)
        il.addWidget(self.falloff)
        il.addWidget(self.min_size)
        form2 = QFormLayout()
        form2.addRow("Cap", self.max_instances)
        form2.addRow("Colour", self.color_box)
        form2.addRow("Fixed colour", self.color)
        form2.addRow("Seed", self.seed)
        il.addLayout(form2)
        il.addWidget(self.specular)
        il.addWidget(self.shininess)
        layout.addWidget(instancers)
        ol = QVBoxLayout(self.own_group)
        ol.addWidget(self.table)
        row = QHBoxLayout()
        for w in (self.add_xform_button, self.remove_xform_button, self.starter_button, self.send_button):
            row.addWidget(w)
        row.addStretch(1)
        ol.addLayout(row)
        layout.addWidget(self.own_group)
        layout.addStretch(1)

    def _connect(self) -> None:
        self.asset_list.currentRowChanged.connect(lambda _r: self._show_asset())
        self.import_button.clicked.connect(self.import_mesh)
        self.from_mesh_button.clicked.connect(self.asset_from_clean_mesh)
        self.remove_asset_button.clicked.connect(lambda: self._document.remove_asset(self.asset_list.currentRow()) if self._document else None)
        self.asset_name.editingFinished.connect(lambda: None if self._updating else self._asset(name=self.asset_name.text().strip() or "asset"))
        self.asset_detail.valueChanged.connect(lambda v: None if self._updating else self._asset(detail=int(v)))
        self.asset_normalize.toggled.connect(lambda on: None if self._updating else self._asset(normalize=bool(on)))
        self.show_fractal_check.toggled.connect(lambda on: None if self._updating else self._document.update_solid(None, show_fractal=bool(on)))
        self.instancer_list.currentRowChanged.connect(self._select_instancer)
        self.add_instancer_button.clicked.connect(self._add_instancer)
        self.remove_instancer_button.clicked.connect(lambda: self._document.remove_instancer(self._current_instancer) if self._document else None)
        self.name.editingFinished.connect(lambda: None if self._updating else self._inst(None, name=self.name.text().strip() or "instancer"))
        self.asset_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._inst(None, asset=self.asset_box.currentData() or ""))
        self.source_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._inst(None, source=self.source_box.currentData()))
        self.mode_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._inst(None, mode=self.mode_box.currentData()))
        self.count.valueChanged.connect(lambda v: None if self._updating else self._inst("count", count=int(v)))
        self.depth.valueChanged.connect(lambda v: None if self._updating else self._inst("depth", depth=int(v)))
        self.levels_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._inst(None, tree_levels=self.levels_box.currentData()))
        self.frame_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._inst(None, frame_mode=self.frame_box.currentData()))
        self.max_instances.valueChanged.connect(lambda v: None if self._updating else self._inst("cap", max_instances=int(v)))
        self.color_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._inst(None, color_mode=self.color_box.currentData()))
        self.seed.valueChanged.connect(lambda v: None if self._updating else self._inst("seed", seed=int(v)))
        self.visible_check.toggled.connect(lambda on: None if self._updating else self._inst(None, visible=bool(on)))
        self.table.cellChanged.connect(self._cell_changed)
        self.add_xform_button.clicked.connect(self._add_xform)
        self.remove_xform_button.clicked.connect(self._remove_xform)
        self.starter_button.clicked.connect(lambda: self._document.set_own_ifs(self._current_instancer, None, "Starter IFS") if self._document else None)
        self.send_button.clicked.connect(self._send)
        for box in (self.count, self.depth, self.max_instances, self.seed, self.asset_detail):
            box.setKeyboardTracking(False)

    # --- helpers ------------------------------------------------------------------------------------------------------
    def _inst_field(self, field: str):
        return lambda value, key: self._inst(key, **{field: value})

    def _mat_field(self, field: str):
        return lambda value, key: self._material(key, **{field: value})

    def _inst(self, merge_key, **fields) -> None:
        if self._document is not None and self._current_instancer >= 0:
            self._document.update_instancer(self._current_instancer, merge_key, **fields)

    def _material(self, merge_key, **fields) -> None:
        if self._document is not None and self._current_instancer >= 0:
            self._document.update_instancer_material(self._current_instancer, merge_key, **fields)

    def _asset(self, **fields) -> None:
        if self._document is not None and self.asset_list.currentRow() >= 0:
            self._document.update_asset(self.asset_list.currentRow(), None, **fields)

    def current_instancer(self) -> Instancer | None:
        if self._document is None or not 0 <= self._current_instancer < len(self._document.scene.instancers):
            return None
        return self._document.scene.instancers[self._current_instancer]

    # --- assets --------------------------------------------------------------------------------------------------------
    def _add_primitive(self, kind: str) -> None:
        if self._document is None:
            return
        index = self._document.add_asset(MeshAsset(kind, "primitive", kind, 2))
        self.asset_list.setCurrentRow(index)

    def import_mesh(self, path: Path | str | None = None) -> bool:
        """Import a mesh file as an asset (a file dialog when no path is given)."""
        if self._document is None:
            return False
        if path is None:
            chosen, _filter = QFileDialog.getOpenFileName(self, "Import mesh", "", MESH_READ_FILTER)
            if not chosen:
                return False
            path = chosen
        path = Path(path)
        try:
            from ...solid.io import read_mesh
            mesh = read_mesh(path)
        except (OSError, ValueError) as exc:
            self.status.emit(f"Could not import {path.name}: {exc}")
            return False
        index = self._document.add_asset(MeshAsset(path.stem, "file", path=str(path), mesh=mesh))
        self.asset_list.setCurrentRow(index)
        self.status.emit(f"Imported {path.name}: {mesh.face_count:,} faces")
        return True

    def asset_from_clean_mesh(self, folder: Path | None = None) -> bool:
        """Save the Mesh tab's clean mesh as a PLY and add it as an asset."""
        if self._document is None or self._document.mesh_result is None:
            self.status.emit("Generate a mesh on the Mesh tab first")
            return False
        from ...solid.io import write_mesh
        folder = Path(folder) if folder is not None else asset_folder()
        name = self._document.flame.name if self._document.flame is not None else "fractal"
        safe = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in name).strip() or "fractal"
        target = folder / f"{safe}.ply"
        index = 2
        while target.exists():
            target = folder / f"{safe} {index}.ply"
            index += 1
        try:
            mesh = self._document.mesh_result.clean
            write_mesh(mesh, target, "ply", None, safe)
        except (OSError, ValueError) as exc:
            self.status.emit(f"Could not save the mesh as an asset: {exc}")
            return False
        asset_index = self._document.add_asset(MeshAsset(safe, "fractal", path=str(target), mesh=mesh))
        self.asset_list.setCurrentRow(asset_index)
        self.status.emit(f"Saved the clean mesh as {target.name}")
        return True

    def _refresh_assets(self) -> None:
        scene = self._document.scene
        current = self.asset_list.currentRow()
        with blocked(self.asset_list):
            self.asset_list.clear()
            for asset in scene.assets:
                faces = asset.mesh.face_count if asset.mesh is not None else 0
                detail = f" (detail {asset.detail})" if asset.kind == "primitive" else ""
                self.asset_list.addItem(f"{asset.name}  ·  {asset.kind}{detail}  ·  {faces:,} faces" if asset.mesh is not None else f"{asset.name}  ·  {asset.kind}  ·  not loaded")
            if scene.assets:
                self.asset_list.setCurrentRow(min(max(0, current), len(scene.assets) - 1))
        self.remove_asset_button.setEnabled(bool(scene.assets))
        self.from_mesh_button.setEnabled(self._document.mesh_result is not None)
        with blocked(self.asset_box):
            chosen = self.asset_box.currentData()
            self.asset_box.clear()
            self.asset_box.addItem("(none)", "")
            for asset in scene.assets:
                self.asset_box.addItem(asset.name, asset.name)
            self.asset_box.setCurrentIndex(max(0, self.asset_box.findData(chosen)))
        self._show_asset()

    def _show_asset(self) -> None:
        row = self.asset_list.currentRow()
        has = self._document is not None and 0 <= row < len(self._document.scene.assets)
        for w in (self.asset_name, self.asset_detail, self.asset_normalize):
            w.setEnabled(has)
        if not has:
            self.asset_info.setText("")
            return
        asset = self._document.scene.assets[row]
        with updating(self), blocked(self.asset_name, self.asset_detail, self.asset_normalize):
            self.asset_name.setText(asset.name)
            self.asset_detail.setValue(int(asset.detail))
            self.asset_normalize.setChecked(bool(asset.normalize))
        self.asset_detail.setEnabled(asset.kind == "primitive")
        self.asset_info.setText(asset.path if asset.path else f"built-in {asset.primitive}")

    # --- instancers ----------------------------------------------------------------------------------------------------
    def _add_instancer(self) -> None:
        if self._document is None:
            return
        if not self._document.scene.assets:
            self._document.add_asset(MeshAsset("sphere", "primitive", "sphere", 2))
        index = self._document.add_instancer()
        self.instancer_list.setCurrentRow(index)

    def _select_instancer(self, row: int) -> None:
        self._current_instancer = row
        self._show_instancer()

    def _refresh_instancers(self) -> None:
        scene = self._document.scene
        current = self._current_instancer if self._current_instancer >= 0 else self.instancer_list.currentRow()
        with blocked(self.instancer_list):
            self.instancer_list.clear()
            for inst in scene.instancers:
                self.instancer_list.addItem(f"{inst.name}  ·  {inst.asset or 'no asset'}  ·  {inst.mode}, depth {inst.depth}"
                                            + ("" if inst.visible else "  ·  hidden"))
            if scene.instancers:
                current = min(max(0, current), len(scene.instancers) - 1)
                self.instancer_list.setCurrentRow(current)
            else:
                current = -1
        self._current_instancer = current
        self.remove_instancer_button.setEnabled(bool(scene.instancers))
        self._show_instancer()

    def _show_instancer(self) -> None:
        inst = self.current_instancer()
        has = inst is not None
        for w in (self.name, self.asset_box, self.source_box, self.mode_box, self.count, self.depth, self.levels_box, self.frame_box, self.size,
                  self.falloff, self.min_size, self.max_instances, self.color_box, self.color, self.seed, self.visible_check, self.specular,
                  self.shininess):
            w.setEnabled(has)
        self.own_group.setVisible(has and inst.source == "own")
        if not has:
            return
        with updating(self), blocked(self.name, self.asset_box, self.source_box, self.mode_box, self.count, self.depth, self.levels_box,
                                     self.frame_box, self.max_instances, self.color_box, self.seed, self.visible_check):
            self.name.setText(inst.name)
            self.asset_box.setCurrentIndex(max(0, self.asset_box.findData(inst.asset)))
            self.source_box.setCurrentIndex(max(0, self.source_box.findData(inst.source)))
            self.mode_box.setCurrentIndex(max(0, self.mode_box.findData(inst.mode)))
            self.count.setValue(int(inst.count))
            self.depth.setValue(int(inst.depth))
            self.levels_box.setCurrentIndex(max(0, self.levels_box.findData(inst.tree_levels)))
            self.frame_box.setCurrentIndex(max(0, self.frame_box.findData(inst.frame_mode)))
            self.size.set_value(inst.size)
            self.falloff.set_value(inst.size_falloff)
            self.min_size.set_value(inst.min_size)
            self.max_instances.setValue(int(inst.max_instances))
            self.color_box.setCurrentIndex(max(0, self.color_box.findData(inst.color_mode)))
            self.color.set_color(inst.material.color)
            self.seed.setValue(int(inst.seed))
            self.visible_check.setChecked(bool(inst.visible))
            self.specular.set_value(inst.material.specular)
            self.shininess.set_value(inst.material.shininess)
        self.count.setEnabled(inst.mode == "chaos")
        self.levels_box.setEnabled(inst.mode == "tree")
        self.seed.setEnabled(inst.mode == "chaos")
        self.color.setEnabled(inst.color_mode == "fixed")
        if inst.source == "own":
            self._refresh_table(inst)

    # --- the own IFS table -------------------------------------------------------------------------------------------------
    def _refresh_table(self, inst: Instancer) -> None:
        flame = inst.flame
        with blocked(self.table):
            self.table.setRowCount(len(flame.xforms) if flame is not None else 0)
            if flame is None:
                return
            for row, xform in enumerate(flame.xforms):
                values = holon.read_affine3d(xform)
                for col, key in enumerate(COLUMN_KEYS):
                    item = QTableWidgetItem()
                    if values is None:
                        item.setText("—" if key not in ("weight", "color") else f"{getattr(xform, key):.3g}")
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setToolTip("This transform is not a plain 3D affine map (edit it in the main window)")
                    else:
                        value = {"weight": values["weight"], "px": values["position"][0], "py": values["position"][1], "pz": values["position"][2],
                                 "rx": values["rotation"][0], "ry": values["rotation"][1], "rz": values["rotation"][2], "scale": values["scale"],
                                 "color": values["color"]}[key]
                        item.setText(f"{value:.{COLUMN_RANGES[key][2]}f}".rstrip("0").rstrip(".") if value != 0 else "0")
                    self.table.setItem(row, col, item)
        self.remove_xform_button.setEnabled(flame is not None and len(flame.xforms) > 1)

    def _cell_changed(self, row: int, col: int) -> None:
        inst = self.current_instancer()
        if inst is None or inst.flame is None or not 0 <= row < len(inst.flame.xforms) or self._updating:
            return
        xform = inst.flame.xforms[row]
        values = holon.read_affine3d(xform)
        if values is None:
            return
        item = self.table.item(row, col)
        try:
            number = float(item.text().replace(",", "."))
        except (TypeError, ValueError):
            self._refresh_table(inst)
            return
        key = COLUMN_KEYS[col]
        lo, hi, _decimals = COLUMN_RANGES[key]
        number = min(hi, max(lo, number))
        position = list(values["position"])
        rotation = list(values["rotation"])
        scale, weight, color = values["scale"], values["weight"], values["color"]
        if key in ("px", "py", "pz"):
            position["xyz".index(key[1])] = number
        elif key in ("rx", "ry", "rz"):
            rotation["xyz".index(key[1])] = number
        elif key == "scale":
            scale = number if abs(number) > 1e-6 else 1e-6
        elif key == "weight":
            weight = number
        else:
            color = number
        new = holon.affine3d_xform(tuple(position), tuple(rotation), scale, weight, color, xform.name)
        self._document.set_own_xform(self._current_instancer, row, new, merge_key=("cell", row, col))
        self._document.end_merge()

    def _add_xform(self) -> None:
        inst = self.current_instancer()
        if inst is None or self._document is None:
            return
        count = len(inst.flame.xforms) if inst.flame is not None else 0
        new = holon.affine3d_xform((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.5, 1.0, (count % 4) / 3.0, f"holon {count + 1}")
        self._document.set_own_xform(self._current_instancer, count, new)

    def _remove_xform(self) -> None:
        inst = self.current_instancer()
        if inst is None or self._document is None:
            return
        row = self.table.currentRow()
        if row >= 0:
            self._document.set_own_xform(self._current_instancer, row, None)

    def _send(self) -> None:
        inst = self.current_instancer()
        if inst is not None and inst.flame is not None:
            self.flame_sent.emit(inst.flame.copy())

    # --- binding -------------------------------------------------------------------------------------------------------
    def bind(self, document: Scene3DDocument) -> None:
        self._document = document
        for signal in (document.scene_replaced, document.scene_restored, document.assets_changed, document.instancers_changed,
                       document.mesh_changed, document.solid_changed):
            signal.connect(self.refresh)
        document.asset_failed.connect(self.status)
        self.refresh()

    def refresh(self) -> None:
        if self._document is None:
            return
        with updating(self), blocked(self.show_fractal_check):
            self.show_fractal_check.setChecked(bool(self._document.scene.solid.show_fractal))
        self._refresh_assets()
        self._refresh_instancers()


__all__ = ["InstancesPanel", "asset_folder", "COLUMNS", "COLUMN_KEYS"]
