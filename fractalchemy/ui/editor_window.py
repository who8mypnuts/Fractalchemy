"""The Transform Editor window — Apophysis's editor, with three affines per transform.

Opened from *Windows ▸ Transform Editor* (`F4`) or the toolbar. A tool window of the main window:
closing hides it, and it follows the document — whatever fractal is shown in the main window is the
one being edited, and every edit is undoable there too (`Ctrl+Z` in either window).

Layout: the toolbar and menus (`EditorActions`), then the three **mode buttons** — *Pre-Affine*,
*Normal*, *Post-Affine* — choosing which of a transform's affines the triangles show and edit, the
triangle canvas (`TriangleView`) on the left with the mini preview and the transform tabs
(`editor_panels`) on the right, and a status bar (cursor position, zoom, what the mouse is over).
The edits themselves are `TransformOperations`; this window keeps the widgets in step with the
document and routes what the user does to the operations.

The main viewport re-renders once the edits pause (`EDIT_RENDER_DELAY_MS`); the mini preview follows
every change.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton,
                               QScrollArea, QSplitter, QStatusBar, QTabWidget, QVBoxLayout, QWidget)

from .. import config
from ..fractal import triangles as T
from ..fractal.scene import XForm, identity_affine
from ..fractal.triangles import Triangle
from ..render.service import RenderService
from ..render.xform_preview import variation_preview
from ..widgets.icons import editor_icon
from ..widgets.silent import blocked, updating
from ..widgets.triangle_view import PIVOT_LOCAL, PIVOT_WORLD, Hit, TriangleEntry, TriangleView, transform_color
from .editor_actions import EditorActions
from .editor_context import FINAL_KEY, MODE_LABELS, MODE_NORMAL, MODE_POST, MODE_PRE, MODE_TIPS, MODES, EditorContext
from .editor_operations import TransformOperations, parse_triangle_text, triangle_text
from .editor_panels import ColorsTab, TransformTab, TriangleTab
from .editor_value_tabs import VariablesTab, VariationsTab, XaosTab
from .live_preview import DEFAULT_QUALITY, LivePreview, quality_level
from .fractal_document import FractalDocument

WINDOW_TITLE = "Transform Editor"
SETTINGS_GROUP = "editor"
FINAL_LABEL = "Final"
SIDE_PANEL_WIDTH = 450
MODE_NOTES = {MODE_PRE: "pre affine → normal → variations → post affine: editing the first step", MODE_NORMAL: "",
              MODE_POST: "pre affine → normal → variations → post affine: editing the last step"}
MODE_BUTTON_STYLE = """
QPushButton {{ padding: 4px 14px; font-weight: bold; border: 1px solid #777; border-radius: 4px; }}
QPushButton:checked {{ background: {color}; color: white; border-color: {dark}; }}
QPushButton:!checked:hover {{ border-color: {color}; }}
"""
# what each kind of document change touches: (refresh the canvas, the tabs to refresh when the selected transform changed)
REFRESH_RULES = {
    "affine": (True, ("triangle_tab", "transform_tab")),
    "variations": (True, ("variations_tab", "variables_tab")),
    "params": (False, ("variables_tab",)),
    "fields": (True, ("header", "colors_tab")),
    "chaos": (False, ("xaos_tab",)),
    "all": (True, ("triangle_tab", "transform_tab", "variations_tab", "variables_tab", "header", "colors_tab", "xaos_tab")),
}


class EditorWindow(QMainWindow):
    """The Transform Editor (see the module docstring)."""

    def __init__(self, document: FractalDocument, service: RenderService, parent: QWidget | None = None,
                 settings: QSettings | None = None):
        """Args:
            document: The main window's document: what the editor edits.
            service: The shared render service (for the mini preview).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where window preferences persist.
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(editor_icon("editor"))
        self.document = document
        self._settings = settings if settings is not None else QSettings()
        self.context = EditorContext(document, self)
        self.view = TriangleView(self)
        self.preview = LivePreview(self)
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
        self.operations = TransformOperations(self.context, self.view.pivot, self.triangle_tab)
        self.mode_buttons: dict[str, QPushButton] = {}
        self.mode_note = QLabel(self)
        self.coords_label = QLabel(self)
        self.zoom_label = QLabel(self)
        self.info_label = QLabel(self)
        self._drag_kind: str | None = None
        self._updating = False
        self._use_transform_colors = False
        self._needs_fit = True
        self._build()
        self.actions = EditorActions(self)
        self.toolbar = self.actions.install(self)
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
        """The Pre-Affine / Normal / Post-Affine buttons, the active one in the highlight colour."""
        row = QHBoxLayout()
        row.setContentsMargins(4, 2, 4, 0)
        row.addWidget(QLabel("Edit:", self))
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
        self.mode_note.setEnabled(False)
        row.addSpacing(12)
        row.addWidget(self.mode_note, 1)
        return row

    def _side_panel(self) -> QWidget:
        """The preview, the transform header (list, name, weight) and the tabs."""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        preview_row = QHBoxLayout()
        preview_row.addStretch(1)
        preview_row.addWidget(self.preview)
        preview_row.addStretch(1)
        layout.addLayout(preview_row)
        layout.addWidget(self._header())
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
            self.tabs.setTabToolTip(self.tabs.addTab(scroll, title), tip)
        layout.addWidget(self.tabs, 1)
        panel.setMinimumWidth(SIDE_PANEL_WIDTH)
        return panel

    def _header(self) -> QWidget:
        header = QWidget(self)
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
        return header

    def _connect(self) -> None:
        doc, view, ops = self.document, self.view, self.operations
        doc.flame_replaced.connect(self._on_flame_replaced)
        doc.flame_restored.connect(self.rebuild)
        doc.transforms_changed.connect(self.rebuild)
        doc.xform_changed.connect(self._on_xform_changed)
        doc.palette_changed.connect(self._on_palette_changed)
        doc.camera_changed.connect(self.preview.request)
        doc.coloring_changed.connect(self.preview.request)
        doc.undo_changed.connect(self._on_undo_changed)
        self.context.selection_changed.connect(self._on_selection_changed)
        self.context.mode_changed.connect(self._on_mode_changed)
        view.selected.connect(self.context.select)
        view.triangle_dragged.connect(self._on_triangle_dragged)
        view.drag_finished.connect(self._on_drag_finished)
        view.triangle_command.connect(self._on_view_command)
        view.context_menu.connect(lambda pos, hit: self.actions.show_context_menu(self, pos, hit is not None))
        view.status.connect(self.coords_label.setText)
        view.view_changed.connect(self._show_zoom)
        view.hover_changed.connect(self._on_hover)
        self.transform_combo.currentIndexChanged.connect(self._on_combo_changed)
        self.name_edit.editingFinished.connect(self._on_name_edited)
        self.weight_box.valueChanged.connect(self._on_weight_edited)
        self.colors_tab.solo_toggled.connect(self._on_solo)
        self.colors_tab.var_preview_changed.connect(self._save_var_preview_settings)
        self.colors_tab.var_preview_changed.connect(self.update_variation_preview)
        self.transform_tab.auto_zscale_toggled.connect(lambda on: ops.set_auto_zscale(self.context.selected, on))
        tab = self.triangle_tab
        tab.rotate_left90.clicked.connect(lambda: ops.rotate(90.0))
        tab.rotate_right90.clicked.connect(lambda: ops.rotate(-90.0))
        tab.rotate_left.clicked.connect(lambda: ops.rotate(ops.rotate_step()))
        tab.rotate_right.clicked.connect(lambda: ops.rotate(-ops.rotate_step()))
        tab.move_up.clicked.connect(lambda: ops.move(0, 1))
        tab.move_down.clicked.connect(lambda: ops.move(0, -1))
        tab.move_left.clicked.connect(lambda: ops.move(-1, 0))
        tab.move_right.clicked.connect(lambda: ops.move(1, 0))
        tab.scale_up.clicked.connect(lambda: ops.scale(True))
        tab.scale_down.clicked.connect(lambda: ops.scale(False))
        tab.reset_triangle.clicked.connect(ops.reset)
        tab.auto_weights.toggled.connect(lambda on: on and doc.area_weights())
        self.preview.quality_changed.connect(lambda q: self._settings.setValue(f"{SETTINGS_GROUP}/preview_quality", q))

    def _load_settings(self) -> None:
        s, a = self._settings, self.actions
        try:
            self.preview.level = quality_level(s.value(f"{SETTINGS_GROUP}/preview_quality", DEFAULT_QUALITY.name))
            for action, key, default in ((a.xform_colors, "transform_colors", "false"), (a.ghosts, "ghosts", "true"),
                                         (a.helpers, "helpers", "true"), (a.var_preview, "var_preview", "false")):
                action.setChecked(s.value(f"{SETTINGS_GROUP}/{key}", default) in ("true", True))
            self.colors_tab.set_var_preview_settings(int(s.value(f"{SETTINGS_GROUP}/var_preview_range", 2)),
                                                     int(s.value(f"{SETTINGS_GROUP}/var_preview_depth", 1)),
                                                     int(s.value(f"{SETTINGS_GROUP}/var_preview_density", 2)))
            geometry = s.value(f"{SETTINGS_GROUP}/geometry")
            if geometry is not None:
                self.restoreGeometry(geometry)
        except (TypeError, ValueError):
            pass

    # --- window management ----------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show the window (restoring it if minimised) and give the canvas the focus."""
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
        s, a = self._settings, self.actions
        s.setValue(f"{SETTINGS_GROUP}/geometry", self.saveGeometry())
        for action, key in ((a.xform_colors, "transform_colors"), (a.ghosts, "ghosts"), (a.helpers, "helpers"), (a.var_preview, "var_preview")):
            s.setValue(f"{SETTINGS_GROUP}/{key}", action.isChecked())
        super().closeEvent(event)

    # --- modes and view options -----------------------------------------------------------------------------
    @property
    def mode(self) -> str:
        """The affine being edited: `pre`, `coefs` or `post`."""
        return self.context.mode

    def set_mode(self, mode: str) -> None:
        """Switch between editing the pre affine, the normal triangle and the post affine."""
        self.context.set_mode(mode)
        button = self.mode_buttons[mode]
        if not button.isChecked():
            button.setChecked(True)

    def _on_mode_changed(self, mode: str) -> None:
        self.view.mode_caption = "" if mode == MODE_NORMAL else f"{MODE_LABELS[mode]} triangles"
        self.mode_note.setText(MODE_NOTES[mode])
        self._refresh_view()
        self._refresh_tabs()

    def set_edit_mode(self, mode: str) -> None:
        """What dragging does on the canvas: `move`, `rotate` or `scale`."""
        self.view.edit_mode = mode
        self.view.update()

    def set_select_mode(self, on: bool) -> None:
        """Whether clicking a triangle selects it (off: every drag acts on the selected transform)."""
        self.view.select_mode = on
        self.info_label.setText("Select mode: click a triangle to select it" if on else "Every drag acts on the selected transform")

    def set_world_pivot(self, on: bool) -> None:
        """Rotate / scale about the world origin (on) or the triangle's O (off)."""
        self.view.set_pivot_mode(PIVOT_WORLD if on else PIVOT_LOCAL)
        self.triangle_tab.refresh_pivot()

    def set_ghosts(self, on: bool) -> None:
        """Show the transform's other affines dotted behind the one being edited."""
        self.view.show_ghosts = on
        self.view.update()

    def set_helpers(self, on: bool) -> None:
        """Show the pivot cross-hair and rotation / scale guides while dragging."""
        self.view.show_helpers = on
        self.view.update()

    def set_transform_colors(self, on: bool) -> None:
        """Colour the triangles with their transforms' palette colours instead of the fixed set."""
        self._use_transform_colors = on
        self._refresh_view()
        self._fill_combo()
        self.update_variation_preview()

    def set_variation_preview(self, on: bool) -> None:
        """Show (or hide) the grid of points sent through the selected transform."""
        self.update_variation_preview()
        self.info_label.setText("Variation preview: a grid of points through the selected transform" if on else "")

    def _save_var_preview_settings(self) -> None:
        for key, value in zip(("range", "depth", "density"), self.colors_tab.var_preview_settings()):
            self._settings.setValue(f"{SETTINGS_GROUP}/var_preview_{key}", value)

    def update_variation_preview(self) -> None:
        """Recompute the canvas's variation preview for the selected transform (or hide it)."""
        xform = self.context.xform()
        if not self.actions.var_preview.isChecked() or xform is None:
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
        self.operations.auto_zscale_keys.clear()
        self.colors_tab.solo.setChecked(False)
        self.rebuild()
        if self.isVisible():
            self.view.fit()
        else:
            self._needs_fit = True

    def rebuild(self) -> None:
        """Everything from the document: the transform list, the triangles, the tabs, the actions and the preview."""
        flame = self.document.flame
        self.context.ensure_valid_selection()
        self._fill_combo()
        self._refresh_view()
        self._refresh_header()
        self._refresh_tabs()
        has_flame = flame is not None
        for action in self.actions.flame_dependent:
            action.setEnabled(has_flame)
        for button in self.mode_buttons.values():
            button.setEnabled(has_flame)
        with blocked(self.actions.final):
            self.actions.final.setChecked(has_flame and flame.final is not None)
        self._sync_selection_actions()
        self.setWindowTitle(f"{WINDOW_TITLE} — {flame.name}" if has_flame else WINDOW_TITLE)
        self._on_undo_changed(self.document.can_undo, self.document.can_redo)
        self.update_variation_preview()
        self.preview.request()

    def _sync_selection_actions(self) -> None:
        """Delete / duplicate / link depend on what is selected (the final transform cannot be duplicated or linked)."""
        flame = self.document.flame
        has_flame = flame is not None
        self.actions.delete.setEnabled(has_flame and (self.context.is_final or len(flame.xforms) > 1))
        self.actions.link.setEnabled(has_flame and not self.context.is_final)
        self.actions.duplicate.setEnabled(has_flame and not self.context.is_final)

    def _on_xform_changed(self, index: object, what: str) -> None:
        """Refresh only what the change touched (a drag reports 'affine' on every mouse move)."""
        refresh_view, parts = REFRESH_RULES.get(what, REFRESH_RULES["all"])
        if refresh_view:
            self._refresh_view()
        if index == self.context.selected:
            for part in parts:
                self._refresh_header() if part == "header" else getattr(self, part).refresh()
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
        self.actions.undo.setEnabled(can_undo)
        self.actions.redo.setEnabled(can_redo)

    def _on_selection_changed(self, key: object) -> None:
        self.view.select(key)
        self._refresh_header()
        self._refresh_tabs()
        with blocked(self.transform_combo):
            keys = self.context.keys()
            if key in keys:
                self.transform_combo.setCurrentIndex(keys.index(key))
        self._sync_selection_actions()
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
        base = FINAL_LABEL if key is FINAL_KEY else f"{key + 1}"
        return base + (f" · {xform.name}" if xform.name else "")

    def _refresh_view(self) -> None:
        """Hand the canvas the triangles of the current mode (with the other affines as ghosts)."""
        flame = self.document.flame
        entries: list[TriangleEntry] = []
        if flame is not None:
            mode = self.context.mode
            for key in self.context.keys():
                xform = self.document.xform(key)
                triangle = T.affine_to_triangle(getattr(xform, mode))
                ghost = T.affine_to_triangle(xform.coefs) if mode != MODE_NORMAL else None
                ghosts = tuple((label, T.affine_to_triangle(getattr(xform, other)))
                               for other, label in ((MODE_PRE, "pre"), (MODE_POST, "post"))
                               if other != mode and getattr(xform, other) != identity_affine())
                hint = tuple(f"{name} = {weight:g}" for name, weight in xform.variations.items())
                entries.append(TriangleEntry(key, triangle, ghost, self._entry_color(key, xform), self._label(key, xform), hint, ghosts))
        self.view.set_entries(entries, self.context.selected)

    def _refresh_header(self) -> None:
        xform = self.context.xform()
        with updating(self):
            self.name_edit.setEnabled(xform is not None)
            self.weight_box.setEnabled(xform is not None and not self.context.is_final)
            self.name_edit.setText(xform.name if xform is not None else "")
            self.weight_box.setValue(xform.weight if xform is not None and not self.context.is_final else 0.0)
            self.weight_box.setSpecialValueText("n/a" if self.context.is_final else "")

    def _refresh_tabs(self) -> None:
        for tab in (self.variations_tab, self.variables_tab, self.xaos_tab, self.triangle_tab, self.transform_tab, self.colors_tab):
            tab.refresh()
        with blocked(self.transform_tab.auto_zscale):
            self.transform_tab.auto_zscale.setChecked(self.context.selected in self.operations.auto_zscale_keys)

    def _fill_combo(self) -> None:
        with blocked(self.transform_combo):
            self.transform_combo.clear()
            keys = self.context.keys()
            for key in keys:
                xform = self.document.xform(key)
                pixmap = QPixmap(12, 12)
                pixmap.fill(self._entry_color(key, xform))
                self.transform_combo.addItem(QIcon(pixmap), self._combo_text(key, xform))
            if self.context.selected in keys:
                self.transform_combo.setCurrentIndex(keys.index(self.context.selected))
        self.transform_combo.setEnabled(self.transform_combo.count() > 0)

    def _combo_text(self, key: object, xform: XForm) -> str:
        return FINAL_LABEL if key is FINAL_KEY else f"{key + 1}" + (f" - {xform.name}" if xform.name else "")

    def _fill_combo_texts(self) -> None:
        with blocked(self.transform_combo):
            for i, key in enumerate(self.context.keys()):
                if i < self.transform_combo.count():
                    self.transform_combo.setItemText(i, self._combo_text(key, self.document.xform(key)))

    def _show_zoom(self) -> None:
        self.zoom_label.setText(f"Zoom: {self.view.pixels_per_unit / 50.0:.2f}")

    def _on_hover(self, hit: Hit | None) -> None:
        xform = self.document.xform(hit.key) if hit is not None else None
        if xform is None:
            self.info_label.setText("")
            return
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

    def _on_weight_edited(self, value: float) -> None:
        if not self._updating and not self.context.is_final:
            self.document.set_xform_fields(self.context.selected, weight=value)

    def _on_triangle_dragged(self, key: object, triangle: Triangle) -> None:
        if self._drag_kind is None:
            self._drag_kind = self.context.new_drag_kind(key)
        self.context.set_triangle(key, triangle, kind=self._drag_kind, sticky=True)
        self.operations.after_affine_edit(key, live=True)

    def _on_drag_finished(self, key: object, changed: bool) -> None:
        self._drag_kind = None
        if changed:
            self.operations.after_affine_edit(key, live=False)

    def _on_solo(self, on: bool) -> None:
        self.preview.set_solo(self.context.selected if on and not self.context.is_final else None)

    def _on_view_command(self, key: object, command: str) -> None:
        """A key or double-click on the canvas: a triangle operation, or one of the window's toggles."""
        a = self.actions
        toggles = {
            "duplicate": self.operations.duplicate, "delete": self.operations.delete,
            "toggle-pivot": lambda: a.pivot.setChecked(not a.pivot.isChecked()),
            "toggle-select": lambda: a.select.setChecked(not a.select.isChecked()),
            "toggle-var-preview": lambda: a.var_preview.setChecked(not a.var_preview.isChecked()),
            "mode-move": lambda: a.move.setChecked(True), "mode-rotate": lambda: a.rotate.setChecked(True),
            "mode-scale": lambda: a.scale.setChecked(True),
            "next-affine": lambda: self.set_mode(MODES[(MODES.index(self.context.mode) + 1) % len(MODES)]),
        }
        if command in toggles:
            toggles[command]()
        else:
            self.operations.run_command(command, key)

    # --- clipboard ------------------------------------------------------------------------------------------
    def copy_triangle(self) -> None:
        """Copy the selected transform's affine (this mode) as text."""
        affine = self.context.affine()
        if affine is not None:
            QGuiApplication.clipboard().setText(triangle_text(affine))
            self.info_label.setText("Triangle copied")

    def paste_triangle(self) -> None:
        """Paste an affine copied with *Copy triangle* (or six numbers) onto the selected transform (this mode)."""
        affine = parse_triangle_text(QGuiApplication.clipboard().text())
        if affine is None:
            self.info_label.setText("The clipboard holds no triangle coordinates")
        else:
            self.operations.paste_affine(affine)

    # --- formulas -------------------------------------------------------------------------------------------
    def reload_formulas(self) -> None:
        """Re-scan the formula folders so formulas added since start-up appear in the lists."""
        from ..formulas import load_all
        report = load_all(force=True)
        self.variations_tab.populate()
        self.variables_tab.refresh()
        self.info_label.setText(report.summary())


__all__ = ["EditorWindow", "parse_triangle_text", "WINDOW_TITLE"]
