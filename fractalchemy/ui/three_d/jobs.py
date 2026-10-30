"""The 3D Editor's background jobs: meshing, exporting and the mesh preview image, each a QThread.

Every job takes copies of what it needs, reports through signals and can be cancelled; the worker code is the
Qt-free `solid.pipeline` / `solid.mesh_preview`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from ...fractal.scene import Camera, Flame
from ...scene3d.model import ExportSettings, MeshSettings, Scene3D
from ...solid.mesh import Mesh
from ...solid.mesh_preview import render_mesh
from ...solid.pipeline import MeshResult, VoxelStage, build_mesh, capture_stage, export_instances, export_result


class MeshJob(QThread):
    """Capture (unless a matching stage is cached), voxelise, extract and clean.

    Signals:
        progressed(float, str): Fraction done and what is happening.
        finished_with(object, object): (`MeshResult`, `VoxelStage`) on success.
        failed(str): The error.
        cancelled_signal(): The job stopped at the user's request.
    """
    progressed = Signal(float, str)
    finished_with = Signal(object, object)
    failed = Signal(str)
    cancelled_signal = Signal()

    def __init__(self, flame: Flame, settings: MeshSettings, stage: VoxelStage | None = None, parent: QObject | None = None,
                 threads: int = 1):
        super().__init__(parent)
        self.flame = flame.copy()
        self.settings = settings.copy()
        self.stage = stage if stage is not None and stage.matches(self.settings) else None
        self.threads = threads
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def _cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:  # noqa: D401 - QThread entry point
        try:
            stage = self.stage
            if stage is None:
                stage = capture_stage(self.flame, self.settings, self._cancelled,
                                      lambda f, m: self.progressed.emit(f * 0.5, m), self.threads)
                if stage is None:
                    self.cancelled_signal.emit()
                    return
            base = 0.5 if self.stage is None else 0.0
            result = build_mesh(stage, self.settings, self._cancelled, lambda f, m: self.progressed.emit(base + f * (1.0 - base), m))
            if result is None:
                self.cancelled_signal.emit()
                return
        except Exception as exc:  # noqa: BLE001 - reported, never raised on a thread
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        self.finished_with.emit(result, stage)


class ExportJob(QThread):
    """Write the mesh files.

    Signals:
        progressed(float, str)
        finished_with(object): `ExportOutcome`.
        failed(str)
    """
    progressed = Signal(float, str)
    finished_with = Signal(object)
    failed = Signal(str)

    def __init__(self, result: MeshResult | None, scene: Scene3D, settings: ExportSettings, folder: Path, name: str,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.result = result
        self.scene = scene.copy()
        self.settings = settings.copy()
        self.folder = Path(folder)
        self.name = name

    def run(self) -> None:  # noqa: D401 - QThread entry point
        try:
            if self.settings.subject != "mesh":
                outcome = export_instances(self.scene, self.settings, self.folder, self.name, lambda f, m: self.progressed.emit(f, m))
            elif self.result is None:
                raise ValueError("generate a mesh on the Mesh tab first")
            else:
                outcome = export_result(self.result, self.scene, self.settings, self.folder, self.name,
                                        lambda f, m: self.progressed.emit(f, m))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        self.finished_with.emit(outcome)


class MeshPreviewJob(QThread):
    """Render a mesh as the viewport shows it (points on its faces through the solid shader).

    Signals:
        finished_with(object, object): (RGBA8 image, the request key).
        failed(str)
    """
    finished_with = Signal(object, object)
    failed = Signal(str)

    def __init__(self, mesh: Mesh, camera: Camera, scene: Scene3D, width: int, height: int, oversample: int, samples: int,
                 key: object, parent: QObject | None = None):
        super().__init__(parent)
        self.mesh = mesh
        self.camera = camera.copy()
        self.scene = scene.copy()
        self.width, self.height, self.oversample, self.samples = width, height, oversample, samples
        self.key = key

    def run(self) -> None:  # noqa: D401 - QThread entry point
        try:
            image = render_mesh(self.mesh, self.camera, self.scene, self.width, self.height, self.oversample, self.samples)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        self.finished_with.emit(np.ascontiguousarray(image), self.key)


__all__ = ["MeshJob", "ExportJob", "MeshPreviewJob"]
