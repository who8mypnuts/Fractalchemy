"""The 3D Editor window: the fractal rendered as a lit solid, with materials, lights and a camera to orbit.

Opened from *Windows ▸ 3D Editor* (`F11`) or the toolbar. A tool window of the main window like the others:
closing hides it, the layout and the last scene are remembered between runs.

The window **pulls** the main window's fractal (*Use main fractal*; with *Follow* on, it re-pulls after every
edit made in the Transform Editor or the main window, a moment after the edits pause) and can **push** a
flame back (*Send to main window*) — the 3D camera the user orbited here travels with it. The scene — the
flame, the materials (one per transform), the lights, the environment and the renderer settings — lives in
its own `.fa3d` file with *New / Open / Save / Save as* here; it is a `Scene3DDocument` with an undo history.

Layout: the toolbar, the viewport (left, the solid render, progressive, through the shared render service)
and the property tabs (right: Render, Camera, Materials, Lights, Environment, Mesh, Export). *Render…* opens
the `SolidRenderWindow` for a render to file with its own size, quality and output options. The Mesh tab's
*Generate mesh* runs a `MeshJob` (capture → voxels → isosurface → clean-up) and the viewport can show the
result; the Export tab's *Export* runs an `ExportJob` writing the files. The status bar shows the render engine
and progress.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (QFileDialog, QLabel, QMainWindow, QMessageBox, QSplitter, QStatusBar, QTabWidget, QToolBar,
                               QWidget)

from ... import config
from ...fractal.scene import Flame
from ...render.service import RenderService
from ...render.settings import RenderStats
from ...scene3d import format as fa3d
from ...scene3d.model import Scene3D
from ...widgets.icons import action_icon, editor_icon, three_d_icon
from ..fractal_document import FractalDocument
from .document import Scene3DDocument
from .jobs import ExportJob, MeshJob
from .instances_panel import InstancesPanel
from .mesh_panels import ExportPanel, MeshPanel
from .panels import CameraPanel, EnvironmentPanel, LightsPanel, MaterialsPanel, RenderPanel
from .render_window import SolidRenderWindow
from .viewport import DEFAULT_QUALITY, Viewport3D, quality_named

WINDOW_TITLE = "3D Editor"
SETTINGS_GROUP = "three_d"
SIDE_PANEL_WIDTH = 600
FOLLOW_DELAY_MS = config.EDIT_RENDER_DELAY_MS


class ThreeDWindow(QMainWindow):
    """The 3D Editor (see the module docstring).

    Signals:
        flame_sent(object): *Send to the main window*: a `Flame` for the main window to show.
        status(str): A message for the status bar.
        formulas_changed(): A mesh formula was registered from an asset (formula lists elsewhere are stale).
    """
    flame_sent = Signal(object)
    status = Signal(str)
    formulas_changed = Signal()

    def __init__(self, service: RenderService, parent: QWidget | None = None, settings: QSettings | None = None,
                 main_document: FractalDocument | None = None, prefer_gpu: bool = True):
        """Args:
            service: The shared render service (the viewport renders through it).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where the layout, the last scene and the options persist.
            main_document: The main window's document, for *Use main fractal* and *Follow* (None: disabled).
            prefer_gpu: Whether renders to file try the OpenGL engine first.
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(three_d_icon())
        self._settings = settings if settings is not None else QSettings()
        self._main = main_document
        self._prefer_gpu = prefer_gpu
        self._render_window: SolidRenderWindow | None = None
        self._stats: RenderStats | None = None
        self.document = Scene3DDocument(self)
        self.viewport = Viewport3D(self)
        self.render_panel = RenderPanel(self)
        self.camera_panel = CameraPanel(self)
        self.materials_panel = MaterialsPanel(self)
        self.lights_panel = LightsPanel(self)
        self.environment_panel = EnvironmentPanel(self)
        self.instances_panel = InstancesPanel(self)
        self.mesh_panel = MeshPanel(self)
        self.export_panel = ExportPanel(self)
        self._mesh_job: MeshJob | None = None
        self._export_job: ExportJob | None = None
        self.tabs = QTabWidget(self)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.engine_label = QLabel(self)
        self.progress_label = QLabel(self)
        self.file_label = QLabel(self)
        self._follow_timer = QTimer(self, singleShot=True, interval=FOLLOW_DELAY_MS)
        self._follow_timer.timeout.connect(self._pull_for_follow)
        self._build_actions()
        self._build_layout()
        self._connect()
        self.viewport.bind(self.document, service)
        for panel in (self.render_panel, self.camera_panel, self.materials_panel, self.lights_panel, self.environment_panel,
                      self.instances_panel, self.mesh_panel, self.export_panel):
            panel.bind(self.document)
        self._restore_state()
        self._on_undo_changed(False, False)
        self._refresh_title()

    # --- construction -------------------------------------------------------------------------------------------
    def _build_actions(self) -> None:
        def act(text: str, icon, slot: Callable, tip: str, shortcut: str | QKeySequence | None = None, checkable: bool = False) -> QAction:
            action = QAction(icon, text, self) if icon is not None else QAction(text, self)
            action.setToolTip(tip + (f"  ({QKeySequence(shortcut).toString()})" if shortcut else ""))
            action.setStatusTip(tip)
            action.setCheckable(checkable)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            if checkable:
                action.toggled.connect(slot)
            else:
                action.triggered.connect(lambda _checked=False: slot())
            return action
        self.use_main_action = act("Use main fractal", editor_icon("pull-fractal"), self.use_main_fractal,
                                   "Copy the main window's fractal into the 3D Editor", "Ctrl+U")
        self.follow_action = act("Follow", editor_icon("follow"), self.set_follow,
                                 "Keep pulling the main window's fractal as it is edited (the camera set here is kept)", checkable=True)
        self.send_action = act("Send to main window", editor_icon("push-fractal"), self.send_to_main,
                               "Show this fractal, with its 3D camera, in the main window", "Ctrl+Shift+U")
        self.new_action = act("New scene", action_icon("new"), self.new_scene, "An empty scene", QKeySequence.StandardKey.New)
        self.open_action = act("Open scene…", action_icon("open"), self.open_scene, f"Open a {fa3d.EXTENSION} scene", QKeySequence.StandardKey.Open)
        self.save_action = act("Save scene", action_icon("save"), self.save_scene, f"Save the scene as {fa3d.EXTENSION}", QKeySequence.StandardKey.Save)
        self.save_as_action = act("Save scene as…", action_icon("save-as"), self.save_scene_as, "Save the scene to a new file", QKeySequence.StandardKey.SaveAs)
        self.undo_action = act("Undo", action_icon("undo"), self.document.undo, "Undo", QKeySequence.StandardKey.Undo)
        self.redo_action = act("Redo", action_icon("redo"), self.document.redo, "Redo", QKeySequence.StandardKey.Redo)
        self.reset_view_action = act("Reset view", editor_icon("reset-view"), self.viewport.reset_view,
                                     "Back to the camera the fractal arrived with (double-click in the viewport)", "Home")
        self.render_action = act("Render…", editor_icon("render-3d"), self.show_render_window, "Render the solid to an image file", "Ctrl+R")
        self.points_action = act("Points", editor_icon("points"), self._set_points_display,
                                 "Show the point cloud in its palette colours, unlit (quicker); off: the lit solid", checkable=True)
        for action in (self.use_main_action, self.send_action):
            action.setEnabled(self._main is not None)
        self.follow_action.setEnabled(self._main is not None)

    def _build_layout(self) -> None:
        toolbar = QToolBar("3D Editor", self)
        toolbar.setObjectName("threeDToolbar")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        for action in (self.use_main_action, self.follow_action, self.send_action):
            toolbar.addAction(action)
        toolbar.addSeparator()
        for action in (self.new_action, self.open_action, self.save_action, self.save_as_action):
            toolbar.addAction(action)
        toolbar.addSeparator()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        toolbar.addSeparator()
        toolbar.addAction(self.reset_view_action)
        toolbar.addAction(self.points_action)
        toolbar.addSeparator()
        toolbar.addAction(self.render_action)
        self.addToolBar(toolbar)
        self.toolbar = toolbar
        self.tabs.addTab(self.render_panel, "Render")
        self.tabs.addTab(self.camera_panel, "Camera")
        self.tabs.addTab(self.materials_panel, "Materials")
        self.tabs.addTab(self.lights_panel, "Lights")
        self.tabs.addTab(self.environment_panel, "Environment")
        self.tabs.addTab(self.mesh_panel, "Mesh")
        self.tabs.addTab(self.instances_panel, "Instances")
        self.tabs.addTab(self.export_panel, "Export")
        self.tabs.setMinimumWidth(SIDE_PANEL_WIDTH - 20)
        self.splitter.addWidget(self.viewport)
        self.splitter.addWidget(self.tabs)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([900, SIDE_PANEL_WIDTH])
        self.setCentralWidget(self.splitter)
        bar = QStatusBar(self)
        bar.addWidget(self.progress_label, 1)
        bar.addPermanentWidget(self.file_label)
        bar.addPermanentWidget(self.engine_label)
        self.setStatusBar(bar)
        self.resize(1500, 900)

    def _connect(self) -> None:
        self.document.undo_changed.connect(self._on_undo_changed)
        self.document.modified_changed.connect(lambda _m: self._refresh_title())
        self.document.path_changed.connect(lambda _p: self._refresh_title())
        self.document.scene_replaced.connect(self._on_scene_replaced)
        self.document.scene_restored.connect(self._on_scene_replaced)
        self.document.fractal_changed.connect(self._refresh_title)
        self.document.solid_changed.connect(self._sync_points_action)
        self.viewport.render_progress.connect(self._on_render_progress)
        self.viewport.render_failed.connect(lambda message: self.progress_label.setText(f"Cannot render: {message}"))
        self.render_panel.quality_changed.connect(self._on_quality_chosen)
        self.camera_panel.reset_requested.connect(self.viewport.reset_view)
        self.mesh_panel.generate_requested.connect(self.generate_mesh)
        self.mesh_panel.cancel_requested.connect(self.cancel_mesh)
        self.mesh_panel.display_requested.connect(self._on_display_requested)
        self.export_panel.export_requested.connect(self.export_mesh)
        self.instances_panel.flame_sent.connect(self.flame_sent)
        self.instances_panel.status.connect(self.status)
        self.instances_panel.formulas_changed.connect(self.formulas_changed)
        self.environment_panel.status.connect(self.status)
        self.document.mesh_changed.connect(self._on_mesh_changed)
        self.document.solid_changed.connect(self._sync_display_choice)
        if self._main is not None:
            for signal in (self._main.flame_replaced, self._main.flame_restored, self._main.xform_changed, self._main.transforms_changed,
                           self._main.palette_changed, self._main.camera_changed, self._main.coloring_changed):
                signal.connect(self._on_main_changed)

    # --- persistence --------------------------------------------------------------------------------------------
    def _restore_state(self) -> None:
        s = self._settings
        geometry = s.value(f"{SETTINGS_GROUP}/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        split = s.value(f"{SETTINGS_GROUP}/split")
        if split is not None:
            self.splitter.restoreState(split)
        quality = s.value(f"{SETTINGS_GROUP}/quality", DEFAULT_QUALITY.name)
        self.viewport.set_quality(quality_named(str(quality)))
        self.render_panel.set_quality_name(self.viewport.quality.name)
        self.tabs.setCurrentIndex(int(s.value(f"{SETTINGS_GROUP}/tab", 0)))
        text = s.value(f"{SETTINGS_GROUP}/scene", "")
        if text:
            try:
                scene = fa3d.scene_from_text(str(text))
            except (fa3d.Scene3DFormatError, ValueError, TypeError):
                scene = None
            if scene is not None:
                path = s.value(f"{SETTINGS_GROUP}/path", "")
                self.document.replace(scene, Path(str(path)) if path else None, modified=bool(s.value(f"{SETTINGS_GROUP}/modified", False, bool)))
                self.follow_action.setChecked(scene.follow_main)

    def save_state(self) -> None:
        """Persist the layout, the options and the scene being edited."""
        s = self._settings
        s.setValue(f"{SETTINGS_GROUP}/geometry", self.saveGeometry())
        s.setValue(f"{SETTINGS_GROUP}/split", self.splitter.saveState())
        s.setValue(f"{SETTINGS_GROUP}/quality", self.viewport.quality.name)
        s.setValue(f"{SETTINGS_GROUP}/tab", self.tabs.currentIndex())
        s.setValue(f"{SETTINGS_GROUP}/scene", fa3d.scene_to_text(self.document.scene) if self.document.flame is not None else "")
        s.setValue(f"{SETTINGS_GROUP}/path", str(self.document.path) if self.document.path else "")
        s.setValue(f"{SETTINGS_GROUP}/modified", self.document.modified)

    # --- window ---------------------------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show the window (restoring it if minimised) and raise it."""
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event) -> None:
        self.save_state()
        super().hideEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.save_state()
        if self._render_window is not None:
            self._render_window.hide()
        super().closeEvent(event)

    def _refresh_title(self) -> None:
        flame = self.document.flame
        name = self.document.path.name if self.document.path else (flame.name if flame is not None else "")
        mark = " •" if self.document.modified else ""
        self.setWindowTitle(f"{WINDOW_TITLE} — {name}{mark}" if name else WINDOW_TITLE)
        self.file_label.setText(str(self.document.path) if self.document.path else "")
        self.send_action.setEnabled(self._main is not None and flame is not None)
        self.render_action.setEnabled(flame is not None)
        self.save_action.setEnabled(flame is not None)
        self.save_as_action.setEnabled(flame is not None)
        self.reset_view_action.setEnabled(flame is not None)

    def _on_undo_changed(self, can_undo: bool, can_redo: bool) -> None:
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        self.undo_action.setText(f"Undo {self.document.undo_label}" if can_undo else "Undo")
        self.redo_action.setText(f"Redo {self.document.redo_label}" if can_redo else "Redo")

    def _on_scene_replaced(self) -> None:
        self._refresh_title()
        self._sync_points_action()
        if self.follow_action.isChecked() != self.document.scene.follow_main:
            self.follow_action.setChecked(self.document.scene.follow_main)

    def _sync_points_action(self) -> None:
        points = self.document.scene.solid.display == "points"
        if self.points_action.isChecked() != points:
            self.points_action.blockSignals(True)
            self.points_action.setChecked(points)
            self.points_action.blockSignals(False)

    def _set_points_display(self, on: bool) -> None:
        self.document.update_solid(None, display="points" if on else "solid")

    def _on_display_requested(self, display: str, form: str) -> None:
        """The Mesh tab's *Show* buttons: the solid render, the clean mesh or the full mesh."""
        self.viewport.set_mesh_form(form)
        self.document.update_solid(None, display=display)

    def _sync_display_choice(self) -> None:
        self.mesh_panel.sync_display(self.document.scene.solid.display, self.viewport.mesh_form)

    def _on_mesh_changed(self) -> None:
        if self.document.mesh_result is None and self.document.scene.solid.display == "mesh":
            self.document.update_solid(None, display="solid")     # the mesh went: back to the fractal
        self._sync_display_choice()

    # --- meshing and export -----------------------------------------------------------------------------------------
    @property
    def meshing(self) -> bool:
        """True while a mesh is being generated."""
        return self._mesh_job is not None

    def generate_mesh(self) -> None:
        """Run the meshing pipeline on a worker thread (the capture is reused when its settings did not change)."""
        flame = self.document.flame
        if flame is None or self._mesh_job is not None:
            return
        job = MeshJob(flame, self.document.scene.mesh, self.document.voxel_stage, self)
        job.progressed.connect(self._on_mesh_progress)
        job.finished_with.connect(self._on_mesh_finished)
        job.failed.connect(self._on_mesh_failed)
        job.cancelled_signal.connect(lambda: self.status.emit("Mesh generation cancelled"))
        job.finished.connect(self._on_mesh_job_done)
        self._mesh_job = job
        self.mesh_panel.set_running(True)
        self.mesh_panel.show_progress(0.0, "Starting")
        job.start()

    def cancel_mesh(self) -> None:
        if self._mesh_job is not None:
            self._mesh_job.cancel()

    def _on_mesh_progress(self, fraction: float, message: str) -> None:
        self.mesh_panel.show_progress(fraction, message)
        self.progress_label.setText(f"Mesh: {message}")

    def _on_mesh_finished(self, result, stage) -> None:
        self.document.set_mesh_result(result, stage)
        rep = result.clean_report
        self.status.emit(f"Mesh ready: {result.full_report.faces:,} faces, clean {rep.faces:,} — {rep.recommendation()}")
        self.mesh_panel.show_progress(1.0, "Mesh ready")

    def _on_mesh_failed(self, message: str) -> None:
        self.mesh_panel.show_progress(0.0, f"Failed: {message}")
        self.status.emit(f"Mesh generation failed: {message}")

    def _on_mesh_job_done(self) -> None:
        job = self._mesh_job
        self._mesh_job = None
        if job is not None:
            job.deleteLater()
        self.mesh_panel.set_running(False)

    @property
    def exporting(self) -> bool:
        return self._export_job is not None

    def export_folder(self) -> Path:
        """Where the export goes: the Export tab's folder, else the last one used, else Documents."""
        e = self.document.scene.export
        if e.folder.strip():
            return Path(e.folder.strip())
        stored = self._settings.value(f"{SETTINGS_GROUP}/export_folder", "")
        return Path(str(stored)) if stored else Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation) or Path.home())

    def export_name(self) -> str:
        e = self.document.scene.export
        name = e.name.strip() or (self.document.flame.name if self.document.flame is not None else "scene")
        return re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "fractal"

    def export_mesh(self) -> None:
        """Write the generated mesh — or the instancers — in the chosen formats on a worker thread."""
        result = self.document.mesh_result
        if self._export_job is not None or not self.export_panel.can_export():
            return
        folder, name = self.export_folder(), self.export_name()
        job = ExportJob(result, self.document.scene, self.document.scene.export, folder, name, self)
        job.progressed.connect(self.export_panel.show_progress)
        job.finished_with.connect(self._on_export_finished)
        job.failed.connect(self._on_export_failed)
        job.finished.connect(self._on_export_job_done)
        self._export_job = job
        self.export_panel.set_running(True)
        self.export_panel.show_progress(0.0, "Starting")
        self._settings.setValue(f"{SETTINGS_GROUP}/export_folder", str(folder))
        job.start()

    def _on_export_finished(self, outcome) -> None:
        self.export_panel.show_outcome(outcome)
        self.export_panel.show_progress(1.0, "Export finished")
        self.status.emit(f"Exported {len(outcome.files)} files to {outcome.files[0].parent if outcome.files else ''}")

    def _on_export_failed(self, message: str) -> None:
        self.export_panel.show_failure(message)
        self.export_panel.show_progress(0.0, "Failed")
        self.status.emit(f"Export failed: {message}")

    def _on_export_job_done(self) -> None:
        job = self._export_job
        self._export_job = None
        if job is not None:
            job.deleteLater()
        self.export_panel.set_running(False)

    def wait_for_jobs(self, timeout_ms: int = 60000) -> None:
        """Block until the mesh / export jobs have exited (tests and quitting)."""
        for job in (self._mesh_job, self._export_job):
            if job is not None:
                job.wait(timeout_ms)

    def _on_quality_chosen(self, name: str) -> None:
        self.viewport.set_quality(quality_named(name))

    def _on_render_progress(self, stats: RenderStats) -> None:
        self._stats = stats
        self.engine_label.setText(stats.engine)
        done = f"pass {stats.passes_done} of {stats.passes_total}" if stats.passes_total else f"{stats.passes_done} passes"
        notes = f"  ·  {'; '.join(stats.notes)}" if stats.notes else ""
        self.progress_label.setText(f"{stats.width} × {stats.height}  ·  {done}  ·  {stats.samples / 1e6:.1f} M samples  ·  {stats.seconds:.1f} s{notes}")

    # --- the main window's fractal ------------------------------------------------------------------------------------
    def use_main_fractal(self) -> None:
        """Copy the main window's fractal into the scene (its own 3D camera included)."""
        flame = self._main.flame if self._main is not None else None
        if flame is None:
            self.status.emit("The main window has no fractal to use")
            return
        self.document.set_fractal(flame, "Use main fractal")
        self.status.emit(f"Using '{flame.name}' from the main window")

    def set_follow(self, follow: bool) -> None:
        """Keep the scene's fractal in step with the main window's."""
        self.document.set_follow(follow)
        if follow:
            self._pull_for_follow()

    def _on_main_changed(self, *_args) -> None:
        if self.follow_action.isChecked() and self._main is not None:
            self._follow_timer.start()

    def _pull_for_follow(self) -> None:
        flame = self._main.flame if self._main is not None else None
        if flame is None or not self.follow_action.isChecked():
            return
        self.document.set_fractal(flame, "Follow main window", keep_camera=self.document.flame is not None)

    def send_to_main(self) -> None:
        flame = self.document.flame
        if flame is not None:
            self.flame_sent.emit(flame.copy())
            self.status.emit(f"Sent '{flame.name}' to the main window")

    # --- files ---------------------------------------------------------------------------------------------------
    def confirm_discard(self) -> bool:
        """Ask before throwing away unsaved changes; True = go ahead."""
        if not self.document.modified or self.document.flame is None:
            return True
        answer = QMessageBox.question(self, WINDOW_TITLE, "The scene has unsaved changes. Discard them?",
                                      QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        return answer == QMessageBox.StandardButton.Discard

    def new_scene(self, ask: bool = True) -> None:
        if ask and not self.confirm_discard():
            return
        self.document.replace(Scene3D())
        self.follow_action.setChecked(False)

    def open_scene(self, path: Path | str | None = None, ask: bool = True) -> bool:
        """Open a `.fa3d` scene (a file dialog when no path is given). Returns True when a scene was opened.

        Args:
            path: The file; None asks for one.
            ask: Confirm discarding unsaved changes and report failures in a dialog (False: scripts and tests —
                failures go to the `status` signal only).
        """
        if ask and not self.confirm_discard():
            return False
        if path is None:
            start = str(self.document.path.parent) if self.document.path else self._settings.value(f"{SETTINGS_GROUP}/folder", "")
            chosen, _filter = QFileDialog.getOpenFileName(self, "Open 3D scene", start, fa3d.FILE_FILTER)
            if not chosen:
                return False
            path = chosen
        path = Path(path)
        try:
            scene = fa3d.load_scene(path)
        except (OSError, fa3d.Scene3DFormatError) as exc:
            self.status.emit(f"Could not open {path.name}: {exc}")
            if ask:
                QMessageBox.warning(self, WINDOW_TITLE, f"Could not open {path.name}:\n{exc}")
            return False
        self.document.replace(scene, path)
        self._settings.setValue(f"{SETTINGS_GROUP}/folder", str(path.parent))
        self.status.emit(f"Opened {path.name}")
        return True

    def save_scene(self) -> bool:
        """Save to the scene's file (asks for one the first time). Returns True when written."""
        if self.document.path is None:
            return self.save_scene_as()
        return self._write(self.document.path)

    def save_scene_as(self, path: Path | str | None = None) -> bool:
        if path is None:
            flame = self.document.flame
            start = self.document.path or Path(self._settings.value(f"{SETTINGS_GROUP}/folder", str(Path.home()))) / f"{flame.name if flame else 'scene'}{fa3d.EXTENSION}"
            chosen, _filter = QFileDialog.getSaveFileName(self, "Save 3D scene", str(start), fa3d.FILE_FILTER)
            if not chosen:
                return False
            path = chosen
        path = Path(path)
        if path.suffix.lower() != fa3d.EXTENSION:
            path = path.with_suffix(fa3d.EXTENSION)
        return self._write(path)

    def _write(self, path: Path) -> bool:
        try:
            fa3d.save_scene(self.document.scene, path)
        except OSError as exc:
            QMessageBox.warning(self, WINDOW_TITLE, f"Could not save {path.name}:\n{exc}")
            return False
        self.document.mark_saved(path)
        self._settings.setValue(f"{SETTINGS_GROUP}/folder", str(path.parent))
        self.status.emit(f"Saved {path.name}")
        return True

    # --- rendering to file ---------------------------------------------------------------------------------------
    @property
    def render_window(self) -> SolidRenderWindow:
        """The render-to-file window (created on first use)."""
        if self._render_window is None:
            self._render_window = SolidRenderWindow(self.document, self, self._settings, self._prefer_gpu,
                                                    preview_size=lambda: (self.viewport.width(), self.viewport.height()))
        return self._render_window

    def show_render_window(self) -> None:
        self.render_window._on_scene_changed()       # the viewport may have been resized since
        self.render_window.bring_to_front()

    def confirm_quit(self) -> bool:
        """Ask about a running render to file before quitting; False = keep going. Mesh / export jobs are stopped."""
        if self._render_window is not None and not self._render_window.confirm_quit():
            return False
        if self._mesh_job is not None:
            self._mesh_job.cancel()
        self.wait_for_jobs()
        return True

    # --- convenience ---------------------------------------------------------------------------------------------------
    def load_flame(self, flame: Flame, label: str = "Use fractal") -> None:
        """Put `flame` in the scene (scripts and tests; *Use main fractal* does the same with the main window's)."""
        self.document.set_fractal(flame, label)


__all__ = ["ThreeDWindow", "WINDOW_TITLE"]
