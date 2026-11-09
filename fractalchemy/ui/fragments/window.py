"""The Fragments window: Fragmentarium inside Fractalchemy — edit a GLSL fragment, tweak its sliders, look around, render.

Opened from *Windows ▸ Fragments* (`F12`) or the toolbar. A tool window of the main window like the others: closing
hides it; its layout, options and open tabs are remembered between runs. Source tabs on the left, the viewport in the
middle, the Parameters dock on the right, the Log dock below — FragM's arrangement. The window only coordinates:
`TabManager` owns the editors and documents, `RenderDriver` decides what to render through the window's own
`RenderService` (a second service thread with the fragment engine), `FragViewport` paints and drives the camera,
`ParameterPanel` edits the values, `FragmentActions` holds the menus, `FragmentFileActions` the files,
`ParameterActions` the parameter / preset commands, `AnimationCoordinator` the clock, the easing dialog and the
timeline, `CameraActions` bookmarks / recording / keyframe handles, `ExploreCoordinator` the History dock (snapshots,
mutate), `SessionActions` sessions and the autosave, `ControllerCoordinator` MIDI / gamepad input and
`FragmentLibraryExtras` tags / ratings / filters; engine chores (*Test GLSL versions*, *Clear texture cache*) go to the
render thread as `FragTask` jobs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QGuiApplication, QTextCursor
from PySide6.QtWidgets import (QDialog, QDockWidget, QInputDialog, QLabel, QMainWindow, QMessageBox, QProgressBar, QSpinBox, QSplitter, QStatusBar,
                               QVBoxLayout, QWidget)

from ... import config
from ...fragments.document_format import read_fragment
from ...fragments.examples import INCLUDE_DIR
from ...fragments.files import FileManager
from ...fragments.glsl_compat import CompatOptions
from ...fragments.preferences import DEFAULT_LOG_NAME, FragPreferences
from ...fragments.gl.engine import FragEngineFactory
from ...fragments.gl.tasks import TASK_PRIORITY, FragTask, check_versions, clear_textures
from ...fragments.source import Message
from ...fragments.state import CAMERA_2D, CAMERA_3D
from ...fragments.templates import Template, save_user_template, user_templates_dir
from ...library.items import LibraryItem
from ...model import Gradient
from ...render.service import RenderService
from ...render.settings import RenderStats
from ...widgets.find_bar import FindBar
from ...widgets.icons import fragments_icon
from ...widgets.layouts import row
from .actions import FragmentActions
from .animation_actions import AnimationCoordinator
from .animation_controls import AnimationControls
from .camera_actions import CameraActions
from .controller_input import ControllerCoordinator
from .buffer_size import BufferSize, BufferSizeBar
from .code_editor import GlslCodeEditor
from .document import BuildOptions, FragDocument
from .explore import ExploreCoordinator
from .file_actions import FragmentFileActions, is_bundled
from .gradient_dialog import GradientDialog
from .grading_panel import GradingPanel
from .library_extras import FragmentLibraryExtras
from .library_panel import FragThumbnailProvider, FragmentLibraryController, FragmentLibraryPanel, make_roots
from .log_panel import LogPanel
from .parameter_actions import ParameterActions
from .parameter_panel import ParameterPanel
from .render_actions import RenderActions
from .render_driver import RenderDriver
from .render_window import FragRenderWindow
from .session_actions import SessionActions
from .tabs import TabManager
from .viewport import FragViewport
from .walkthrough_panel import WalkthroughPanel
from ...fragments.editor_themes import canonical
from ..library_host import LibraryHost
from ...widgets.windows import bring_to_front
from ...widgets.theming import set_themed_style

WINDOW_TITLE = "Fragments"
SETTINGS_GROUP = "fragments"
PREFERENCES_GROUP = "fragments/preferences"
AUTO_BUILD_DELAY_MS = 1000
GLSL_VERSIONS = (330, 400, 410, 420, 430, 440, 450, 460)
CONTROLS_HELP = """<h3>Mouse and keyboard</h3>
<p><b>3D camera, orbit navigation (default; Camera ▸ Navigation style)</b> — left-drag: orbit the target · middle-drag (or Shift+right):
pan · right-drag, Ctrl+middle or wheel: dolly towards the target (Ctrl+wheel: fine) · Shift+left: look around · Alt+left: orbit the origin ·
middle-click: Target (Ctrl: LightPos) at the point under the cursor · numpad <tt>1 3 7</tt> front / right / top (Ctrl: back / left / bottom) ·
numpad <tt>9</tt> opposite side · numpad <tt>4 6 8 2</tt> orbit 15° · numpad <tt>.</tt> frame the origin · Alt+T turntable.</p>
<p><b>3D camera, fly navigation (FragM)</b> — left-drag: orient · Shift+left: orbit the origin · Shift+Alt+left: orbit the target · right-drag: pan ·
left+right drag or wheel: dolly · Shift+wheel: step size.</p>
<p><b>Keys (both styles)</b> — <tt>W S A D R F</tt> fly · <tt>T G Y H</tt> pitch / yaw · <tt>Q E</tt> roll · <tt>1 3 2 5</tt> step ×½ ×2 ×10 reset · Shift+~ look at the origin.</p>
<p><b>2D camera</b> — left-drag: pan · right-drag: zoom about the press point · wheel: zoom · <tt>A D W S</tt> pan · <tt>Q E</tt> zoom · <tt>1 3 2 X</tt> step.</p>
<p><b>Overlays</b> — Ctrl+drag: a region of interest for the render window · Ctrl+M mini-map · Ctrl+Shift+A freeze the reference, Ctrl+Shift+B
A/B compare (drag the divider) · with camera paths drawn, drag a keyframe's eye point to move it.</p>
<p><b>Window</b> — F1 reset all · F2 / F3 copy / paste settings · F4 group → preset · F5 build · F6 randomize group · Shift+F6 mutate · Ctrl+F6 snapshot ·
F8 add preset · F9 select preset · Ctrl+F9 preset gallery · Esc fullscreen · Ctrl+Z / Ctrl+Shift+Z undo / redo (parameters; the editor has its own
when it has focus).</p>
<p><b>Editor</b> — Ctrl+Space complete · Ctrl+click go to definition · hover for signatures and build messages · Tab walks a snippet's stops ·
Ctrl+Shift+D / Ctrl+Shift+L select the next / every occurrence (type to edit them all, Esc leaves) · arrow keys on a slider nudge it
(Shift ×10, Ctrl ×0.1).</p>"""


class FragmentsWindow(QMainWindow):
    """Fragmentarium's editor / renderer as a Fractalchemy tool window (see the module docstring).

    Signals:
        status(str): A message for the main window's status bar.
    """
    status = Signal(str)

    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None, prefer_gpu: bool = True,
                 gradient_provider: Callable[[], Gradient | None] | None = None, three_d=None):
        """Args:
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where the layout and the options persist.
            prefer_gpu: Kept for symmetry with the other windows (fragments always need OpenGL).
            gradient_provider: Returns the Gradient Library's current gradient (*Insert gradient…*).
            three_d: Returns the 3D Editor window (*Export mesh… ▸ Send to 3D Editor*).
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(fragments_icon())
        self._settings = settings if settings is not None else QSettings()
        self.gradient_provider = gradient_provider
        self._three_d = three_d
        self.service = RenderService(self, prefer_gpu=prefer_gpu, factory=FragEngineFactory())
        self.buffer_size = BufferSize()
        self.driver = RenderDriver(self.service, self.buffer_size, self)
        self.tabs = TabManager(self)
        self.viewport = FragViewport(self)
        self.parameters = ParameterPanel(self)
        self.grading_panel = GradingPanel(self)
        self.log = LogPanel(self)
        self.walkthrough = WalkthroughPanel(self)
        self.files = FragmentFileActions(self.tabs, self, self._settings)
        self.library_panel = FragmentLibraryPanel(self)
        self.library = FragmentLibraryController(self.library_panel.model, make_roots(self._settings, self), self)
        self.library_host = LibraryHost(self.library_panel, self.library, self, self.open_item, message_ms=6000)
        self.thumbnails = FragThumbnailProvider(self.service, self.library_panel.model, lambda: self._capabilities, self)
        self.library_extras = FragmentLibraryExtras(self, self.library_panel, self.library, self.thumbnails, self.files.recent, self._settings)
        self.library_host.menu = self.library_extras.menu
        self.library_dock = self.make_dock("Library", "fragmentsLibrary", self.library_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.find_bar = FindBar(None, self)
        self.build_label = QLabel("", self)
        self.subframe_widget, self.subframe_spin, self.done_label = self._make_subframe_widget()
        self.buffer_bar = BufferSizeBar(self.buffer_size, self)
        self.engine_label, self.size_label, self.fps_label = QLabel(self), QLabel(self), QLabel(self)
        self.anim = AnimationControls(self)
        self.prefs = load_preferences(self._settings)
        self._tasks: dict = {}
        self._task_seq = 0
        self._paused = False
        self._capabilities = None
        self._fullscreen_state = None
        self._auto_timer = QTimer(self, singleShot=True, interval=AUTO_BUILD_DELAY_MS)
        self._auto_timer.timeout.connect(self._auto_build)
        self.animation = AnimationCoordinator(self)
        self.sessions = SessionActions(self)
        self.controllers = ControllerCoordinator(self)
        self.rendering = RenderActions(self)
        self.params = ParameterActions(self)
        self.camera = CameraActions(self)
        self.actions = FragmentActions(self)
        self.actions.build_menus()
        self.actions.build_toolbars()
        self._build_layout()
        self._connect()
        self.viewport.bind(self.driver)
        self.setAcceptDrops(True)
        self._restore_state()
        self._refresh_actions()
        self.service.start()
        self.library.rescan_all()
        self.actions.recover_session.setEnabled(self.sessions.announce_recovery())

    # --- construction -----------------------------------------------------------------------------------------------------
    def _make_subframe_widget(self) -> tuple[QWidget, QSpinBox, QLabel]:
        spin = QSpinBox(self)
        spin.setRange(0, 100000)
        spin.setSingleStep(5)
        spin.setValue(config.FRAG_DEFAULT_SUBFRAMES)
        spin.setToolTip("Subframe Max: stop accumulating after this many subframes (0 = keep going)")
        done = QLabel(" 0 rendered", self)
        done.setMinimumWidth(90)
        widget = QWidget(self)
        widget.setLayout(row(QLabel("Subframe max:", self), spin, done))
        widget.layout().setContentsMargins(4, 0, 4, 0)
        return widget, spin, done

    def _build_layout(self) -> None:
        editor_box = QWidget(self)
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        editor_layout.addWidget(self.tabs.widget, 1)
        editor_layout.addWidget(self.find_bar)
        self.find_bar.hide()
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(editor_box)
        self.splitter.addWidget(self.viewport)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([600, 800])
        self.setCentralWidget(self.splitter)
        self.parameters.setMinimumWidth(380)
        self.parameters_dock = self.make_dock("Parameters", "fragmentsParameters", self.parameters, Qt.DockWidgetArea.RightDockWidgetArea)
        self.log_dock = self.make_dock("Log", "fragmentsLog", self.log, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.parameters.add_page("Grading", self.grading_panel)
        self.walkthrough_dock = self.make_dock("Walkthrough", "fragmentsWalkthrough", self.walkthrough, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.tabifyDockWidget(self.library_dock, self.walkthrough_dock)
        self.walkthrough_dock.hide()
        self.explore = ExploreCoordinator(self)
        self.tabifyDockWidget(self.log_dock, self.explore.dock)
        self.actions.add_dock_toggles([self.library_dock, self.parameters_dock, self.log_dock, self.walkthrough_dock, self.explore.dock])
        self.library_panel.setMinimumWidth(220)
        bar = QStatusBar(self)
        self.progress = QProgressBar(self)
        self.progress.setFixedWidth(160)
        self.progress.setTextVisible(True)
        self.progress.setToolTip("Subframes accumulated against Subframe max")
        bar.addPermanentWidget(self.progress)
        bar.addPermanentWidget(self.fps_label)
        bar.addPermanentWidget(self.size_label)
        bar.addPermanentWidget(self.engine_label)
        self.setStatusBar(bar)
        self.resize(1500, 900)

    def make_dock(self, title: str, name: str, widget: QWidget, area) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(area, dock)
        return dock

    def _connect(self) -> None:
        self.service.engine_ready.connect(self._on_engine_ready)
        self.service.job_finished.connect(self._on_task_finished)
        self.service.job_failed.connect(self._on_task_failed)
        self.tabs.current_changed.connect(self._on_current_changed)
        self.tabs.document_opened.connect(self._on_document_opened)
        self.tabs.document_closed.connect(self._on_document_closed)
        self.driver.stats_changed.connect(self._on_stats)
        self.driver.fps_changed.connect(self._on_fps)
        self.driver.failed.connect(lambda message: self.message(f"Cannot render: {message}"))
        self.viewport.status.connect(self.message)
        self.viewport.fullscreen_requested.connect(self.toggle_fullscreen)
        self.viewport.context_menu_requested.connect(self._fullscreen_menu)
        self.viewport.viewport_menu_requested.connect(self._viewport_menu)
        self.viewport.keyframe_moved.connect(self.camera.move_keyframe)
        self.viewport.region_selected.connect(self.rendering.render_region)
        self.parameters.status.connect(self.message)
        self.parameters.select_source_requested.connect(self.params.select_source)
        self.parameters.bounds_edit_requested.connect(self.params.edit_bound)
        self.parameters.group_preset_requested.connect(self.params.group_to_preset)
        self.parameters.mode_changed.connect(lambda mode: setattr(self.prefs, "parameter_layout", mode))
        self.log.location_activated.connect(self.open_location)
        self.walkthrough.bind(lambda: self.tabs.document.text if self.tabs.document is not None else None)
        self.walkthrough.line_activated.connect(lambda line: self._with_editor(lambda e: e.goto_line(line)))
        self.walkthrough_dock.visibilityChanged.connect(lambda shown: self.walkthrough.refresh() if shown else None)
        self.files.status.connect(self.message)
        self.files.recent_changed.connect(lambda: self.actions.refresh_recent(self.files.recent()))
        self.files.file_changed_externally.connect(lambda path: self.log.add("warning", f"{path.name} changed on disk; reload it to see the changes"))
        self.library_panel.view_mode_changed.connect(self._set_thumbnail_view)
        self.library_dock.visibilityChanged.connect(lambda shown: self.actions.show_library.setChecked(shown) if self.actions.show_library.isChecked() != shown else None)
        self.library.status.connect(self.message)
        self.subframe_spin.valueChanged.connect(self.driver.set_subframe_max)
        self.buffer_bar.changed.connect(self._on_buffer_size_changed)
        self.anim.slider.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.animation.connect()
        self.actions.refresh_recent(self.files.recent())

    # --- engine ----------------------------------------------------------------------------------------------------------
    def _on_engine_ready(self, name: str) -> None:
        self.engine_label.setText(name)
        engine = self.service.engine
        self._capabilities = getattr(engine, "capabilities", None)
        if self._capabilities is not None:
            for line in self._capabilities.describe():
                self.log.add("info", line)
        else:
            self.log.add("critical", f"No OpenGL context for fragments: {name}")
        for tab in self.tabs.tabs:          # tabs restored before the engine was ready
            if tab.document.needs_build and self.prefs.autorun:
                self.build_document(tab.document)

    def build_options(self) -> BuildOptions:
        caps = self._capabilities
        compat = CompatOptions(self.prefs.compat_mode, caps.glsl_version if caps else 330, caps.has_fp64 if caps else False)
        return BuildOptions(self.prefs.move_main, self.prefs.use_defines, compat, self.include_paths())

    @staticmethod
    def document_folder(document: FragDocument) -> Path | None:
        """The folder files belonging to the document go to — never the bundled library (None: ask)."""
        if document.path is None or is_bundled(document.path):
            return None
        return document.path.parent

    def include_paths(self) -> list[Path]:
        """The user's extra include folders (preferences)."""
        return [Path(p) for p in self.prefs.include_paths]

    # --- documents -----------------------------------------------------------------------------------------------------------
    def _on_document_opened(self, document: FragDocument) -> None:
        document.message.connect(self.log.add_message)
        document.build_failed.connect(lambda diagnostics, d=document: self._on_build_failed(d, diagnostics))
        document.needs_build_changed.connect(lambda _n: self._refresh_build_label())
        document.undo_changed.connect(lambda *_a: self._refresh_actions())
        document.modified_changed.connect(lambda _m: self._refresh_title())
        document.path_changed.connect(lambda _p: self._refresh_title())
        document.built.connect(lambda _s, d=document: self._on_built(d))
        document.facts_changed.connect(lambda facts, d=document: self._on_facts(d, facts))
        document.easing_changed.connect(lambda d=document: self.animation.refresh(d))
        self.explore.watch(document)
        tab = self.tabs.tab_for(document)
        if tab is not None:
            tab.editor.textChanged.connect(self._on_editor_typed)
            tab.editor.find_requested.connect(self.show_find)
            tab.editor.goto_requested.connect(self.goto_line)
            tab.editor.save_requested.connect(lambda as_new: self.files.save_as() if as_new else self.files.save())
            tab.editor.status.connect(self.message)
            tab.editor.zoom_requested.connect(self.zoom_editors)
            tab.editor.definition_requested.connect(lambda name, d=document: self.goto_include_definition(d, name))
        if not document.metadata.animation:          # no clock of its own: the preferred frame rate and loop mode
            document.animation = document.animation.with_(fps=self.prefs.default_fps, loop_play=self.prefs.loop_play)
        if self.prefs.autorun and self._capabilities is not None:
            self.build_document(document)

    def _on_document_closed(self, document: FragDocument) -> None:
        if self.driver.document is document:
            self.driver.set_document(None)
        self.explore.forget(document)

    def _on_current_changed(self, document: FragDocument | None) -> None:
        self.find_bar.set_editor(self.tabs.editor)
        self.driver.set_document(document)
        self.viewport.set_document(document)
        self.parameters.set_document(document)
        self.grading_panel.set_document(document)
        if document is not None and document.source is not None and document.source.subframe_max >= 0:
            self.subframe_spin.setValue(document.source.subframe_max)
        self.anim.stop()
        if document is not None:
            self.anim.apply_settings(document.animation)
            self.actions.loop_play.setChecked(document.animation.loop_play)
            self.actions.loop_path.setChecked(document.animation.loop_path)
            self.actions.interpolate_all.setChecked(document.animation.interpolation == "all")
            self.actions.interpolate_camera.setChecked(document.animation.interpolation != "all")
        self.animation.refresh(document)
        self.camera.refresh_menu()
        self.walkthrough.refresh()
        self.explore.show_document(document)
        self._refresh_title()
        self._refresh_actions()
        self._refresh_build_label()

    def _on_built(self, document: FragDocument) -> None:
        if document is self.tabs.document:
            if document.source.subframe_max >= 0:
                self.subframe_spin.setValue(document.source.subframe_max)
            self.parameters.rebuild()
            self.animation.refresh(document)
            tab = self.tabs.tab_for(document)
            if tab is not None:
                tab.editor.set_error_line(None)
                tab.editor.set_diagnostics([])
        kind = document.source.camera_kind
        self.log.add("info", f"Built {document.name}: {len(document.state.params)} parameters, {kind} camera, buffer {document.source.buffer or 'RGBA32F'}"
                     + (", buffer shader" if document.source.buffer_shader else ""))
        self.log.add("info", "Camera: Use W/S to fly. 1/3 adjusts speed. Q/E rolls. Click on the viewport for key focus. See Help for more."
                     if kind == "3D" else "Camera: Click on the viewport for key focus. See Help for more.")
        if not document.source.runnable:
            self.log.add("info", "Not a runnable fragment.")
        if self.prefs.verbose:
            for line in document.state.to_text().splitlines():
                self.log.add("script", line)

    def _on_build_failed(self, document: FragDocument, diagnostics: list) -> None:
        self.log.add_diagnostics(diagnostics)
        tab = self.tabs.tab_for(document)
        if tab is None:
            return
        marks = []
        for item in diagnostics:
            file = getattr(item, "file", None)
            line = getattr(item, "line", 0)
            same = (file is None and document.path is None) or (file is not None and document.path is not None and Path(file).resolve() == document.path.resolve())
            if same and line:
                severity = getattr(item, "severity", None) or ("warning" if getattr(item, "level", "") == "warning" else "error")
                marks.append((line, severity, getattr(item, "message", None) or getattr(item, "text", "")))
        if marks:
            tab.editor.set_error_line(marks[0][0])
            if document is self.tabs.document and self.prefs.jump_to_error:
                tab.editor.goto_line(marks[0][0])
        tab.editor.set_diagnostics(marks)
        self.message("Build failed — see the log")

    def goto_include_definition(self, document: FragDocument, name: str) -> None:
        """Ctrl+click on a name the tab does not define: look through the files it includes (then every include folder)."""
        from ...fragments.definitions import find_in_files
        files = list(document.source.dependencies) if document.source is not None else []
        manager = FileManager(self.include_paths(), document.path)
        for folder in manager.include_paths:
            files += sorted(p for p in folder.glob("*.frag") if p not in files)
        found = find_in_files(name, files)
        if found is None or found.file is None:
            self.message(f"No definition of {name} found")
            return
        self.open_location(found.file, found.line)
        self.message(f"{name}: {found.kind} in {found.file.name} line {found.line}")

    # --- building --------------------------------------------------------------------------------------------------------------
    def build(self) -> None:
        """F5: build the current tab."""
        document = self.tabs.document
        if document is not None:
            self.build_document(document, forced=True)

    def build_document(self, document: FragDocument, forced: bool = False) -> None:
        if self._capabilities is None:
            self.log.add("warning", "The OpenGL engine is not ready yet; the fragment will be built when it is")
            return
        self.log.add("info", f"Parse: {document.path.name if document.path else 'Unnamed'}")
        if document.build(self.build_options()):
            self._refresh_build_label()
        elif forced:
            self.message("Build failed — see the log")

    def _on_editor_typed(self) -> None:
        if self.prefs.auto_build:
            self._auto_timer.start()
        if self.walkthrough_dock.isVisible():
            self.walkthrough.schedule_refresh()

    def _auto_build(self) -> None:
        document = self.tabs.document
        if document is not None and document.needs_build:
            self.build_document(document)

    def set_navigation(self, style: str) -> None:
        """*Navigation style*: `orbit` (DCC conventions) or `fragm` (FragM's fly controls); kept in the preferences."""
        self.viewport.navigation = style
        self.prefs.navigation = style
        if not isinstance(self.actions, FragmentActions):
            return                                 # still building the actions
        self.actions.nav_orbit.setChecked(style == "orbit")
        self.actions.nav_fragm.setChecked(style != "orbit")
        self.message("Orbit navigation: left-drag orbits the target, middle pans, right / wheel dolly (numpad 1 3 7 for the views)"
                     if style == "orbit" else "Fly navigation: left-drag turns, right-drag pans, W A S D fly")

    def set_editor_theme(self, name: str) -> None:
        """*Edit ▸ Editor theme*: follow the application theme, or pin one to every fragment editor (a preference)."""
        name = canonical(name)
        self.prefs.editor_theme = name
        self.tabs.theme = name
        for tab in self.tabs.tabs:
            tab.editor.set_theme(name)
        if isinstance(self.actions, FragmentActions):
            self.actions.check_theme(name)

    def zoom_editors(self, direction: int) -> None:
        """Ctrl + wheel / plus / minus / 0 in an editor: every tab's font size (kept in the preferences)."""
        editor = self.tabs.editor
        current = self.prefs.font_size or (editor.font().pointSize() if editor is not None else 10)
        size = 0 if direction == 0 else max(6, min(48, current + direction))
        self.prefs.font_size = size
        self.tabs.font_size = size
        for tab in self.tabs.tabs:
            tab.editor.set_font_size(size)
        self.message(f"Editor font: {'system size' if size == 0 else f'{size} pt'}")

    def toggle_editor(self, shown: bool) -> None:
        """*Editor pane*: hide the source tabs to give the viewport the whole width (Ctrl+E)."""
        if hasattr(self, "splitter"):
            self.splitter.widget(0).setVisible(shown)

    def step_preset(self, delta: int) -> None:
        """Ctrl+PgDown / Ctrl+PgUp: apply the next / previous preset."""
        combo = self.parameters.preset_combo
        if combo.count() == 0:
            return
        combo.setCurrentIndex((combo.currentIndex() + delta) % combo.count())
        self.parameters.apply_current_preset()

    def show_controllers(self) -> None:
        """*Windows ▸ Controllers…*: MIDI knobs and gamepad sticks bound to sliders."""
        from .controller_input import ControllerDialog
        dialog = ControllerDialog(self, self.controllers)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()

    def show_preset_gallery(self) -> None:
        """*Preset gallery…*: every preset rendered small; double-click applies one."""
        from .preset_gallery import PresetGalleryDialog
        document = self.tabs.document
        if document is None or document.source is None:
            self.message("Build the fragment first")
            return
        dialog = PresetGalleryDialog(self, document, self.service)
        dialog.preset_chosen.connect(self.parameters.apply_preset)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()

    def set_manual_render(self, enabled: bool) -> None:
        """*Manual rendering*: the viewport only renders on request (a change made while manual renders when turned off)."""
        self.driver.manual = enabled
        self.message("Manual rendering: use Render now (Shift+F5)" if enabled else "Automatic rendering")
        if not enabled and self.driver.pending:
            self.driver.render_now()

    def set_auto_build(self, enabled: bool) -> None:
        self.prefs.auto_build = enabled
        if enabled:
            self._auto_build()

    def _refresh_build_label(self) -> None:
        document = self.tabs.document
        stale = document is not None and document.needs_build
        failed = stale and document.build_failed_last
        self.build_label.setText(" Build failed — see the log " if failed else " Build needed " if stale else "")
        set_themed_style(self.build_label, "QLabel {{ color: {error}; font-weight: bold; }}" if failed
                         else "QLabel {{ color: {warning}; font-weight: bold; }}" if stale else "")
        self.build_label.setToolTip("The last build was rejected; the previous program (if any) keeps rendering" if failed
                                    else "The source, a lock or a build option changed since the shown program was built (F5)" if stale else "")
        self.actions.build.setEnabled(document is not None)

    # --- engine chores (run on the render thread) ------------------------------------------------------------------------------
    def run_engine_task(self, name: str, body, on_done) -> None:
        """Run `body(engine)` on the render thread; `on_done(result)` on the GUI thread (failures go to the log)."""
        self._task_seq += 1
        key = ("task", self._task_seq)
        self._tasks[key] = (name, on_done)
        self.service.submit(key, FragTask(name, body), None, priority=TASK_PRIORITY)

    def _on_task_finished(self, key: object, stats: RenderStats) -> None:
        task = self._tasks.pop(key, None)
        if task is not None:
            task[1](stats.facts)

    def _on_task_failed(self, key: object, message: str) -> None:
        task = self._tasks.pop(key, None)
        if task is not None:
            self.log.add("critical", f"{task[0]} failed: {message}")

    def test_glsl_versions(self) -> None:
        """*Test GLSL versions*: compile the current fragment at every version the driver offers and log the outcome."""
        document = self.tabs.document
        if document is None or document.source is None or self._capabilities is None:
            self.message("Build the fragment first")
            return
        top = self._capabilities.glsl_version
        versions = [v for v in GLSL_VERSIONS if v <= top]
        body = check_versions(document.source, self.prefs.compat_mode, versions, self._capabilities.has_fp64)
        self.log.add("info", f"Testing {document.name} at GLSL {', '.join(map(str, versions))}…")
        self.run_engine_task("Test GLSL versions", body, lambda results: self._report_versions(document, results))

    def _report_versions(self, document: FragDocument, results) -> None:
        for version, diagnostics in results:
            if not diagnostics:
                self.log.add("info", f"GLSL {version}: compiled")
                continue
            first = diagnostics[0]
            text = first if isinstance(first, str) else f"{first.stage} shader: {first.message}" + (f" (line {first.line})" if first.line else "")
            self.log.add("warning", f"GLSL {version}: {len(diagnostics)} problem{'s' if len(diagnostics) != 1 else ''} — {text}")
        self.message(f"GLSL versions tested: {sum(1 for _v, d in results if not d)} of {len(results)} compiled")

    def clear_texture_cache(self) -> None:
        """*Clear texture cache*: drop the engine's textures; the next subframe reloads them from disk."""
        self.run_engine_task("Clear texture cache", clear_textures, lambda _r: (self.log.add("info", "Texture cache cleared"), self.driver.render(clear=True)))

    def set_debug_view(self, view: str) -> None:
        """*Debug view*: the picture, or the depth buffer."""
        document = self.tabs.document
        if document is not None:
            document.set_debug_view(view)
        self.message("Depth buffer view: near bright, far dark, background black" if view == "depth" else "Picture view")

    def show_composer(self) -> None:
        """*DE Composer…*: folds + transforms + a primitive → a fragment tab (reopens the current tab's recipe if it has one)."""
        from ...fragments.composer import Recipe
        from .composer_dialog import RECIPE_KEY, ComposerDialog
        document = self.tabs.document
        recipe_data = document.metadata.tabs.get(RECIPE_KEY) if document is not None else None
        dialog = ComposerDialog(self, Recipe.from_dict(recipe_data) if recipe_data else None, document if recipe_data else None)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()

    def show_de_slice(self) -> None:
        """*Debug view ▸ DE slice…* for fragments with a distance estimator."""
        from ...fragments.gl.mesh import has_distance_estimator
        from .de_slice_dialog import DESliceDialog
        document = self.tabs.document
        request = document.request() if document is not None else None
        if request is None or not has_distance_estimator(request.modern):
            self.message("The DE slice needs a built fragment with `float DE(vec3 p)`")
            return
        dialog = DESliceDialog(self, document)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()

    def show_preprocessed(self) -> None:
        """*Show preprocessed source*: the GLSL handed to the driver, line by line with its origin."""
        document = self.tabs.document
        if document is None or document.modern is None:
            self.message("Build the fragment first")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Preprocessed source — {document.name}")
        editor = GlslCodeEditor(dialog)
        editor.setReadOnly(True)
        editor.set_theme(self.prefs.editor_theme)
        parts = []
        for title, text, line_map in (("vertex shader", document.modern.vertex, document.modern.vertex_map),
                                      ("fragment shader", document.modern.fragment, document.modern.fragment_map)):
            parts.append(f"// ===== {title} =====")
            for number, line in enumerate(text.split("\n"), start=1):
                origin = line_map.origin(number)
                where = f"{origin[0].name if origin[0] else 'tab'}:{origin[1]}" if origin else "generated"
                parts.append(f"{line:<100}// {where}")
        editor.set_text("\n".join(parts))
        layout = QVBoxLayout(dialog)
        layout.addWidget(editor)
        dialog.resize(1100, 800)
        dialog.show()

    # --- rendering facts ------------------------------------------------------------------------------------------------------
    def _on_stats(self, stats: RenderStats) -> None:
        self.done_label.setText(f" {stats.passes_done} rendered")
        self._show_progress(stats)
        if self.viewport.hud_enabled:
            self.viewport.update()
        tiled = f"  tiled {stats.facts.tiled}×{stats.facts.tiled}" if stats.facts is not None and stats.facts.tiled > 1 else ""
        self.size_label.setText(f"{stats.width}×{stats.height}  aspect {stats.width / max(1, stats.height):.3f}{tiled}")

    def _show_progress(self, stats: RenderStats) -> None:
        limit = self.driver.subframe_max
        if limit > 0:
            self.progress.setRange(0, limit)
            self.progress.setValue(min(stats.passes_done, limit))
            self.progress.setFormat("%v / %m subframes")
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.progress.setFormat(f"{stats.passes_done} subframes")

    def _on_facts(self, document: FragDocument, facts) -> None:
        """The first pass after a build: FragM's "Compiled script in N ms" (the cached figure for an unchanged program)."""
        if document is self.tabs.document:
            self.log.add("info", f"Compiled script in {facts.compile_ms:.0f} ms.")
            for note in facts.notes:
                self.log.add("warning" if "cannot" in note or "not found" in note else "info", note)

    def _on_fps(self, fps: float) -> None:
        self.fps_label.setText(f"FPS: {fps:.1f}" if fps > 0 else "FPS: n.a.")

    def _on_buffer_size_changed(self) -> None:
        self.driver.render(clear=True)

    # --- files, templates, examples -------------------------------------------------------------------------------------------
    def new_from_template(self, template: Template) -> None:
        self.files.new_from_template(template)

    def import_shadertoy(self) -> None:
        """*Import from Shadertoy…*: paste the passes, get a fragment tab (two files next to each other with a Buffer A)."""
        from .shadertoy_dialog import ShadertoyDialog
        dialog = ShadertoyDialog(self, Path(str(self._settings.value("fragments/folder", str(Path.home())))))
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result_conversion is None:
            return
        conversion = dialog.result_conversion
        for note in conversion.notes:
            self.log.add("info", f"Shadertoy import: {note}")
        if conversion.image is None:
            self.open_text(conversion.main)
            return
        folder = dialog.target_folder
        main_path = folder / f"{conversion.image_file[:-len('-image.frag')]}.frag"
        try:
            (folder / conversion.image_file).write_text(conversion.image, encoding="utf-8")
            main_path.write_text(conversion.main, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Fragments", f"Cannot write the fragment files:\n{exc}")
            return
        self.open_path(main_path)

    def open_example(self, path: Path) -> None:
        self.files.open_path(path)

    def open_path(self, path: Path) -> None:
        """Open a fragment file (the main window's `--fragment` argument and drops)."""
        self.files.open_path(Path(path))

    def open_item(self, item: LibraryItem) -> None:
        """A library row was chosen."""
        if item.opens_entry:
            self.files.open_path(item.path)

    def _set_thumbnail_view(self, thumbnails: bool) -> None:
        from ..fractal_library_panel import LIST_ICON_SIZE
        self.thumbnails.set_enabled(thumbnails)
        self.library_panel.apply_icon_size(self.thumbnails.size if thumbnails else LIST_ICON_SIZE)
        if self.actions.thumbnails.isChecked() != thumbnails:
            self.actions.thumbnails.setChecked(thumbnails)

    def save_as_template(self) -> None:
        """Keep the current source as one of the user's templates (a `.fafrag` in the templates folder)."""
        document = self.tabs.document
        if document is None:
            return
        name, ok = QInputDialog.getText(self, "Save as template", "Template name:", text=document.name)
        if ok and name.strip():
            path = save_user_template(name.strip(), document.text)
            self.actions.refresh_templates()
            self.message(f"Saved template {path.name}")

    def open_templates_folder(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        folder = user_templates_dir()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def save_screenshot(self) -> None:
        self.files.save_screenshot(self.viewport.image)

    # --- drag and drop ----------------------------------------------------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt override
        if any(self._droppable(Path(url.toLocalFile())) for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt override
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in (".frag", ".fafrag"):
                self.files.open_path(path)
            elif self._droppable(path):
                self.files.load_parameters(path)
        event.acceptProposedAction()

    @staticmethod
    def _droppable(path: Path) -> bool:
        return path.suffix.lower() in (".frag", ".fafrag", ".fragparams", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr")

    def open_location(self, path: Path, line: int) -> None:
        """A log row was clicked: show the file (bundled includes read-only) at `line`."""
        tab = self.tabs.tab_for_path(path)
        if tab is None:
            if not path.is_file():
                return
            self.tabs.open_file(path, read_only=is_bundled(path) and path.parent == INCLUDE_DIR)
            tab = self.tabs.tab_for_path(path)
        if tab is not None:
            self.tabs.set_current(tab.document)
            tab.editor.goto_line(line)
            tab.editor.setFocus()

    def include_names(self) -> list[str]:
        return FileManager(self.include_paths()).fragment_files()

    # --- editing helpers ------------------------------------------------------------------------------------------------------
    def _with_editor(self, fn) -> None:
        editor = self.tabs.editor
        if editor is not None:
            fn(editor)

    def show_find(self, replace: bool = False) -> None:
        self.find_bar.set_editor(self.tabs.editor)
        self.find_bar.open(replace)

    def goto_line(self) -> None:
        editor = self.tabs.editor
        if editor is None:
            return
        line, ok = QInputDialog.getInt(self, "Go to line", "Line:", editor.line_column()[0], 1, max(1, editor.blockCount()))
        if ok:
            editor.goto_line(line)

    def indent_script(self) -> None:
        self._with_editor(lambda e: e.indent_script())

    def insert_snippet(self, text: str) -> None:
        self._with_editor(lambda e: e.insert_snippet(text + "\n"))

    def insert_template(self, template: str) -> None:
        """A snippet with `${n:stop}` placeholders at the cursor; Tab moves between the stops."""
        self._with_editor(lambda e: (e.insert_template(template), e.setFocus()))

    def insert_gradient(self) -> None:
        """*Insert gradient…*: a gradient as GLSL at the cursor (or on the clipboard)."""
        document = self.tabs.document
        if document is None:
            return
        dialog = GradientDialog(self, self.gradient_provider, self.document_folder(document))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        strip = dialog.write_texture_if_needed()
        if strip is not None:
            self.log.add("info", f"Wrote gradient strip {strip}")
        text = dialog.result_text()
        if dialog.accepted_action == "copy":
            QGuiApplication.clipboard().setText(text)
            self.message("Copied the gradient's GLSL")
        else:
            self.insert_snippet(text)

    def compare_with_original(self) -> None:
        """*Compare with original…*: a diff against the bundled example the tab came from, or against its file on disk."""
        from .diff_dialog import DiffDialog
        from .file_actions import origin_path
        document = self.tabs.document
        if document is None:
            return
        source = origin_path(document) or document.path
        if source is None or not source.is_file():
            self.message("Nothing to compare with: the tab was never saved and did not come from the library")
            return
        try:
            original = read_fragment(source)[0]
        except OSError as exc:
            self.message(f"Cannot read {source.name}: {exc}")
            return
        dialog = DiffDialog(self, original, document.text, source.name, document.name, source)
        dialog.revert_requested.connect(self.replace_text)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()

    def undo(self) -> None:
        editor, document = self.tabs.editor, self.tabs.document
        if editor is not None and editor.hasFocus():
            editor.undo()
        elif document is not None:
            document.undo()

    def redo(self) -> None:
        editor, document = self.tabs.editor, self.tabs.document
        if editor is not None and editor.hasFocus():
            editor.redo()
        elif document is not None:
            document.redo()

    def replace_text(self, text: str) -> None:
        """Replace the whole editor text as one undoable edit (the document mirrors it)."""
        editor = self.tabs.editor
        if editor is None:
            return
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(text)
        cursor.endEditBlock()

    # --- rendering to file (the commands live in `render_actions.py`) ------------------------------------------------------------
    @property
    def render_window(self) -> FragRenderWindow:
        """The Render Fragment window (created on first use)."""
        return self.rendering.render_window

    @property
    def render_queue(self):
        """The Render Queue window (created on first use)."""
        return self.rendering.queue

    def show_render_window(self) -> None:
        self.rendering.show_render_window()

    def queue_current_render(self) -> None:
        self.rendering.queue_current()

    def freeze_reference(self) -> None:
        """*Compare ▸ Freeze reference*: the current picture becomes the A side of the wipe."""
        if self.viewport.freeze_reference():
            self.actions.compare.setChecked(True)
            self.message("Reference frozen — drag the divider; the right side is live")
        else:
            self.message("Nothing rendered yet")

    # --- fullscreen ---------------------------------------------------------------------------------------------------------------
    def toggle_fullscreen(self) -> None:
        """Only the viewport, over the whole screen (Esc toggles; Shift+right-click for the menus)."""
        if self._fullscreen_state is None:
            self._fullscreen_state = (self.saveState(), self.tabs.widget.isVisible())
            for widget in (self.parameters_dock, self.log_dock, self.library_dock, self.walkthrough_dock, self.explore.dock, self.actions.toolbar,
                           self.actions.mode_toolbar, self.actions.nav_toolbar, self.actions.time_toolbar, self.menuBar(), self.statusBar(), self.tabs.widget):
                widget.hide()
            self.showFullScreen()
            self.viewport.setFocus()
        else:
            state, tabs_visible = self._fullscreen_state
            self._fullscreen_state = None
            self.showNormal()
            self.restoreState(state)
            for widget in (self.menuBar(), self.statusBar(), self.actions.toolbar, self.actions.mode_toolbar, self.actions.nav_toolbar, self.actions.time_toolbar):
                widget.show()
            self.tabs.widget.setVisible(tabs_visible)
        self.actions.fullscreen.blockSignals(True)
        self.actions.fullscreen.setChecked(self._fullscreen_state is not None)
        self.actions.fullscreen.blockSignals(False)

    def _viewport_menu(self, pos) -> None:
        """Right-click (without a drag) on the viewport: the common image and camera actions."""
        from PySide6.QtWidgets import QMenu
        a = self.actions
        menu = QMenu(self)
        for action in (a.copy_image, a.screenshot, None, a.add_bookmark, a.reset_camera, None, a.hud, a.fullscreen, None, a.render, a.export_mesh):
            menu.addSeparator() if action is None else menu.addAction(action)
        menu.exec(pos)

    def copy_image(self) -> None:
        """*Copy image*: the viewport's picture on the clipboard."""
        image = self.viewport.image
        if image is None:
            self.message("Nothing rendered yet")
            return
        QGuiApplication.clipboard().setImage(image)
        self.message("Image copied to the clipboard")

    def reset_camera(self) -> None:
        """*Reset camera*: the camera of the current preset (or the annotation defaults)."""
        document = self.tabs.document
        if document is None or document.source is None:
            return
        names = list(CAMERA_3D if document.camera_kind == "3D" else CAMERA_2D)
        body = document.source.presets.get(document.current_preset or "Default", "")
        lines = [line for line in body.splitlines() if line.split("=")[0].strip() in names]
        if lines:
            document.apply_settings("\n".join(lines), label="reset camera")
        else:
            document.reset([n for n in names if n in document.state])
        self.message("Camera reset")

    def _fullscreen_menu(self, pos) -> None:
        """Shift + right-click in fullscreen: the menu bar's menus as a popup (FragM's fullscreen context menu)."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        for action in self.menuBar().actions():
            if action.menu() is not None:
                menu.addMenu(action.menu())
        menu.exec(pos)

    # --- help -----------------------------------------------------------------------------------------------------------------------
    def show_controls_help(self) -> None:
        QMessageBox.information(self, "Fragments — mouse and keyboard", CONTROLS_HELP)

    def start_tutorials(self) -> None:
        """*Help ▸ Start the tutorials*: the first tutorial fragment with the Walkthrough dock in front."""
        from ...fragments.examples import examples_dir
        tutorials = sorted((examples_dir() / "Fractalchemy Tutorials").glob("*.frag"))
        if not tutorials:
            self.message("The tutorial fragments are not installed")
            return
        self.files.open_path(tutorials[0])
        self.walkthrough_dock.show()
        self.walkthrough_dock.raise_()
        self.walkthrough.refresh()
        self.message("Follow the steps in the Walkthrough dock; the next tutorials are in Library ▸ Examples ▸ Fractalchemy Tutorials")

    # --- window ----------------------------------------------------------------------------------------------------------------------
    def _refresh_title(self) -> None:
        document = self.tabs.document
        if document is None:
            self.setWindowTitle(WINDOW_TITLE)
        else:
            self.setWindowTitle(f"{WINDOW_TITLE} — {document.path.name if document.path else 'Unnamed'}{' *' if document.modified else ''}")

    def _refresh_actions(self) -> None:
        document = self.tabs.document
        has = document is not None
        for action in (self.actions.save, self.actions.save_as, self.actions.close_tab, self.actions.reload, self.actions.reset_all,
                       self.actions.copy_settings, self.actions.paste_settings, self.actions.insert_preset, self.actions.select_preset,
                       self.actions.group_preset, self.actions.find, self.actions.replace, self.actions.goto, self.actions.indent):
            action.setEnabled(has)
        self.actions.reload.setEnabled(has and document.path is not None)
        self.actions.undo.setEnabled(has and document.can_undo)
        self.actions.redo.setEnabled(has and document.can_redo)

    def message(self, text: str) -> None:
        self.statusBar().showMessage(text, 6000)
        self.status.emit(text)

    def bring_to_front(self) -> None:
        bring_to_front(self)

    def confirm_quit(self) -> bool:
        """Before the application quits: a running render? unsaved tabs?"""
        return self.rendering.confirm_quit() and self.files.confirm_close_all()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._fullscreen_state is not None:
            self.toggle_fullscreen()
        self.save_state()
        if self.parent() is not None:
            event.ignore()
            self.hide()
            return
        if not self.files.confirm_close_all():
            event.ignore()
            return
        self.shutdown()
        super().closeEvent(event)

    def shutdown(self) -> None:
        """Stop the render service and any render to file (the main window calls this when the application quits)."""
        self.driver.cancel()
        self.rendering.shutdown()
        self.sessions.clean_shutdown()
        self.controllers.shutdown()
        self.service.stop()

    def hideEvent(self, event) -> None:
        self.save_state()
        self._set_paused(True)
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._set_paused(False)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._set_paused(self.isMinimized())

    def _set_paused(self, paused: bool) -> None:
        """*Pause when hidden*: stop accumulating while nobody can see the viewport; continue where it was on show."""
        if not self.prefs.pause_when_hidden or paused == self._paused:
            return
        self._paused = paused
        if paused:
            self.driver.cancel()
        elif self.tabs.document is not None and self.tabs.document.request() is not None:
            self.driver.render(clear=False)

    # --- preferences ------------------------------------------------------------------------------------------------------------------
    def show_preferences(self) -> None:
        """*Preferences…*: edit, then apply and store."""
        from .preferences_dialog import PreferencesDialog
        dialog = PreferencesDialog(self, self.prefs)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_preferences(dialog.preferences())
            store_preferences(self._settings, self.prefs)

    def apply_preferences(self, prefs: FragPreferences) -> None:
        """Push `prefs` into every part that uses them (a changed build option marks the open tabs as needing a build)."""
        rebuild = prefs.compat_mode != self.prefs.compat_mode or prefs.move_main != self.prefs.move_main \
            or prefs.use_defines != self.prefs.use_defines or prefs.include_paths != self.prefs.include_paths
        self.prefs = prefs.copy()
        self.actions.auto_build.setChecked(prefs.auto_build)
        self.actions.save_easing.setChecked(prefs.save_easing)
        self.actions.draw_paths.setChecked(prefs.draw_paths)
        self.actions.occlude_paths.setChecked(prefs.occlude_paths)
        self.viewport.draw_paths = prefs.draw_paths
        self.viewport.set_occlusion(prefs.occlude_paths)
        self.viewport.traveling_wheel = prefs.traveling_wheel
        self.set_navigation(prefs.navigation)
        self.driver.refresh_ms = prefs.refresh_ms
        self.driver.interactive_scale = prefs.interactive_scale
        self.driver.gpu_load = prefs.gpu_load / 100.0
        self.files.autoload = prefs.autoload
        self.files.max_recent = prefs.max_recent
        self.log.max_rows = prefs.log_max_rows
        self.log.set_log_file(log_file_path(prefs) if prefs.log_to_file else None, prefs.log_file_max_kb * 1024)
        for tab in self.tabs.tabs:
            tab.editor.set_font_size(prefs.font_size)
        self.tabs.font_size = prefs.font_size
        self.set_editor_theme(prefs.editor_theme)
        self.parameters.set_mode(prefs.parameter_layout)
        self.sessions.set_interval(prefs.autosave_minutes)
        self.viewport.update()
        if rebuild:
            for tab in self.tabs.tabs:
                tab.document.set_needs_build(True)
            self._refresh_build_label()

    # --- persistence --------------------------------------------------------------------------------------------------------------------
    def _restore_state(self) -> None:
        s = self._settings
        geometry = s.value(f"{SETTINGS_GROUP}/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = s.value(f"{SETTINGS_GROUP}/state")
        if state is not None:
            self.restoreState(state)
        split = s.value(f"{SETTINGS_GROUP}/split")
        if split is not None:
            self.splitter.restoreState(split)
        self.subframe_spin.setValue(int(s.value(f"{SETTINGS_GROUP}/subframes", config.FRAG_DEFAULT_SUBFRAMES)))
        self.buffer_size.locked_to_window = s.value(f"{SETTINGS_GROUP}/buffer_locked", "true") in ("true", True, "True")
        self.buffer_size.width = int(s.value(f"{SETTINGS_GROUP}/buffer_width", 1280))
        self.buffer_size.height = int(s.value(f"{SETTINGS_GROUP}/buffer_height", 720))
        self.buffer_bar.refresh()
        self.actions.show_library.setChecked(not self.library_dock.isHidden())
        self.apply_preferences(self.prefs)
        thumbnails = s.value(f"{SETTINGS_GROUP}/thumbnails", "false") in ("true", True, "True")
        self.library_panel.set_thumbnail_view(thumbnails)
        self._set_thumbnail_view(thumbnails)
        self._restore_tabs()

    def _restore_tabs(self) -> None:
        """Reopen the files that were open last time (FragM does the same)."""
        paths = self._settings.value(f"{SETTINGS_GROUP}/open_files", [])
        if isinstance(paths, str):
            paths = [paths]
        for text in paths or []:
            path = Path(text)
            if path.is_file():
                self.files.open_path(path)
        current = int(self._settings.value(f"{SETTINGS_GROUP}/current_tab", 0))
        if 0 <= current < self.tabs.bar.count():
            self.tabs.bar.setCurrentIndex(current)

    def save_state(self) -> None:
        """Persist the layout and the options."""
        s = self._settings
        s.setValue(f"{SETTINGS_GROUP}/geometry", self.saveGeometry())
        s.setValue(f"{SETTINGS_GROUP}/state", self.saveState())
        s.setValue(f"{SETTINGS_GROUP}/split", self.splitter.saveState())
        s.setValue(f"{SETTINGS_GROUP}/subframes", self.subframe_spin.value())
        s.setValue(f"{SETTINGS_GROUP}/buffer_locked", self.buffer_size.locked_to_window)
        s.setValue(f"{SETTINGS_GROUP}/buffer_width", self.buffer_size.width)
        s.setValue(f"{SETTINGS_GROUP}/buffer_height", self.buffer_size.height)
        s.setValue(f"{SETTINGS_GROUP}/thumbnails", self.library_panel.thumbnails_shown)
        store_preferences(s, self.prefs)
        s.setValue(f"{SETTINGS_GROUP}/open_files", [str(t.document.path) for t in self.tabs.tabs if t.document.path is not None])
        s.setValue(f"{SETTINGS_GROUP}/current_tab", self.tabs.bar.currentIndex())

    # --- convenience (scripts and tests) ------------------------------------------------------------------------------------------------
    def open_text(self, text: str, path: Path | None = None) -> FragDocument:
        """A new tab with `text`."""
        return self.tabs.open_text(text, path)

    def log_message(self, level: str, text: str) -> None:
        self.log.add_message(Message(level, text))


def load_preferences(settings: QSettings) -> FragPreferences:
    """The stored preferences (defaults for anything missing)."""
    data = {}
    settings.beginGroup(PREFERENCES_GROUP)
    for key in settings.childKeys():
        data[key] = settings.value(key)
    settings.endGroup()
    return FragPreferences.from_dict(data)


def store_preferences(settings: QSettings, prefs: FragPreferences) -> None:
    """Persist `prefs` one key per field."""
    settings.beginGroup(PREFERENCES_GROUP)
    for key, value in prefs.to_dict().items():
        settings.setValue(key, value)
    settings.endGroup()


def log_file_path(prefs: FragPreferences) -> Path:
    """Where the log mirror goes (the cache folder when the preference is empty)."""
    if prefs.log_file:
        return Path(prefs.log_file)
    from ...formulas.loader import cache_dir
    return cache_dir() / DEFAULT_LOG_NAME


__all__ = ["FragmentsWindow", "WINDOW_TITLE", "load_preferences", "store_preferences"]
