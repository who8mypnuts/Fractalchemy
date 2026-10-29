"""The Formula Editor's actions, its two toolbars, menus and the canvas's context menu, in one place.

Shortcuts the code editor uses itself (Ctrl+Z / Ctrl+Shift+Z, Ctrl+D, Ctrl+F / H / G, Ctrl+Left / Right, Ctrl+Delete …)
are claimed by it while it has the focus, so the transform actions that share them act when the canvas does.

`FormulaEditorActions` builds every QAction (icon, shortcut, tooltip) the window offers: the *transform*
ones acting on the editor's little flame (undo / redo, add linear / spherical / formula transforms,
delete, flip …) and the *formula* ones acting on the code (new / open / save / save as / delete, the
editing helpers). The window wires nothing but the handlers and reads the checkable states.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMenu, QToolBar

from ..widgets.actions import make_action, populate
from ..widgets.icons import action_icon


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
        self.var_preview = act("Variation preview", "var-preview", w.set_variation_preview, None,
                               "Show a grid of points sent through the selected transform on the canvas — key V on the canvas",
                               checkable=True)
        self.helpers = act("Helper lines", None, w.set_helpers, None, "Pivot cross-hair, rotation circle and scale rays while dragging",
                           checkable=True)
        self.fit = act("Fit triangles", "fit", w.view.fit, "Ctrl+0", "Zoom the canvas to show every triangle")
        self.zoom_in = act("Zoom in", None, lambda: w.view.zoom_by(1.25), "Ctrl++", "Zoom the canvas in")
        self.zoom_out = act("Zoom out", None, lambda: w.view.zoom_by(0.8), "Ctrl+-", "Zoom the canvas out")
        self.gradient = act("Choose gradient…", None, w.choose_gradient, None, "Pick or edit the gradient in the Gradient Library")
        # --- the formula's code --------------------------------------------------------------------------------------
        self.new_formula = act("New formula", "new-formula", w.new_formula, "Ctrl+N", "Start a new formula from the boilerplate template")
        self.open_formula = act("Open formula file…", action_icon("open"), w.open_formula, "Ctrl+O", "Load a .c formula file from anywhere")
        self.save_formula = act("Save formula", action_icon("save"), w.save_formula, "Ctrl+S",
                                "Save the formula to your formulas folder (it is registered at once)")
        self.save_as_formula = act("Save formula as…", action_icon("save-as"), w.save_formula_as, "Ctrl+Shift+S",
                                   "Save the formula under another file name")
        self.delete_formula = act("Delete formula", action_icon("clear"), w.delete_formula, None,
                                  "Delete the formula's file from your formulas folder")
        self.code_undo = act("Undo edit", action_icon("undo"), code.undo, None, "Undo the last edit of the code")
        self.code_redo = act("Redo edit", action_icon("redo"), code.redo, None, "Redo the code edit you undid")
        self.find = act("Find…", action_icon("find"), lambda: w.find_bar.open(False), None, "Find (Ctrl+F) / replace (Ctrl+H) in the code")
        self.replace = act("Replace…", None, lambda: w.find_bar.open(True), None, "Find and replace in the code")
        self.goto = act("Go to line…", None, w.goto_line, None, "Jump to a line of the code")
        self.comment = act("Toggle comment", action_icon("comment"), code.toggle_comment, None, "Comment / uncomment the selected lines (Ctrl+/)")
        self.indent = act("Indent", action_icon("indent"), code.indent, None, "Indent the selected lines (Tab)")
        self.outdent = act("Outdent", action_icon("outdent"), code.outdent, None, "Outdent the selected lines (Shift+Tab)")
        self.compile = act("Compile now", action_icon("check"), w.session.compile_now, "Ctrl+Return",
                           "Compile the code without waiting (it compiles by itself a moment after every change)")
        self.reload = act("Reload formulas", "reload", w.reload_formulas, None, "Re-read the formula folders and refresh the list")
        self.close = act("Close", None, w.close, "Ctrl+W", "Close the Formula Editor")
        self.helpers.setChecked(True)      # (the variation preview is switched on by the window once it is complete)
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
                 None, self.flip_h, self.flip_v, self.var_preview, self.fit, None)
        window.addToolBar(transforms)
        code = QToolBar("Formula", window)
        code.setMovable(False)
        populate(code, self.new_formula, self.open_formula, self.save_formula, self.save_as_formula, self.delete_formula, None, self.code_undo,
                 self.code_redo, None, self.find, self.comment, self.indent, self.outdent, None, self.compile)
        bar = window.menuBar()
        populate(bar.addMenu("Formula"), self.new_formula, self.open_formula, None, self.save_formula, self.save_as_formula, self.delete_formula,
                 None, self.compile, self.reload, None, self.close)
        populate(bar.addMenu("Edit"), self.undo, self.redo, None, self.code_undo, self.code_redo, None, self.find, self.replace, self.goto,
                 None, self.comment, self.indent, self.outdent)
        populate(bar.addMenu("Transform"), self.add_linear, self.add_spherical, self.add_formula, None, self.use_formula, self.make_linear,
                 self.make_spherical, None, self.duplicate, self.delete, None, self.rot_ccw, self.rot_cw, self.flip_h, self.flip_v,
                 self.reset_triangle, self.reset_all, None, self.new_flame)
        populate(bar.addMenu("View"), self.fit, self.zoom_in, self.zoom_out, None, self.var_preview, self.helpers, None, self.gradient)
        return transforms, code

    def context_menu(self, window, on_triangle: bool) -> QMenu:
        """The canvas's context menu: the transform operations when a triangle was clicked, then the additions and the view."""
        menu = QMenu(window)
        if on_triangle:
            populate(menu, self.use_formula, self.make_linear, self.make_spherical, None, self.duplicate, self.delete, None, self.rot_ccw,
                     self.rot_cw, self.flip_h, self.flip_v, self.reset_triangle, None)
        populate(menu, self.add_linear, self.add_spherical, self.add_formula, None, self.undo, self.redo, None, self.fit, self.var_preview)
        return menu

    def show_context_menu(self, window, pos: QPoint, on_triangle: bool) -> None:
        """Pop the canvas's context menu at `pos` (canvas coordinates)."""
        self.context_menu(window, on_triangle).exec(window.view.mapToGlobal(pos))


__all__ = ["FormulaEditorActions"]
