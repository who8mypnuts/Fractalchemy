"""The Transform Editor window — Apophysis's editor, with three affines per transform.

Opened from *Windows ▸ Transform Editor* (`F4`) or the toolbar. A tool window of the main window:
closing hides it, and it follows the document — whatever fractal is shown in the main window is the
one being edited, and every edit is undoable there too (`Ctrl+Z` in either window).

Layout: a toolbar (add / duplicate / delete / link transforms, undo / redo, copy / paste triangle, the
select / move / rotate / scale mouse modes, world pivot, 90° rotations and flips, the final transform,
fit), then the three **mode buttons** — *Pre-Affine*, *Normal*, *Post-Affine* — choosing which of a
transform's affines the triangles show and edit, the triangle canvas on the left with the mini preview
and the transform tabs on the right, and a status bar (cursor position, zoom, what the mouse is over).

The main viewport re-renders once the edits pause (`EDIT_RENDER_DELAY_MS`); the mini preview follows
every change.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QCloseEvent, QGuiApplication, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMenu, QPushButton, QScrollArea, QSplitter, QStatusBar, QTabWidget,
                               QToolBar, QVBoxLayout, QWidget)

from .. import config
from ..fractal import triangles as T
from ..fractal import xform_ops
from ..fractal.scene import Affine, XForm, identity_affine
from ..fractal.triangles import CORNER_O, CORNER_X, CORNER_Y, Triangle
from ..render.service import RenderService
from ..render.xform_preview import variation_preview
from ..widgets.icons import action_icon, editor_icon
from ..widgets.triangle_view import (MODE_MOVE, MODE_ROTATE, MODE_SCALE, PIVOT_LOCAL, PIVOT_WORLD, TriangleEntry,
                                     TriangleView, transform_color)
from .editor_context import FINAL_KEY, MODE_LABELS, MODE_NORMAL, MODE_POST, MODE_PRE, MODE_TIPS, MODES, EditorContext
from .editor_panels import ColorsTab, TransformTab, TriangleTab, VariablesTab, VariationsTab, XaosTab
from .editor_preview import DEFAULT_QUALITY, EditorPreview, quality_level
from .fractal_document import FractalDocument

WINDOW_TITLE = "Transform Editor"
SETTINGS_GROUP = "editor"
TRIANGLE_CLIPBOARD_PREFIX = "fractalchemy-triangle"
FINAL_LABEL = "Final"
SIDE_PANEL_WIDTH = 450

MODE_BUTTON_STYLE = """
QPushButton {{ padding: 4px 14px; font-weight: bold; border: 1px solid #777; border-radius: 4px; }}
QPushButton:checked {{ background: {color}; color: white; border-color: {dark}; }}
QPushButton:!checked:hover {{ border-color: {color}; }}
"""


class EditorWindow(QMainWindow):
    """The Transform Editor (see the module docstring)."""

    def __init__(self, document: FractalDocument, service: RenderService, parent: QWidget | None = None,
                 settings: QSettings | None = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(editor_icon("editor"))
        self.document = document
        self.service = service
        self._settings = settings if settings is not None else QSettings()
        self.context = EditorContext(document, self)
        self.view = TriangleView(self)
        self.preview = EditorPreview(self)
        self.preview.bind(document, service)
        self.transform_combo = QComboBox(self)
        self.name_edit = QLineEdit(self)
        self.weight_box = QDoubleSpinBox(self)
        self.tabs = QTabWidget(self)
        self.variations_tab = VariationsTab(self.context, self)
        self.variables_tab = VariablesTab(self.context, self)
        self.xaos_tab = XaosTab(self.context, self)
        self.triangle_tab = TriangleTab(self.context, self.view, self)
        self.transform_tab = TransformTab(self.context, self)
        self.colors_tab = ColorsTab(self.context, self)
        self.mode_buttons: dict[str, QPushButton] = {}
        self.coords_label = QLabel(self)
        self.zoom_label = QLabel(self)
        self.info_label = QLabel(self)
        self._drag_kind: str | None = None
        self._auto_zscale: set[object] = set()
        self._updating = False
        self._use_transform_colors = False
        self._needs_fit = True
        self._build()
        self._build_actions()
        self._connect()
        self._load_settings()
        self.rebuild()

    # --- construction ---------------------------------------------------------------------------------------
    def _build(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        layout.addLayout(self._mode_row())
        splitter = QSplitter(Qt.Orientation.Horizontal, central)
        splitter.addWidget(self.view)
        splitter.addWidget(self._side_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([790, SIDE_PANEL_WIDTH])
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)
        status = QStatusBar(self)
        self.coords_label.setMinimumWidth(190)
        self.zoom_label.setMinimumWidth(90)
        status.addWidget(self.coords_label)
        status.addWidget(self.zoom_label)
        status.addWidget(self.info_label, 1)
        self.setStatusBar(status)
        self.resize(1260, 780)

    def _mode_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(4, 2, 4, 0)
        label = QLabel("Edit:", self)
        row.addWidget(label)
        group = QButtonGroup(self)
        group.setExclusive(True)
        color = QColor(config.HIGHLIGHT_COLOR)
        style = MODE_BUTTON_STYLE.format(color=color.name(), dark=color.darker(130).name())
        for mode in MODES:
            button = QPushButton(MODE_LABELS[mode], self)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)     # keep the keyboard on the canvas
            button.setToolTip(MODE_TIPS[mode])
            button.setStyleSheet(style)
            button.setChecked(mode == MODE_NORMAL)
            button.clicked.connect(lambda _c=False, m=mode: self.set_mode(m))
            group.addButton(button)
            self.mode_buttons[mode] = button
            row.addWidget(button)
        self.mode_note = QLabel(self)
        self.mode_note.setEnabled(False)
        row.addSpacing(12)
        row.addWidget(self.mode_note, 1)
        return row

    def _side_panel(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        preview_row = QHBoxLayout()
        preview_row.addStretch(1)
        preview_row.addWidget(self.preview)
        preview_row.addStretch(1)
        layout.addLayout(preview_row)
        header = QWidget(panel)
        form = QVBoxLayout(header)
        form.setContentsMargins(0, 0, 0, 0)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Transform:", header))
        self.transform_combo.setToolTip("The transform being edited (or click a triangle)")
        row1.addWidget(self.transform_combo, 1)
        form.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Name:", header))
        self.name_edit.setPlaceholderText("label for this transform")
        self.name_edit.setToolTip("A label to keep track of what the transform does (saved with the fractal)")
        row2.addWidget(self.name_edit, 1)
        row2.addWidget(QLabel("Weight:", header))
        self.weight_box.setRange(0.0, 1000.0)
        self.weight_box.setDecimals(4)
        self.weight_box.setSingleStep(0.05)
        self.weight_box.setKeyboardTracking(False)
        self.weight_box.setFixedWidth(82)
        self.weight_box.setToolTip("Relative probability of the transform being chosen (0 = never)")
        row2.addWidget(self.weight_box)
        form.addLayout(row2)
        layout.addWidget(header)
        self.tabs.setDocumentMode(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        self.tabs.tabBar().setStyleSheet("QTabBar::tab { padding: 5px 7px; }")
        for tab, title, tip in ((self.variations_tab, "Variations", "Weights of every loaded variation (plugin) for this transform"),
                                (self.variables_tab, "Variables", "Parameters of the active variations (3D ones included)"),
                                (self.xaos_tab, "Xaos", "Transform-to-transform weights"),
                                (self.triangle_tab, "Triangle", "Corner coordinates, rotate / move / scale, pivot"),
                                (self.transform_tab, "Transform", "The pre, normal and post affines as vectors"),
                                (self.colors_tab, "Colors", "Transform colour, colour speed, opacity")):
            scroll = QScrollArea(self.tabs)
            scroll.setWidget(tab)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            index = self.tabs.addTab(scroll, title)
            self.tabs.setTabToolTip(index, tip)
        layout.addWidget(self.tabs, 1)
        panel.setMinimumWidth(SIDE_PANEL_WIDTH)
        return panel

    def _action(self, text: str, icon: str | QIcon | None, slot, shortcut: str | QKeySequence | None = None,
                tip: str = "", checkable: bool = False) -> QAction:
        action = QAction(text, self)
        if isinstance(icon, str):
            action.setIcon(editor_icon(icon))
        elif icon is not None:
            action.setIcon(icon)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        action.setToolTip(tip + (f" ({QKeySequence(shortcut).toString()})" if shortcut else "") if tip else text)
        action.setStatusTip(tip or text)
        action.setCheckable(checkable)
        if checkable:
            action.toggled.connect(slot)
        else:
            action.triggered.connect(slot)
        return action

    def _build_actions(self) -> None:
        self.act_new_flame = self._action("New flame", "erase", self.new_flame, None,
                                          "Erase the fractal: one linear transform on the reference triangle, camera reset (palette and colouring kept)")
        self.act_add = self._action("Add transform", "add-transform", self.add_transform, "Ctrl+N", "Add a new transform (the reference triangle, linear)")
        self.act_duplicate = self._action("Duplicate transform", "duplicate-transform", self.duplicate_transform, "Ctrl+D", "Duplicate the selected transform")
        self.act_delete = self._action("Delete transform", "delete-transform", self.delete_transform, "Ctrl+Delete", "Remove the selected transform")
        self.act_link = self._action("Add linked transform", "linked-transform", self.add_linked_transform, None,
                                     "Add a transform linked by xaos: the selected one leads only to it, and it leads on where the selected one did")
        self.act_final = self._action("Final transform", "final-transform", self._toggle_final, "Ctrl+F", "Enable or disable the final transform", checkable=True)
        self.act_var_preview = self._action("Variation preview", "var-preview", self._set_var_preview, None,
                                            "Show a grid of points sent through the selected transform on the canvas "
                                            "(range / depth / density on the Colors tab) — key V on the canvas", checkable=True)
        self.act_undo = self._action("Undo", action_icon("undo"), self.document.undo, QKeySequence.StandardKey.Undo, "Undo the last change to the fractal")
        self.act_redo = self._action("Redo", action_icon("redo"), self.document.redo, "Ctrl+Shift+Z", "Redo the change you undid")
        self.act_copy = self._action("Copy triangle", action_icon("copy"), self.copy_triangle, "Ctrl+C", "Copy the selected triangle's coordinates")
        self.act_paste = self._action("Paste triangle", action_icon("paste"), self.paste_triangle, "Ctrl+V", "Paste coordinates onto the selected triangle")
        self.act_select = self._action("Select mode", "select", self._set_select_mode, None, "Clicking a triangle selects it (off: every drag acts on the selected transform) — key A on the canvas", checkable=True)
        self.act_move = self._action("Move", "move", lambda on: on and self._set_edit_mode(MODE_MOVE), None, "Dragging moves the triangle — key M on the canvas", checkable=True)
        self.act_rotate = self._action("Rotate", "rotate", lambda on: on and self._set_edit_mode(MODE_ROTATE), None, "Dragging rotates the triangle about the pivot (or hold Alt) — key R on the canvas", checkable=True)
        self.act_scale = self._action("Scale", "scale", lambda on: on and self._set_edit_mode(MODE_SCALE), None, "Dragging scales the triangle about the pivot (or hold Ctrl) — key S on the canvas", checkable=True)
        self.act_pivot = self._action("World pivot", "pivot", self._set_world_pivot, None, "Rotate / scale about the world origin instead of the triangle's O — key W or Space on the canvas", checkable=True)
        self.act_rot_ccw = self._action("Rotate 90° counter-clockwise", "rotate-ccw", lambda: self.rotate_selected(90.0), "Ctrl+Left", "Rotate the selected triangle 90° counter-clockwise")
        self.act_rot_cw = self._action("Rotate 90° clockwise", "rotate-cw", lambda: self.rotate_selected(-90.0), "Ctrl+Right", "Rotate the selected triangle 90° clockwise")
        self.act_flip_h = self._action("Flip horizontally", "flip-h", lambda: self.flip_selected(horizontal=True), "Ctrl+H", "Mirror the selected triangle left–right about the pivot")
        self.act_flip_v = self._action("Flip vertically", "flip-v", lambda: self.flip_selected(horizontal=False), "Ctrl+J", "Mirror the selected triangle top–bottom about the pivot")
        self.act_fit = self._action("Fit triangles", "fit", self.view.fit, "Ctrl+0", "Zoom the canvas to show every triangle")
        self.act_zoom_in = self._action("Zoom in", None, lambda: self.view.zoom_by(1.25), "Ctrl++", "Zoom the canvas in")
        self.act_zoom_out = self._action("Zoom out", None, lambda: self.view.zoom_by(0.8), "Ctrl+-", "Zoom the canvas out")
        self.act_reset_triangle = self._action("Reset triangle", None, self.reset_selected, None, "Back to the reference triangle")
        self.act_reset_all = self._action("Reset all triangles", None, self.reset_all, None, "Every transform's triangle (this mode) back to the reference")
        self.act_ghosts = self._action("Show the other affines dotted", None, self._set_ghosts, None,
                                       "Draw the normal triangles dotted behind the pre / post affine triangles, and pre / post affines "
                                       "that do something faintly behind the normal ones", checkable=True)
        self.act_helpers = self._action("Helper lines", None, self._set_helpers, None, "Pivot cross-hair, rotation circle and scale rays while dragging", checkable=True)
        self.act_xform_colors = self._action("Use transform colors", None, self._set_transform_colors, None,
                                             "Colour each triangle with its transform's palette colour instead of the fixed set", checkable=True)
        self.act_reload = self._action("Reload formulas", "reload", self.reload_formulas, None,
                                       "Re-read the formula folders (new user formulas appear in the Variations list)")
        self.act_close = self._action("Close", None, self.close, "Ctrl+W", "Close the editor")
        self.act_select.setChecked(True)
        self.act_move.setChecked(True)
        self.act_ghosts.setChecked(True)
        self.act_helpers.setChecked(True)
        mode_group = QActionGroup(self)
        for action in (self.act_move, self.act_rotate, self.act_scale):
            mode_group.addAction(action)
        toolbar = QToolBar("Editor", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        for item in (self.act_new_flame, self.act_add, self.act_duplicate, self.act_delete, self.act_link, None, self.act_undo, self.act_redo, None,
                     self.act_copy, self.act_paste, None, self.act_select, self.act_move, self.act_rotate, self.act_scale,
                     self.act_pivot, None, self.act_rot_ccw, self.act_rot_cw, self.act_flip_h, self.act_flip_v, None,
                     self.act_var_preview, self.act_final, self.act_fit):
            if item is None:
                toolbar.addSeparator()
            else:
                toolbar.addAction(item)
        self.addToolBar(toolbar)
        self.toolbar = toolbar
        menu_transform = self.menuBar().addMenu("Transform")
        for item in (self.act_new_flame, None, self.act_add, self.act_duplicate, self.act_link, self.act_delete, None, self.act_final, None,
                     self.act_rot_ccw, self.act_rot_cw, self.act_flip_h, self.act_flip_v, None, self.act_reset_triangle, self.act_reset_all):
            menu_transform.addSeparator() if item is None else menu_transform.addAction(item)
        menu_edit = self.menuBar().addMenu("Edit")
        for item in (self.act_undo, self.act_redo, None, self.act_copy, self.act_paste, None, self.act_select, self.act_move,
                     self.act_rotate, self.act_scale, self.act_pivot):
            menu_edit.addSeparator() if item is None else menu_edit.addAction(item)
        menu_view = self.menuBar().addMenu("View")
        for item in (self.act_fit, self.act_zoom_in, self.act_zoom_out, None, self.act_var_preview, self.act_ghosts, self.act_helpers,
                     self.act_xform_colors, None, self.act_reload, None, self.act_close):
            menu_view.addSeparator() if item is None else menu_view.addAction(item)

    def _connect(self) -> None:
        doc = self.document
        doc.flame_replaced.connect(self._on_flame_replaced)
        doc.flame_restored.connect(self.rebuild)
        doc.transforms_changed.connect(self._on_transforms_changed)
        doc.xform_changed.connect(self._on_xform_changed)
        doc.palette_changed.connect(self._on_palette_changed)
        doc.camera_changed.connect(self.preview.request)
        doc.coloring_changed.connect(self.preview.request)
        doc.undo_changed.connect(self._on_undo_changed)
        self.context.selection_changed.connect(self._on_selection_changed)
        self.context.mode_changed.connect(self._on_mode_changed)
        view = self.view
        view.selected.connect(self.context.select)
        view.triangle_dragged.connect(self._on_triangle_dragged)
        view.drag_finished.connect(self._on_drag_finished)
        view.triangle_command.connect(self._on_view_command)
        view.context_menu.connect(self._show_context_menu)
        view.status.connect(self.coords_label.setText)
        view.view_changed.connect(self._show_zoom)
        view.hover_changed.connect(self._on_hover)
        self.transform_combo.currentIndexChanged.connect(self._on_combo_changed)
        self.name_edit.editingFinished.connect(self._on_name_edited)
        self.weight_box.valueChanged.connect(self._on_weight_edited)
        self.colors_tab.solo_toggled.connect(self._on_solo)
        self.colors_tab.var_preview_changed.connect(self._save_var_preview_settings)
        self.colors_tab.var_preview_changed.connect(self.update_variation_preview)
        self.transform_tab.auto_zscale_toggled.connect(self._on_auto_zscale)
        self.triangle_tab.rotate_left90.clicked.connect(lambda: self.rotate_selected(90.0))
        self.triangle_tab.rotate_right90.clicked.connect(lambda: self.rotate_selected(-90.0))
        self.triangle_tab.rotate_left.clicked.connect(lambda: self.rotate_selected(self._rotate_step()))
        self.triangle_tab.rotate_right.clicked.connect(lambda: self.rotate_selected(-self._rotate_step()))
        self.triangle_tab.move_up.clicked.connect(lambda: self.move_selected(0, 1))
        self.triangle_tab.move_down.clicked.connect(lambda: self.move_selected(0, -1))
        self.triangle_tab.move_left.clicked.connect(lambda: self.move_selected(-1, 0))
        self.triangle_tab.move_right.clicked.connect(lambda: self.move_selected(1, 0))
        self.triangle_tab.scale_up.clicked.connect(lambda: self.scale_selected(True))
        self.triangle_tab.scale_down.clicked.connect(lambda: self.scale_selected(False))
        self.triangle_tab.reset_triangle.clicked.connect(self.reset_selected)
        self.triangle_tab.auto_weights.toggled.connect(lambda on: on and self._apply_auto_weights())
        self.preview.quality_changed.connect(lambda q: self._settings.setValue(f"{SETTINGS_GROUP}/preview_quality", q))

    def _load_settings(self) -> None:
        s = self._settings
        try:
            self.preview.level = quality_level(s.value(f"{SETTINGS_GROUP}/preview_quality", DEFAULT_QUALITY.name))
            self.act_xform_colors.setChecked(s.value(f"{SETTINGS_GROUP}/transform_colors", "false") in ("true", True))
            self.act_ghosts.setChecked(s.value(f"{SETTINGS_GROUP}/ghosts", "true") in ("true", True))
            self.act_helpers.setChecked(s.value(f"{SETTINGS_GROUP}/helpers", "true") in ("true", True))
            self.colors_tab.set_var_preview_settings(int(s.value(f"{SETTINGS_GROUP}/var_preview_range", 2)),
                                                     int(s.value(f"{SETTINGS_GROUP}/var_preview_depth", 1)),
                                                     int(s.value(f"{SETTINGS_GROUP}/var_preview_density", 2)))
            self.act_var_preview.setChecked(s.value(f"{SETTINGS_GROUP}/var_preview", "false") in ("true", True))
            geometry = s.value(f"{SETTINGS_GROUP}/geometry")
            if geometry is not None:
                self.restoreGeometry(geometry)
        except (TypeError, ValueError):
            pass

    # --- window management ----------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show the window (restoring it if minimised) and give it focus."""
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()
        self.preview.request()
        self.view.setFocus()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._needs_fit:
            self._needs_fit = False
            QTimer.singleShot(0, self.view.fit)     # once the canvas has its real size

    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings.setValue(f"{SETTINGS_GROUP}/geometry", self.saveGeometry())
        self._settings.setValue(f"{SETTINGS_GROUP}/transform_colors", self.act_xform_colors.isChecked())
        self._settings.setValue(f"{SETTINGS_GROUP}/ghosts", self.act_ghosts.isChecked())
        self._settings.setValue(f"{SETTINGS_GROUP}/helpers", self.act_helpers.isChecked())
        self._settings.setValue(f"{SETTINGS_GROUP}/var_preview", self.act_var_preview.isChecked())
        super().closeEvent(event)

    # --- modes ----------------------------------------------------------------------------------------------
    @property
    def mode(self) -> str:
        return self.context.mode

    def set_mode(self, mode: str) -> None:
        """Switch between editing the pre affine, the normal triangle and the post affine."""
        self.context.set_mode(mode)
        button = self.mode_buttons[mode]
        if not button.isChecked():
            button.setChecked(True)

    def _on_mode_changed(self, mode: str) -> None:
        self.view.mode_caption = "" if mode == MODE_NORMAL else f"{MODE_LABELS[mode]} triangles"
        self.mode_note.setText({MODE_PRE: "pre affine → normal → variations → post affine: editing the first step",
                                MODE_NORMAL: "",
                                MODE_POST: "pre affine → normal → variations → post affine: editing the last step"}[mode])
        self._refresh_view()
        self._refresh_tabs()

    def _set_edit_mode(self, mode: str) -> None:
        self.view.edit_mode = mode
        self.view.update()

    def _set_select_mode(self, on: bool) -> None:
        self.view.select_mode = on
        self.info_label.setText("Select mode: click a triangle to select it" if on else "Every drag acts on the selected transform")

    def _set_world_pivot(self, on: bool) -> None:
        self.view.set_pivot_mode(PIVOT_WORLD if on else PIVOT_LOCAL)
        self.triangle_tab.refresh_pivot()

    def _set_ghosts(self, on: bool) -> None:
        self.view.show_ghosts = on
        self.view.update()

    def _set_helpers(self, on: bool) -> None:
        self.view.show_helpers = on
        self.view.update()

    def _set_transform_colors(self, on: bool) -> None:
        self._use_transform_colors = on
        self._refresh_view()
        self._fill_combo()
        self.update_variation_preview()

    def _set_var_preview(self, on: bool) -> None:
        self.update_variation_preview()
        self.info_label.setText("Variation preview: a grid of points through the selected transform" if on else "")

    def _save_var_preview_settings(self) -> None:
        r, d, n = self.colors_tab.var_preview_settings()
        self._settings.setValue(f"{SETTINGS_GROUP}/var_preview_range", r)
        self._settings.setValue(f"{SETTINGS_GROUP}/var_preview_depth", d)
        self._settings.setValue(f"{SETTINGS_GROUP}/var_preview_density", n)

    def update_variation_preview(self) -> None:
        """Recompute the canvas's variation preview for the selected transform (or hide it)."""
        xform = self.context.xform()
        if not self.act_var_preview.isChecked() or xform is None:
            self.view.set_variation_preview(None)
            return
        range_units, depth, density = self.colors_tab.var_preview_settings()
        try:
            points = variation_preview(xform, range_units, density, depth)
        except Exception as exc:  # noqa: BLE001 - a formula that cannot run on this input: show nothing, say why
            self.view.set_variation_preview(None)
            self.info_label.setText(f"Variation preview unavailable: {exc}")
            return
        points[:, 1] = -points[:, 1]          # fractal y (down) → editor y (up)
        self.view.set_variation_preview(points, self._entry_color(self.context.selected, xform))

    # --- document → editor ----------------------------------------------------------------------------------
    def _on_flame_replaced(self) -> None:
        self.context.reset_selection()
        self._auto_zscale.clear()
        self.colors_tab.solo.setChecked(False)
        self.rebuild()
        if self.isVisible():
            self.view.fit()
        else:
            self._needs_fit = True

    def rebuild(self) -> None:
        """Everything from the document: the transform list, the triangles, the tabs and the preview."""
        flame = self.document.flame
        self.context.ensure_valid_selection()
        self._fill_combo()
        self._refresh_view()
        self._refresh_header()
        self._refresh_tabs()
        has_flame = flame is not None
        for action in (self.act_new_flame, self.act_add, self.act_duplicate, self.act_delete, self.act_link, self.act_final, self.act_copy,
                       self.act_paste, self.act_rot_ccw, self.act_rot_cw, self.act_flip_h, self.act_flip_v, self.act_reset_triangle,
                       self.act_reset_all):
            action.setEnabled(has_flame)
        for button in self.mode_buttons.values():
            button.setEnabled(has_flame)
        with _blocked(self.act_final):
            self.act_final.setChecked(has_flame and flame.final is not None)
        self.act_delete.setEnabled(has_flame and (self.context.is_final or len(flame.xforms) > 1))
        self.act_link.setEnabled(has_flame and not self.context.is_final)
        self.act_duplicate.setEnabled(has_flame and not self.context.is_final)
        self.setWindowTitle(f"{WINDOW_TITLE} — {flame.name}" if has_flame else WINDOW_TITLE)
        self._on_undo_changed(self.document.can_undo, self.document.can_redo)
        self.update_variation_preview()
        self.preview.request()

    def _on_transforms_changed(self) -> None:
        self.rebuild()

    def _on_xform_changed(self, index: object, what: str) -> None:
        """Refresh only what the change touched (a drag reports 'affine' on every mouse move)."""
        if what in ("affine", "variations", "fields", "all"):
            self._refresh_view()
        if index == self.context.selected:
            if what in ("affine", "all"):
                self.triangle_tab.refresh()
                self.transform_tab.refresh()
            if what in ("variations", "all"):
                self.variations_tab.refresh()
                self.variables_tab.refresh()
            if what in ("params", "all"):
                self.variables_tab.refresh()
            if what in ("fields", "all"):
                self._refresh_header()
                self.colors_tab.refresh()
            if what in ("chaos", "all"):
                self.xaos_tab.refresh()
        elif what in ("chaos", "fields", "all"):
            self.xaos_tab.refresh()          # the other transform's links / name show here too
        if what in ("fields", "all"):
            self._fill_combo_texts()
        if index == self.context.selected and what in ("affine", "variations", "params", "all"):
            self.update_variation_preview()
        self.preview.request()

    def _on_palette_changed(self) -> None:
        self.colors_tab.refresh()
        if self._use_transform_colors:
            self._refresh_view()
            self._fill_combo()
        self.preview.request()

    def _on_undo_changed(self, can_undo: bool, can_redo: bool) -> None:
        self.act_undo.setEnabled(can_undo)
        self.act_redo.setEnabled(can_redo)

    def _on_selection_changed(self, key: object) -> None:
        self.view.select(key)
        self._refresh_header()
        self._refresh_tabs()
        with _blocked(self.transform_combo):
            keys = self.context.keys()
            if key in keys:
                self.transform_combo.setCurrentIndex(keys.index(key))
        flame = self.document.flame
        self.act_delete.setEnabled(flame is not None and (self.context.is_final or len(flame.xforms) > 1))
        self.act_link.setEnabled(flame is not None and not self.context.is_final)
        self.act_duplicate.setEnabled(flame is not None and not self.context.is_final)
        if self.colors_tab.solo.isChecked():
            self.preview.set_solo(None if self.context.is_final else key)
        self.update_variation_preview()
        self.view.update()

    # --- refreshing the parts ---------------------------------------------------------------------------------
    def _entry_color(self, key: object, xform: XForm) -> QColor:
        flame = self.document.flame
        if self._use_transform_colors and flame is not None and key is not FINAL_KEY and flame.palette:
            r, g, b = flame.palette[max(0, min(len(flame.palette) - 1, int(xform.color * (len(flame.palette) - 1))))]
            return QColor(int(r), int(g), int(b))
        return transform_color(key)

    def _label(self, key: object, xform: XForm) -> str:
        if key is FINAL_KEY:
            return FINAL_LABEL + (f" · {xform.name}" if xform.name else "")
        return f"{key + 1}" + (f" · {xform.name}" if xform.name else "")

    def _refresh_view(self) -> None:
        flame = self.document.flame
        entries: list[TriangleEntry] = []
        if flame is not None:
            mode = self.context.mode
            for key in self.context.keys():
                xform = self.document.xform(key)
                triangle = T.affine_to_triangle(getattr(xform, mode))
                ghost = T.affine_to_triangle(xform.coefs) if mode != MODE_NORMAL else None
                ghosts = []   # the other two affines, when they do something (faint, captioned)
                for other, label in ((MODE_PRE, "pre"), (MODE_POST, "post")):
                    if other != mode and getattr(xform, other) != identity_affine():
                        ghosts.append((label, T.affine_to_triangle(getattr(xform, other))))
                hint = tuple(f"{name} = {weight:g}" for name, weight in xform.variations.items())
                entries.append(TriangleEntry(key, triangle, ghost, self._entry_color(key, xform), self._label(key, xform), hint,
                                             tuple(ghosts)))
        self.view.set_entries(entries, self.context.selected)

    def _refresh_header(self) -> None:
        xform = self.context.xform()
        self._updating = True
        try:
            self.name_edit.setEnabled(xform is not None)
            self.weight_box.setEnabled(xform is not None and not self.context.is_final)
            self.name_edit.setText(xform.name if xform is not None else "")
            self.weight_box.setValue(xform.weight if xform is not None and not self.context.is_final else 0.0)
            self.weight_box.setSpecialValueText("n/a" if self.context.is_final else "")
        finally:
            self._updating = False

    def _refresh_tabs(self) -> None:
        for tab in (self.variations_tab, self.variables_tab, self.xaos_tab, self.triangle_tab, self.transform_tab, self.colors_tab):
            tab.refresh()
        self.transform_tab.auto_zscale.blockSignals(True)
        self.transform_tab.auto_zscale.setChecked(self.context.selected in self._auto_zscale)
        self.transform_tab.auto_zscale.blockSignals(False)

    def _fill_combo(self) -> None:
        with _blocked(self.transform_combo):
            self.transform_combo.clear()
            for key in self.context.keys():
                xform = self.document.xform(key)
                pixmap = QPixmap(12, 12)
                pixmap.fill(self._entry_color(key, xform))
                self.transform_combo.addItem(QIcon(pixmap), self._combo_text(key, xform))
            keys = self.context.keys()
            if self.context.selected in keys:
                self.transform_combo.setCurrentIndex(keys.index(self.context.selected))
        self.transform_combo.setEnabled(self.transform_combo.count() > 0)

    def _combo_text(self, key: object, xform: XForm) -> str:
        return FINAL_LABEL if key is FINAL_KEY else f"{key + 1}" + (f" - {xform.name}" if xform.name else "")

    def _fill_combo_texts(self) -> None:
        with _blocked(self.transform_combo):
            for i, key in enumerate(self.context.keys()):
                if i < self.transform_combo.count():
                    self.transform_combo.setItemText(i, self._combo_text(key, self.document.xform(key)))

    def _show_zoom(self) -> None:
        self.zoom_label.setText(f"Zoom: {self.view.pixels_per_unit / 50.0:.2f}")

    def _on_hover(self, hit: object) -> None:
        if hit is None:
            self.info_label.setText("")
            return
        xform = self.document.xform(hit.key)
        if xform is not None:
            self.info_label.setText(f"Transform {self._label(hit.key, xform)}: " + ", ".join(f"{n} {w:g}" for n, w in xform.variations.items()))

    # --- editor → document ----------------------------------------------------------------------------------
    def _on_combo_changed(self, index: int) -> None:
        keys = self.context.keys()
        if 0 <= index < len(keys):
            self.context.select(keys[index])

    def _on_name_edited(self) -> None:
        xform = self.context.xform()
        if self._updating or xform is None or xform.name == self.name_edit.text():
            return
        self.document.set_xform_fields(self.context.selected, name=self.name_edit.text().replace('"', "'"))
        self._fill_combo_texts()

    def _on_weight_edited(self, value: float) -> None:
        if not self._updating and not self.context.is_final:
            self.document.set_xform_fields(self.context.selected, weight=value)

    def _on_triangle_dragged(self, key: object, triangle: Triangle) -> None:
        if self._drag_kind is None:
            self._drag_kind = self.context.new_drag_kind(key)
        self.context.set_triangle(key, triangle, kind=self._drag_kind, sticky=True)
        self._after_affine_edit(key, live=True)

    def _on_drag_finished(self, key: object, changed: bool) -> None:
        self._drag_kind = None
        if changed:
            self._after_affine_edit(key, live=False)

    def _after_affine_edit(self, key: object, live: bool) -> None:
        """Side effects of an affine change: auto pre_zscale and auto weights (the latter only when a drag ends)."""
        if self.context.mode == MODE_NORMAL and key in self._auto_zscale:
            self._apply_auto_zscale(key)
        if not live and self.context.mode == MODE_NORMAL and self.triangle_tab.auto_weights.isChecked():
            self._apply_auto_weights()

    def _apply_auto_zscale(self, key: object) -> None:
        xform = self.document.xform(key)
        if xform is None:
            return
        a, b, c, d, _e, _f = xform.coefs
        det = a * d - b * c
        value = 0.0 if det == 1.0 else math.copysign(math.sqrt(abs(det)), det)
        if xform.variations.get("pre_zscale", 0.0) != value:
            self.document.set_variation(key, "pre_zscale", value)

    def _apply_auto_weights(self) -> None:
        self.document.area_weights()

    def _on_auto_zscale(self, on: bool) -> None:
        key = self.context.selected
        if on:
            self._auto_zscale.add(key)
            self._apply_auto_zscale(key)
        else:
            self._auto_zscale.discard(key)

    def _on_solo(self, on: bool) -> None:
        self.preview.set_solo(self.context.selected if on and not self.context.is_final else None)

    def _edit_selected_triangle(self, fn, kind: str, key: object = "selected") -> None:
        """Replace the selected triangle (this mode) by `fn(triangle)` as one undo step."""
        key = self.context.selected if key == "selected" else key
        triangle = self.context.triangle(key)
        if triangle is None:
            return
        new = fn(triangle)
        if new == triangle:
            return
        self.context.set_triangle(key, new, kind=f"{kind}:{self.context.mode}:{key}:{id(new)}")
        self._after_affine_edit(key, live=False)

    def _rotate_step(self) -> float:
        step = self.triangle_tab.rotate_degrees()
        mods = QApplication.keyboardModifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            step /= 6.0
        elif mods & Qt.KeyboardModifier.ShiftModifier:
            step *= 6.0
        return step

    def rotate_selected(self, degrees: float) -> None:
        """Rotate the selected triangle about the pivot (counter-clockwise for positive angles)."""
        pivot = self.view.pivot()
        self._edit_selected_triangle(lambda t: T.rotate_about(t, pivot, math.radians(degrees)), "rotate")

    def move_selected(self, dx: int, dy: int) -> None:
        """Nudge the selected triangle by the Triangle tab's step (Ctrl: ÷10, Shift: ×10)."""
        step = self.triangle_tab.move_amount()
        mods = QApplication.keyboardModifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            step /= 10.0
        elif mods & Qt.KeyboardModifier.ShiftModifier:
            step *= 10.0
        self._edit_selected_triangle(lambda t: T.translate(t, dx * step, dy * step), "move")

    def scale_selected(self, up: bool) -> None:
        """Scale the selected triangle about the pivot by the Triangle tab's percentage (Ctrl: √, Shift: squared)."""
        factor = self.triangle_tab.scale_factor()
        if not up:
            factor = 1.0 / factor
        mods = QApplication.keyboardModifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            factor = math.sqrt(factor)
        elif mods & Qt.KeyboardModifier.ShiftModifier:
            factor = factor * factor
        pivot = self.view.pivot()
        self._edit_selected_triangle(lambda t: T.scale_about(t, pivot, factor), "scale")

    def flip_selected(self, horizontal: bool) -> None:
        pivot = self.view.pivot()
        self._edit_selected_triangle(lambda t: T.flip_horizontal(t, pivot) if horizontal else T.flip_vertical(t, pivot), "flip")

    def reset_selected(self) -> None:
        self._edit_selected_triangle(lambda _t: T.REFERENCE, "reset")

    def new_flame(self) -> None:
        """Apophysis's *New flame*: one linear transform, camera reset; palette, colouring and size are kept (undoable)."""
        flame = self.document.flame
        if flame is None:
            return
        new = flame.copy()
        new.xforms = [xform_ops.new_xform()]
        new.final = None
        new.camera.center, new.camera.zoom, new.camera.rotate = (0.0, 0.0), 0.0, 0.0
        new.camera.scale = new.camera.width / 4.0          # Apophysis: pixels_per_unit = width / 4
        new.camera.pitch = new.camera.yaw = new.camera.pitch_y = new.camera.perspective = new.camera.zpos = new.camera.dof = 0.0
        self.document.replace_flame_parameters(new, "new-flame")
        self.context.select(0)
        self.view.fit()

    def reset_all(self) -> None:
        """Every transform's triangle of the current mode back to the reference (one undo step)."""
        flame = self.document.flame
        if flame is None:
            return
        new = flame.copy()
        for xform in list(new.xforms) + ([new.final] if new.final else []):
            setattr(xform, self.context.mode, identity_affine())
        self.document.replace_flame_parameters(new, "reset-all")

    def _on_view_command(self, key: object, command: str) -> None:
        corner = {"x": CORNER_X, "o": CORNER_O, "y": CORNER_Y}
        if command.startswith("reset-corner-"):
            self._edit_selected_triangle(lambda t: T.reset_corner(t, corner[command[-1]]), "reset-corner", key)
        elif command.startswith("snap-corner-"):
            self._edit_selected_triangle(lambda t: T.snap_corner_rotation(t, corner[command[-1]]), "snap-corner", key)
        elif command.startswith("unit-corner-"):
            self._edit_selected_triangle(lambda t: T.reset_corner_scale(t, corner[command[-1]]), "unit-corner", key)
        elif command == "reset-rotation":
            self._edit_selected_triangle(T.snap_rotation, "reset-rotation", key)
        elif command == "reset-scale":
            self._edit_selected_triangle(T.reset_scale, "reset-scale", key)
        elif command == "reset-position":
            self._edit_selected_triangle(lambda t: T.reset_corner(t, CORNER_O), "reset-position", key)
        elif command == "move-left":
            self.move_selected(-1, 0)
        elif command == "move-right":
            self.move_selected(1, 0)
        elif command == "move-up":
            self.move_selected(0, 1)
        elif command == "move-down":
            self.move_selected(0, -1)
        elif command == "rotate-ccw":
            self.rotate_selected(self._rotate_step())
        elif command == "rotate-cw":
            self.rotate_selected(-self._rotate_step())
        elif command == "scale-up":
            self.scale_selected(True)
        elif command == "scale-down":
            self.scale_selected(False)
        elif command == "duplicate":
            self.duplicate_transform()
        elif command == "delete":
            self.delete_transform()
        elif command == "toggle-pivot":
            self.act_pivot.setChecked(not self.act_pivot.isChecked())
        elif command == "toggle-select":
            self.act_select.setChecked(not self.act_select.isChecked())
        elif command == "mode-move":
            self.act_move.setChecked(True)
        elif command == "mode-rotate":
            self.act_rotate.setChecked(True)
        elif command == "mode-scale":
            self.act_scale.setChecked(True)
        elif command == "toggle-var-preview":
            self.act_var_preview.setChecked(not self.act_var_preview.isChecked())
        elif command == "next-affine":
            self.set_mode(MODES[(MODES.index(self.context.mode) + 1) % len(MODES)])

    # --- transforms -----------------------------------------------------------------------------------------
    def add_transform(self) -> None:
        index = self.document.add_xform()
        if index is not None:
            self.context.select(index)

    def duplicate_transform(self) -> None:
        if self.context.is_final:
            return
        index = self.document.duplicate_xform(self.context.selected)
        if index is not None:
            self.context.select(index)

    def add_linked_transform(self) -> None:
        if self.context.is_final:
            return
        index = self.document.add_linked_xform(self.context.selected)
        if index is not None:
            self.context.select(index)

    def delete_transform(self) -> None:
        if self.context.is_final:
            self.document.set_final_enabled(False)
            return
        index = self.document.delete_xform(self.context.selected)
        if index is not None:
            self.context.select(index)

    def _toggle_final(self, on: bool) -> None:
        flame = self.document.flame
        if flame is None or (flame.final is not None) == on:
            return
        self.document.set_final_enabled(on)
        if on:
            self.context.select(FINAL_KEY)

    # --- clipboard ------------------------------------------------------------------------------------------
    def copy_triangle(self) -> None:
        """Copy the selected transform's affine (this mode) as text."""
        affine = self.context.affine()
        if affine is not None:
            QGuiApplication.clipboard().setText(f"{TRIANGLE_CLIPBOARD_PREFIX} " + " ".join(repr(float(v)) for v in affine))
            self.info_label.setText("Triangle copied")

    def paste_triangle(self) -> None:
        """Paste an affine copied with *Copy triangle* (or six numbers) onto the selected transform (this mode)."""
        affine = parse_triangle_text(QGuiApplication.clipboard().text())
        if affine is None:
            self.info_label.setText("The clipboard holds no triangle coordinates")
            return
        key = self.context.selected
        if self.context.set_affine(key, affine, kind=f"paste:{key}:{id(affine)}"):
            self._after_affine_edit(key, live=False)

    # --- formulas -------------------------------------------------------------------------------------------
    def reload_formulas(self) -> None:
        """Re-scan the formula folders so formulas added since start-up appear in the lists."""
        from ..formulas import load_all
        report = load_all(force=True)
        self.variations_tab.populate()
        self.variables_tab.refresh()
        self.info_label.setText(report.summary() if hasattr(report, "summary") else "Formulas reloaded")

    # --- context menu ---------------------------------------------------------------------------------------
    def _show_context_menu(self, pos: QPoint, hit: object) -> None:
        menu = QMenu(self)
        if hit is not None:
            for action in (self.act_duplicate, self.act_delete, self.act_link):
                menu.addAction(action)
            menu.addSeparator()
            for action in (self.act_rot_ccw, self.act_rot_cw, self.act_flip_h, self.act_flip_v, self.act_reset_triangle):
                menu.addAction(action)
            menu.addSeparator()
        for action in (self.act_add, self.act_final, self.act_reset_all):
            menu.addAction(action)
        menu.addSeparator()
        for action in (self.act_undo, self.act_redo):
            menu.addAction(action)
        menu.addSeparator()
        for action in (self.act_fit, self.act_ghosts, self.act_xform_colors):
            menu.addAction(action)
        menu.exec(self.view.mapToGlobal(pos))


def parse_triangle_text(text: str) -> Affine | None:
    """Six numbers (optionally after the `fractalchemy-triangle` prefix) → an affine, else None."""
    parts = text.replace(",", " ").split()
    if parts and parts[0] == TRIANGLE_CLIPBOARD_PREFIX:
        parts = parts[1:]
    if len(parts) != 6:
        return None
    try:
        return tuple(float(p) for p in parts)   # type: ignore[return-value]
    except ValueError:
        return None


class _blocked:
    """`with _blocked(obj):` blocks the object's signals."""

    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        self.obj.blockSignals(True)

    def __exit__(self, *exc):
        self.obj.blockSignals(False)


__all__ = ["EditorWindow", "parse_triangle_text", "WINDOW_TITLE"]
