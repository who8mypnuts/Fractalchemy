"""The background jobs of *Export mesh…*: DE → mesh on its own OpenGL context, the export, the preview image.

`MeshFromDEJob` creates a `FragEngine` on its thread (a GL context is thread-bound), probes the distance estimator
(`gl/mesh.py`) and meshes the result (`fragments/mesh.py`); `DEExportJob` writes the files; `DEPreviewJob` renders a
still of the mesh through the host's solid renderer so the dialog can show what it made. Every job takes copies,
reports through signals and can be cancelled.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from ...fractal.scene import Camera
from ...fragments.gl.engine import FragEngine
from ...fragments.gl.job import FragRequest
from ...fragments.gl.mesh import DistanceProbe
from ...fragments.mesh import DEExportSettings, DEMeshResult, DEMeshSettings, build_de_mesh, export_de_mesh
from ...scene3d.model import Scene3D
from ...solid.mesh import Mesh
from ...solid.mesh_preview import render_mesh


class MeshFromDEJob(QThread):
    """Probe the DE and mesh it.

    Signals:
        progressed(float, str): Fraction done and what is happening.
        finished_with(object): The `DEMeshResult`.
        failed(str): The error.
        cancelled_signal(): Stopped at the user's request.
    """
    progressed = Signal(float, str)
    finished_with = Signal(object)
    failed = Signal(str)
    cancelled_signal = Signal()

    def __init__(self, request: FragRequest, settings: DEMeshSettings, parent: QObject | None = None):
        super().__init__(parent)
        self.request = request.copy()
        self.settings = settings.copy()
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def _cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:  # noqa: D401 - QThread entry point
        engine = None
        probe = None
        try:
            engine = FragEngine()
            probe = DistanceProbe(engine, self.request)
            result = self._mesh(probe)
        except Exception as exc:  # noqa: BLE001 - reported to the dialog
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        finally:
            if probe is not None:
                probe.close()
            if engine is not None:
                engine.close()
        if result is None:
            self.cancelled_signal.emit()
        else:
            self.finished_with.emit(result)

    def _mesh(self, probe: DistanceProbe) -> DEMeshResult | None:
        s = self.settings
        bounds = s.bounds
        if s.fit:
            self.progressed.emit(0.0, "Finding the fractal (coarse pass)")
            bounds = probe.fit_bounds(bounds, s.threshold_voxels * bounds.spacing(48) + bounds.spacing(48))
        if self._cancelled():
            return None
        sampled = probe.sample(bounds, s.resolution, s.colors, lambda f, m: self.progressed.emit(0.05 + 0.45 * f, m), self._cancelled)
        if sampled is None:
            return None
        return build_de_mesh(sampled, s, lambda f, m: self.progressed.emit(0.5 + 0.5 * f, m), self._cancelled)


class DEExportJob(QThread):
    """Write the mesh files.

    Signals:
        progressed(float, str)
        finished_with(object): The `DEExportOutcome`.
        failed(str)
    """
    progressed = Signal(float, str)
    finished_with = Signal(object)
    failed = Signal(str)

    def __init__(self, result: DEMeshResult, settings: DEExportSettings, folder: Path, name: str, fragment_name: str,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.result = result
        self.settings = settings.copy()
        self.folder, self.name, self.fragment_name = Path(folder), name, fragment_name

    def run(self) -> None:  # noqa: D401 - QThread entry point
        try:
            outcome = export_de_mesh(self.result, self.settings, self.folder, self.name, self.fragment_name,
                                     lambda f, m: self.progressed.emit(f, m))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        self.finished_with.emit(outcome)


class DEPreviewJob(QThread):
    """A still of the mesh (the host's solid renderer over points sampled on its faces).

    Signals:
        finished_with(object): RGBA8 `(height, width, 4)`.
        failed(str)
    """
    finished_with = Signal(object)
    failed = Signal(str)

    def __init__(self, mesh: Mesh, width: int, height: int, parent: QObject | None = None):
        super().__init__(parent)
        self.mesh = mesh
        self.width, self.height = width, height

    def run(self) -> None:  # noqa: D401 - QThread entry point
        try:
            image = render_mesh(self.mesh, preview_camera(self.mesh, self.width, self.height), Scene3D(), self.width, self.height, 2,
                                min(800_000, 40 * max(1, self.mesh.face_count)))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        self.finished_with.emit(np.ascontiguousarray(image))


def preview_camera(mesh: Mesh, width: int, height: int) -> Camera:
    """A three-quarter view framing the mesh."""
    lo, hi = mesh.bounds()
    centre = (lo + hi) / 2.0
    extent = max(float((hi - lo).max()), 1e-6)
    return Camera(center=(float(centre[0]), float(centre[1])), scale=width * 0.7 / extent, width=width, height=height,
                  pitch=-0.9, yaw=0.6, zpos=float(centre[2]))


__all__ = ["MeshFromDEJob", "DEExportJob", "DEPreviewJob", "preview_camera"]
