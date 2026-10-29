"""The Formula Editor window: write a formula (variation / plugin) and watch it work while you type.

Opened from *Windows ▸ Formula Editor* (`F10`) or the toolbar. A tool window of the main window, like the
Transform Editor: closing hides it, and what was being written is remembered between runs.

Layout: the *transform* toolbar (undo / redo, add a linear / spherical / formula transform, delete, flip,
variation preview, compare, fit, the test rigs, the transform list) over the triangle canvas — the editor's
own little flame, one formula transform to begin with, with the variation preview on so the formula's effect
is drawn on the grid — and, beneath it, the *code* toolbar (new from a template, open, save, save as, delete,
edit helpers, insert variable, compile, drawer) and the code editor with C highlighting and completion. The
side column holds the live preview (the shared render service, so the GPU when there is one), the *compare*
preview, the gradient bar with its presets, the variation-preview options, the variables with their tools
and the list of every loaded formula. A collapsible drawer on the right has the dialect reference, the
compiler's output and the point probe / engine check.

The formula being edited is a `FormulaSession`: the text is compiled on the thread pool a moment after every
change and registered in the registry's scratch slot (`workbench.SCRATCH_NAME`), which is what the flame's
formula transforms refer to — so both the canvas preview and the rendered preview follow the code without
any registry entry of a real formula being touched. *Save* writes the `.c` file to the user's formulas
folder and registers the formula under its real name. Bundled and built-in formulas are read-only: a formula
carrying one of their names cannot be saved — *Duplicate as my own* (or the prompt on Save) renames it first.

The gradient starts as a bright three-colour one. Clicking the bar hands it to the Gradient Library (which
recolours the main window's fractal too — one gradient everywhere) and from then on gradient edits made
there recolour this preview as well; the presets button beside it picks a bright gradient without the library.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

import numpy as np
from PySide6.QtCore import QFileSystemWatcher, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox, QSplitter,
                               QStatusBar, QVBoxLayout, QWidget)

from ..formulas import authoring as A, loader, workbench as W
from ..fractal import triangles as T
from ..fractal import variations as V
from ..fractal.scene import Flame, XForm
from ..fractal.triangles import Triangle
from ..model import Gradient
from ..render.service import RenderService
from ..render.settings import RenderStats
from ..render.xform_preview import preview_grid, variation_preview
from ..widgets.collapsible_section import CollapsibleSection
from ..widgets.collapsible_splitter import CollapsibleSplitter
from ..widgets.find_bar import FindBar
from ..widgets.formula_code_editor import FormulaCodeEditor
from ..widgets.gradient_bar import GradientBar
from ..widgets.icons import formula_icon
from ..widgets.silent import blocked
from ..widgets.triangle_view import Hit, TriangleEntry, TriangleView, transform_color
from .editor_context import EditorContext
from .editor_operations import FixedSteps, TransformOperations
from .formula_drawer import FormulaDrawer
from .formula_editor_actions import FormulaEditorActions
from .formula_editor_panels import GradientPresetsButton, PreviewOptions, VariableDialog, VariableTools
from .formula_list_panel import FormulaListPanel
from .formula_session import ORIGIN_FILE, ORIGIN_NEW, ORIGIN_REGISTERED, FormulaNameTaken, FormulaSession
from .fractal_document import FractalDocument
from .live_preview import DEFAULT_QUALITY, LivePreview, quality_level

WINDOW_TITLE = "Formula Editor"
SETTINGS_GROUP = "formula_editor"
SIDE_PANEL_WIDTH = 400
DRAWER_WIDTH = 380
CODE_HEIGHT = 300
RECENT_LIMIT = 12
DEFAULT_GRADIENT = "Yellow · cyan · magenta"
FORMULA_FILTER = "Formula sources (*.c);;All files (*)"
OK_STYLE = "color: #2e7d32;"
ERROR_STYLE = "color: #c62828;"


def default_gradient() -> Gradient:
    """The bright three-colour gradient the editor starts with."""
    return A.preset_gradient(DEFAULT_GRADIENT)


def default_flame() -> Flame:
    """One formula transform on the reference triangle, the default camera and the default gradient."""
    flame = A.test_rig("Formula alone")
    flame.set_gradient(default_gradient())
    return flame


class FormulaEditorWindow(QMainWindow):
    """The Formula Editor (see the module docstring).

    Signals:
        flame_sent(object): *Send to the main window*: a `Flame` for the main window to show.
    """
    flame_sent = Signal(object)

    def __init__(self, service: RenderService, gradient_window=None, parent: QWidget | None = None, settings: QSettings | None = None,
                 user_dir: Path | None = None, flame_source: Callable[[], Flame | None] | None = None):
        """Args:
            service: The shared render service (the previews render through it).
            gradient_window: The Gradient Library window, for choosing a gradient (None: the bar does nothing).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where the draft, layout and preferences persist.
            user_dir: Folder saved formulas go to (the per-user formulas folder by default).
            flame_source: Returns the main window's fractal, for *Use the main window's fractal* (None: disabled).
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(formula_icon())
        self._settings = settings if settings is not None else QSettings()
        self._gradient_window = gradient_window
        self._flame_source = flame_source
        self._gradient = default_gradient()        # the preview's gradient as editable nodes (the flame holds its palette)
        self._gradient_linked = False
        self._loading_text = False
        self._needs_fit = True
        self._recent: list[str] = []              # "registered:name" / "file:path", newest first
        self._file_stamps: dict[Path, float] = {}
        self.document = FractalDocument(self)
        self.context = EditorContext(self.document, self)
        self.session = FormulaSession(self, user_dir)
        self.view = TriangleView(self)
        self.operations = TransformOperations(self.context, self.view.pivot, FixedSteps())
        self.preview = LivePreview(self, flame_provider=self._render_flame, name="formula-preview")
        self.preview.placeholder = "No formula"
        self.preview.bind(None, service)
        self.original_preview = LivePreview(self, flame_provider=self._original_flame, name="formula-original")
        self.original_preview.placeholder = "No original to compare with"
        self.original_preview.setToolTip("The formula as it was before the edits (the registered one)")
        self.original_preview.bind(None, service)
        self.original_preview.hide()
        self.code = FormulaCodeEditor(self)
        self.find_bar = FindBar(self.code, self)
        self.formula_list = FormulaListPanel(self, user_dir)
        self.gradient_bar = GradientBar("Gradient", self)
        self.gradient_presets = GradientPresetsButton(self)
        self.preview_options = PreviewOptions(self)
        self.variables = VariableTools(self.context, self.session, self)
        self.drawer = FormulaDrawer(self.session, self._selected_params, self)
        self.transform_combo = QComboBox(self)
        self.source_label = QLabel(self)
        self.compile_label = QLabel(self)
        self.coords_label = QLabel(self)
        self.zoom_label = QLabel(self)
        self.info_label = QLabel(self)
        self.side_panel: QWidget | None = None
        self.actions = FormulaEditorActions(self)
        self.transform_toolbar, self.code_toolbar = self.actions.install(self)
        self._watcher = QFileSystemWatcher(self)
        self._build()
        self._connect()
        self.document.replace(default_flame())
        self._load_settings()
        self._watch_user_folder()

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
        self.side_panel = self._side_panel()
        inner = QSplitter(Qt.Orientation.Horizontal, self)
        inner.addWidget(left)
        inner.addWidget(self.side_panel)
        inner.setStretchFactor(0, 1)
        inner.setStretchFactor(1, 0)
        inner.setSizes([820, SIDE_PANEL_WIDTH])
        self.splitter = inner
        outer = CollapsibleSplitter(self, last_width=DRAWER_WIDTH, collapse_last=True)
        outer.last_label = "reference drawer"
        outer.addWidget(inner)
        outer.addWidget(self.drawer)
        outer.setStretchFactor(0, 1)
        outer.setStretchFactor(1, 0)
        self.outer_splitter = outer
        self.setCentralWidget(outer)
        status = QStatusBar(self)
        self.coords_label.setMinimumWidth(190)
        self.zoom_label.setMinimumWidth(90)
        status.addWidget(self.coords_label)
        status.addWidget(self.zoom_label)
        status.addWidget(self.info_label, 1)
        self.setStatusBar(status)
        self.resize(1380, 860)

    def _side_panel(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 0, 0)
        for preview in (self.preview, self.original_preview):
            preview_row = QHBoxLayout()
            preview_row.addStretch(1)
            preview_row.addWidget(preview)
            preview_row.addStretch(1)
            layout.addLayout(preview_row)
        self.gradient_bar.setToolTip("The preview's gradient — click to pick or edit one in the Gradient Library "
                                     "(the main window follows it too)")
        gradient_row = QHBoxLayout()
        gradient_row.addWidget(self.gradient_bar, 1)
        gradient_row.addWidget(self.gradient_presets, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(gradient_row)
        self.preview_section = CollapsibleSection("Variation preview options", self.preview_options, panel, expanded=False)
        self.preview_section.setToolTip("Range, depth and density of the grid of points drawn on the canvas")
        layout.addWidget(self.preview_section)
        lists = QSplitter(Qt.Orientation.Vertical, panel)
        variables = QWidget(lists)
        variables_layout = QVBoxLayout(variables)
        variables_layout.setContentsMargins(0, 0, 0, 0)
        variables_layout.addWidget(QLabel("Variables", variables))
        variables_layout.addWidget(self.variables, 1)
        formulas = QWidget(lists)
        formulas_layout = QVBoxLayout(formulas)
        formulas_layout.setContentsMargins(0, 0, 0, 0)
        formulas_layout.addWidget(QLabel("Formulas", formulas))
        formulas_layout.addWidget(self.formula_list, 1)
        lists.addWidget(variables)
        lists.addWidget(formulas)
        lists.setStretchFactor(0, 0)
        lists.setStretchFactor(1, 1)
        lists.setSizes([180, 320])
        self.lists_splitter = lists
        layout.addWidget(lists, 1)
        panel.setMinimumWidth(SIDE_PANEL_WIDTH)
        self.formula_list.new_button.setMenu(self.actions.templates_menu)
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
        self.preview.quality_changed.connect(self._on_quality_changed)
        self.preview.rendered.connect(self._on_rendered)
        session.text_loaded.connect(self._show_session_text)
        session.text_replaced.connect(self._take_session_text)
        session.compiled.connect(self._on_compiled)
        session.failed.connect(self._on_compile_failed)
        session.state_changed.connect(self._refresh_title)
        session.formulas_changed.connect(self._on_formulas_changed)
        self.code.textChanged.connect(self._on_code_changed)
        self.code.find_requested.connect(self.find_bar.open)
        self.code.goto_requested.connect(self.goto_line)
        self.code.save_requested.connect(lambda as_new: self.save_formula_as() if as_new else self.save_formula())
        self.code.status.connect(self._message)
        self.formula_list.formula_chosen.connect(self.load_formula)
        self.formula_list.new_requested.connect(lambda: self.new_formula())
        self.formula_list.favourites_changed.connect(self._save_favourites)
        self.gradient_bar.clicked.connect(self.choose_gradient)
        self.gradient_presets.gradient_chosen.connect(self.apply_gradient)
        self.preview_options.changed.connect(self._on_preview_options_changed)
        self.drawer.reference.insert_requested.connect(self.code.insert_snippet)
        self.drawer.probe.status.connect(self._message)
        self.outer_splitter.last_collapsed_changed.connect(self._on_drawer_collapsed)
        self._watcher.directoryChanged.connect(lambda _p: self._scan_user_folder())
        self._watcher.fileChanged.connect(self._on_file_changed)
        if self._gradient_window is not None:
            gradient_document = self._gradient_window.document
            gradient_document.gradient_replaced.connect(self._on_library_gradient_changed)
            gradient_document.gradient_changed.connect(self._on_library_gradient_changed)
            gradient_document.stop_changed.connect(self._on_library_gradient_changed)
        self.actions.use_current.setEnabled(self._flame_source is not None)

    # --- persistence ------------------------------------------------------------------------------------------
    def _load_settings(self) -> None:
        s, a = self._settings, self.actions

        def flag(key: str, default: str = "true") -> bool:
            return s.value(f"{SETTINGS_GROUP}/{key}", default) in ("true", True, "True")

        try:
            self.preview.level = quality_level(s.value(f"{SETTINGS_GROUP}/preview_quality", DEFAULT_QUALITY.name))
            self._check_quality_action()
            for action, key, default in ((a.var_preview, "var_preview", "true"), (a.helpers, "helpers", "true"), (a.compare, "compare", "false"),
                                         (a.side_panel, "side_panel", "true")):
                action.setChecked(flag(key, default))
            self.preview_options.set_settings(int(s.value(f"{SETTINGS_GROUP}/var_preview_range", 2)),
                                              int(s.value(f"{SETTINGS_GROUP}/var_preview_depth", 1)),
                                              int(s.value(f"{SETTINGS_GROUP}/var_preview_density", 2)), flag("var_preview_inputs", "false"))
            geometry = s.value(f"{SETTINGS_GROUP}/geometry")
            if geometry is not None:
                self.restoreGeometry(geometry)
            for splitter, key in ((self.splitter, "split"), (self.vertical_splitter, "vsplit"), (self.lists_splitter, "lsplit")):
                state = s.value(f"{SETTINGS_GROUP}/{key}")
                if state is not None:
                    splitter.restoreState(state)
            if flag("drawer_collapsed", "true"):
                QTimer.singleShot(0, lambda: self.outer_splitter.set_last_collapsed(True))
            self.actions.drawer.setChecked(not flag("drawer_collapsed", "true"))
            self.preview_section.set_expanded(flag("preview_options_open", "false"))
            recent = s.value(f"{SETTINGS_GROUP}/recent", [])
            self._recent = [r for r in (recent if isinstance(recent, list) else [recent]) if isinstance(r, str) and r][:RECENT_LIMIT]
            favourites = s.value(f"{SETTINGS_GROUP}/favourites", [])
            self.formula_list.set_favourites([f for f in (favourites if isinstance(favourites, list) else [favourites]) if isinstance(f, str)])
            center, ppu = s.value(f"{SETTINGS_GROUP}/view_center"), s.value(f"{SETTINGS_GROUP}/view_ppu")
            if center is not None and ppu is not None:
                cx, cy = (float(v) for v in str(center).split(","))
                self.view.set_view((cx, cy), float(ppu))
                self._needs_fit = False
        except (TypeError, ValueError):
            pass
        self._fill_recent_menu()
        draft = s.value(f"{SETTINGS_GROUP}/draft_text", None)
        if isinstance(draft, str) and draft.strip():
            self.session.restore(draft, s.value(f"{SETTINGS_GROUP}/draft_name", "") or "", s.value(f"{SETTINGS_GROUP}/draft_path", "") or "",
                                 s.value(f"{SETTINGS_GROUP}/draft_origin", "") or "",
                                 s.value(f"{SETTINGS_GROUP}/draft_modified", "false") in ("true", True, "True"))
        else:
            self.session.load_blank()
        try:
            selected = int(s.value(f"{SETTINGS_GROUP}/selected", 0))
            if selected in self.context.keys():
                self.context.select(selected)
        except (TypeError, ValueError):
            pass

    def save_state(self) -> None:
        """Persist the draft, the layout, the view and the options."""
        s, a = self._settings, self.actions
        for key, value in self.session.draft().items():
            s.setValue(f"{SETTINGS_GROUP}/draft_{key}", value)
        s.setValue(f"{SETTINGS_GROUP}/geometry", self.saveGeometry())
        s.setValue(f"{SETTINGS_GROUP}/split", self.splitter.saveState())
        s.setValue(f"{SETTINGS_GROUP}/vsplit", self.vertical_splitter.saveState())
        s.setValue(f"{SETTINGS_GROUP}/lsplit", self.lists_splitter.saveState())
        s.setValue(f"{SETTINGS_GROUP}/drawer_collapsed", self.outer_splitter.is_last_collapsed())
        s.setValue(f"{SETTINGS_GROUP}/preview_options_open", self.preview_section.expanded)
        for action, key in ((a.var_preview, "var_preview"), (a.helpers, "helpers"), (a.compare, "compare"), (a.side_panel, "side_panel")):
            s.setValue(f"{SETTINGS_GROUP}/{key}", action.isChecked())
        range_units, depth, density, inputs = self.preview_options.settings()
        for key, value in (("range", range_units), ("depth", depth), ("density", density), ("inputs", inputs)):
            s.setValue(f"{SETTINGS_GROUP}/var_preview_{key}", value)
        s.setValue(f"{SETTINGS_GROUP}/recent", list(self._recent))
        s.setValue(f"{SETTINGS_GROUP}/view_center", f"{self.view.center[0]!r},{self.view.center[1]!r}")
        s.setValue(f"{SETTINGS_GROUP}/view_ppu", self.view.pixels_per_unit)
        s.setValue(f"{SETTINGS_GROUP}/selected", self.context.selected if isinstance(self.context.selected, int) else 0)
        self._save_favourites()

    def _save_favourites(self) -> None:
        self._settings.setValue(f"{SETTINGS_GROUP}/favourites", sorted(self.formula_list.favourites))

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
        self.variables.sweep_button.setChecked(False)
        self.save_state()
        super().closeEvent(event)

    def toggle_focus(self) -> None:
        """Ctrl+E: the keyboard goes to the grid when the code has it, else to the code."""
        (self.view if self.code.hasFocus() else self.code).setFocus()

    # --- view options ----------------------------------------------------------------------------------------
    def set_variation_preview(self, on: bool) -> None:
        """Show (or hide) the grid of points sent through the selected transform."""
        self.update_variation_preview()
        self.info_label.setText("Variation preview: a grid of points through the selected transform" if on else "")

    def set_helpers(self, on: bool) -> None:
        """Show the pivot cross-hair and rotation / scale guides while dragging."""
        self.view.show_helpers = on
        self.view.update()

    def set_compare(self, on: bool) -> None:
        """Show a second preview rendering the formula the edit started from."""
        self.original_preview.setVisible(on)
        if on:
            self.original_preview.request()

    def set_side_panel_shown(self, shown: bool) -> None:
        """Show or hide the preview / variables / formulas column (hidden: a compact code-and-grid window)."""
        if self.side_panel is not None:
            self.side_panel.setVisible(shown)

    def set_drawer_shown(self, shown: bool) -> None:
        """Show or hide the reference drawer."""
        self.outer_splitter.set_last_collapsed(not shown)

    def _on_drawer_collapsed(self, collapsed: bool) -> None:
        if self.actions.drawer.isChecked() == collapsed:
            self.actions.drawer.setChecked(not collapsed)

    def show_drawer_tab(self, name: str) -> None:
        """Open the drawer on one of its tabs (`reference`, `compiler`, `probe`)."""
        self.outer_splitter.set_last_collapsed(False)
        self.drawer.show_tab(name)

    def _on_quality_changed(self, name: str) -> None:
        self._settings.setValue(f"{SETTINGS_GROUP}/preview_quality", name)
        self._check_quality_action()
        if self.original_preview.isVisible():
            self.original_preview.set_quality(self.preview.level)

    def _check_quality_action(self) -> None:
        action = self.actions.quality_actions.get(self.preview.level.name)
        if action is not None and not action.isChecked():
            action.setChecked(True)

    def _on_rendered(self, stats: RenderStats) -> None:
        """Surface the engine's notes (e.g. the GPU rejected the shader and the CPU rendered instead)."""
        if stats.notes:
            self.info_label.setText("; ".join(stats.notes))

    def _on_preview_options_changed(self) -> None:
        self.update_variation_preview()

    def update_variation_preview(self) -> None:
        """Recompute the canvas's variation preview for the selected transform (or hide it)."""
        xform = self.context.xform()
        if not self.actions.var_preview.isChecked() or xform is None or (W.uses_scratch(xform) and self.session.variation is None):
            self.view.set_variation_preview(None)      # (an empty editor: nothing to send the grid through)
            return
        self.session.ensure_registered()
        range_units, depth, density, show_inputs = self.preview_options.settings()
        try:
            points = variation_preview(W.prepared_xform(xform, self.session.variation), range_units, density, depth)
        except Exception as exc:  # noqa: BLE001 - a formula that cannot run on this input: show nothing, say why
            self.view.set_variation_preview(None)
            self.info_label.setText(f"Variation preview unavailable: {exc}")
            return
        points[:, 1] = -points[:, 1]          # fractal y (down) → editor y (up)
        inputs = None
        if show_inputs:
            gx, gy = preview_grid(range_units, density)
            inputs = np.column_stack([gx, -gy])
        self.view.set_variation_preview(points, transform_color(self.context.selected), inputs)

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

    def _original_flame(self) -> Flame | None:
        """What the compare preview renders: the same flame with the formula the edit started from."""
        flame = self.document.flame
        original = self.session.original
        if flame is None or original is None:
            return None
        if W.original_variation() is None:
            W.register_original(original)
        return W.prepared_flame(flame, W.original_variation(), slot=W.ORIGINAL_NAME)

    def _selected_params(self) -> dict[str, float]:
        xform = self.context.xform()
        return dict(xform.params) if xform is not None else {}

    def _new_color(self) -> float:
        flame = self.document.flame
        return A.TRANSFORM_COLORS[(len(flame.xforms) if flame else 0) % len(A.TRANSFORM_COLORS)]

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

    def _replace_flame(self, new: Flame, kind: str) -> None:
        flame = self.document.flame
        if flame is not None:
            new.palette = list(flame.palette)
        self.document.replace_flame_parameters(new, kind)
        self.context.select(0)
        self.view.fit()

    def reset_flame(self) -> None:
        """Back to one formula transform on the reference triangle (the gradient is kept; undoable)."""
        self._replace_flame(default_flame(), "reset-flame")

    def load_rig(self, name: str) -> None:
        """Put one of the test rigs (`authoring.RIGS`) on the grid (the gradient is kept; undoable)."""
        self._replace_flame(A.test_rig(name), f"rig:{name}")
        self._message(f"Test rig: {name}")

    def use_current_fractal(self) -> None:
        """Copy the main window's fractal onto the grid (its camera and palette included; undoable)."""
        flame = self._flame_source() if self._flame_source is not None else None
        if flame is None:
            self._message("The main window shows no fractal")
            return
        copy = flame.copy()
        self.document.replace_flame_parameters(copy, "use-current")
        self._gradient = copy.gradient
        self.context.select(0)
        self.view.fit()
        self._message(f"Using '{flame.name}' — put the formula on a transform with *Use the formula on this transform*")

    def send_to_main(self) -> None:
        """Hand the grid's flame to the main window as a new fractal (formula transforms become the saved formula when it
        is registered under its real name, else they are left out with a warning)."""
        flame = self.document.flame
        if flame is None:
            return
        copy = flame.copy()
        copy.name = self.session.name or "formula test"
        real = self.session.compiled_real.name if self.session.compiled_real is not None else None
        usable = real is not None and not V.is_private(real) and real in V.REGISTRY and not self.session.modified
        for x in copy.xforms:
            if W.uses_scratch(x):
                if usable:
                    x.variations = {(real if n == W.SCRATCH_NAME else n): w for n, w in x.variations.items()}
                else:
                    x.variations.pop(W.SCRATCH_NAME, None)
                    x.variations.setdefault("linear", 1.0)
        self.flame_sent.emit(copy)
        self._message("Sent to the main window" if usable else
                      "Sent to the main window — save the formula first for its transforms to use it (they are linear now)")

    # --- document → widgets ----------------------------------------------------------------------------------
    def _on_flame_replaced(self) -> None:
        self.context.reset_selection()
        self.rebuild()
        self.gradient_bar.set_palette(self.document.flame.palette if self.document.flame else [])

    def rebuild(self) -> None:
        """Everything from the document: the transform list, the triangles, the variables, the actions and the previews."""
        self.context.ensure_valid_selection()
        self._fill_combo()
        self._refresh_view()
        self.variables.refresh()
        self._sync_selection_actions()
        self._on_undo_changed(self.document.can_undo, self.document.can_redo)
        self.update_variation_preview()
        self._request_previews()

    def _request_previews(self) -> None:
        self.preview.request()
        if self.original_preview.isVisible():
            self.original_preview.request()

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
        if index == self.context.selected and what in ("variations", "params", "all") and not self.variables.sweeping:
            self.variables.refresh()
        elif index == self.context.selected and what == "params":
            self.variables.table.refresh()
        if what in ("fields", "variations", "all"):
            self._fill_combo()
        if index == self.context.selected:
            self.update_variation_preview()
        self._request_previews()

    def _on_palette_changed(self) -> None:
        self.gradient_bar.set_palette(self.document.flame.palette if self.document.flame else [])
        self._request_previews()

    def _on_undo_changed(self, can_undo: bool, can_redo: bool) -> None:
        self.actions.undo.setEnabled(can_undo)
        self.actions.redo.setEnabled(can_redo)

    def _on_selection_changed(self, key: object) -> None:
        self.view.select(key)
        self.variables.refresh()
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
        self._remember_recent()
        self._show_compile_state()
        self.variables.refresh()
        self._refresh_view()
        self.update_variation_preview()
        self.drawer.refresh()
        self._request_previews()
        self._watch_own_file()

    def _take_session_text(self) -> None:
        """The session rewrote the text (a rename): put it in the editor as one undoable edit, keeping the cursor."""
        if self.code.text() == self.session.text:
            return
        position = self.code.position
        self._loading_text = True
        try:
            cursor = self.code.textCursor()
            cursor.beginEditBlock()
            cursor.select(cursor.SelectionType.Document)
            cursor.insertText(self.session.text)
            cursor.endEditBlock()
            cursor.setPosition(min(position, len(self.session.text)))
            self.code.setTextCursor(cursor)
        finally:
            self._loading_text = False

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
        self._watch_own_file()

    def _on_code_changed(self) -> None:
        if not self._loading_text:
            self.session.set_text(self.code.text())
            self.compile_label.setText("Compiling…")
            self.compile_label.setStyleSheet("")

    def _on_compiled(self, var: V.Variation) -> None:
        self.code.set_error_line(None)
        self._show_compile_state()
        self.variables.refresh()
        self._refresh_view()
        self.update_variation_preview()
        self.drawer.refresh()
        self._request_previews()

    def _on_compile_failed(self, message: str, line: object) -> None:
        self._show_compile_state()
        self.code.set_error_line(line)
        self.drawer.refresh()
        if not message:                   # an empty editor: nothing in the scratch slot either
            self.update_variation_preview()
            self._request_previews()

    def _show_compile_state(self) -> None:
        session = self.session
        if session.error:
            where = f"  (line {session.error_line})" if session.error_line and f"line {session.error_line}" not in session.error else ""
            self.compile_label.setText(f"✗ {session.error}{where}")
            self.compile_label.setStyleSheet(ERROR_STYLE)
        elif session.variation is not None:
            var = session.variation
            facts = [session.kind_label] + [tag for flag, tag in ((var.z == V.Z_FORMULA, "3D"), (var.dc, "direct colour"), (var.random, "random")) if flag]
            count = len(var.params)
            remarks = f"; {len(session.warnings)} compiler remark{'s' if len(session.warnings) != 1 else ''}" if session.warnings else ""
            self.compile_label.setText(f"✓ {session.name} — {', '.join(facts)}; {count} variable{'s' if count != 1 else ''}{remarks}")
            self.compile_label.setStyleSheet(OK_STYLE)
        else:
            self.compile_label.setText("No formula — pick one from the list, or start a new one")
            self.compile_label.setStyleSheet("")

    def _refresh_title(self) -> None:
        session = self.session
        name = session.name or "untitled"
        self.setWindowTitle(f"{WINDOW_TITLE} — {name}[*]")
        self.setWindowModified(session.modified)
        taken = session.taken_by()
        if session.path is not None:
            where = str(session.path) if session.own_file is not None else f"{session.path.name}  (bundled, read-only — Save makes your own copy)"
        elif session.origin == ORIGIN_REGISTERED:
            where = "native built-in, read-only — Save makes a formula of your own"
        else:
            where = "not saved yet"
        if taken and session.origin != ORIGIN_REGISTERED:
            where += f"  — '{name}' is a bundled formula's name, so Save will rename yours"
        self.source_label.setText(f"  {name}  —  {where}")
        self.actions.delete_formula.setEnabled(session.own_file is not None)
        has_text = bool(session.text.strip())
        for action in (self.actions.save_formula, self.actions.save_as_formula, self.actions.rename_formula, self.actions.duplicate_formula,
                       self.actions.copy_source):
            action.setEnabled(has_text)
        self.actions.revert_formula.setEnabled(session.modified and (session.own_file is not None or session.origin == ORIGIN_REGISTERED))
        self.actions.compare.setEnabled(session.original is not None)
        if session.origin == ORIGIN_NEW:
            self.formula_list.select(None)
        self._show_compile_state()

    # --- recent formulas and the user folder ---------------------------------------------------------------------
    def _remember_recent(self) -> None:
        session = self.session
        if session.origin == ORIGIN_REGISTERED and session.name:
            entry = f"registered:{session.name}"
        elif session.origin == ORIGIN_FILE and session.path is not None:
            entry = f"file:{session.path}"
        else:
            return
        self._recent = [entry] + [r for r in self._recent if r != entry]
        del self._recent[RECENT_LIMIT:]
        self._fill_recent_menu()

    def _fill_recent_menu(self) -> None:
        menu = self.actions.recent_menu
        menu.clear()
        for entry in self._recent:
            kind, _sep, value = entry.partition(":")
            label = value if kind == "registered" else Path(value).name + f"   ({Path(value).parent})"
            menu.addAction(label, lambda e=entry: self.open_recent(e))
        menu.setEnabled(bool(self._recent))

    def open_recent(self, entry: str) -> bool:
        """Load a *Recent formulas* entry (`registered:name` or `file:path`)."""
        kind, _sep, value = entry.partition(":")
        if kind == "registered":
            return self.load_formula(value)
        if not self.confirm_discard():
            return False
        return self.open_path(Path(value))

    def _watch_user_folder(self) -> None:
        folder = self.session.folder
        if folder.is_dir() and str(folder) not in self._watcher.directories():
            self._watcher.addPath(str(folder))
            self._file_stamps = {p: p.stat().st_mtime for p in folder.glob("*.c")}

    def _watch_own_file(self) -> None:
        for path in self._watcher.files():
            self._watcher.removePath(path)
        own = self.session.own_file
        if own is not None and own.is_file():
            self._watcher.addPath(str(own))
        self._watch_user_folder()

    def _scan_user_folder(self) -> None:
        """The user folder changed on disk: load formulas that appeared or changed (other than the one being edited)."""
        folder = self.session.folder
        if not folder.is_dir():
            return
        changed = []
        for path in folder.glob("*.c"):
            stamp = path.stat().st_mtime
            if self._file_stamps.get(path) != stamp:
                self._file_stamps[path] = stamp
                if path != self.session.own_file:
                    changed.append(path)
        for path in list(self._file_stamps):
            if not path.exists():
                del self._file_stamps[path]
        if not changed:
            return
        report = loader.LoadReport()
        for path in changed:
            loader.load_source_file(path, report)
        self.session.ensure_registered()
        self.formula_list.populate()
        names = ", ".join(report.loaded) or "nothing"
        self._message(f"Formulas folder changed: loaded {names}" + (f"; {len(report.errors)} failed" if report.errors else ""))

    def _on_file_changed(self, path_text: str) -> None:
        """The formula's own file changed on disk: reload it unless there are unsaved edits."""
        path = Path(path_text)
        if path != self.session.own_file:
            return
        if not path.exists():
            self._message(f"{path.name} was removed from disk")
            return
        self._file_stamps[path] = path.stat().st_mtime
        if self.session.modified:
            self._message(f"{path.name} changed on disk — Revert to saved loads it")
        else:
            self.session.load_file(path)
            self._message(f"{path.name} changed on disk: reloaded")

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

    def new_formula(self, kind: str = "normal") -> bool:
        """Start a new formula from a template (with a name no formula has yet)."""
        if not self.confirm_discard():
            return False
        self.session.load_new(self._unique_name(W.DEFAULT_NEW_NAME), kind)
        self.code.setFocus()
        self._message("New formula from the template — rename it (Formula ▸ Rename…) and press Save when it does what you want")
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
        self._message(f"Opened {path}" + ("  (inside the package: read-only, Save makes your own copy)" if W.is_bundled_path(path) else ""))
        return True

    def save_formula(self, path: Path | None = None) -> bool:
        """Save to `path`, the formula's own file, or the user's formulas folder; the formula is registered at once.

        A bundled / built-in name is never overwritten: the formula is offered a name of its own first.
        """
        session = self.session
        if not session.text.strip():
            self._message("Nothing to save")
            return False
        taken = session.taken_by()
        if taken and not self._rename_for_save(taken):
            return False
        target = path or session.own_file or session.default_path()
        if path is None and session.own_file is None and target.exists() and not self._confirm(f"{target.name} exists in your formulas folder. Overwrite it?"):
            return False
        try:
            written = session.save(target)
        except FormulaNameTaken as exc:
            self._report_error("Cannot save formula", exc)
            return False
        except OSError as exc:
            self._report_error("Cannot save formula", exc)
            return False
        note = "" if session.error is None else " — it does not compile yet, so it is not registered and will be skipped at start-up"
        self._message(f"Saved {written}{note}")
        return True

    def _rename_for_save(self, taken: str) -> bool:
        """The name belongs to a bundled formula: offer `name_mine`; False when the user declines."""
        session = self.session
        suggestion = A.derived_name(session.name, set(dict.keys(V.REGISTRY)))
        answer = QMessageBox.question(self, WINDOW_TITLE,
                                      f"'{session.name}' is a bundled formula ({taken}).\nBundled and built-in formulas are read-only. "
                                      f"Save yours as '{suggestion}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes:
            return False
        session.rename(suggestion)
        session.path = None
        return True

    def save_formula_as(self) -> bool:
        """Save under a file name of your choosing (outside the package)."""
        if not self.session.text.strip():
            self._message("Nothing to save")
            return False
        start = self.session.own_file or self.session.default_path()
        path, _ = QFileDialog.getSaveFileName(self, "Save formula as", str(start), FORMULA_FILTER)
        if not path:
            return False
        path = Path(path)
        path = path.with_suffix(".c") if not path.suffix else path
        if W.is_bundled_path(path):
            self._report_error("Cannot save formula", ValueError(f"{path} is inside Fractalchemy's own folders; choose a folder of your own"))
            return False
        return self.save_formula(path)

    def rename_formula(self) -> bool:
        """Ask for a new name and rename the formula in the code (its variable prefixes too)."""
        name, ok = QInputDialog.getText(self, "Rename formula", "New name (a C identifier):", text=self.session.name)
        if not ok or not name.strip():
            return False
        new_name = self.session.rename(name)
        self._message(f"Renamed to {new_name}" + (" — a bundled name; Save will ask for another" if self.session.taken_by() else ""))
        return True

    def duplicate_formula(self) -> bool:
        """Make the code a new formula of your own (renamed `name_mine`, not yet saved)."""
        if not self.session.text.strip():
            return False
        taken = {p.stem for p in self.session.folder.glob("*.c")} if self.session.folder.is_dir() else set()
        new_name = self.session.duplicate_as_new(taken)
        self._message(f"Now '{new_name}', a formula of your own — Save puts it in your formulas folder")
        return True

    def revert_formula(self) -> bool:
        """Throw the edits away: back to the file or the registered formula."""
        if self.session.modified and not self._confirm(f"Discard the edits to '{self.session.name}'?"):
            return False
        if not self.session.revert():
            self._message("Nothing to revert to")
            return False
        self._message("Reverted")
        return True

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

    def copy_source(self) -> None:
        """Put the whole source on the clipboard."""
        QGuiApplication.clipboard().setText(self.session.text)
        self._message("Source copied")

    def open_folder(self) -> None:
        """Open the user's formulas folder in the file manager (created if needed)."""
        folder = self.session.folder
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(folder))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except OSError as exc:
            self._message(f"Cannot open {folder}: {exc}")
            return
        self._message(str(folder))

    def reload_formulas(self) -> None:
        """Re-scan the formula folders so formulas added since start-up appear in the list."""
        report = loader.load_all(force=True)
        self.session.ensure_registered()
        if self.session.original is not None:
            W.register_original(self.session.original)
        self.formula_list.populate()
        self.variables.refresh()
        self.session.formulas_changed.emit()
        self._message(report.summary())

    # --- code helpers ----------------------------------------------------------------------------------------
    def goto_line(self) -> None:
        """Ask for a line number and jump there."""
        line, ok = QInputDialog.getInt(self, "Go to line", "Line:", self.code.line_column()[0], 1, max(1, self.code.blockCount()))
        if ok:
            self.code.goto_line(line)

    def insert_snippet(self, snippet: A.Snippet) -> None:
        """Insert a snippet at the cursor, with the formula's stem filled in."""
        self.code.insert_snippet(A.snippet_text(snippet, self.code.text()))

    def insert_variable(self) -> bool:
        """Ask for a variable and declare it in the struct and `APO_VARIABLES`, with `VAR(name)` at the cursor."""
        dialog = VariableDialog(A.stem_of(self.session.name or W.DEFAULT_NEW_NAME), self)
        if not dialog.exec():
            return False
        return self.add_variable(dialog.short_name, dialog.default, dialog.kind, dialog.bounds)

    def add_variable(self, short_name: str, default: float = 1.0, kind: str = "real", bounds=None) -> bool:
        """Declare a variable (see `authoring.add_variable`); False with a message when the name is invalid or taken."""
        selection = self.code.textCursor()
        anchor, position = selection.anchor(), selection.position()
        try:
            text, expression = A.add_variable(self.code.text(), short_name, default, kind, bounds)
        except ValueError as exc:
            self._message(str(exc))
            return False
        old_text = self.code.text()
        offset = len(text) - len(old_text)               # the declarations went in before the cursor
        inside_function = old_text.count("{", 0, position) > old_text.count("}", 0, position)
        self.code.set_text(text)
        cursor = self.code.textCursor()
        cursor.setPosition(max(0, min(len(text), anchor + offset)))
        cursor.setPosition(max(0, min(len(text), position + offset)), cursor.MoveMode.KeepAnchor)   # a selection is replaced
        self.code.setTextCursor(cursor)
        self.code.centerCursor()
        if inside_function:
            self.code.insert_snippet(expression)
        self.code.setFocus()
        self._message(f"Declared {expression[4:-1]}" + ("" if inside_function else f" — use it as {expression}"))
        return True

    # --- gradient --------------------------------------------------------------------------------------------
    @property
    def gradient(self) -> Gradient:
        """The preview's gradient: the bright default, a preset, or what the Gradient Library last gave it."""
        return self._gradient

    @property
    def gradient_linked(self) -> bool:
        """True once the gradient is shared with the Gradient Library (after the bar was clicked)."""
        return self._gradient_linked

    def apply_gradient(self, gradient: Gradient) -> None:
        """Recolour the preview with `gradient` (a preset or a random one); while linked, the Gradient Library takes it too."""
        self._gradient = gradient.copy()
        if self._gradient_linked and self._gradient_window is not None:
            self._gradient_window.files.show_gradient(gradient.copy())      # flows back through the link
        else:
            self.document.set_gradient(gradient)

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
