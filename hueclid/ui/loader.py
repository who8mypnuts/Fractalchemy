"""Load a Qt Designer `.ui` file *into* an existing widget instance.

Stock QUiLoader always creates a new top-level widget, which prevents using a
QMainWindow subclass with signals/slots. This loader hands the top-level back
as `base` and registers every child as an attribute (``self.btnOpen`` etc.),
mirroring the behaviour of PyQt's ``uic.loadUi``. Custom widgets are promoted
by class name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from PySide6.QtCore import QMetaObject
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget


class _InstanceLoader(QUiLoader):
    def __init__(self, base: QWidget, custom_widgets: Mapping[str, type[QWidget]]):
        super().__init__(base)
        self._base = base
        self._custom = dict(custom_widgets)

    def createWidget(self, class_name: str, parent: QWidget | None = None, name: str = ""):
        if parent is None:
            return self._base  # the top-level described by the .ui is our instance
        if class_name in self._custom:
            widget = self._custom[class_name](parent)
            widget.setObjectName(name)
        else:
            widget = super().createWidget(class_name, parent, name)
        setattr(self._base, name, widget)
        return widget


def load_ui(base: QWidget, ui_path: Path | str, custom_widgets: Mapping[str, type[QWidget]] | None = None) -> None:
    loader = _InstanceLoader(base, custom_widgets or {})
    widget = loader.load(str(ui_path))  # no parent: top-level resolves to `base`
    if widget is None:
        raise RuntimeError(f"Failed to load UI file: {ui_path} ({loader.errorString()})")
    QMetaObject.connectSlotsByName(base)
