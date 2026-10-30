"""The 3D Editor's Mesh and Export tabs.

`MeshPanel`: the capture (points, resolution), the density (a log-histogram with the threshold marker, smoothing,
dilate / erode, colours), the clean-up level and its knobs, *Generate mesh* with progress, the result summary
and what the viewport shows (the solid render, the clean mesh or the full mesh). `ExportPanel`: form, formats,
materials, units, destination, *Export* with progress and links to the files. Both bind to the
`Scene3DDocument` like the other panels; the window runs the jobs and feeds progress back.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QSize, QUrl, Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QProgressBar, QPushButton, QRadioButton, QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

from ...solid.io import EXPORT_FORMATS
from ...solid.io.usd import usd_core_available
from ...widgets.silent import blocked, updating
from .document import Scene3DDocument
from .panels import _Panel

HISTOGRAM_HEIGHT = 72
BAR = QColor(90, 150, 220)
BAR_BELOW = QColor(120, 120, 120)
MARKER = QColor(230, 90, 60)
BACKGROUND = QColor(28, 28, 32)
TEXT = QColor(150, 150, 150)
POINT_STEPS = (100_000, 250_000, 500_000, 1_000_000, 2_000_000, 4_000_000, 8_000_000)
TEXTURE_SIZES = (512, 1024, 2048, 4096)


class DensityHistogram(QWidget):
    """The log-histogram of the normalized voxel density with the threshold as a draggable marker.

    Signals:
        threshold_changed(float): The marker was dragged (merge key "threshold"; `drag_finished` ends the step).
        drag_finished()
    """
    threshold_changed = Signal(float)
    drag_finished = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._edges: np.ndarray | None = None
        self._counts: np.ndarray | None = None
        self._threshold = 0.15
        self._dragging = False
        self.setMinimumHeight(HISTOGRAM_HEIGHT)
        self.setMaximumHeight(HISTOGRAM_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.SplitHCursor)
        self.setToolTip("How much of the fractal sits at each density (log scale). Drag the marker to set the threshold: "
                        "what is denser becomes solid.")

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(240, HISTOGRAM_HEIGHT)

    def set_histogram(self, edges: np.ndarray | None, counts: np.ndarray | None) -> None:
        self._edges = None if edges is None else np.asarray(edges, dtype=np.float64)
        self._counts = None if counts is None else np.asarray(counts, dtype=np.float64)
        self.update()

    def set_threshold(self, threshold: float) -> None:
        self._threshold = float(threshold)
        self.update()

    @property
    def threshold(self) -> float:
        return self._threshold

    # --- geometry: x ↔ density on a log axis over the histogram's range -------------------------------------------
    def _range(self) -> tuple[float, float]:
        if self._edges is None or self._edges.size < 2:
            return 1e-3, 1.0
        return max(float(self._edges[0]), 1e-9), max(float(self._edges[-1]), 1e-8)

    def _x_of(self, value: float) -> float:
        lo, hi = self._range()
        span = max(np.log(hi) - np.log(lo), 1e-9)
        return 1 + (self.width() - 2) * (np.log(max(value, lo)) - np.log(lo)) / span

    def _value_at(self, x: float) -> float:
        lo, hi = self._range()
        t = min(1.0, max(0.0, (x - 1) / max(1, self.width() - 2)))
        return float(np.exp(np.log(lo) + t * (np.log(hi) - np.log(lo))))

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND)
        h = self.height()
        if self._counts is None or self._edges is None or self._counts.sum() == 0:
            painter.setPen(TEXT)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Generate a mesh to see the density")
        else:
            peak = max(np.log1p(self._counts).max(), 1e-9)
            for i, count in enumerate(self._counts):
                x0, x1 = self._x_of(self._edges[i]), self._x_of(self._edges[i + 1])
                bar = (h - 4) * np.log1p(count) / peak
                painter.fillRect(int(x0), int(h - 2 - bar), max(1, int(x1 - x0) - 1), int(bar),
                                 BAR if self._edges[i + 1] > self._threshold else BAR_BELOW)
        x = int(self._x_of(self._threshold))
        painter.setPen(QPen(MARKER, 2))
        painter.drawLine(x, 0, x, h)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._move(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._move(event.position().x())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._dragging = False
            self.drag_finished.emit()

    def _move(self, x: float) -> None:
        value = round(self._value_at(x), 4)
        if value != self._threshold:
            self._threshold = value
            self.update()
            self.threshold_changed.emit(value)


class MeshPanel(_Panel):
    """Meshing settings, *Generate mesh*, the result and the viewport's display choice.

    Signals:
        generate_requested(): The button.
        cancel_requested(): Cancel while a job runs.
        display_requested(str, str): (display mode: solid / mesh, mesh form: clean / full).
    """
    generate_requested = Signal()
    cancel_requested = Signal()
    display_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.points_box = QComboBox(self)
        for n in POINT_STEPS:
            self.points_box.addItem(f"{n / 1e6:g} M points" if n >= 1_000_000 else f"{n // 1000} k points", n)
        self.points_box.setToolTip("Orbit points captured into the voxel grid (more = denser, slower)")
        self.resolution = QSpinBox(self)
        self.resolution.setRange(16, 512)
        self.resolution.setSingleStep(16)
        self.resolution.setToolTip("Voxels along the longest side (128 = quick, 256 = detailed, 512 = large meshes and a long wait)")
        self.histogram = DensityHistogram(self)
        self.threshold = self._row("Threshold", 0.001, 1.0, 3, "Iso-level on the normalized density: lower keeps more, higher keeps only the dense core",
                                   self._mesh("threshold"), "threshold")
        self.smoothing = self._row("Smoothing", 0.0, 4.0, 1, "Gaussian blur of the density in voxels: rounds the surface, closes small gaps",
                                   self._mesh("smoothing"), "smoothing")
        self.dilate = QSpinBox(self)
        self.dilate.setRange(0, 3)
        self.dilate.setToolTip("Thicken thin parts by this many voxels")
        self.erode = QSpinBox(self)
        self.erode.setRange(0, 3)
        self.erode.setToolTip("Thin the shape by this many voxels (removes noise)")
        self.colors_check = QCheckBox("Vertex colours from the palette", self)
        self.level_box = QComboBox(self)
        self.level_box.addItem("Simple clean-up (weld, drop debris, orient)", "simple")
        self.level_box.addItem("Aggressive (largest piece, fill holes, smooth, decimate)", "aggressive")
        self.level_box.addItem("Remesh (closed voxel solid — the last resort)", "remesh")
        self.level_box.setToolTip("How far the clean mesh goes beyond the raw surface")
        self.min_piece = QSpinBox(self)
        self.min_piece.setRange(0, 100_000)
        self.min_piece.setSingleStep(50)
        self.min_piece.setToolTip("Pieces with fewer faces are dropped (0 = keep every piece)")
        self.fill_holes = QSpinBox(self)
        self.fill_holes.setRange(0, 5000)
        self.fill_holes.setSingleStep(50)
        self.fill_holes.setToolTip("Holes with up to this many edges are closed (aggressive / remesh)")
        self.smooth_iterations = QSpinBox(self)
        self.smooth_iterations.setRange(0, 50)
        self.smooth_iterations.setToolTip("Taubin smoothing passes on the clean mesh (shrink-free)")
        self.target_faces = QSpinBox(self)
        self.target_faces.setRange(0, 5_000_000)
        self.target_faces.setSingleStep(10_000)
        self.target_faces.setSpecialValueText("no decimation")
        self.target_faces.setToolTip("Decimate the clean mesh to about this many faces (quadric edge collapse; 0 = keep all)")
        self.generate_button = QPushButton("Generate mesh", self)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setEnabled(False)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress_label = QLabel(self)
        self.result_label = QLabel(self)
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.show_solid = QRadioButton("Solid render", self)
        self.show_clean = QRadioButton("Clean mesh", self)
        self.show_full = QRadioButton("Full mesh", self)
        self.show_group = QButtonGroup(self)
        for button in (self.show_solid, self.show_clean, self.show_full):
            self.show_group.addButton(button)
        self.show_solid.setChecked(True)
        self._build()
        self._connect()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        capture = QGroupBox("Capture", self)
        form = QFormLayout(capture)
        form.addRow("Points", self.points_box)
        form.addRow("Resolution", self.resolution)
        layout.addWidget(capture)
        density = QGroupBox("Surface", self)
        d = QVBoxLayout(density)
        d.addWidget(self.histogram)
        d.addWidget(self.threshold)
        d.addWidget(self.smoothing)
        morph = QHBoxLayout()
        morph.addWidget(QLabel("Dilate", density))
        morph.addWidget(self.dilate)
        morph.addSpacing(12)
        morph.addWidget(QLabel("Erode", density))
        morph.addWidget(self.erode)
        morph.addStretch(1)
        d.addLayout(morph)
        d.addWidget(self.colors_check)
        layout.addWidget(density)
        cleanup = QGroupBox("Clean mesh", self)
        c = QFormLayout(cleanup)
        c.addRow(self.level_box)
        c.addRow("Min piece (faces)", self.min_piece)
        c.addRow("Fill holes up to", self.fill_holes)
        c.addRow("Smoothing passes", self.smooth_iterations)
        c.addRow("Target faces", self.target_faces)
        layout.addWidget(cleanup)
        buttons = QHBoxLayout()
        buttons.addWidget(self.generate_button)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(self.progress)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.result_label)
        show = QHBoxLayout()
        show.addWidget(QLabel("Show", self))
        for button in (self.show_solid, self.show_clean, self.show_full):
            show.addWidget(button)
        show.addStretch(1)
        layout.addLayout(show)
        layout.addStretch(1)

    def _connect(self) -> None:
        self.points_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._set(None, points=int(self.points_box.currentData())))
        self.resolution.valueChanged.connect(lambda v: None if self._updating else self._set("resolution", resolution=int(v)))
        self.dilate.valueChanged.connect(lambda v: None if self._updating else self._set("dilate", dilate=int(v)))
        self.erode.valueChanged.connect(lambda v: None if self._updating else self._set("erode", erode=int(v)))
        self.colors_check.toggled.connect(lambda on: None if self._updating else self._set(None, colors=bool(on)))
        self.level_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._set(None, clean=self.level_box.currentData()))
        self.min_piece.valueChanged.connect(lambda v: None if self._updating else self._set("min_piece", min_piece_faces=int(v)))
        self.fill_holes.valueChanged.connect(lambda v: None if self._updating else self._set("fill_holes", fill_holes=int(v)))
        self.smooth_iterations.valueChanged.connect(lambda v: None if self._updating else self._set("smooth_iterations", smooth_iterations=int(v)))
        self.target_faces.valueChanged.connect(lambda v: None if self._updating else self._set("target_faces", target_faces=int(v)))
        self.histogram.threshold_changed.connect(lambda v: None if self._updating else self._set("threshold", threshold=float(v)))
        self.histogram.drag_finished.connect(lambda: self._document.end_merge() if self._document else None)
        self.generate_button.clicked.connect(self.generate_requested)
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.show_solid.toggled.connect(lambda on: self.display_requested.emit("solid", "clean") if on else None)
        self.show_clean.toggled.connect(lambda on: self.display_requested.emit("mesh", "clean") if on else None)
        self.show_full.toggled.connect(lambda on: self.display_requested.emit("mesh", "full") if on else None)
        for box in (self.resolution, self.dilate, self.erode, self.min_piece, self.fill_holes, self.smooth_iterations, self.target_faces):
            box.setKeyboardTracking(False)

    def _mesh(self, field: str):
        return lambda value, key: self._set(key, **{field: value})

    def _set(self, merge_key, **fields) -> None:
        if self._document is not None:
            self._document.update_mesh_settings(merge_key, **fields)

    def bind(self, document: Scene3DDocument) -> None:
        self._document = document
        for signal in (document.scene_replaced, document.scene_restored, document.mesh_settings_changed):
            signal.connect(self.refresh)
        document.mesh_changed.connect(self.show_result)
        document.fractal_changed.connect(self.refresh)
        self.refresh()
        self.show_result()

    def refresh(self) -> None:
        if self._document is None:
            return
        m = self._document.scene.mesh
        with updating(self), blocked(self.points_box, self.resolution, self.dilate, self.erode, self.colors_check, self.level_box,
                                     self.min_piece, self.fill_holes, self.smooth_iterations, self.target_faces):
            index = self.points_box.findData(int(m.points))
            if index < 0:
                index = int(np.argmin([abs(n - m.points) for n in POINT_STEPS]))
            self.points_box.setCurrentIndex(index)
            self.resolution.setValue(int(m.resolution))
            self.threshold.set_value(m.threshold)
            self.histogram.set_threshold(m.threshold)
            self.smoothing.set_value(m.smoothing)
            self.dilate.setValue(int(m.dilate))
            self.erode.setValue(int(m.erode))
            self.colors_check.setChecked(bool(m.colors))
            self.level_box.setCurrentIndex(max(0, self.level_box.findData(m.clean)))
            self.min_piece.setValue(int(m.min_piece_faces))
            self.fill_holes.setValue(int(m.fill_holes))
            self.smooth_iterations.setValue(int(m.smooth_iterations))
            self.target_faces.setValue(int(m.target_faces))
        aggressive = m.clean in ("aggressive", "remesh")
        self.fill_holes.setEnabled(aggressive)
        self.generate_button.setEnabled(self._document.flame is not None and not self.cancel_button.isEnabled())
        result = self._document.mesh_result
        stale = result is not None and result.settings != m
        self.generate_button.setText("Generate mesh" if result is None or not stale else "Regenerate mesh (settings changed)")

    def show_result(self) -> None:
        """Summarise the generated mesh (or say there is none) and enable the mesh displays."""
        result = self._document.mesh_result if self._document is not None else None
        has = result is not None
        for button in (self.show_clean, self.show_full):
            button.setEnabled(has)
        if not has:
            self.result_label.setText("No mesh yet.")
            self.histogram.set_histogram(None, None)
            if not self.show_solid.isChecked():
                with blocked(self.show_group, self.show_solid, self.show_clean, self.show_full):
                    self.show_solid.setChecked(True)
            self.refresh()
            return
        edges, counts = result.histogram
        self.histogram.set_histogram(edges, counts)
        full, cl = result.full_report, result.clean_report
        lines = [f"<b>Full:</b> {full.faces:,} faces, {full.components} pieces, {'watertight' if full.watertight else 'open'}",
                 f"<b>Clean:</b> {cl.faces:,} faces, {cl.components} piece{'s' if cl.components != 1 else ''}, "
                 f"{'watertight' if cl.watertight else 'open'}, {'consistent' if cl.consistent else 'inconsistent'}"
                 + (f", thinnest wall ≥ {cl.thin_wall:.3g}" if cl.thin_wall is not None else "")
                 + (f", {cl.self_intersections} self-intersections" if cl.self_intersections else ""),
                 f"<i>{cl.recommendation()}</i>"]
        if cl.notes:
            lines.append("Clean-up: " + "; ".join(cl.notes))
        lines.append(f"{result.points:,} points · grid {'×'.join(map(str, result.grid_shape))} · "
                     + " · ".join(f"{k} {v:.1f} s" for k, v in result.seconds.items()))
        self.result_label.setText("<br>".join(lines))
        self.refresh()

    def set_running(self, running: bool) -> None:
        self.cancel_button.setEnabled(running)
        self.generate_button.setEnabled(not running and self._document is not None and self._document.flame is not None)
        if not running:
            self.progress.setValue(0)
        for widget in (self.points_box, self.resolution, self.level_box):
            widget.setEnabled(not running)

    def show_progress(self, fraction: float, message: str) -> None:
        self.progress.setValue(int(fraction * 1000))
        self.progress_label.setText(message)

    def sync_display(self, display: str, form: str) -> None:
        """Reflect the document's display mode (solid / mesh) and the viewport's mesh form in the radio buttons."""
        with blocked(self.show_group, self.show_solid, self.show_clean, self.show_full):
            if display != "mesh":
                self.show_solid.setChecked(True)
            elif form == "full":
                self.show_full.setChecked(True)
            else:
                self.show_clean.setChecked(True)


def _installed(module: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(module) is not None


def optional_dependency_hints() -> list[str]:
    """What the optional packages would add (shown under the Export tab)."""
    hints = []
    if not usd_core_available():
        hints.append("usd-core is not installed: USD exports are written as .usda text only.")
    if not _installed("xatlas"):
        hints.append("xatlas is not installed: the atlas UV mode falls back to the box projection.")
    if not _installed("fast_simplification"):
        hints.append("fast-simplification is not installed: decimation uses the built-in quadric collapser (slower on very large meshes).")
    return hints


class ExportPanel(_Panel):
    """Form, formats, materials, units, destination and *Export*.

    Signals:
        export_requested(): The button.
    """
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.subject_mesh = QRadioButton("The Mesh tab's mesh", self)
        self.subject_instances = QRadioButton("The instancers, instanced", self)
        self.subject_instances.setToolTip("USD PointInstancer, glTF instancing and the Blender script keep the instances; other formats get the baked mesh")
        self.subject_baked = QRadioButton("The instancers baked into one mesh", self)
        self.subject_group = QButtonGroup(self)
        for button in (self.subject_mesh, self.subject_instances, self.subject_baked):
            self.subject_group.addButton(button)
        self.form_clean = QRadioButton("Clean mesh (print-ready)", self)
        self.form_full = QRadioButton("Full mesh (every triangle)", self)
        self.form_group = QButtonGroup(self)
        self.form_group.addButton(self.form_clean)
        self.form_group.addButton(self.form_full)
        self.format_checks: dict[str, QCheckBox] = {}
        for fmt in EXPORT_FORMATS:
            box = QCheckBox(fmt.label, self)
            if not fmt.available:
                box.setEnabled(False)
                box.setToolTip(f"Not available: {fmt.hint}")
            self.format_checks[fmt.key] = box
        self.materials_box = QComboBox(self)
        self.materials_box.addItem("Vertex colours", "vertex")
        self.materials_box.addItem("UVs + baked texture", "texture")
        self.materials_box.addItem("Geometry only", "none")
        self.uv_box = QComboBox(self)
        self.uv_box.addItem("Box projection", "box")
        self.uv_box.addItem("Spherical", "spherical")
        self.uv_box.addItem("Cylindrical", "cylindrical")
        self.uv_box.addItem("Atlas (xatlas)", "atlas")
        self.texture_box = QComboBox(self)
        for size in TEXTURE_SIZES:
            self.texture_box.addItem(f"{size} px", size)
        self.units_world = QRadioButton("Flame units", self)
        self.units_mm = QRadioButton("Millimetres, longest side", self)
        self.units_group = QButtonGroup(self)
        self.units_group.addButton(self.units_world)
        self.units_group.addButton(self.units_mm)
        self.size_mm = QSpinBox(self)
        self.size_mm.setRange(1, 2000)
        self.size_mm.setSuffix(" mm")
        self.blender_check = QCheckBox("Blender scene script (lights, camera, material)", self)
        self.report_check = QCheckBox("Mesh report (Markdown)", self)
        self.folder = QLineEdit(self)
        self.folder.setPlaceholderText("Folder to write into")
        self.browse_button = QPushButton("Browse…", self)
        self.name = QLineEdit(self)
        self.name.setPlaceholderText("File name (without extension)")
        self.export_button = QPushButton("Export", self)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress_label = QLabel(self)
        self.result_label = QLabel(self)
        self.result_label.setWordWrap(True)
        self.result_label.setOpenExternalLinks(False)
        self.result_label.linkActivated.connect(lambda link: QDesktopServices.openUrl(QUrl.fromLocalFile(link.removeprefix("file:"))))
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.hint_label = QLabel(self)
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: #808080;")
        self._running = False
        self._build()
        self._connect()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        subject_box = QGroupBox("What to export", self)
        sb = QVBoxLayout(subject_box)
        for button in (self.subject_mesh, self.subject_instances, self.subject_baked):
            sb.addWidget(button)
        layout.addWidget(subject_box)
        form_box = QGroupBox("Which mesh", self)
        fb = QHBoxLayout(form_box)
        fb.addWidget(self.form_clean)
        fb.addWidget(self.form_full)
        layout.addWidget(form_box)
        self.form_box = form_box
        formats = QGroupBox("Formats", self)
        fl = QVBoxLayout(formats)
        for box in self.format_checks.values():
            fl.addWidget(box)
        layout.addWidget(formats)
        materials = QGroupBox("Materials and units", self)
        ml = QFormLayout(materials)
        ml.addRow("Colour", self.materials_box)
        ml.addRow("UVs", self.uv_box)
        ml.addRow("Texture", self.texture_box)
        units = QHBoxLayout()
        units.addWidget(self.units_world)
        units.addWidget(self.units_mm)
        units.addWidget(self.size_mm)
        units.addStretch(1)
        ml.addRow("Units", units)
        ml.addRow(self.blender_check)
        ml.addRow(self.report_check)
        layout.addWidget(materials)
        dest = QGroupBox("Destination", self)
        dl = QFormLayout(dest)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(self.browse_button)
        dl.addRow("Folder", folder_row)
        dl.addRow("Name", self.name)
        layout.addWidget(dest)
        buttons = QHBoxLayout()
        buttons.addWidget(self.export_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(self.progress)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.result_label)
        layout.addWidget(self.hint_label)
        layout.addStretch(1)
        self.hint_label.setText(" ".join(optional_dependency_hints()))

    def _connect(self) -> None:
        self.subject_mesh.toggled.connect(lambda on: None if self._updating or not on else self._set(subject="mesh"))
        self.subject_instances.toggled.connect(lambda on: None if self._updating or not on else self._set(subject="instances"))
        self.subject_baked.toggled.connect(lambda on: None if self._updating or not on else self._set(subject="baked"))
        self.form_clean.toggled.connect(lambda on: None if self._updating or not on else self._set(form="clean"))
        self.form_full.toggled.connect(lambda on: None if self._updating or not on else self._set(form="full"))
        for box in self.format_checks.values():
            box.toggled.connect(lambda _on: None if self._updating else self._set(formats=self.selected_formats()))
        self.materials_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._set(materials=self.materials_box.currentData()))
        self.uv_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._set(uv_mode=self.uv_box.currentData()))
        self.texture_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._set(texture_size=int(self.texture_box.currentData())))
        self.units_world.toggled.connect(lambda on: None if self._updating or not on else self._set(units="world"))
        self.units_mm.toggled.connect(lambda on: None if self._updating or not on else self._set(units="mm"))
        self.size_mm.valueChanged.connect(lambda v: None if self._updating else self._set(size_mm=float(v)))
        self.blender_check.toggled.connect(lambda on: None if self._updating else self._set(blender=bool(on)))
        self.report_check.toggled.connect(lambda on: None if self._updating else self._set(report=bool(on)))
        self.folder.editingFinished.connect(lambda: None if self._updating else self._set(folder=self.folder.text().strip()))
        self.name.editingFinished.connect(lambda: None if self._updating else self._set(name=self.name.text().strip()))
        self.browse_button.clicked.connect(self._browse)
        self.export_button.clicked.connect(self.export_requested)
        self.size_mm.setKeyboardTracking(False)

    def _set(self, **fields) -> None:
        if self._document is not None:
            self._document.update_export_settings(**fields)

    def selected_formats(self) -> list[str]:
        return [key for key, box in self.format_checks.items() if box.isChecked()]

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Export folder", self.folder.text().strip() or str(Path.home()))
        if chosen:
            self.folder.setText(chosen)
            self._set(folder=chosen)

    def bind(self, document: Scene3DDocument) -> None:
        self._document = document
        for signal in (document.scene_replaced, document.scene_restored, document.export_settings_changed, document.mesh_changed,
                       document.instancers_changed, document.assets_changed):
            signal.connect(self.refresh)
        self.refresh()

    def can_export(self) -> bool:
        """Whether there is something to write for the chosen subject."""
        if self._document is None:
            return False
        e = self._document.scene.export
        if e.subject == "mesh":
            return self._document.mesh_result is not None
        return bool(self._document.scene.visible_instancers())

    def refresh(self) -> None:
        if self._document is None:
            return
        e = self._document.scene.export
        with updating(self), blocked(self.form_group, self.form_clean, self.form_full, self.materials_box, self.uv_box, self.texture_box,
                                     self.units_group, self.units_world, self.units_mm, self.size_mm, self.blender_check, self.report_check,
                                     self.folder, self.name, self.subject_group, self.subject_mesh, self.subject_instances, self.subject_baked,
                                     *self.format_checks.values()):
            {"mesh": self.subject_mesh, "instances": self.subject_instances, "baked": self.subject_baked}.get(e.subject, self.subject_mesh).setChecked(True)
            (self.form_full if e.form == "full" else self.form_clean).setChecked(True)
            for key, box in self.format_checks.items():
                box.setChecked(key in e.formats)
            self.materials_box.setCurrentIndex(max(0, self.materials_box.findData(e.materials)))
            self.uv_box.setCurrentIndex(max(0, self.uv_box.findData(e.uv_mode)))
            self.texture_box.setCurrentIndex(max(0, self.texture_box.findData(int(e.texture_size))))
            (self.units_mm if e.units == "mm" else self.units_world).setChecked(True)
            self.size_mm.setValue(int(round(e.size_mm)))
            self.blender_check.setChecked(bool(e.blender))
            self.report_check.setChecked(bool(e.report))
            if not self.folder.hasFocus():
                self.folder.setText(e.folder)
            if not self.name.hasFocus():
                self.name.setText(e.name)
        textured = e.materials == "texture"
        self.form_box.setEnabled(e.subject == "mesh")
        self.materials_box.setEnabled(e.subject == "mesh")
        self.uv_box.setEnabled(textured and e.subject == "mesh")
        self.texture_box.setEnabled(textured and e.subject == "mesh")
        self.size_mm.setEnabled(e.units == "mm")
        self.export_button.setEnabled(self.can_export() and bool(e.formats) and not self._running)
        self.export_button.setToolTip("" if self.can_export() else ("Generate a mesh first" if e.subject == "mesh" else "Add a visible instancer with an asset first"))

    def set_running(self, running: bool) -> None:
        self._running = running
        self.export_button.setEnabled(not running and self.can_export())
        if not running:
            self.progress.setValue(0)

    def show_progress(self, fraction: float, message: str) -> None:
        self.progress.setValue(int(fraction * 1000))
        self.progress_label.setText(message)

    def show_outcome(self, outcome) -> None:
        """Links to the files written."""
        links = ", ".join(f'<a href="file:{p}">{p.name}</a>' for p in outcome.files)
        line = f"Wrote {len(outcome.files)} file{'s' if len(outcome.files) != 1 else ''} in {outcome.seconds:.1f} s: {links}"
        if outcome.report is not None:
            line += f'<br>Report: <a href="file:{outcome.report}">{outcome.report.name}</a>'
        if outcome.notes:
            line += "<br><i>" + "; ".join(outcome.notes) + "</i>"
        self.result_label.setText(line)

    def show_failure(self, message: str) -> None:
        self.result_label.setText(f'<span style="color:#c0392b">{message}</span>')


__all__ = ["MeshPanel", "ExportPanel", "DensityHistogram"]
