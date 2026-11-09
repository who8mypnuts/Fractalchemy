"""Tool-window helpers shared by every window of the application."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def bring_to_front(window: QWidget) -> None:
    """Show `window` (restoring it if minimised), raise it above its siblings and give it the focus.

    Every tool window's `bring_to_front()` starts with this, then adds its own step (refresh a preview, focus an
    editor) if it has one.
    """
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
    window.show()
    window.raise_()
    window.activateWindow()


__all__ = ["bring_to_front"]
