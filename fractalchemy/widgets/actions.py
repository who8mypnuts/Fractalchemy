"""A QAction factory for the tool windows' toolbars and menus."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QWidget

from .icons import editor_icon


def make_action(parent: QWidget, text: str, icon: QIcon | str | None, slot: Callable, shortcut=None, tip: str = "",
                checkable: bool = False, context: Qt.ShortcutContext = Qt.ShortcutContext.WindowShortcut) -> QAction:
    """Build a QAction with icon, shortcut, tooltip (shortcut appended) and status tip.

    Args:
        parent: The window owning the action.
        text: Menu text.
        icon: A QIcon, the name of a painted glyph (`editor_icon`), or None.
        slot: Connected to `toggled` for checkable actions, else to `triggered`.
        shortcut: A key sequence string or `QKeySequence.StandardKey` (None = no shortcut).
        tip: Tooltip and status tip (the text when empty).
        checkable: Whether the action is a toggle.
        context: Where the shortcut applies.

    Returns:
        The configured action.
    """
    action = QAction(text, parent)
    if isinstance(icon, str):
        action.setIcon(editor_icon(icon))
    elif icon is not None:
        action.setIcon(icon)
    if shortcut is not None:
        sequence = QKeySequence(shortcut)
        action.setShortcut(sequence)
        action.setShortcutContext(context)
        keys = f" ({sequence.toString()})" if sequence.toString() else ""
    else:
        keys = ""
    action.setToolTip((tip or text) + keys)
    action.setStatusTip(tip or text)
    action.setCheckable(checkable)
    (action.toggled if checkable else action.triggered).connect(slot)
    return action


def populate(target, *items) -> None:
    """Add actions to a menu or toolbar, a `None` item standing for a separator."""
    for item in items:
        if item is None:
            target.addSeparator()
        else:
            target.addAction(item)


__all__ = ["make_action", "populate"]
