"""Top-level application window: Fractal Library on the left, the fractal viewport in the centre.

Menus (File / Edit / View / Windows / Help), a toolbar, and a status bar showing the
loaded fractal, render facts, the progressive pass counter and a progress bar. The
Gradient Library is a separate tool window opened from *Windows* or the toolbar.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from .. import config
from ..fractal.scene import Flame
from ..library.catalog import FRACTAL_CATALOG
from ..library.context_menu import LibraryContextMenu
from ..library.controller import LibraryController
from ..library.dialog import EditLibraryDialog
from ..library.items import LibraryItem
from ..library.roots import LibraryRoots
from ..render.service import RenderService
from ..widgets.collapsible_splitter import CollapsibleSplitter
from ..widgets.icons import action_icon, gradient_icon
from .fractal_document import FractalDocument
from .fractal_file_actions import FractalFileActions
from .fractal_library_panel import LIST_ICON_SIZE, FractalLibraryPanel
from .fractal_viewport import FractalViewport
from .gradient_library_window import GradientLibraryWindow
from .gradient_link import GradientLink
from .loader import load_ui
from .render_status import RenderStatus
from .settings_panel import SettingsPanel
from .thumbnails import ThumbnailProvider
from .viewer_bar import ViewerBar

UI_FILE = Path(__file__).resolve().parents[2] / "ui" / "main_window.ui"
CUSTOM_WIDGETS = {
    "FractalLibraryPanel": FractalLibraryPanel,
    "FractalViewport": FractalViewport,
    "ViewerBar": ViewerBar,
    "SettingsPanel": SettingsPanel,
    "CollapsibleSplitter": CollapsibleSplitter,
}
SCANNING_MESSAGE = "Scanning fractal library…"
LIBRARY_PANE_WIDTH = 300
SETTINGS_PANE_WIDTH = 230
MESSAGE_MS = 6000
ABOUT_TEXT = (
    f"<h3>{config.APP_NAME} {config.APP_VERSION}</h3>"
    "<p>A fractal flame viewer, gradient editor and library, growing into a full fractal editor.</p>"
    "<p>Reads Apophysis / flam3 (<code>.flame</code>), Chaotica (<code>.chaos</code>) and Fractalchemy "
    "(<code>.fa</code>) fractals; renders previews on the GPU (OpenGL) with a multithreaded CPU fallback.</p>"
)


class MainWindow(QMainWindow):
    """Application shell: fractal library + viewport, menus, toolbar, status bar, and the Gradient Library window."""
    def __init__(self, roots: LibraryRoots | None = None, fractal_roots: LibraryRoots | None = None,
                 prefer_gpu: bool = True, settings: QSettings | None = None):
        """Args:
            roots: Gradient library folders; defaults to the persisted list.
            fractal_roots: Fractal library folders; defaults to the persisted list.
            prefer_gpu: Try the OpenGL preview engine first (tests may force the CPU engine).
            settings: Store for preferences such as preview quality; defaults to the application's.
        """
        super().__init__()
        load_ui(self, UI_FILE, CUSTOM_WIDGETS)
        self.setWindowIcon(gradient_icon())
        self.render_service = RenderService(self, prefer_gpu=prefer_gpu)
        self.document = FractalDocument(self)
        self.files = FractalFileActions(self.document, self)
        self.status = RenderStatus(self.statusBar())
        self.viewport.bind(self.document, self.render_service)
        self.fractal_library = LibraryController(
            self.fractalLibraryPanel.model, fractal_roots or LibraryRoots(parent=self, key=FRACTAL_CATALOG.roots_key), self)
        self.fractal_menu = LibraryContextMenu(self.fractal_library, self.open_item, self)
        self.thumbnails = ThumbnailProvider(self.render_service, self.fractalLibraryPanel.model, self)
        self.gradient_library = GradientLibraryWindow(roots, self)
        self.gradient_link = GradientLink(self.document, self.gradient_library, self.viewport, self)
        self.splitter.first_label, self.splitter.last_label = "fractal library", "settings panel"
        self.splitter.set_first_width(LIBRARY_PANE_WIDTH)
        self.splitter.set_last_width(SETTINGS_PANE_WIDTH)
        for pane, stretch in ((0, 0), (1, 1), (2, 0)):   # window resizes go to the viewport, not the side panes
            self.splitter.setStretchFactor(pane, stretch)
        self.settingsPanel.attach_settings(settings if settings is not None else QSettings())
        self._connect_actions()
        self._connect_document()
        self._connect_library()
        self._connect_render()
        self._connect_viewer_controls()
        self.render_service.start()
        self.fractal_library.rescan_all()

    # --- wiring -------------------------------------------------------------
    def _connect_actions(self) -> None:
        self.actionOpenFractal.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton))
        self.actionOpenFractal.triggered.connect(self.files.open)
        for action, name in ((self.actionSave, "save"), (self.actionSaveAs, "save-as"), (self.actionUndo, "undo"),
                             (self.actionRedo, "redo"), (self.actionCopy, "copy"), (self.actionPaste, "paste")):
            action.setIcon(action_icon(name))
        self.actionSave.triggered.connect(self.files.save)
        self.actionSaveAs.triggered.connect(self.files.save_as)
        self.actionCopy.triggered.connect(lambda: self.files.copy("fa"))
        self.actionCopyApophysis.triggered.connect(lambda: self.files.copy("flame"))
        self.actionCopyChaotica.triggered.connect(lambda: self.files.copy("chaos"))
        self.actionPaste.triggered.connect(self.files.paste)
        stack = self.document.undo_stack
        self.actionUndo.triggered.connect(stack.undo)
        self.actionRedo.triggered.connect(stack.redo)
        stack.canUndoChanged.connect(self.actionUndo.setEnabled)
        stack.canRedoChanged.connect(self.actionRedo.setEnabled)
        stack.undoTextChanged.connect(self._set_undo_text)   # bound methods auto-disconnect on destruction; lambdas don't
        stack.redoTextChanged.connect(self._set_redo_text)
        self.files.status.connect(self._message)
        self.files.file_opened.connect(self.fractal_library.set_opened_file)
        self.files.file_written.connect(self.fractal_library.rescan_containing)
        self.actionGradientLibrary.setIcon(gradient_icon())
        self.actionGradientLibrary.triggered.connect(self.show_gradient_library)
        self.actionEditFractalLibrary.triggered.connect(self.edit_fractal_library)
        self.actionToggleFractalLibrary.toggled.connect(lambda shown: self.splitter.set_collapsed(not shown))
        self.actionRefreshFractalLibrary.triggered.connect(self.fractal_library.rescan_all)
        self.actionThumbnailView.toggled.connect(self.fractalLibraryPanel.set_thumbnail_view)
        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.about)
        self.actionAboutQt.triggered.connect(lambda: QMessageBox.aboutQt(self, f"About Qt — {config.APP_NAME}"))
        self.menuView.insertAction(self.actionShowStatusBar, self.toolBar.toggleViewAction())
        self.actionShowStatusBar.toggled.connect(self.statusBar().setVisible)
        self.splitter.collapsed_changed.connect(lambda collapsed: self.actionToggleFractalLibrary.setChecked(not collapsed))
        self.actionToggleSettings.toggled.connect(lambda shown: self.splitter.set_last_collapsed(not shown))
        self.splitter.last_collapsed_changed.connect(lambda collapsed: self.actionToggleSettings.setChecked(not collapsed))
        self.actionZoomFit.triggered.connect(self.viewport.zoom_to_fit)
        self.actionZoomActual.triggered.connect(lambda: self.viewport.set_zoom(1.0))

    def _connect_document(self) -> None:
        self.document.flame_replaced.connect(self._on_flame_replaced)
        self.document.camera_changed.connect(self._on_camera_changed)
        self.document.palette_changed.connect(self._on_palette_changed)
        self.document.modified_changed.connect(self._on_modified_changed)

    def _connect_library(self) -> None:
        panel = self.fractalLibraryPanel
        panel.add_requested.connect(self.add_fractal_folder)
        panel.edit_requested.connect(self.edit_fractal_library)
        panel.item_chosen.connect(self.open_item)
        panel.menu_requested.connect(lambda item, pos: self.fractal_menu.show(item, panel.tree.selected_items(), pos))
        panel.view_mode_changed.connect(self._set_thumbnail_view)
        self.fractal_library.status.connect(self._message)
        self.fractal_library.failed.connect(self._report_library_error)
        self.fractal_library.scanning.connect(self._show_scanning)
        self.fractal_library.file_changed_externally.connect(self._on_external_change)

    def _connect_render(self) -> None:
        self.render_service.engine_ready.connect(self.status.set_engine)
        self.viewport.render_progress.connect(self.status.show_progress)
        self.viewport.render_failed.connect(lambda message: self._message(f"Cannot render: {message}"))

    def _connect_viewer_controls(self) -> None:
        bar, panel, view = self.viewerBar, self.settingsPanel, self.viewport
        bar.zoom_requested.connect(view.set_zoom)
        bar.resolution_chosen.connect(self.document.set_image_size)
        view.view_changed.connect(bar.show_zoom)
        panel.render_settings_changed.connect(self._apply_render_settings)
        self._apply_render_settings(panel.passes, panel.quality, render=False)

    def _apply_render_settings(self, passes: int, quality: float, render: bool = True) -> None:
        settings = self.viewport.settings.with_effort(passes, quality)
        if render:
            self.viewport.set_render_settings(settings)
        else:
            self.viewport.settings = settings

    # --- fractal loading ----------------------------------------------------
    def open_file(self) -> None:
        """Prompt for a fractal file and show its first flame (its flames appear at the top of the library)."""
        self.files.open()

    def open_item(self, item: LibraryItem) -> None:
        """Show the flame a library row refers to (asks about unsaved edits first)."""
        if self.document.is_showing(item.path, item.index) and not self.document.modified:
            return
        if self.files.confirm_discard():
            self.files.open_path(item.path, item.index)

    def open_path(self, path: Path, index: int = 0) -> None:
        """Load flame `index` of `path` on a worker thread, then show it."""
        self.files.open_path(path, index)

    def show_flame(self, flame: Flame) -> None:
        """Show a flame that did not come from a file."""
        self.document.replace(flame)

    # --- library slots ------------------------------------------------------
    def add_fractal_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add folder to the fractal library")
        if folder and not self.fractal_library.roots.add(Path(folder)):
            self._message("That folder is already in the fractal library")

    def edit_fractal_library(self) -> None:
        EditLibraryDialog(self.fractal_library, self.add_fractal_folder, self).exec()

    def _set_thumbnail_view(self, thumbnails: bool) -> None:
        self.thumbnails.set_enabled(thumbnails)
        self.fractalLibraryPanel.apply_icon_size(self.thumbnails.size if thumbnails else LIST_ICON_SIZE)
        if self.actionThumbnailView.isChecked() != thumbnails:
            self.actionThumbnailView.setChecked(thumbnails)

    def _show_scanning(self, busy: bool) -> None:
        if busy:
            self.statusBar().showMessage(SCANNING_MESSAGE)
        elif self.statusBar().currentMessage() == SCANNING_MESSAGE:
            self.statusBar().clearMessage()

    def _on_external_change(self, path: Path) -> None:
        """Reload the shown flame if another program changed its file (not our own saves), unless it has unsaved edits."""
        if path != self.document.source_path or self.document.modified:
            return
        if self.files.wrote_recently(path) or self.gradient_library.files.wrote_recently(path):
            return
        self.open_path(path, self.document.source_index)

    # --- other slots --------------------------------------------------------
    def show_gradient_library(self) -> None:
        """Open the Gradient Library window, or bring it to the front if it is already open."""
        self.gradient_library.bring_to_front()

    def about(self) -> None:
        QMessageBox.about(self, f"About {config.APP_NAME}", ABOUT_TEXT)

    def _on_flame_replaced(self) -> None:
        flame = self.document.flame
        source = self.document.source_path.name if self.document.source_path else ""
        self.status.show_fractal(flame, source)
        self.status.show_idle()
        self.viewerBar.show_flame(flame)
        self._refresh_title()

    def _set_undo_text(self, text: str) -> None:
        self.actionUndo.setText(f"Undo {text}" if text else "Undo")

    def _set_redo_text(self, text: str) -> None:
        self.actionRedo.setText(f"Redo {text}" if text else "Redo")

    def _on_modified_changed(self, _modified: bool) -> None:
        self._refresh_title()

    def _refresh_title(self) -> None:
        flame = self.document.flame
        self.setWindowTitle(f"{config.APP_NAME} — {flame.name}[*]" if flame else f"{config.APP_NAME}[*]")
        self.setWindowModified(self.document.modified)

    def _on_camera_changed(self) -> None:
        flame = self.document.flame
        if flame is not None:
            cx, cy = flame.camera.center
            self._message(f"center {cx:.4f}, {cy:.4f}   zoom {flame.camera.zoom:.2f}", 2000)

    def _on_palette_changed(self) -> None:
        self._message("Gradient applied to the fractal", 2000)

    def _message(self, text: str, ms: int = MESSAGE_MS) -> None:
        self.statusBar().showMessage(text, ms)

    def _report_library_error(self, message: str) -> None:
        self._message(message)
        QMessageBox.warning(self, "Fractal Library", message)

    # --- Qt overrides -------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        """Quitting closes the tool windows too, so check for unsaved fractal and gradient edits first."""
        if not self.files.confirm_discard() or not self.gradient_library.files.confirm_discard():
            event.ignore()
            return
        self.gradient_library.close()
        self.render_service.stop()
        super().closeEvent(event)
