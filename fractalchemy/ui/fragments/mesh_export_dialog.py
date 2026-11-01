"""*Render ▸ Export mesh…*: a DE-based fragment as a printable mesh (settings, progress, preview, report, export).

Left: how to sample (resolution, the box or *fit*, the threshold in voxels, colours, the clean-up level) with a
memory estimate, *Build mesh* / *Cancel* and the progress. Right: a preview still and the print report of the
clean mesh. Bottom: the export (formats, form, units, folder, name), *Export* and *Send to 3D Editor* (the clean
mesh as a PLY asset in the 3D Editor's asset folder). The jobs run on their own threads (`mesh_job.py`); the
settings persist under `fragments/mesh/`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ...fragments.gl.job import FragRequest
from ...fragments.gl.mesh import Bounds, provides_color
from ...fragments.mesh import CLEAN_LEVELS, MAX_RESOLUTION, DEExportSettings, DEMeshResult, DEMeshSettings, estimated_bytes
from ...solid.io import EXPORT_FORMATS
from ...widgets.images import rgba_to_qimage
from ...widgets.layouts import row
from .mesh_job import DEExportJob, DEPreviewJob, MeshFromDEJob

SETTINGS_GROUP = "fragments/mesh"
PREVIEW_SIZE = (360, 300)


class MeshExportDialog(QDialog):
    """DE → mesh → files (see the module docstring).

    Args:
        parent: The Fragments window.
        request: The built fragment (program + values) to probe.
        fragment_name: For the report and the default file name.
        settings: Where the dialog's settings persist.
        three_d: Returns the 3D Editor window (None: no *Send to 3D Editor*).
        fragment_dir: The default export folder.
    """

    def __init__(self, parent: QWidget | None, request: FragRequest, fragment_name: str, settings: QSettings,
                 three_d: Callable | None = None, fragment_dir: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Export mesh — {fragment_name}")
        self._request = request
        self._fragment_name = fragment_name
        self._settings = settings
        self._three_d = three_d
        self._result: DEMeshResult | None = None
        self._job: MeshFromDEJob | None = None
        self._export_job: DEExportJob | None = None
        self._preview_job: DEPreviewJob | None = None
        self._build()
        self._restore(fragment_dir)
        self._refresh_estimate()
        self._refresh_buttons()

    # --- layout --------------------------------------------------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(self._sampling_group(), 0)
        top.addWidget(self._result_group(), 1)
        layout.addLayout(top)
        layout.addWidget(self._export_group())
        buttons = QHBoxLayout()
        self.send_button = QPushButton("Send to 3D Editor")
        self.send_button.setToolTip("Save the clean mesh as a PLY asset and open it in the 3D Editor's Instances tab")
        self.send_button.clicked.connect(self._send_to_three_d)
        self.send_button.setVisible(self._three_d is not None)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        buttons.addWidget(self.send_button)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def _sampling_group(self) -> QGroupBox:
        group = QGroupBox("Sampling the distance estimator")
        form = QFormLayout(group)
        self.resolution = QSpinBox()
        self.resolution.setRange(8, MAX_RESOLUTION)
        self.resolution.setSingleStep(16)
        self.resolution.setToolTip("Voxels per axis (memory and time grow with the cube)")
        self.resolution.valueChanged.connect(self._refresh_estimate)
        form.addRow("Resolution", self.resolution)
        self.fit = QCheckBox("Fit the box to the fractal (coarse pass first)")
        form.addRow(self.fit)
        self.centre = [self._coord_spin() for _ in range(3)]
        form.addRow("Box centre", row(*self.centre, stretch_all=True))
        self.size = QDoubleSpinBox()
        self.size.setRange(0.001, 1000.0)
        self.size.setDecimals(3)
        self.size.setToolTip("Side of the cube sampled (shrunk by *fit*)")
        form.addRow("Box size", self.size)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(-10.0, 10.0)
        self.threshold.setSingleStep(0.1)
        self.threshold.setDecimals(2)
        self.threshold.setToolTip("The shell is DE = threshold × voxel size; 0.5 closes estimators that never go negative")
        form.addRow("Threshold (voxels)", self.threshold)
        self.colors = QCheckBox("Vertex colours from baseColor()")
        self.colors.setEnabled(provides_color(self._request.modern))
        self.colors.setToolTip("Needs `#define providesColor` and a baseColor() in the fragment")
        self.colors.toggled.connect(self._refresh_estimate)
        form.addRow(self.colors)
        self.clean = QComboBox()
        for level in CLEAN_LEVELS:
            self.clean.addItem(level, level)
        form.addRow("Clean-up", self.clean)
        self.smoothing = QSpinBox()
        self.smoothing.setRange(0, 50)
        form.addRow("Smoothing passes", self.smoothing)
        self.target_faces = QSpinBox()
        self.target_faces.setRange(0, 50_000_000)
        self.target_faces.setSingleStep(50_000)
        self.target_faces.setSpecialValueText("keep all")
        form.addRow("Target faces", self.target_faces)
        self.estimate = QLabel()
        form.addRow(self.estimate)
        self.build_button = QPushButton("Build mesh")
        self.build_button.clicked.connect(self._start)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel)
        form.addRow(row(self.build_button, self.cancel_button))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        form.addRow(self.progress)
        self.status = QLabel("Build the mesh to see it here")
        self.status.setWordWrap(True)
        form.addRow(self.status)
        return group

    def _coord_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-1000.0, 1000.0)
        spin.setDecimals(3)
        return spin

    def _result_group(self) -> QGroupBox:
        group = QGroupBox("Result")
        layout = QVBoxLayout(group)
        self.preview = QLabel()
        self.preview.setMinimumSize(*PREVIEW_SIZE)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("QLabel { background: #3a3f48; }")
        layout.addWidget(self.preview, 1)
        self.report = QLabel()
        self.report.setWordWrap(True)
        self.report.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.report)
        return group

    def _export_group(self) -> QGroupBox:
        group = QGroupBox("Export")
        grid = QGridLayout(group)
        self.format_checks: dict[str, QCheckBox] = {}
        for index, fmt in enumerate(EXPORT_FORMATS):
            box = QCheckBox(fmt.label)
            box.setEnabled(fmt.available)
            if not fmt.available:
                box.setToolTip(fmt.hint)
            self.format_checks[fmt.key] = box
            grid.addWidget(box, index // 4, index % 4)
        options = QHBoxLayout()
        self.form = QComboBox()
        self.form.addItem("clean mesh", "clean")
        self.form.addItem("full isosurface", "full")
        self.export_colors = QCheckBox("Vertex colours")
        self.units = QComboBox()
        self.units.addItem("world units", "world")
        self.units.addItem("millimetres", "mm")
        self.size_mm = QDoubleSpinBox()
        self.size_mm.setRange(1.0, 10000.0)
        self.size_mm.setSuffix(" mm")
        self.units.currentIndexChanged.connect(lambda: self.size_mm.setEnabled(self.units.currentData() == "mm"))
        self.report_check = QCheckBox("Report")
        for widget in (QLabel("Form"), self.form, self.export_colors, self.units, self.size_mm, self.report_check):
            options.addWidget(widget)
        options.addStretch(1)
        grid.addLayout(options, 2, 0, 1, 4)
        where = QHBoxLayout()
        self.folder = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        self.name = QLineEdit()
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self._export)
        for widget, stretch in ((QLabel("Folder"), 0), (self.folder, 1), (browse, 0), (QLabel("Name"), 0), (self.name, 0), (self.export_button, 0)):
            where.addWidget(widget, stretch)
        grid.addLayout(where, 3, 0, 1, 4)
        return group

    # --- settings ------------------------------------------------------------------------------------------------------------
    def _restore(self, fragment_dir: Path | None) -> None:
        s = self._settings
        g = SETTINGS_GROUP
        self.resolution.setValue(int(s.value(f"{g}/resolution", 128)))
        self.fit.setChecked(s.value(f"{g}/fit", True, type=bool))
        for spin, axis in zip(self.centre, "xyz"):
            spin.setValue(float(s.value(f"{g}/centre_{axis}", 0.0)))
        self.size.setValue(float(s.value(f"{g}/size", 2.5)))
        self.threshold.setValue(float(s.value(f"{g}/threshold", 0.5)))
        self.colors.setChecked(s.value(f"{g}/colors", True, type=bool) and self.colors.isEnabled())
        self.clean.setCurrentIndex(max(0, self.clean.findData(s.value(f"{g}/clean", "simple"))))
        self.smoothing.setValue(int(s.value(f"{g}/smoothing", 0)))
        self.target_faces.setValue(int(s.value(f"{g}/target_faces", 0)))
        chosen = s.value(f"{g}/formats", ["ply"])
        chosen = [chosen] if isinstance(chosen, str) else list(chosen or ["ply"])
        for key, box in self.format_checks.items():
            box.setChecked(key in chosen and box.isEnabled())
        self.form.setCurrentIndex(max(0, self.form.findData(s.value(f"{g}/form", "clean"))))
        self.export_colors.setChecked(s.value(f"{g}/export_colors", True, type=bool))
        self.units.setCurrentIndex(max(0, self.units.findData(s.value(f"{g}/units", "world"))))
        self.size_mm.setValue(float(s.value(f"{g}/size_mm", 100.0)))
        self.size_mm.setEnabled(self.units.currentData() == "mm")
        self.report_check.setChecked(s.value(f"{g}/report", True, type=bool))
        self.folder.setText(str(s.value(f"{g}/folder", "") or (fragment_dir or Path.home())))
        self.name.setText(self._fragment_name.rsplit(".", 1)[0] or "fragment")

    def _save_settings(self) -> None:
        s = self._settings
        g = SETTINGS_GROUP
        m = self.mesh_settings()
        s.setValue(f"{g}/resolution", m.resolution)
        s.setValue(f"{g}/fit", m.fit)
        for axis, value in zip("xyz", m.bounds.center):
            s.setValue(f"{g}/centre_{axis}", value)
        s.setValue(f"{g}/size", m.bounds.size)
        s.setValue(f"{g}/threshold", m.threshold_voxels)
        s.setValue(f"{g}/colors", m.colors)
        s.setValue(f"{g}/clean", m.clean)
        s.setValue(f"{g}/smoothing", m.smooth_iterations)
        s.setValue(f"{g}/target_faces", m.target_faces)
        e = self.export_settings()
        s.setValue(f"{g}/formats", e.formats)
        s.setValue(f"{g}/form", e.form)
        s.setValue(f"{g}/export_colors", e.colors)
        s.setValue(f"{g}/units", e.units)
        s.setValue(f"{g}/size_mm", e.size_mm)
        s.setValue(f"{g}/report", e.report)
        s.setValue(f"{g}/folder", self.folder.text())

    def mesh_settings(self) -> DEMeshSettings:
        """The sampling / meshing settings as set in the dialog."""
        return DEMeshSettings(self.resolution.value(), Bounds(tuple(spin.value() for spin in self.centre), self.size.value()),
                              self.fit.isChecked(), self.threshold.value(), self.colors.isChecked(), self.clean.currentData(),
                              self.smoothing.value(), self.target_faces.value())

    def export_settings(self) -> DEExportSettings:
        """The export settings as set in the dialog."""
        formats = [key for key, box in self.format_checks.items() if box.isChecked()]
        return DEExportSettings(self.form.currentData(), formats, self.export_colors.isChecked(), self.units.currentData(),
                                self.size_mm.value(), self.report_check.isChecked())

    # --- building ------------------------------------------------------------------------------------------------------------
    def _refresh_estimate(self) -> None:
        size = estimated_bytes(self.resolution.value(), self.colors.isChecked())
        self.estimate.setText(f"{self.resolution.value()}³ voxels ≈ {size / 1e6:,.0f} MB")

    def _refresh_buttons(self) -> None:
        running = self._job is not None or self._export_job is not None
        self.build_button.setEnabled(not running)
        self.cancel_button.setEnabled(self._job is not None)
        ready = self._result is not None and not running and self._result.clean.face_count > 0
        self.export_button.setEnabled(ready)
        self.send_button.setEnabled(ready)

    def _start(self) -> None:
        settings = self.mesh_settings()
        problems = settings.check()
        if problems:
            self.status.setText("; ".join(problems))
            return
        self._save_settings()
        self._job = MeshFromDEJob(self._request, settings, self)
        self._job.progressed.connect(self._progressed)
        self._job.finished_with.connect(self._finished)
        self._job.failed.connect(self._failed)
        self._job.cancelled_signal.connect(self._cancelled)
        self._job.finished.connect(self._job_done)
        self.progress.setValue(0)
        self.status.setText("Starting…")
        self._refresh_buttons()
        self._job.start()

    def _cancel(self) -> None:
        if self._job is not None:
            self._job.cancel()
            self.status.setText("Cancelling…")

    def _progressed(self, fraction: float, message: str) -> None:
        self.progress.setValue(int(fraction * 1000))
        self.status.setText(message)

    def _finished(self, result: DEMeshResult) -> None:
        self._result = result
        rep = result.clean_report
        b = result.settings.bounds
        self.status.setText(f"{rep.faces:,} faces in {sum(result.seconds.values()):.1f} s — box centre "
                            f"({b.center[0]:.3g}, {b.center[1]:.3g}, {b.center[2]:.3g}) size {b.size:.3g}")
        self.report.setText(self._report_text(result))
        self._start_preview(result)

    def _report_text(self, result: DEMeshResult) -> str:
        rep = result.clean_report
        size = rep.size
        facts = [f"<b>{rep.vertices:,}</b> vertices, <b>{rep.faces:,}</b> faces, {rep.components} piece{'s' if rep.components != 1 else ''}",
                 f"{'watertight' if rep.watertight else f'{rep.boundary_edges} open edges'}, "
                 f"{rep.nonmanifold_edges} non-manifold edges, volume {rep.volume:.4g}",
                 f"size {size[0]:.3g} × {size[1]:.3g} × {size[2]:.3g} units, voxel {result.voxel_size:.3g}"]
        if rep.thin_wall is not None:
            facts.append(f"thinnest wall ≈ {rep.thin_wall:.3g} units")
        facts.append(f"<i>{rep.recommendation()}</i>")
        if rep.notes:
            facts.append("clean-up: " + "; ".join(rep.notes))
        return "<br>".join(facts)

    def _failed(self, message: str) -> None:
        self.status.setText(f"Failed: {message}")

    def _cancelled(self) -> None:
        self.status.setText("Cancelled")

    def _job_done(self) -> None:
        self._job = None
        self._refresh_buttons()

    # --- preview -------------------------------------------------------------------------------------------------------------
    def _start_preview(self, result: DEMeshResult) -> None:
        if result.clean.face_count == 0:
            self.preview.setText("empty mesh")
            return
        self.preview.setText("rendering the preview…")
        self._preview_job = DEPreviewJob(result.clean, *PREVIEW_SIZE, self)
        self._preview_job.finished_with.connect(self._show_preview)
        self._preview_job.failed.connect(lambda message: self.preview.setText(f"preview failed: {message}"))
        self._preview_job.start()

    def _show_preview(self, image) -> None:
        self.preview.setPixmap(QPixmap.fromImage(rgba_to_qimage(image)))

    # --- export --------------------------------------------------------------------------------------------------------------
    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Export folder", self.folder.text())
        if chosen:
            self.folder.setText(chosen)

    def _export(self) -> None:
        if self._result is None:
            return
        settings = self.export_settings()
        if not settings.formats:
            self.status.setText("Choose at least one format")
            return
        self._save_settings()
        name = self.name.text().strip() or "fragment"
        self._export_job = DEExportJob(self._result, settings, Path(self.folder.text() or "."), name, self._fragment_name, self)
        self._export_job.progressed.connect(self._progressed)
        self._export_job.finished_with.connect(self._exported)
        self._export_job.failed.connect(self._failed)
        self._export_job.finished.connect(self._export_done)
        self._refresh_buttons()
        self._export_job.start()

    def _exported(self, outcome) -> None:
        names = ", ".join(p.name for p in outcome.files)
        self.status.setText(f"Wrote {names}" + (f" and {outcome.report.name}" if outcome.report else "") + f" in {self.folder.text()}")

    def _export_done(self) -> None:
        self._export_job = None
        self._refresh_buttons()

    def _send_to_three_d(self) -> None:
        """The clean mesh as a PLY asset in the 3D Editor."""
        if self._result is None or self._three_d is None:
            return
        from ...solid.io import write_mesh
        from ..three_d.instances_panel import asset_folder

        name = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in self.name.text().strip()) or "fragment"
        target = asset_folder() / f"{name}.ply"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            write_mesh(self._result.clean, target, "ply", None, name)
        except (OSError, ValueError) as exc:
            self.status.setText(f"Could not save the asset: {exc}")
            return
        editor = self._three_d()
        editor.bring_to_front()
        editor.tabs.setCurrentWidget(editor.instances_panel)
        if editor.instances_panel.import_mesh(target):
            self.status.setText(f"Sent {target.name} to the 3D Editor")

    # --- closing -------------------------------------------------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        for job in (self._job, self._export_job, self._preview_job):
            if job is not None and job.isRunning():
                if hasattr(job, "cancel"):
                    job.cancel()
                job.wait(30000)
        self._save_settings()
        super().closeEvent(event)


__all__ = ["MeshExportDialog"]
