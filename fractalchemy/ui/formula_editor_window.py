"""The Formula Editor window: write a formula (variation / plugin) and watch it work while you type.

Opened from *Windows ▸ Formula Editor* (`F10`) or the toolbar. A tool window of the main window, like the
Transform Editor: closing hides it, and what was being written is remembered between runs.

Layout: the *transform* toolbar (undo / redo, add a linear / spherical / formula transform, delete, flip,
variation preview, fit, the transform list) over the triangle canvas — the editor's own little flame, one
formula transform to begin with, with the variation preview on so the formula's effect is drawn on the
grid — and, beneath it, the *code* toolbar (new / open / save / save as / delete, edit helpers) and the
code editor with C highlighting. On the right: the live preview (the shared render service, so the GPU
when there is one), the gradient bar, the formula's variables and the list of every loaded formula.

The formula being edited is a `FormulaSession`: the text is compiled on the thread pool a moment after every
change and registered in the registry's scratch slot (`workbench.SCRATCH_NAME`), which is what the flame's
formula transforms refer to — so both the canvas preview and the rendered preview follow the code without
any registry entry of a real formula being touched. *Save* writes the `.c` file to the user's formulas
folder and registers the formula under its real name, so the Transform Editor can use it at once.

The gradient starts as a bright three-colour one. Clicking the bar hands it to the Gradient Library (which
recolours the main window's fractal too — one gradient everywhere) and from then on gradient edits made
there recolour this preview as well.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox, QSplitter,
                               QStatusBar, QVBoxLayout, QWidget)

from ..formulas import workbench as W
from ..fractal import triangles as T
from ..fractal import variations as V
from ..fractal.scene import Camera, Flame, XForm
from ..fractal.triangles import Triangle
from ..model import Gradient
from ..render.service import RenderService
from ..render.xform_preview import variation_preview
from ..widgets.find_bar import FindBar
from ..widgets.formula_code_editor import FormulaCodeEditor
from ..widgets.gradient_bar import GradientBar
from ..widgets.icons import formula_icon
from ..widgets.silent import blocked
from ..widgets.triangle_view import Hit, TriangleEntry, TriangleView, transform_color
from ..widgets.value_table import ValueRow
from .editor_context import EditorContext
from .editor_operations import FixedSteps, TransformOperations
from .editor_value_tabs import VariablesTab
from .formula_editor_actions import FormulaEditorActions
from .formula_list_panel import FormulaListPanel
from .formula_session import ORIGIN_NEW, ORIGIN_REGISTERED, FormulaSession
from .fractal_document import FractalDocument
from .live_preview import DEFAULT_QUALITY, LivePreview, quality_level

WINDOW_TITLE = "Formula Editor"
SETTINGS_GROUP = "formula_editor"
FLAME_NAME = "Formula Editor"
PREVIEW_WIDTH, PREVIEW_HEIGHT = 400, 300          # the flame's own size: four units across, as Apophysis starts
SIDE_PANEL_WIDTH = 400
CODE_HEIGHT = 300
VAR_PREVIEW_RANGE, VAR_PREVIEW_DEPTH, VAR_PREVIEW_DENSITY = 2, 1, 2
DEFAULT_GRADIENT_COLORS = ((255, 210, 48), (41, 217, 255), (255, 63, 181))   # bright yellow → cyan → magenta
TRANSFORM_COLORS = (0.0, 0.5, 1.0, 0.25, 0.75)   # palette positions handed out to new transforms in turn
FORMULA_FILTER = "Formula sources (*.c);;All files (*)"
OK_STYLE = "color: #2e7d32;"
ERROR_STYLE = "color: #c62828;"


def default_gradient() -> Gradient:
    """The bright three-colour gradient the editor starts with."""
    return Gradient.from_colors("Formula Editor", list(DEFAULT_GRADIENT_COLORS))


def default_flame() -> Flame:
    """One formula transform on the reference triangle, the default camera and the default gradient."""
    flame = Flame(FLAME_NAME, [W.formula_xform("formula", TRANSFORM_COLORS[0])])
    flame.camera = Camera(scale=PREVIEW_WIDTH / 4.0, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT)
    flame.set_gradient(default_gradient())
    return flame


class FormulaVariablesTab(VariablesTab):
    """The Variables tab with the scratch slot listed under the formula's own name."""

    def __init__(self, context: EditorContext, session: FormulaSession, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.session = session
        self.show_all.hide()

    def rows(self) -> list[ValueRow]:
        """The selected transform's parameters, the formula's own under its real name; values left behind by a formula
        edited earlier (their names no longer declared) are not listed."""
        name = self.session.name or "formula"
        return [replace(row, info=name) if row.info == W.SCRATCH_NAME else row for row in super().rows() if row.info]


class FormulaEditorWindow(QMainWindow):
    """The Formula Editor (see the module docstring)."""

    def __init__(self, service: RenderService, gradient_window=None, parent: QWidget | None = None, settings: QSettings | None = None,
                 user_dir: Path | None = None):
        """Args:
            service: The shared render service (the preview renders through it).
            gradient_window: The Gradient Library window, for choosing a gradient (None: the bar does nothing).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where the draft, layout and preferences persist.
            user_dir: Folder saved formulas go to (the per-user formulas folder by default).
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(formula_icon())
        self._settings = settings if settings is not None else QSettings()
        self._gradient_window = gradient_window
        self._gradient = default_gradient()        # the preview's gradient as editable nodes (the flame holds its palette)
        self._gradient_linked = False
        self._loading_text = False
        self._needs_fit = True
        self.document = FractalDocument(self)
        self.context = EditorContext(self.document, self)
        self.session = FormulaSession(self, user_dir)
        self.view = TriangleView(self)
        self.operations = TransformOperations(self.context, self.view.pivot, FixedSteps())
        self.preview = LivePreview(self, flame_provider=self._render_flame, name="formula-preview")
        self.preview.placeholder = "No formula"
        self.preview.bind(None, service)
        self.code = FormulaCodeEditor(self)
        self.find_bar = FindBar(self.code, self)
        self.formula_list = FormulaListPanel(self, user_dir)
        self.gradient_bar = GradientBar("Gradient", self)
        self.variables_tab = FormulaVariablesTab(self.context, self.session, self)
        self.transform_combo = QComboBox(self)
        self.source_label = QLabel(self)
        self.compile_label = QLabel(self)
        self.coords_label = QLabel(self)
        self.zoom_label = QLabel(self)
        self.info_label = QLabel(self)
        self.actions = FormulaEditorActions(self)
        self.transform_toolbar, self.code_toolbar = self.actions.install(self)
        self._build()
        self._connect()
        self.document.replace(default_flame())
        self._load_settings()

    # --- construction ---------------------------------------------------------------------------------------
    def _build(self) -> None:
        self.transform_toolbar.addWidget(QLabel(" Transform: ", self))
        self.transform_combo.setToolTip("The transform being edited (or click a triangle)")
        self.transform_combo.setMinimumWidth(150)
        self.transform_toolbar.addWidget(self.transform_combo)
        self.view.setToolTip("Drag triangles (corners move, edges rotate / scale); right-click for more; V toggles the variation preview")
        self.source_label.setEnabled(False)
        self.compile_label.setWordWrap(True)
        self.compile_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.code_toolbar.addWidget(self.source_label)
        code_box = QWidget(self)
        code_layout = QVBoxLayout(code_box)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.setSpacing(0)
        code_layout.addWidget(self.code_toolbar)
        code_layout.addWidget(self.find_bar)
        code_layout.addWidget(self.code, 1)
        code_layout.addWidget(self.compile_label)
        left = QSplitter(Qt.Orientation.Vertical, self)
        left.addWidget(self.view)
        left.addWidget(code_box)
        left.setStretchFactor(0, 1)
        left.setStretchFactor(1, 1)
        left.setSizes([420, CODE_HEIGHT])
        self.vertical_splitter = left
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(left)
        splitter.addWidget(self._side_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([820, SIDE_PANEL_WIDTH])
        self.splitter = splitter
        self.setCentralWidget(splitter)
        status = QStatusBar(self)
        self.coords_label.setMinimumWidth(190)
        self.zoom_label.setMinimumWidth(90)
        status.addWidget(self.coords_label)
        status.addWidget(self.zoom_label)
        status.addWidget(self.info_label, 1)
        self.setStatusBar(status)
        self.resize(1280, 820)

    def _side_panel(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 0, 0)
        preview_row = QHBoxLayout()
        preview_row.addStretch(1)
        preview_row.addWidget(self.preview)
        preview_row.addStretch(1)
        layout.addLayout(preview_row)
        self.gradient_bar.setToolTip("The preview's gradient — click to pick or edit one in the Gradient Library "
                                     "(the main window follows it too)")
        layout.addWidget(self.gradient_bar)
        lists = QSplitter(Qt.Orientation.Vertical, panel)
        variables = QWidget(lists)
        variables_layout = QVBoxLayout(variables)
        variables_layout.setContentsMargins(0, 0, 0, 0)
        variables_layout.addWidget(QLabel("Variables", variables))
        variables_layout.addWidget(self.variables_tab, 1)
        formulas = QWidget(lists)
        formulas_layout = QVBoxLayout(formulas)
        formulas_layout.setContentsMargins(0, 0, 0, 0)
        formulas_layout.addWidget(QLabel("Formulas", formulas))
        formulas_layout.addWidget(self.formula_list, 1)
        lists.addWidget(variables)
        lists.addWidget(formulas)
        lists.setStretchFactor(0, 0)
        lists.setStretchFactor(1, 1)
        lists.setSizes([160, 360])
        layout.addWidget(lists, 1)
        panel.setMinimumWidth(SIDE_PANEL_WIDTH)
        return panel

    def _connect(self) -> None:
        doc, view, session = self.document, self.view, self.session
        doc.flame_replaced.connect(self._on_flame_replaced)
        doc.flame_restored.connect(self.rebuild)
        doc.transforms_changed.connect(self.rebuild)
        doc.xform_changed.connect(self._on_xform_changed)
        doc.palette_changed.connect(self._on_palette_changed)
        doc.undo_changed.connect(self._on_undo_changed)
        self.context.selection_changed.connect(self._on_selection_changed)
        view.selected.connect(self.context.select)
        view.triangle_dragged.connect(self._on_triangle_dragged)
        view.drag_finished.connect(self._on_drag_finished)
        view.triangle_command.connect(self._on_view_command)
        view.context_menu.connect(lambda pos, hit: self.actions.show_context_menu(self, pos, hit is not None))
        view.status.connect(self.coords_label.setText)
        view.view_changed.connect(self._show_zoom)
        view.hover_changed.connect(self._on_hover)
        self.transform_combo.currentIndexChanged.connect(self._on_combo_changed)
        self.preview.quality_changed.connect(lambda q: self._settings.setValue(f"{SETTINGS_GROUP}/preview_quality", q))
        session.text_loaded.connect(self._show_session_text)
        session.compiled.connect(self._on_compiled)
        session.failed.connect(self._on_compile_failed)
        session.state_changed.connect(self._refresh_title)
        session.formulas_changed.connect(self._on_formulas_changed)
        self.code.textChanged.connect(self._on_code_changed)
        self.code.find_requested.connect(self.find_bar.open)
        self.code.goto_requested.connect(self.goto_line)
        self.code.save_requested.connect(lambda as_new: self.save_formula_as() if as_new else self.save_formula())
        self.formula_list.formula_chosen.connect(self.load_formula)
        self.formula_list.new_requested.connect(self.new_formula)
        self.gradient_bar.clicked.connect(self.choose_gradient)
        if self._gradient_window is not None:
            gradient_document = self._gradient_window.document
            gradient_document.gradient_replaced.connect(self._on_library_gradient_changed)
            gradient_document.gradient_changed.connect(self._on_library_gradient_changed)
            gradient_document.stop_changed.connect(self._on_library_gradient_changed)

    def _load_settings(self) -> None:
        s = self._settings
        try:
            self.preview.level = quality_level(s.value(f"{SETTINGS_GROUP}/preview_quality", DEFAULT_QUALITY.name))
            for action, key, default in ((self.actions.var_preview, "var_preview", "true"), (self.actions.helpers, "helpers", "true")):
                action.setChecked(s.value(f"{SETTINGS_GROUP}/{key}", default) in ("true", True))
            geometry = s.value(f"{SETTINGS_GROUP}/geometry")
            if geometry is not None:
                self.restoreGeometry(geometry)
            for splitter, key in ((self.splitter, "split"), (self.vertical_splitter, "vsplit")):
                state = s.value(f"{SETTINGS_GROUP}/{key}")
                if state is not None:
                    splitter.restoreState(state)
        except (TypeError, ValueError):
            pass
        draft = s.value(f"{SETTINGS_GROUP}/draft_text", None)
        if isinstance(draft, str) and draft.strip():
            self.session.restore(draft, s.value(f"{SETTINGS_GROUP}/draft_name", "") or "", s.value(f"{SETTINGS_GROUP}/draft_path", "") or "",
                                 s.value(f"{SETTINGS_GROUP}/draft_origin", "") or "",
                                 s.value(f"{SETTINGS_GROUP}/draft_modified", "false") in ("true", True, "True"))
        else:
            self.session.load_blank()

    def save_state(self) -> None:
        """Persist the draft, the layout and the view options."""
        s = self._settings
        draft = self.session.draft()
        for key, value in draft.items():
            s.setValue(f"{SETTINGS_GROUP}/draft_{key}", value)
        s.setValue(f"{SETTINGS_GROUP}/geometry", self.saveGeometry())
        s.setValue(f"{SETTINGS_GROUP}/split", self.splitter.saveState())
        s.setValue(f"{SETTINGS_GROUP}/vsplit", self.vertical_splitter.saveState())
        s.setValue(f"{SETTINGS_GROUP}/var_preview", self.actions.var_preview.isChecked())
        s.setValue(f"{SETTINGS_GROUP}/helpers", self.actions.helpers.isChecked())

    # --- window management ----------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show the window (restoring it if minimised) and give the code editor the focus."""
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()
        self.preview.request()
        self.code.setFocus()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._needs_fit:
            self._needs_fit = False
            QTimer.singleShot(0, self.view.fit)     # once the canvas has its real size

    def hideEvent(self, event) -> None:
        self.save_state()
        super().hideEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.save_state()
        super().closeEvent(event)

    # --- the editor's flame ----------------------------------------------------------------------------------
    def _render_flame(self) -> Flame | None:
        """What the preview renders: the flame with every formula transform prepared (the scratch slot filled)."""
        flame = self.document.flame
        if flame is None:
            return None
        self.session.ensure_registered()
        if self.session.variation is None and all(x.variations.keys() == {W.SCRATCH_NAME} for x in flame.xforms):
            return None                      # an empty editor and nothing else to show: the placeholder, not a dot
        return W.prepared_flame(flame, self.session.variation)

    def _new_color(self) -> float:
        flame = self.document.flame
        return TRANSFORM_COLORS[(len(flame.xforms) if flame else 0) % len(TRANSFORM_COLORS)]

    def _add(self, xform: XForm) -> None:
        index = self.document.add_xform(xform)
        if index is not None:
            self.context.select(index)
            self.view.setFocus()

    def add_linear(self) -> None:
        """Add a transform with `linear = 1` on the reference triangle."""
        self._add(XForm(weight=1.0, color=self._new_color(), color_speed=0.5, variations={"linear": 1.0}, name="linear"))

    def add_spherical(self) -> None:
        """Add a transform with `spherical = 1` on the reference triangle."""
        self._add(XForm(weight=1.0, color=self._new_color(), color_speed=0.5, variations={"spherical": 1.0}, name="spherical"))

    def add_formula(self) -> None:
        """Add a transform running the formula being edited."""
        self._add(W.formula_xform("formula", self._new_color()))

    def _set_variations(self, variations: dict[str, float], name: str) -> None:
        key = self.context.selected
        if self.context.xform() is None:
            return

        def apply(x: XForm) -> None:
            x.variations = dict(variations)
            x.name = name
        self.document.edit_xform(key, f"set-variations:{key}:{name}", apply, "variations")

    def use_formula(self) -> None:
        """Replace the selected transform's variations by the formula being edited."""
        self._set_variations({W.SCRATCH_NAME: 1.0}, "formula")

    def make_linear(self) -> None:
        """Replace the selected transform's variations by `linear = 1`."""
        self._set_variations({"linear": 1.0}, "linear")

    def make_spherical(self) -> None:
        """Replace the selected transform's variations by `spherical = 1`."""
        self._set_variations({"spherical": 1.0}, "spherical")

    def reset_flame(self) -> None:
        """Back to one formula transform on the reference triangle (the gradient is kept; undoable)."""
        flame = self.document.flame
        if flame is None:
            return
        new = default_flame()
        new.palette = list(flame.palette)
        self.document.replace_flame_parameters(new, "reset-flame")
        self.context.select(0)

    # --- view options ----------------------------------------------------------------------------------------
    def set_variation_preview(self, on: bool) -> None:
        """Show (or hide) the grid of points sent through the selected transform."""
        self.update_variation_preview()
        self.info_label.setText("Variation preview: a grid of points through the selected transform" if on else "")

    def set_helpers(self, on: bool) -> None:
        """Show the pivot cross-hair and rotation / scale guides while dragging."""
        self.view.show_helpers = on
        self.view.update()

    def update_variation_preview(self) -> None:
        """Recompute the canvas's variation preview for the selected transform (or hide it)."""
        xform = self.context.xform()
        if not self.actions.var_preview.isChecked() or xform is None or (W.uses_scratch(xform) and self.session.variation is None):
            self.view.set_variation_preview(None)      # (an empty editor: nothing to send the grid through)
            return
        self.session.ensure_registered()
        try:
            points = variation_preview(W.prepared_xform(xform, self.session.variation), VAR_PREVIEW_RANGE, VAR_PREVIEW_DENSITY,
                                       VAR_PREVIEW_DEPTH)
        except Exception as exc:  # noqa: BLE001 - a formula that cannot run on this input: show nothing, say why
            self.view.set_variation_preview(None)
            self.info_label.setText(f"Variation preview unavailable: {exc}")
            return
        points[:, 1] = -points[:, 1]          # fractal y (down) → editor y (up)
        self.view.set_variation_preview(points, transform_color(self.context.selected))

    # --- document → widgets ----------------------------------------------------------------------------------
    def _on_flame_replaced(self) -> None:
        self.context.reset_selection()
        self.rebuild()
        self.gradient_bar.set_palette(self.document.flame.palette if self.document.flame else [])

    def rebuild(self) -> None:
        """Everything from the document: the transform list, the triangles, the variables, the actions and the preview."""
        self.context.ensure_valid_selection()
        self._fill_combo()
        self._refresh_view()
        self.variables_tab.refresh()
        self._sync_selection_actions()
        self._on_undo_changed(self.document.can_undo, self.document.can_redo)
        self.update_variation_preview()
        self.preview.request()

    def _sync_selection_actions(self) -> None:
        flame = self.document.flame
        has_selection = self.context.xform() is not None
        for action in self.actions.selection_dependent:
            action.setEnabled(has_selection)
        self.actions.delete.setEnabled(has_selection and flame is not None and len(flame.xforms) > 1)

    def _on_xform_changed(self, index: object, what: str) -> None:
        """Refresh only what the change touched (a drag reports 'affine' on every mouse move)."""
        if what != "params":
            self._refresh_view()
        if index == self.context.selected and what in ("variations", "params", "all"):
            self.variables_tab.refresh()
        if what in ("fields", "variations", "all"):
            self._fill_combo()
        if index == self.context.selected:
            self.update_variation_preview()
        self.preview.request()

    def _on_palette_changed(self) -> None:
        self.gradient_bar.set_palette(self.document.flame.palette if self.document.flame else [])
        self.preview.request()

    def _on_undo_changed(self, can_undo: bool, can_redo: bool) -> None:
        self.actions.undo.setEnabled(can_undo)
        self.actions.redo.setEnabled(can_redo)

    def _on_selection_changed(self, key: object) -> None:
        self.view.select(key)
        self.variables_tab.refresh()
        with blocked(self.transform_combo):
            keys = self.context.keys()
            if key in keys:
                self.transform_combo.setCurrentIndex(keys.index(key))
        self._sync_selection_actions()
        self.update_variation_preview()
        self.view.update()

    def _label(self, key: object, xform: XForm) -> str:
        return f"{key + 1}" + (f" · {xform.name}" if xform.name else "")

    def _refresh_view(self) -> None:
        entries: list[TriangleEntry] = []
        for key in self.context.keys():
            xform = self.document.xform(key)
            hint = tuple(f"{self._variation_label(name)} = {weight:g}" for name, weight in xform.variations.items())
            entries.append(TriangleEntry(key, T.affine_to_triangle(xform.coefs), None, transform_color(key), self._label(key, xform), hint))
        self.view.set_entries(entries, self.context.selected)

    def _variation_label(self, name: str) -> str:
        return (self.session.name or "formula") if name == W.SCRATCH_NAME else name

    def _fill_combo(self) -> None:
        with blocked(self.transform_combo):
            self.transform_combo.clear()
            keys = self.context.keys()
            for key in keys:
                xform = self.document.xform(key)
                pixmap = QPixmap(12, 12)
                pixmap.fill(transform_color(key))
                self.transform_combo.addItem(QIcon(pixmap), f"{key + 1}" + (f" - {xform.name}" if xform.name else ""))
            if self.context.selected in keys:
                self.transform_combo.setCurrentIndex(keys.index(self.context.selected))
        self.transform_combo.setEnabled(self.transform_combo.count() > 0)

    def _show_zoom(self) -> None:
        self.zoom_label.setText(f"Zoom: {self.view.pixels_per_unit / 50.0:.2f}")

    def _on_hover(self, hit: Hit | None) -> None:
        xform = self.document.xform(hit.key) if hit is not None else None
        if xform is None:
            self.info_label.setText("")
            return
        self.info_label.setText(f"Transform {self._label(hit.key, xform)}: "
                                + ", ".join(f"{self._variation_label(n)} {w:g}" for n, w in xform.variations.items()))

    # --- widgets → document ----------------------------------------------------------------------------------
    def _on_combo_changed(self, index: int) -> None:
        keys = self.context.keys()
        if 0 <= index < len(keys):
            self.context.select(keys[index])

    def _on_triangle_dragged(self, key: object, triangle: Triangle) -> None:
        self.context.set_triangle(key, triangle, sticky=True)

    def _on_drag_finished(self, key: object, changed: bool) -> None:
        if changed:
            self.operations.after_affine_edit(key, live=False)

    def _on_view_command(self, key: object, command: str) -> None:
        """A key or double-click on the canvas: a triangle operation, or one of the window's toggles."""
        a = self.actions
        toggles = {
            "duplicate": self.operations.duplicate, "delete": self.operations.delete,
            "toggle-var-preview": lambda: a.var_preview.setChecked(not a.var_preview.isChecked()),
        }
        if command in toggles:
            toggles[command]()
        else:
            self.operations.run_command(command, key)

    # --- the formula: session ↔ code editor -----------------------------------------------------------------
    def _show_session_text(self) -> None:
        self._loading_text = True
        try:
            self.code.set_text(self.session.text)
        finally:
            self._loading_text = False
        if self.session.origin != ORIGIN_NEW:
            self._show_calc_function()       # past the licence header straight to the maths
        self.formula_list.select(self.session.name if self.session.origin != ORIGIN_NEW else None)
        self._show_compile_state()
        self.variables_tab.refresh()
        self._refresh_view()
        self.update_variation_preview()
        self.preview.request()

    def _show_calc_function(self) -> None:
        """Scroll the code so `PluginVarCalc` is in view (the cursor goes to its line, the focus stays where it is)."""
        for number, line in enumerate(self.session.text.splitlines(), 1):
            if "PluginVarCalc" in line and "(" in line:
                focus = QApplication.focusWidget()
                self.code.goto_line(number)
                if focus is not None and focus is not self.code:
                    focus.setFocus()
                return

    def _on_formulas_changed(self) -> None:
        """A formula was saved or deleted: the list is stale, and the saved one is the current row."""
        self.formula_list.populate()
        self.formula_list.select(self.session.name if self.session.origin != ORIGIN_NEW else None)

    def _on_code_changed(self) -> None:
        if not self._loading_text:
            self.session.set_text(self.code.text())
            self.compile_label.setText("Compiling…")
            self.compile_label.setStyleSheet("")

    def _on_compiled(self, var: V.Variation) -> None:
        self.code.set_error_line(None)
        self._show_compile_state()
        self.variables_tab.refresh()
        self._refresh_view()
        self.update_variation_preview()
        self.preview.request()

    def _on_compile_failed(self, message: str, line: object) -> None:
        self._show_compile_state()
        self.code.set_error_line(line)
        if not message:                   # an empty editor: nothing in the scratch slot either
            self.update_variation_preview()
            self.preview.request()

    def _show_compile_state(self) -> None:
        session = self.session
        if session.error:
            where = f"  (line {session.error_line})" if session.error_line and f"line {session.error_line}" not in session.error else ""
            self.compile_label.setText(f"✗ {session.error}{where}")
            self.compile_label.setStyleSheet(ERROR_STYLE)
        elif session.variation is not None:
            var = session.variation
            kind = {V.PRE: "pre", V.POST: "post"}.get(var.kind, "normal")
            facts = [kind] + [tag for flag, tag in ((var.z == V.Z_FORMULA, "3D"), (var.dc, "direct colour"), (var.random, "random")) if flag]
            count = len(var.params)
            self.compile_label.setText(f"✓ {session.name} — {', '.join(facts)}; {count} variable{'s' if count != 1 else ''}")
            self.compile_label.setStyleSheet(OK_STYLE)
        else:
            self.compile_label.setText("No formula — pick one from the list, or start a new one")
            self.compile_label.setStyleSheet("")

    def _refresh_title(self) -> None:
        session = self.session
        name = session.name or "untitled"
        self.setWindowTitle(f"{WINDOW_TITLE} — {name}[*]")
        self.setWindowModified(session.modified)
        if session.path is not None:
            where = str(session.path) if session.own_file is not None else f"{session.path.name}  (bundled — Save makes your own copy)"
        elif session.origin == ORIGIN_REGISTERED:
            where = "native built-in — Save makes a formula of your own"
        else:
            where = "not saved yet"
        self.source_label.setText(f"  {name}  —  {where}")
        self.actions.delete_formula.setEnabled(session.own_file is not None)
        self.actions.save_formula.setEnabled(bool(session.text.strip()))
        self.actions.save_as_formula.setEnabled(bool(session.text.strip()))
        if session.origin == ORIGIN_NEW:
            self.formula_list.select(None)
        self._show_compile_state()

    # --- formula files ---------------------------------------------------------------------------------------
    def confirm_discard(self) -> bool:
        """Ask about unsaved code before replacing it; False if the caller should abort."""
        if not self.session.modified or not self.session.text.strip():
            return True
        buttons = QMessageBox.StandardButton
        answer = QMessageBox.question(self, WINDOW_TITLE, f"'{self.session.name or 'the formula'}' has unsaved changes.",
                                      buttons.Save | buttons.Discard | buttons.Cancel, buttons.Save)
        if answer == buttons.Save:
            return self.save_formula()
        return answer == buttons.Discard

    def load_formula(self, name: str) -> bool:
        """Load a registered formula's code into the editor (its real self in the previews until the text changes)."""
        if name == self.session.name and self.session.origin == ORIGIN_REGISTERED and not self.session.modified:
            return True
        if not self.confirm_discard():
            self.formula_list.select(self.session.name if self.session.origin == ORIGIN_REGISTERED else None)
            return False
        if not self.session.load_registered(name):
            self._message(f"{name}: no such formula")
            return False
        self._message(f"Loaded {name}")
        return True

    def new_formula(self) -> bool:
        """Start a new formula from the boilerplate (with a name no formula has yet)."""
        if not self.confirm_discard():
            return False
        self.session.load_new(self._unique_name(W.DEFAULT_NEW_NAME))
        self.code.setFocus()
        self._message("New formula from the template — rename it in APO_PLUGIN(\"…\") and press Save when it does what you want")
        return True

    def _unique_name(self, base: str) -> str:
        """`base`, or `base2`, `base3` … — a name no registered formula or file in the user's folder has."""
        taken = set(dict.keys(V.REGISTRY))
        if self.session.folder.is_dir():
            taken |= {p.stem for p in self.session.folder.glob("*.c")}
        name, n = base, 1
        while name in taken:
            n += 1
            name = f"{base}{n}"
        return name

    def open_formula(self) -> bool:
        """Load a `.c` file from anywhere."""
        if not self.confirm_discard():
            return False
        start = str(self.session.own_file.parent if self.session.own_file else self.session.folder)
        path, _ = QFileDialog.getOpenFileName(self, "Open formula", start, FORMULA_FILTER)
        if not path:
            return False
        return self.open_path(Path(path))

    def open_path(self, path: Path) -> bool:
        """Load the formula file `path`; False (with a message) if it cannot be read."""
        try:
            self.session.load_file(path)
        except OSError as exc:
            self._report_error("Cannot open formula", exc)
            return False
        self._message(f"Opened {path}")
        return True

    def save_formula(self, path: Path | None = None) -> bool:
        """Save to `path`, the formula's own file, or the user's formulas folder; the formula is registered at once."""
        session = self.session
        if not session.text.strip():
            self._message("Nothing to save")
            return False
        target = path or session.own_file or session.default_path()
        if path is None and session.own_file is None and target.exists() and not self._confirm(f"{target.name} exists in your formulas folder. Overwrite it?"):
            return False
        shadowed = session.overrides_bundled()
        if shadowed and not self._confirm(f"A bundled formula called '{session.name}' exists ({shadowed}).\n"
                                          "Your file will take its place whenever Fractalchemy runs. Continue?"):
            return False
        try:
            written = session.save(target)
        except OSError as exc:
            self._report_error("Cannot save formula", exc)
            return False
        note = "" if session.error is None else " — it does not compile yet, so it will be skipped at start-up"
        self._message(f"Saved {written}{note}")
        return True

    def save_formula_as(self) -> bool:
        """Save under a file name of your choosing."""
        if not self.session.text.strip():
            self._message("Nothing to save")
            return False
        start = self.session.own_file or self.session.default_path()
        path, _ = QFileDialog.getSaveFileName(self, "Save formula as", str(start), FORMULA_FILTER)
        if not path:
            return False
        path = Path(path)
        return self.save_formula(path.with_suffix(".c") if not path.suffix else path)

    def delete_formula(self) -> bool:
        """Delete the formula's file (yours only) and take it out of the registry; the code stays in the editor."""
        path = self.session.own_file
        if path is None:
            self._message("Only formulas saved in your formulas folder can be deleted")
            return False
        if not self._confirm(f"Delete {path}?\nThe code stays in the editor until you load another formula."):
            return False
        try:
            self.session.delete()
        except OSError as exc:
            self._report_error("Cannot delete formula", exc)
            return False
        self._message(f"Deleted {path}")
        return True

    def reload_formulas(self) -> None:
        """Re-scan the formula folders so formulas added since start-up appear in the list."""
        from ..formulas import load_all
        report = load_all(force=True)
        self.session.ensure_registered()
        self.formula_list.populate()
        self.variables_tab.refresh()
        self.session.formulas_changed.emit()
        self._message(report.summary())

    def goto_line(self) -> None:
        """Ask for a line number and jump there."""
        line, ok = QInputDialog.getInt(self, "Go to line", "Line:", self.code.line_column()[0], 1, max(1, self.code.blockCount()))
        if ok:
            self.code.goto_line(line)

    # --- gradient --------------------------------------------------------------------------------------------
    @property
    def gradient(self) -> Gradient:
        """The preview's gradient: the bright default, or what the Gradient Library last gave it."""
        return self._gradient

    @property
    def gradient_linked(self) -> bool:
        """True once the gradient is shared with the Gradient Library (after the bar was clicked)."""
        return self._gradient_linked

    def choose_gradient(self) -> None:
        """Hand the preview's gradient to the Gradient Library and open it; from now on its edits recolour this preview."""
        window = self._gradient_window
        if window is None:
            self._message("No Gradient Library to choose from")
            return
        if not self._gradient_linked:
            if window.document.gradient.sample(16) != self._gradient.sample(16):
                if not window.files.confirm_discard():
                    return
                window.files.show_gradient(self._gradient.copy())
            self._gradient_linked = True
        window.bring_to_front()

    def _on_library_gradient_changed(self, *_args) -> None:
        if self._gradient_linked and self._gradient_window is not None:
            gradient = self._gradient_window.document.gradient
            if gradient.stops:
                self._gradient = gradient.copy()
                self.document.set_gradient(gradient)

    # --- messages --------------------------------------------------------------------------------------------
    def _message(self, text: str, ms: int = 6000) -> None:
        self.statusBar().showMessage(text, ms)

    def _confirm(self, question: str) -> bool:
        return QMessageBox.question(self, WINDOW_TITLE, question) == QMessageBox.StandardButton.Yes

    def _report_error(self, title: str, exc: Exception) -> None:
        self._message(f"{title}: {exc}")
        QMessageBox.warning(self, title, str(exc))


__all__ = ["FormulaEditorWindow", "default_flame", "default_gradient", "WINDOW_TITLE"]
