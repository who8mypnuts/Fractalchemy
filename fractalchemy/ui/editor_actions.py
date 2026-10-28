"""The Transform Editor's actions, toolbar and menus, in one place.

`EditorActions` builds every QAction the window offers (with icon, shortcut and tooltip), lays them
out on the toolbar and in the *Transform* / *Edit* / *View* menus, and can pop the canvas's context
menu. The window only wires the handlers and reads the checkable states.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QActionGroup, QKeySequence
from PySide6.QtWidgets import QMenu, QToolBar

from ..widgets.actions import make_action, populate
from ..widgets.icons import action_icon


class EditorActions:
    """Every action of the editor window (attributes named after what they do).

    Args:
        window: The `EditorWindow`; its methods are the handlers, and it owns the actions.
    """

    def __init__(self, window):
        w, ops = window, window.operations

        def act(text, icon, slot, shortcut=None, tip="", checkable=False):
            return make_action(w, text, icon, slot, shortcut, tip, checkable)

        self.new_flame = act("New flame", "erase", ops.new_flame, None,
                             "Erase the fractal: one linear transform on the reference triangle, camera reset (palette and colouring kept)")
        self.add = act("Add transform", "add-transform", ops.add, "Ctrl+N", "Add a new transform (the reference triangle, linear)")
        self.duplicate = act("Duplicate transform", "duplicate-transform", ops.duplicate, "Ctrl+D", "Duplicate the selected transform")
        self.delete = act("Delete transform", "delete-transform", ops.delete, "Ctrl+Delete", "Remove the selected transform")
        self.link = act("Add linked transform", "linked-transform", ops.add_linked, None,
                        "Add a transform linked by xaos: the selected one leads only to it, and it leads on where the selected one did")
        self.final = act("Final transform", "final-transform", ops.set_final_enabled, "Ctrl+F", "Enable or disable the final transform",
                         checkable=True)
        self.var_preview = act("Variation preview", "var-preview", w.set_variation_preview, None,
                               "Show a grid of points sent through the selected transform on the canvas "
                               "(range / depth / density on the Colors tab) — key V on the canvas", checkable=True)
        self.undo = act("Undo", action_icon("undo"), w.document.undo, QKeySequence.StandardKey.Undo, "Undo the last change to the fractal")
        self.redo = act("Redo", action_icon("redo"), w.document.redo, "Ctrl+Shift+Z", "Redo the change you undid")
        self.copy = act("Copy triangle", action_icon("copy"), w.copy_triangle, "Ctrl+C", "Copy the selected triangle's coordinates")
        self.paste = act("Paste triangle", action_icon("paste"), w.paste_triangle, "Ctrl+V", "Paste coordinates onto the selected triangle")
        self.select = act("Select mode", "select", w.set_select_mode, None,
                          "Clicking a triangle selects it (off: every drag acts on the selected transform) — key A on the canvas", checkable=True)
        self.move = act("Move", "move", lambda on: on and w.set_edit_mode("move"), None, "Dragging moves the triangle — key M on the canvas",
                        checkable=True)
        self.rotate = act("Rotate", "rotate", lambda on: on and w.set_edit_mode("rotate"), None,
                          "Dragging rotates the triangle about the pivot (or hold Alt) — key R on the canvas", checkable=True)
        self.scale = act("Scale", "scale", lambda on: on and w.set_edit_mode("scale"), None,
                         "Dragging scales the triangle about the pivot (or hold Ctrl) — key S on the canvas", checkable=True)
        self.pivot = act("World pivot", "pivot", w.set_world_pivot, None,
                         "Rotate / scale about the world origin instead of the triangle's O — key W or Space on the canvas", checkable=True)
        self.rot_ccw = act("Rotate 90° counter-clockwise", "rotate-ccw", lambda: ops.rotate(90.0), "Ctrl+Left",
                           "Rotate the selected triangle 90° counter-clockwise")
        self.rot_cw = act("Rotate 90° clockwise", "rotate-cw", lambda: ops.rotate(-90.0), "Ctrl+Right", "Rotate the selected triangle 90° clockwise")
        self.flip_h = act("Flip horizontally", "flip-h", lambda: ops.flip(True), "Ctrl+H", "Mirror the selected triangle left–right about the pivot")
        self.flip_v = act("Flip vertically", "flip-v", lambda: ops.flip(False), "Ctrl+J", "Mirror the selected triangle top–bottom about the pivot")
        self.fit = act("Fit triangles", "fit", w.view.fit, "Ctrl+0", "Zoom the canvas to show every triangle")
        self.zoom_in = act("Zoom in", None, lambda: w.view.zoom_by(1.25), "Ctrl++", "Zoom the canvas in")
        self.zoom_out = act("Zoom out", None, lambda: w.view.zoom_by(0.8), "Ctrl+-", "Zoom the canvas out")
        self.reset_triangle = act("Reset triangle", None, ops.reset, None, "Back to the reference triangle")
        self.reset_all = act("Reset all triangles", None, ops.reset_all, None, "Every transform's triangle (this mode) back to the reference")
        self.ghosts = act("Show the other affines dotted", None, w.set_ghosts, None,
                          "Draw the normal triangles dotted behind the pre / post affine triangles, and pre / post affines "
                          "that do something faintly behind the normal ones", checkable=True)
        self.helpers = act("Helper lines", None, w.set_helpers, None, "Pivot cross-hair, rotation circle and scale rays while dragging",
                           checkable=True)
        self.xform_colors = act("Use transform colors", None, w.set_transform_colors, None,
                                "Colour each triangle with its transform's palette colour instead of the fixed set", checkable=True)
        self.reload = act("Reload formulas", "reload", w.reload_formulas, None,
                          "Re-read the formula folders (new user formulas appear in the Variations list)")
        self.close = act("Close", None, w.close, "Ctrl+W", "Close the editor")
        self.select.setChecked(True)
        self.move.setChecked(True)
        self.ghosts.setChecked(True)
        self.helpers.setChecked(True)
        self._mode_group = QActionGroup(w)
        for action in (self.move, self.rotate, self.scale):
            self._mode_group.addAction(action)

    @property
    def flame_dependent(self) -> tuple:
        """Actions that need a loaded fractal."""
        return (self.new_flame, self.add, self.duplicate, self.delete, self.link, self.final, self.copy, self.paste, self.rot_ccw,
                self.rot_cw, self.flip_h, self.flip_v, self.reset_triangle, self.reset_all)

    def install(self, window) -> QToolBar:
        """Add the toolbar and the menus to `window`; returns the toolbar."""
        toolbar = QToolBar("Editor", window)
        toolbar.setMovable(False)
        populate(toolbar, self.new_flame, self.add, self.duplicate, self.delete, self.link, None, self.undo, self.redo, None,
                 self.copy, self.paste, None, self.select, self.move, self.rotate, self.scale, self.pivot, None,
                 self.rot_ccw, self.rot_cw, self.flip_h, self.flip_v, None, self.var_preview, self.final, self.fit)
        window.addToolBar(toolbar)
        populate(window.menuBar().addMenu("Transform"), self.new_flame, None, self.add, self.duplicate, self.link, self.delete, None,
                 self.final, None, self.rot_ccw, self.rot_cw, self.flip_h, self.flip_v, None, self.reset_triangle, self.reset_all)
        populate(window.menuBar().addMenu("Edit"), self.undo, self.redo, None, self.copy, self.paste, None, self.select, self.move,
                 self.rotate, self.scale, self.pivot)
        populate(window.menuBar().addMenu("View"), self.fit, self.zoom_in, self.zoom_out, None, self.var_preview, self.ghosts,
                 self.helpers, self.xform_colors, None, self.reload, None, self.close)
        return toolbar

    def show_context_menu(self, window, pos: QPoint, on_triangle: bool) -> None:
        """Pop the canvas's context menu at `pos` (canvas coordinates)."""
        menu = QMenu(window)
        if on_triangle:
            populate(menu, self.duplicate, self.delete, self.link, None, self.rot_ccw, self.rot_cw, self.flip_h, self.flip_v,
                     self.reset_triangle, None)
        populate(menu, self.add, self.final, self.reset_all, None, self.undo, self.redo, None, self.fit, self.ghosts, self.xform_colors)
        menu.exec(window.view.mapToGlobal(pos))


__all__ = ["EditorActions"]
