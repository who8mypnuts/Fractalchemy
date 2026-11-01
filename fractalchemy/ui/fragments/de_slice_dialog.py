"""*Build ▸ Debug view ▸ DE slice…*: the distance estimator on a plane, as a heat map — the debugger for estimators.

The plane goes through the camera's *Target* (or a centre you type) and is either aligned with the view (spanned
by the camera's right and up vectors) or one of the XY / XZ / YZ planes. Negative distances (inside) are blue,
positive ones run from white at the surface through yellow to red far away, and contour lines at multiples of a
step show the gradient: a good estimator has evenly spaced contours; overestimation (rays stepping through
surfaces, the "dust" of a fractal) shows as contours bunching towards the surface. *Follow the camera* re-samples
after every camera move. The sampling runs on its own context (`DESliceJob`).
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

from ...fragments.camera import Camera3D
from ...widgets.images import rgba_to_qimage
from ...widgets.layouts import row
from .document import FragDocument
from .mesh_job import DESliceJob

PLANES = ("view", "xy", "xz", "yz")
PLANE_LABELS = {"view": "Facing the camera (through Target)", "xy": "XY plane", "xz": "XZ plane", "yz": "YZ plane"}


def heat_map(values: np.ndarray, step: float) -> np.ndarray:
    """`(H, W, 4)` RGBA8 of a distance slice: inside blue, the surface white, outside white → yellow → red, contours every `step`."""
    d = np.nan_to_num(np.asarray(values, dtype=np.float64), nan=0.0, posinf=1e9, neginf=-1e9)
    outside = d >= 0.0
    t = np.clip(np.abs(d) / max(step * 8.0, 1e-9), 0.0, 1.0)            # 0 at the surface, 1 eight steps away
    rgb = np.zeros(d.shape + (3,), dtype=np.float64)
    rgb[outside] = np.stack([np.ones_like(t), 1.0 - t * 0.5, 1.0 - t], axis=-1)[outside]          # white → yellow → red
    rgb[~outside] = np.stack([1.0 - t, 1.0 - t * 0.6, np.ones_like(t)], axis=-1)[~outside]        # white → blue
    contour = np.abs((np.abs(d) / max(step, 1e-9)) % 1.0 - 0.5) > 0.46
    rgb[contour] *= 0.55
    rgba = np.concatenate([np.clip(rgb * 255.0, 0, 255).astype(np.uint8), np.full(d.shape + (1,), 255, np.uint8)], axis=-1)
    return rgba


class DESliceDialog(QDialog):
    """The slice view (see the module docstring)."""

    def __init__(self, parent: QWidget | None, document: FragDocument):
        super().__init__(parent)
        self.setWindowTitle(f"DE slice — {document.name}")
        self.document = document
        self._job: DESliceJob | None = None
        self._again = False
        self._timer = QTimer(self, singleShot=True, interval=300)
        self._timer.timeout.connect(self.refresh)
        self._build()
        document.camera_changed.connect(self._camera_moved)
        document.parameters_changed.connect(lambda *_a: self._camera_moved())
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.plane = QComboBox()
        for key in PLANES:
            self.plane.addItem(PLANE_LABELS[key], key)
        self.plane.currentIndexChanged.connect(lambda _i: self.refresh())
        form.addRow("Plane", self.plane)
        self.use_target = QCheckBox("Through the camera's Target")
        self.use_target.setChecked(True)
        self.use_target.toggled.connect(lambda _on: self._timer.start())
        form.addRow(self.use_target)
        self.centre = []
        for _axis in range(3):
            spin = QDoubleSpinBox()
            spin.setRange(-1000.0, 1000.0)
            spin.setDecimals(3)
            spin.valueChanged.connect(lambda _v: self._timer.start())
            self.centre.append(spin)
        form.addRow("Centre", row(*self.centre, stretch_all=True))
        self.size = QDoubleSpinBox()
        self.size.setRange(0.001, 1000.0)
        self.size.setDecimals(3)
        self.size.setValue(4.0)
        self.size.valueChanged.connect(lambda _v: self._timer.start())
        form.addRow("Width", self.size)
        self.resolution = QSpinBox()
        self.resolution.setRange(32, 1024)
        self.resolution.setValue(256)
        self.resolution.valueChanged.connect(lambda _v: self._timer.start())
        form.addRow("Resolution", self.resolution)
        self.step = QDoubleSpinBox()
        self.step.setRange(0.0001, 100.0)
        self.step.setDecimals(4)
        self.step.setValue(0.05)
        self.step.valueChanged.connect(lambda _v: self._show())
        form.addRow("Contour step", self.step)
        self.follow = QCheckBox("Follow the camera")
        self.follow.setChecked(True)
        form.addRow(self.follow)
        layout.addLayout(form)
        self.image = QLabel()
        self.image.setMinimumSize(400, 400)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image, 1)
        bottom = QHBoxLayout()
        self.info = QLabel()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        bottom.addWidget(self.info, 1)
        bottom.addWidget(refresh)
        layout.addLayout(bottom)
        self._values: np.ndarray | None = None

    # --- sampling -------------------------------------------------------------------------------------------------------------
    def frame(self) -> tuple[tuple, tuple, tuple]:
        """`(centre, u, v)` of the plane from the document's camera."""
        state = self.document.state
        if self.use_target.isChecked() and "Target" in state:
            centre = tuple(float(c) for c in state.get("Target"))
        else:
            centre = tuple(spin.value() for spin in self.centre)
        key = self.plane.currentData()
        if key == "xy":
            return centre, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
        if key == "xz":
            return centre, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
        if key == "yz":
            return centre, (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
        if "Eye" in state and "Up" in state:
            camera = Camera3D(tuple(state.get("Eye")), centre, tuple(state.get("Up"))).orthogonalized()
            right = camera.right
            up = np.cross(right, camera.dir)
            up = up / max(float(np.linalg.norm(up)), 1e-9)
            return centre, tuple(float(c) for c in right), tuple(float(c) for c in up)
        return centre, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)

    def refresh(self) -> None:
        request = self.document.request()
        if request is None:
            self.info.setText("Build the fragment first")
            return
        if self._job is not None:
            self._again = True
            return
        centre, u, v = self.frame()
        self._job = DESliceJob(request, centre, u, v, self.size.value(), self.resolution.value(), self)
        self._job.finished_with.connect(self._sampled)
        self._job.failed.connect(lambda message: self.info.setText(f"Failed: {message}"))
        self._job.finished.connect(self._job_done)
        self._job.start()

    def _job_done(self) -> None:
        self._job = None
        if self._again:
            self._again = False
            self.refresh()

    def _sampled(self, values: np.ndarray) -> None:
        self._values = values
        finite = values[np.isfinite(values)]
        if finite.size:
            self.info.setText(f"DE from {finite.min():.4g} to {finite.max():.4g}; {np.mean(finite < 0) * 100:.1f}% inside")
        self._show()

    def _show(self) -> None:
        if self._values is None:
            return
        rgba = heat_map(self._values[::-1], self.step.value())      # row 0 at the top
        pixmap = QPixmap.fromImage(rgba_to_qimage(np.ascontiguousarray(rgba)))
        self.image.setPixmap(pixmap.scaled(self.image.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))

    def _camera_moved(self) -> None:
        if self.follow.isChecked() and self.isVisible():
            self._timer.start()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._show()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._job is not None:
            self._job.wait(10000)
        super().closeEvent(event)


__all__ = ["DESliceDialog", "heat_map"]
