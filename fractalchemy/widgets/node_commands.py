"""The single-node operations of the gradient editor, shared by every way of reaching them.

The *Selected node* panel's buttons, the node bar's keys (Delete / Backspace, ← / →, Enter), its right-click menu and
the double-click gesture on the strip all call `NodeCommands`, so each operation exists once:

* `add_after()`: a node in the same colour, midway to the next one;
* `add_random()`: a node in an entirely new colour;
* `randomize()`: nudge the node's hue, saturation and lightness;
* `delete()`: remove it (never below two nodes);
* `nudge(units)`: move it by Ultra Fractal index units (1 / 399 of the gradient);
* `add_at(position)`: a node at any position in the colour already there, so the gradient does not change;
* `pick_colour(anchor)`: the live colour picker.

It also owns one `QAction` per menu operation, kept enabled / disabled with the selection, and the colour picker.
"""

from __future__ import annotations

import random

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QWidget

from .. import config
from ..model import RGB, node_ops, rgb_to_hex
from ..model.operations import MIN_NODES
from ..ui.document import GradientDocument
from .actions import populate
from .color_dialog import ColorPickerDialog

INDEX_UNITS = config.UGR_MAX_INDEX          # positions shown and nudged in 0..399 (Ultra Fractal's gradient index)


class NodeCommands(QObject):
    """Node operations on a `GradientDocument` (see the module docstring).

    Signals:
        status(str): What an operation did, or why it could not (for the window's status bar).
    """
    status = Signal(str)

    def __init__(self, document: GradientDocument, dialog_parent: QWidget):
        """Args:
            document: The gradient being edited.
            dialog_parent: The widget that owns the colour picker (it opens beside that widget's window).
        """
        super().__init__(dialog_parent)
        self._document = document
        self._rng = random.Random()
        self.picker = ColorPickerDialog(dialog_parent)
        self.picker.color_changed.connect(self.set_color)
        self.add_action = self._action("Add node", self.add_after, "Insert a node after this one, in the same colour")
        self.add_random_action = self._action("Add random node", self.add_random, "Insert a node after this one, in an entirely new colour")
        self.randomize_action = self._action("Randomize node", self.randomize, "Nudge this node's hue, saturation and lightness at random")
        self.pick_action = self._action("Pick colour…", lambda: self.pick_colour(None), "Open the colour picker for this node", "Return")
        self.delete_action = self._action("Delete node", self.delete, "Remove this node", "Del")
        for signal in (document.selection_changed, document.gradient_changed, document.gradient_replaced, document.stop_changed):
            signal.connect(self._on_document_changed)
        self.refresh_actions()

    def _action(self, text: str, slot, tip: str, keys: str | None = None) -> QAction:
        action = QAction(text, self)
        action.setToolTip(tip)
        action.setStatusTip(tip)
        if keys:                               # shown in the menu (and usable while it is open); the node bar's
                                               # keyPressEvent is what handles the keys otherwise
            action.setShortcut(QKeySequence(keys))
            action.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        action.triggered.connect(lambda _checked=False: slot())
        return action

    # --- state ----------------------------------------------------------------------------------------------------
    @property
    def selected(self) -> int:
        """The selected node's index, -1 for none."""
        return self._document.selected_index

    @property
    def can_delete(self) -> bool:
        """Whether the selected node may be removed (a gradient keeps at least two)."""
        return self.selected >= 0 and len(self._document.gradient.stops) > MIN_NODES

    def refresh_actions(self, *_args) -> None:
        """Enable the actions that make sense for the current selection."""
        active = 0 <= self.selected < len(self._document.gradient.stops)
        for action in (self.add_action, self.add_random_action, self.randomize_action, self.pick_action):
            action.setEnabled(active)
        self.delete_action.setEnabled(active and self.can_delete)

    def _on_document_changed(self, *_args) -> None:
        self.refresh_actions()
        self._retarget_picker()

    def _retarget_picker(self) -> None:
        """Keep an open picker on the selected node (hide it when nothing is selected)."""
        if not self.picker.isVisible():
            return
        if not 0 <= self.selected < len(self._document.gradient.stops):
            self.picker.hide()
        elif self.picker.color() != self._current_color():
            self.picker.set_color(self._current_color(), as_original=True)

    def actions(self) -> list[QAction | None]:
        """The node menu's actions in order (None = a separator)."""
        return [self.add_action, self.add_random_action, self.randomize_action, None, self.pick_action, None,
                self.delete_action]

    def populate_menu(self, menu: QMenu) -> None:
        """Fill `menu` with the node operations."""
        populate(menu, *self.actions())

    # --- operations -----------------------------------------------------------------------------------------------
    def add_after(self) -> None:
        """Insert a node in the selected node's colour, midway to the next node."""
        if self.selected >= 0:
            self._insert(self._current_color())

    def add_random(self) -> None:
        """Insert a node in a new, harmonious colour after the selected one."""
        if self.selected >= 0:
            self._insert(node_ops.random_color(self._rng))

    def randomize(self) -> None:
        """Nudge the selected node's colour."""
        if self.selected >= 0:
            self.set_color(node_ops.perturbed_color(self._current_color(), self._rng))

    def delete(self) -> bool:
        """Remove the selected node; False (with a status note) when none is selected or only two remain."""
        if self.selected < 0:
            return False
        if not self.can_delete:
            self.status.emit(f"A gradient needs at least {MIN_NODES} nodes")
            return False
        self._document.remove_stop(self.selected)
        return True

    def nudge(self, units: int) -> None:
        """Move the selected node by `units` index units (the selection follows it past neighbours)."""
        index = self.selected
        if index < 0:
            return
        position = node_ops.nudged_position(self._document.gradient.stops[index].position, units, INDEX_UNITS)
        new_index = self._document.move_stop(index, position)
        self.status.emit(f"Node {new_index + 1} at {round(position * INDEX_UNITS)}")

    def add_at(self, position: float, reach: float = 0.0) -> int:
        """Add a node at `position` in the colour already there (the gradient is unchanged) and select it.

        Args:
            position: Where, 0..1.
            reach: A node closer than this (in 0..1 units) is selected instead of adding a second one on top of it.

        Returns:
            The index of the node now selected.
        """
        stops = self._document.gradient.stops
        nearest = min(range(len(stops)), key=lambda i: abs(stops[i].position - position), default=-1)
        if nearest >= 0 and abs(stops[nearest].position - position) <= reach:
            self._document.select(nearest)
            return nearest
        new_stops, index = node_ops.inserted_at(self._document.gradient, position)
        self._document.insert_stop(new_stops, index)
        color = new_stops[index].color
        self.status.emit(f"Added node {index + 1} at {round(new_stops[index].position * INDEX_UNITS)} (#{rgb_to_hex(color)})")
        return index

    def pick_colour(self, anchor: QWidget | None) -> None:
        """Show the colour picker for the selected node beside `anchor`'s window (the dialog's parent by default)."""
        if self.selected < 0:
            return
        self.picker.set_color(self._current_color(), as_original=True)
        self.picker.show_beside(anchor if anchor is not None else self.picker.parentWidget())

    def set_color(self, color: RGB) -> None:
        """Recolour the selected node (the picker's live edits land here)."""
        index = self.selected
        if index >= 0 and self._document.gradient.stops[index].color != tuple(color):
            self._document.set_color(index, tuple(color))

    # --- helpers --------------------------------------------------------------------------------------------------
    def _insert(self, color: RGB) -> None:
        stops, new_index = node_ops.inserted_after(self._document.gradient, self.selected, color)
        self._document.insert_stop(stops, new_index)

    def _current_color(self) -> RGB:
        return self._document.gradient.stops[self.selected].color


__all__ = ["NodeCommands", "INDEX_UNITS"]
