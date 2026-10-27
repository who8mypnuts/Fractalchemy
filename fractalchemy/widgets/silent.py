"""Update Qt input widgets without triggering their change signals."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from typing import Iterator

from PySide6.QtCore import QObject, QSignalBlocker
from PySide6.QtWidgets import QWidget


@contextmanager
def blocked(*objects: QObject) -> Iterator[None]:
    """Block the signals of several objects for the duration of a `with` block (e.g. while a panel shows a model)."""
    with ExitStack() as stack:
        for obj in objects:
            stack.enter_context(QSignalBlocker(obj))
        yield


def set_value_silently(widget: QWidget, value: int, minimum: int | None = None, maximum: int | None = None) -> None:
    """Set a spin box / slider value (and optionally its range) with signals blocked.

    Used when a control is being synchronised *from* the model so the change is
    not echoed back as a user edit. The range is applied first because shrinking
    it can clamp the current value, which would otherwise emit too.
    """
    with QSignalBlocker(widget):
        if minimum is not None and maximum is not None:
            widget.setRange(minimum, maximum)
        widget.setValue(value)
