"""Small layout helpers shared by the option panels."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget


def row(*widgets: QWidget, stretch_first: bool = False, stretch_all: bool = False, trailing_stretch: bool = False) -> QHBoxLayout:
    """Widgets side by side in one form row.

    Args:
        *widgets: The widgets, left to right.
        stretch_first: The first widget takes the spare width.
        stretch_all: Every widget shares the spare width.
        trailing_stretch: The spare width trails after the last widget.

    Returns:
        The layout holding the widgets.
    """
    layout = QHBoxLayout()
    for i, widget in enumerate(widgets):
        layout.addWidget(widget, 1 if stretch_all or (stretch_first and i == 0) else 0)
    if trailing_stretch:
        layout.addStretch(1)
    return layout


__all__ = ["row"]
