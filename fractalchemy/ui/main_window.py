"""Top-level application window: Fractal Library on the left, the fractal viewport in the centre.

Menus (File / Edit / View / Windows / Help), a toolbar, and a status bar showing the
loaded fractal, render facts, the progressive pass counter and a progress bar. The
Transform Editor, the Gradient Library, the Animation window and the Render Image window are separate
tool windows opened from *Windows* or the toolbar.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QToolButton

from .. import config
from ..fractal.formats import flame_from_text, flame_to_text, load_flame, open_dialog_filter
from ..fractal.scene import Flame
from ..library.catalog import FRACTAL_CATALOG
from ..library.context_menu import LibraryContextMenu
from ..library.controller import LibraryController
from ..library.dialog import EditLibraryDialog
from ..library.items import LibraryItem
from ..library.roots import LibraryRoots
from ..render.service import RenderService
from ..widgets.collapsible_splitter import CollapsibleSplitter
from ..widgets.icons import action_icon, animation_icon, editor_icon, gradient_icon, render_icon
from .animation_window import AnimationWindow
from .background import run_in_background
from .editor_window import EditorWindow
from .fractal_document import FractalDocument
from .fractal_file_actions import FractalFileActions
from .fractal_library_panel import LIST_ICON_SIZE, FractalLibraryPanel
from .fractal_viewport import FractalViewport
from .gradient_library_window import GradientLibraryWindow
from .gradient_link import GradientLink
from .loader import load_ui
from .render_status import RenderStatus
from .render_window import RenderWindow
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
SETTINGS_PANE_WIDTH = 320
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
        self.status = RenderStatus(self.statusBar())
        self.viewport.bind(self.document, self.render_service)
        self.fractal_library = LibraryController(
            self.fractalLibraryPanel.model, fractal_roots or LibraryRoots(parent=self, key=FRACTAL_CATALOG.roots_key), self)
        self.fractal_menu = LibraryContextMenu(self.fractal_library, self.open_item, self)
        self.thumbnails = ThumbnailProvider(self.render_service, self.fractalLibraryPanel.model, self)
        self._formula_browser = None
        self._random_window = None
        self._batch: list[Flame] = []          # generated fractals shown in the library's temporary area
        self._batch_showing: int | None = None
        self.files = FractalFileActions(self.document, self)
        self.gradient_library = GradientLibraryWindow(roots, self)
        self.gradient_link = GradientLink(self.document, self.gradient_library, self.viewport, self)
        self.render_window = RenderWindow(self.document, self, settings if settings is not None else QSettings(),
                                          rate_hint=self._preview_rate)
        self.editor = EditorWindow(self.document, self.render_service, self, settings if settings is not None else QSettings())
        self.animation = AnimationWindow(self.document, self.render_service, self.show_flame, self,
                                         settings if settings is not None else QSettings())
        self.animation.rate_hint = self._preview_rate
        self.splitter.first_label, self.splitter.last_label = "fractal library", "settings panel"
        self.splitter.set_first_width(LIBRARY_PANE_WIDTH)
        self.splitter.set_last_width(SETTINGS_PANE_WIDTH)
        for pane, stretch in ((0, 0), (1, 1), (2, 0)):   # window resizes go to the viewport, not the side panes
            self.splitter.setStretchFactor(pane, stretch)
        self._settings = settings if settings is not None else QSettings()
        self.settingsPanel.attach_settings(self._settings)
        self.settingsPanel.bind(self.document)
        self._connect_actions()
        self._connect_document()
        self._connect_library()
        self._connect_render()
        self._connect_viewer_controls()
        self.render_service.start()
        self.fractal_library.rescan_all()

    # --- wiring -------------------------------------------------------------
    def _connect_actions(self) -> None:
        self.actionGradientLibrary.setIcon(gradient_icon())
        self.actionGradientLibrary.triggered.connect(self.show_gradient_library)
        self.actionRenderImage.setIcon(render_icon())
        self.actionRenderImage.triggered.connect(self.show_render_window)
        self.actionEditor.setIcon(editor_icon("editor"))
        self.actionEditor.triggered.connect(self.show_editor)
        self.actionAnimation.setIcon(animation_icon())
        self.actionAnimation.triggered.connect(self.show_animation)
        self.actionOpenFractal.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton))
        self.actionOpenFractal.triggered.connect(self.open_file)
        self.actionSaveFractal.setIcon(action_icon("save"))
        self.actionSaveFractal.triggered.connect(self.files.save)
        self.actionSaveAs.setIcon(action_icon("save-as"))
        self.actionSaveAs.setMenu(self.menuSaveAs)
        self.actionSaveAs.triggered.connect(self.files.save_as_new_file)
        save_as_button = self.toolBar.widgetForAction(self.actionSaveAs)
        if isinstance(save_as_button, QToolButton):
            save_as_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.actionSaveAsNewEntry.triggered.connect(self.files.save_as_new_entry)
        self.actionSaveAsNewFile.triggered.connect(self.files.save_as_new_file)
        self.actionSaveAsIntoFile.triggered.connect(self.files.save_as_into_file)
        self.actionUndo.setIcon(action_icon("undo"))
        self.actionRedo.setIcon(action_icon("redo"))
        self.actionUndo.triggered.connect(self.document.undo)
        self.actionRedo.triggered.connect(self.document.redo)
        self.actionCopyParameters.setIcon(action_icon("copy"))
        self.actionPasteParameters.setIcon(action_icon("paste"))
        self.actionCopyParameters.triggered.connect(self.copy_parameters)
        self.actionPasteParameters.triggered.connect(self.paste_parameters)
        self.files.status.connect(self._message)
        self.files.file_written.connect(self._on_fractal_written)
        self.actionGradientLibrary.setIcon(gradient_icon())
        self.actionGradientLibrary.triggered.connect(self.show_gradient_library)
        self.actionEditFractalLibrary.triggered.connect(self.edit_fractal_library)
        self.actionToggleFractalLibrary.toggled.connect(lambda shown: self.splitter.set_collapsed(not shown))
        self.actionRefreshFractalLibrary.triggered.connect(self.fractal_library.rescan_all)
        self.actionThumbnailView.toggled.connect(self.fractalLibraryPanel.set_thumbnail_view)
        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.about)
        self.actionFormulas.triggered.connect(lambda: self.show_formulas())
        self.actionRandomBatch.setIcon(action_icon("random"))
        self.actionRandomBatch.triggered.connect(self.show_random_batch_window)
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
        self.document.coloring_changed.connect(self.settingsPanel.info.show_coloring)
        self.document.modified_changed.connect(self._on_modified_changed)
        self.document.undo_changed.connect(self._on_undo_changed)
        self.document.flame_restored.connect(self._on_flame_restored)
        self.document.xform_changed.connect(self._on_xform_changed)
        self.document.transforms_changed.connect(self._on_xform_changed)
        self._info_timer = QTimer(self, singleShot=True, interval=config.EDIT_RENDER_DELAY_MS)
        self._info_timer.timeout.connect(self._on_flame_restored)
        self.settingsPanel.info.formula_activated.connect(self.show_formulas)

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
        self.viewport.render_progress.connect(self.settingsPanel.info.show_render)
        self.viewport.render_failed.connect(lambda message: self._message(f"Cannot render: {message}"))

    def _connect_viewer_controls(self) -> None:
        bar, panel, view = self.viewerBar, self.settingsPanel, self.viewport
        bar.zoom_requested.connect(view.set_zoom)
        bar.resolution_chosen.connect(self.document.set_image_size)
        bar.detail_chosen.connect(view.set_render_scale)
        view.view_changed.connect(bar.show_zoom)
        panel.render_settings_changed.connect(self._apply_render_settings)
        panel.render_options_changed.connect(self._apply_render_options)
        self._apply_render_settings(panel.passes, panel.quality, render=False)
        self._apply_render_options(panel.oversample, panel.filter_radius, panel.refine_to, render=False)

    def _apply_render_settings(self, passes: int, quality: float, render: bool = True) -> None:
        self._set_render_settings(self.viewport.settings.with_effort(passes, quality), render)

    def _apply_render_options(self, oversample: int, filter_radius: float, refine_to: float, render: bool = True) -> None:
        self._set_render_settings(self.viewport.settings.with_filter(oversample, filter_radius).with_refine(refine_to), render)

    def _set_render_settings(self, settings, render: bool) -> None:
        if render:
            self.viewport.set_render_settings(settings)
        else:
            self.viewport.settings = settings

    # --- fractal loading ----------------------------------------------------
    def open_file(self) -> None:
        """Prompt for a fractal file and show its first flame."""
        start = str(self.document.source_path.parent) if self.document.source_path else ""
        path, _ = QFileDialog.getOpenFileName(self, "Open fractal", start, open_dialog_filter())
        if path:
            self.open_file_path(Path(path))

    def open_file_path(self, path: Path) -> None:
        """Show `path` in the library's temporary area (browsable like any file) and load its first flame."""
        self._forget_batch()
        self.fractal_library.show_file(path)
        self.open_path(path, 0)

    def _forget_batch(self) -> None:
        self._batch = []
        self._batch_showing = None
        self.thumbnails.set_virtual(None)

    def open_item(self, item: LibraryItem) -> None:
        """Show the flame a library row refers to (generated ones come from memory)."""
        if item.virtual:
            self.show_batch_entry(item.index)
        elif not self.document.is_showing(item.path, item.index):
            self.open_path(item.path, item.index)

    def open_path(self, path: Path, index: int = 0) -> None:
        """Load flame `index` of `path` on a worker thread, then show it."""
        self._message(f"Loading {path.name}…")
        run_in_background(load_flame, path, index,
                          on_done=lambda flame: self._loaded(flame, path, index),
                          on_error=lambda exc: self._report_error("Could not open fractal", exc))

    def show_flame(self, flame: Flame) -> None:
        """Show a flame that did not come from a file."""
        self._batch_showing = None
        self.document.replace(flame)

    # --- random batch -------------------------------------------------------
    def show_random_batch_window(self) -> None:
        """Open (or raise) the Random Batch window."""
        if self._random_window is None:
            from .random_batch_window import RandomBatchWindow
            self._random_window = RandomBatchWindow(self, self._settings)
            self._random_window.batch_ready.connect(self.show_random_batch)
            self._random_window.status.connect(self._message)
        else:
            self._random_window.populate()   # formulas added meanwhile
        self._random_window.show()
        self._random_window.raise_()
        self._random_window.activateWindow()

    def show_random_batch(self, flames: list) -> None:
        """Put generated flames in the library's temporary area (under 'Randomly Generated') and show the first."""
        from .random_batch_window import BATCH_NAME
        self._batch = [f.copy() for f in flames]
        self._batch_showing = None
        self.thumbnails.set_virtual(Path(BATCH_NAME), self._batch)
        self.fractal_library.show_virtual(BATCH_NAME, [f.name for f in self._batch])
        if self._batch:
            self.show_batch_entry(0)

    def show_batch_entry(self, index: int) -> None:
        """Show generated flame `index` (kept in memory; Save writes it to a file of your choosing)."""
        if not 0 <= index < len(self._batch) or self._batch_showing == index:
            return
        self._batch_showing = index
        self.document.replace(self._batch[index])
        self._message(f"Showing generated fractal {index + 1} of {len(self._batch)} — not saved yet")

    def _loaded(self, flame: Flame, path: Path, index: int) -> None:
        self._batch_showing = None
        self.document.replace(flame, path, index)
        self._message(f"Loaded '{flame.name}' from {path.name}")

    def copy_parameters(self) -> None:
        """Put the fractal's parameters (gradient included) on the clipboard as .fa text."""
        flame = self.document.flame
        if flame is None:
            return
        QGuiApplication.clipboard().setText(flame_to_text(flame))
        self._message(f"Copied the parameters of '{flame.name}'")

    def paste_parameters(self) -> None:
        """Replace the shown fractal with parameters from the clipboard (.fa, <flame> XML or a Chaotica world)."""
        text = QGuiApplication.clipboard().text()
        try:
            flame = flame_from_text(text)
        except Exception as exc:  # noqa: BLE001 - parse errors of any of the formats
            self._report_error("Cannot paste parameters", exc)
            return
        self.document.paste(flame)
        self._message(f"Pasted '{flame.name}'" + (f" — ignored: {', '.join(flame.unsupported)}" if flame.unsupported else ""))

    def _on_fractal_written(self, path: Path, _index: int) -> None:
        library = self.fractal_library
        if library.root_of(path) is None and library.open_file != path and not self._batch:
            library.show_file(path)       # a new file outside the library: browse it from the temporary area
        else:
            library.rescan_containing(path)   # (a generated batch stays on show so the rest can be saved too)
        self._on_flame_replaced()   # the source (file, entry) changed: status bar, Info tab, title

    def _on_modified_changed(self, modified: bool) -> None:
        self.actionSaveFractal.setEnabled(self.document.flame is not None)
        self._update_title()

    def _on_undo_changed(self, can_undo: bool, can_redo: bool) -> None:
        self.actionUndo.setEnabled(can_undo)
        self.actionRedo.setEnabled(can_redo)

    def _on_xform_changed(self, *_args) -> None:
        """A transform was edited: refresh the status bar / Info tab once the edits pause (not on every drag step)."""
        self._update_title()
        self._info_timer.start()

    def _on_flame_restored(self) -> None:
        """Undo / redo / paste: everything may have changed."""
        flame = self.document.flame
        self.status.show_fractal(flame, self.document.source_path.name if self.document.source_path else "")
        self.settingsPanel.info.show_flame(flame, self.document.source_path, self.document.source_index)
        self._update_title()

    def _update_title(self) -> None:
        flame = self.document.flame
        star = "*" if self.document.modified else ""
        self.setWindowTitle(f"{config.APP_NAME} — {flame.name}{star}" if flame else config.APP_NAME)

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
        """Reload the shown flame if another program changed its file (not our own gradient saves)."""
        if path == self.document.source_path and not self.gradient_library.files.wrote_recently(path) \
                and not self.files.wrote_recently(path):
            self.open_path(path, self.document.source_index)

    # --- other slots --------------------------------------------------------
    def show_gradient_library(self) -> None:
        """Open the Gradient Library window, or bring it to the front if it is already open."""
        self.gradient_library.bring_to_front()

    def show_render_window(self) -> None:
        """Open the Render Image window (a render in progress keeps its progress view)."""
        self.render_window.bring_to_front()

    def show_editor(self) -> None:
        """Open the Transform Editor (or bring it to the front); it edits the fractal shown here."""
        self.editor.bring_to_front()

    def show_animation(self) -> None:
        """Open the Animation window (or bring it to the front); keyframes are captured from the fractal shown here."""
        self.animation.bring_to_front()

    def _preview_rate(self) -> tuple[str, float] | None:
        """(engine, samples/s) of the last viewport render, for the Render window's time estimate."""
        stats = self.viewport.stats
        if stats is None or stats.samples_per_second <= 0:
            return None
        return stats.engine, stats.samples_per_second

    def about(self) -> None:
        QMessageBox.about(self, f"About {config.APP_NAME}", ABOUT_TEXT)

    def show_formulas(self, name: str = "") -> None:
        """Open (or raise) the formula browser, on formula `name` if given."""
        if self._formula_browser is None:
            from .formula_browser import FormulaBrowser
            self._formula_browser = FormulaBrowser(self)
        if name:
            self._formula_browser.select(name)
        self._formula_browser.show()
        self._formula_browser.raise_()
        self._formula_browser.activateWindow()

    def _on_flame_replaced(self) -> None:
        flame = self.document.flame
        source = self.document.source_path.name if self.document.source_path else ""
        self.status.show_fractal(flame, source)
        self.status.show_idle()
        self.viewerBar.show_flame(flame)
        self.settingsPanel.info.show_flame(flame, self.document.source_path, self.document.source_index)
        for action in (self.actionSaveFractal, self.actionSaveAs, self.actionCopyParameters):
            action.setEnabled(flame is not None)
        self._update_title()

    def _on_camera_changed(self) -> None:
        flame = self.document.flame
        if flame is not None:
            cx, cy = flame.camera.center
            self._message(f"center {cx:.4f}, {cy:.4f}   zoom {flame.camera.zoom:.2f}", 2000)
        self.settingsPanel.info.show_camera()

    def _on_palette_changed(self) -> None:
        self._message("Gradient applied to the fractal", 2000)
        self.settingsPanel.info.show_palette()

    def _message(self, text: str, ms: int = MESSAGE_MS) -> None:
        self.statusBar().showMessage(text, ms)

    def _report_error(self, title: str, exc: Exception) -> None:
        self._message(f"{title}: {exc}")
        QMessageBox.warning(self, title, str(exc))

    def _report_library_error(self, message: str) -> None:
        self._message(message)
        QMessageBox.warning(self, "Fractal Library", message)

    # --- Qt overrides -------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        """Quitting closes the tool windows too, so check for unsaved gradient edits first."""
        if not self.gradient_library.files.confirm_discard():
            event.ignore()
            return
        if not self.render_window.confirm_quit():
            event.ignore()
            return
        if not self.animation.confirm_discard():
            event.ignore()
            return
        if self.animation.render_window is not None and not self.animation.render_window.confirm_quit():
            event.ignore()
            return
        self.gradient_library.close()
        self.render_window.hide()
        self.editor.close()
        self.animation.close()
        self.render_service.stop()
        super().closeEvent(event)
