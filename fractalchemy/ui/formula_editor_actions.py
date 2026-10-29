"""The Formula Editor's actions, its two toolbars, menus and the canvas's context menu, in one place.

`FormulaEditorActions` builds every QAction (icon, shortcut, tooltip) the window offers: the *transform*
ones acting on the editor's little flame (undo / redo, add linear / spherical / formula transforms,
delete, flip, the test rigs …), the *formula* ones acting on the code (new from a template, open, recent,
save, save as, rename, duplicate, revert, delete, the editing helpers, snippets, insert variable) and the
*view* ones (variation preview, compare with the original, the side panel, the drawer, the preview
quality). The window only wires the handlers and reads the checkable states.

Shortcuts the code editor uses itself (Ctrl+Z / Ctrl+Shift+Z, Ctrl+D, Ctrl+F / H / G, Ctrl+Left / Right, Ctrl+Delete …)
are claimed by it while it has the focus, so the transform actions that share them act when the canvas does.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QActionGroup, QKeySequence
from PySide6.QtWidgets import QMenu, QToolBar, QToolButton

from ..formulas import authoring as A
from ..widgets.actions import make_action, populate
from ..widgets.icons import action_icon
from .live_preview import QUALITIES


class FormulaEditorActions:
    """Every action of the Formula Editor window (attributes named after what they do).

    Args:
        window: The `FormulaEditorWindow`; its methods are the handlers, and it owns the actions.
    """

    def __init__(self, window):
        w, ops, code = window, window.operations, window.code

        def act(text, icon, slot, shortcut=None, tip="", checkable=False):
            return make_action(w, text, icon, slot, shortcut, tip, checkable)

        # --- the transforms on the canvas ---------------------------------------------------------------------
        self.undo = act("Undo", action_icon("undo"), w.document.undo, QKeySequence.StandardKey.Undo, "Undo the last change to the transforms")
        self.redo = act("Redo", action_icon("redo"), w.document.redo, "Ctrl+Shift+Z", "Redo the transform change you undid")
        self.add_linear = act("Add linear transform", "add-linear", w.add_linear, "Ctrl+Shift+L",
                              "Add a transform with linear = 1 on the reference triangle")
        self.add_spherical = act("Add spherical transform", "add-spherical", w.add_spherical, "Ctrl+Shift+P",
                                 "Add a transform with spherical = 1 on the reference triangle")
        self.add_formula = act("Add formula transform", "add-formula", w.add_formula, "Ctrl+Shift+N",
                               "Add a transform running the formula being edited")
        self.duplicate = act("Duplicate transform", "duplicate-transform", ops.duplicate, "Ctrl+Shift+D", "Duplicate the selected transform")
        self.delete = act("Delete transform", "delete-transform", ops.delete, "Ctrl+Delete", "Remove the selected transform")
        self.use_formula = act("Use the formula on this transform", "use-formula", w.use_formula, None,
                               "Replace the selected transform's variations by the formula being edited")
        self.make_linear = act("Make it linear", None, w.make_linear, None, "Replace the selected transform's variations by linear = 1")
        self.make_spherical = act("Make it spherical", None, w.make_spherical, None,
                                  "Replace the selected transform's variations by spherical = 1")
        self.rot_ccw = act("Rotate 90° counter-clockwise", "rotate-ccw", lambda: ops.rotate(90.0), "Ctrl+Left",
                           "Rotate the selected triangle 90° counter-clockwise")
        self.rot_cw = act("Rotate 90° clockwise", "rotate-cw", lambda: ops.rotate(-90.0), "Ctrl+Right", "Rotate the selected triangle 90° clockwise")
        self.flip_h = act("Flip horizontally", "flip-h", lambda: ops.flip(True), "Ctrl+Shift+H", "Mirror the selected triangle left–right about its O")
        self.flip_v = act("Flip vertically", "flip-v", lambda: ops.flip(False), "Ctrl+Shift+J", "Mirror the selected triangle top–bottom about its O")
        self.reset_triangle = act("Reset triangle", None, ops.reset, None, "Back to the reference triangle")
        self.reset_all = act("Reset all triangles", None, ops.reset_all, None, "Every transform's triangle back to the reference")
        self.new_flame = act("Start over", "erase", w.reset_flame, None, "Back to one formula transform on the reference triangle")
        self.use_current = act("Use the main window's fractal", None, w.use_current_fractal, None,
                               "Copy the fractal shown in the main window onto the grid, to try the formula on it")
        self.send_to_main = act("Send to the main window", None, w.send_to_main, None,
                                "Show the grid's flame in the main window (as a new fractal, gradient included)")
        self.rigs_menu = QMenu("Test rig", w)
        for name in A.RIGS:
            self.rigs_menu.addAction(name, lambda n=name: w.load_rig(n))
        self.rigs_menu.setToolTip("Starter flames for trying the formula: the formula alone, with a linear, a Julia pair …")
        # --- the formula's code --------------------------------------------------------------------------------------
        self.new_formula = act("New formula", "new-formula", w.new_formula, "Ctrl+N", "Start a new formula from the boilerplate template")
        self.templates_menu = QMenu("New from template", w)
        for template in A.TEMPLATES:
            action = self.templates_menu.addAction(template.title, lambda t=template: w.new_formula(t.key))
            action.setToolTip(template.description)
            action.setStatusTip(template.description)
        self.templates_menu.setToolTipsVisible(True)
        self.open_formula = act("Open formula file…", action_icon("open"), w.open_formula, "Ctrl+O", "Load a .c formula file from anywhere")
        self.recent_menu = QMenu("Recent formulas", w)
        self.save_formula = act("Save formula", action_icon("save"), w.save_formula, "Ctrl+S",
                                "Save the formula to your formulas folder (it is registered at once)")
        self.save_as_formula = act("Save formula as…", action_icon("save-as"), w.save_formula_as, "Ctrl+Shift+S",
                                   "Save the formula under another file name")
        self.rename_formula = act("Rename formula…", None, w.rename_formula, None,
                                  "Rename the formula (APO_PLUGIN and its variable prefixes)")
        self.duplicate_formula = act("Duplicate as my own", None, w.duplicate_formula, None,
                                     "Make the code a new formula of yours (renamed name_mine, saved to your folder)")
        self.revert_formula = act("Revert to saved", action_icon("revert"), w.revert_formula, None,
                                  "Throw the edits away: back to the file or the registered formula")
        self.delete_formula = act("Delete formula", action_icon("clear"), w.delete_formula, None,
                                  "Delete the formula's file from your formulas folder")
        self.copy_source = act("Copy source", action_icon("copy"), w.copy_source, None, "Copy the whole formula source to the clipboard")
        self.open_folder = act("Open formulas folder", None, w.open_folder, None, "Open your formulas folder in the file manager")
        self.code_undo = act("Undo edit", action_icon("undo"), code.undo, None, "Undo the last edit of the code")
        self.code_redo = act("Redo edit", action_icon("redo"), code.redo, None, "Redo the code edit you undid")
        self.find = act("Find…", action_icon("find"), lambda: w.find_bar.open(False), None, "Find (Ctrl+F) / replace (Ctrl+H) in the code")
        self.replace = act("Replace…", None, lambda: w.find_bar.open(True), None, "Find and replace in the code")
        self.goto = act("Go to line…", None, w.goto_line, None, "Jump to a line of the code")
        self.comment = act("Toggle comment", action_icon("comment"), code.toggle_comment, None, "Comment / uncomment the selected lines (Ctrl+/)")
        self.indent = act("Indent", action_icon("indent"), code.indent, None, "Indent the selected lines (Tab)")
        self.outdent = act("Outdent", action_icon("outdent"), code.outdent, None, "Outdent the selected lines (Shift+Tab)")
        self.insert_variable = act("Insert variable…", "add-variable", w.insert_variable, "Ctrl+Shift+I",
                                   "Declare a variable in the struct and APO_VARIABLES at once, and put VAR(name) at the cursor")
        self.snippets_menu = QMenu("Insert snippet", w)
        for snippet in A.SNIPPETS:
            action = self.snippets_menu.addAction(snippet.title, lambda s=snippet: w.insert_snippet(s))
            action.setToolTip(snippet.description)
            action.setStatusTip(snippet.description)
        self.snippets_menu.setToolTipsVisible(True)
        self.complete = act("Complete name", None, lambda: code.open_completion(True), None, "Complete the name before the cursor (Tab / Ctrl+Space)")
        self.compile = act("Compile now", action_icon("check"), w.session.compile_now, "Ctrl+Return",
                           "Compile the code without waiting (it compiles by itself a moment after every change)")
        self.reload = act("Reload formulas", "reload", w.reload_formulas, None, "Re-read the formula folders and refresh the list")
        self.focus_code = act("Switch focus: code ↔ grid", None, w.toggle_focus, "Ctrl+E", "Move the keyboard between the code and the grid")
        self.close = act("Close", None, w.close, "Ctrl+W", "Close the Formula Editor")
        # --- view -------------------------------------------------------------------------------------------------------
        self.var_preview = act("Variation preview", "var-preview", w.set_variation_preview, "Ctrl+Shift+V",
                               "Show a grid of points sent through the selected transform on the canvas — key V on the canvas",
                               checkable=True)
        self.helpers = act("Helper lines", None, w.set_helpers, None, "Pivot cross-hair, rotation circle and scale rays while dragging",
                           checkable=True)
        self.compare = act("Compare with the original", "compare", w.set_compare, "Ctrl+Shift+O",
                           "Show a second preview rendering the formula as it was before the edits", checkable=True)
        self.side_panel = act("Side panel", None, w.set_side_panel_shown, "Ctrl+Shift+B",
                              "Show or hide the preview / variables / formulas column (off: a compact window)", checkable=True)
        self.drawer = act("Reference drawer", action_icon("drawer"), w.set_drawer_shown, "Ctrl+L",
                          "Show or hide the drawer: the dialect reference, the compiler's output, the point probe", checkable=True)
        self.show_reference = act("Dialect reference", None, lambda: w.show_drawer_tab("reference"), "F1", "The dialect guide and the names it knows")
        self.show_compiler = act("Compiler output", None, lambda: w.show_drawer_tab("compiler"), None, "The generated numpy and GLSL, and warnings")
        self.show_probe = act("Probe / check engines", None, lambda: w.show_drawer_tab("probe"), None,
                              "Send a point through the formula, or compare numpy and GLSL on the sample points")
        self.fit = act("Fit triangles", "fit", w.view.fit, "Ctrl+0", "Zoom the canvas to show every triangle")
        self.zoom_in = act("Zoom in", None, lambda: w.view.zoom_by(1.25), "Ctrl++", "Zoom the canvas in")
        self.zoom_out = act("Zoom out", None, lambda: w.view.zoom_by(0.8), "Ctrl+-", "Zoom the canvas out")
        self.quality_menu = QMenu("Preview quality", w)
        group = QActionGroup(w)
        self.quality_actions = {}
        for level in QUALITIES:
            action = self.quality_menu.addAction(f"{level.name} quality", lambda lv=level: w.preview.set_quality(lv))
            action.setCheckable(True)
            action.setToolTip(f"{level.quality:g} samples per pixel" + (", anti-aliased" if level.oversample > 1 else ""))
            group.addAction(action)
            self.quality_actions[level.name] = action
        self.gradient = act("Choose gradient…", None, w.choose_gradient, None, "Pick or edit the gradient in the Gradient Library")
        self.helpers.setChecked(True)
        self.side_panel.setChecked(True)
        for action in (self.code_undo, self.code_redo):
            action.setEnabled(False)
        code.undoAvailable.connect(self.code_undo.setEnabled)
        code.redoAvailable.connect(self.code_redo.setEnabled)

    @property
    def selection_dependent(self) -> tuple:
        """Actions that act on the selected transform."""
        return (self.duplicate, self.delete, self.use_formula, self.make_linear, self.make_spherical, self.rot_ccw, self.rot_cw,
                self.flip_h, self.flip_v, self.reset_triangle)

    def install(self, window) -> tuple[QToolBar, QToolBar]:
        """Add the menus and the two toolbars to `window`; returns (transform toolbar, code toolbar)."""
        transforms = QToolBar("Transforms", window)
        transforms.setMovable(False)
        populate(transforms, self.undo, self.redo, None, self.add_linear, self.add_spherical, self.add_formula, self.duplicate, self.delete,
                 None, self.flip_h, self.flip_v, self.var_preview, self.compare, self.fit, None)
        rigs = QToolButton(window)
        rigs.setText("Test rig")
        rigs.setToolTip("Starter flames for trying the formula on")
        rigs.setMenu(self.rigs_menu)
        rigs.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        transforms.addWidget(rigs)
        transforms.addSeparator()
        window.addToolBar(transforms)
        code = QToolBar("Formula", window)
        code.setMovable(False)
        populate(code, self.new_formula, self.open_formula, self.save_formula, self.save_as_formula, self.delete_formula, None, self.code_undo,
                 self.code_redo, None, self.find, self.comment, self.indent, self.outdent, self.insert_variable, None, self.compile, self.drawer)
        new_button = code.widgetForAction(self.new_formula)
        if isinstance(new_button, QToolButton):
            new_button.setMenu(self.templates_menu)
            new_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        bar = window.menuBar()
        formula = bar.addMenu("Formula")
        populate(formula, self.new_formula)
        formula.addMenu(self.templates_menu)
        populate(formula, self.open_formula)
        formula.addMenu(self.recent_menu)
        populate(formula, None, self.save_formula, self.save_as_formula, self.rename_formula, self.duplicate_formula, self.revert_formula,
                 self.delete_formula, None, self.copy_source, self.open_folder, None, self.compile, self.reload, None, self.close)
        edit = bar.addMenu("Edit")
        populate(edit, self.undo, self.redo, None, self.code_undo, self.code_redo, None, self.find, self.replace, self.goto, None, self.comment,
                 self.indent, self.outdent, None, self.insert_variable)
        edit.addMenu(self.snippets_menu)
        populate(edit, self.complete, None, self.focus_code)
        transform = bar.addMenu("Transform")
        populate(transform, self.add_linear, self.add_spherical, self.add_formula, None, self.use_formula, self.make_linear, self.make_spherical,
                 None, self.duplicate, self.delete, None, self.rot_ccw, self.rot_cw, self.flip_h, self.flip_v, self.reset_triangle, self.reset_all,
                 None)
        transform.addMenu(self.rigs_menu)
        populate(transform, self.use_current, self.send_to_main, self.new_flame)
        view = bar.addMenu("View")
        populate(view, self.fit, self.zoom_in, self.zoom_out, None, self.var_preview, self.helpers, self.compare, None, self.side_panel,
                 self.drawer, self.show_reference, self.show_compiler, self.show_probe, None)
        view.addMenu(self.quality_menu)
        populate(view, self.gradient)
        return transforms, code

    def context_menu(self, window, on_triangle: bool) -> QMenu:
        """The canvas's context menu: the transform operations when a triangle was clicked, then the additions and the view."""
        menu = QMenu(window)
        if on_triangle:
            populate(menu, self.use_formula, self.make_linear, self.make_spherical, None, self.duplicate, self.delete, None, self.rot_ccw,
                     self.rot_cw, self.flip_h, self.flip_v, self.reset_triangle, None)
        populate(menu, self.add_linear, self.add_spherical, self.add_formula)
        menu.addMenu(self.rigs_menu)
        populate(menu, None, self.undo, self.redo, None, self.fit, self.var_preview, self.compare)
        return menu

    def show_context_menu(self, window, pos: QPoint, on_triangle: bool) -> None:
        """Pop the canvas's context menu at `pos` (canvas coordinates)."""
        self.context_menu(window, on_triangle).exec(window.view.mapToGlobal(pos))


__all__ = ["FormulaEditorActions"]
