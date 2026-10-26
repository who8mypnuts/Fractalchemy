"""Top-level window: loads the Designer layout and wires it to the document."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow

from .. import config
from ..model import rgb_to_hex
from ..widgets import GradientEditor
from .document import GradientDocument
from .file_actions import FileActions
from .loader import load_ui

UI_FILE = Path(__file__).resolve().parents[2] / "ui" / "main_window.ui"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        load_ui(self, UI_FILE, {"GradientEditor": GradientEditor})
        self.document = GradientDocument(self)
        self.gradientEditor.bind(self.document)
        self.files = FileActions(self.document, self)
        self._connect_actions()
        self._connect_document()

    # --- wiring -------------------------------------------------------------
    def _connect_actions(self) -> None:
        self.actionOpen.triggered.connect(self.files.open)
        self.actionSave.triggered.connect(self.files.save)
        self.actionSaveAs.triggered.connect(self.files.save_as)
        self.actionExit.triggered.connect(self.close)
        self.btnOpen.clicked.connect(self.files.open)
        self.btnSaveAs.clicked.connect(self.files.save_as)
        self.files.status.connect(self.statusBar().showMessage)

    def _connect_document(self) -> None:
        self.document.gradient_replaced.connect(self._refresh_header)
        self.document.stop_changed.connect(self._show_stop)
        self.document.selection_changed.connect(self._show_stop)

    # --- presentation -------------------------------------------------------
    def _refresh_header(self) -> None:
        gradient = self.document.gradient
        source = self.document.source_path
        self.lblGradientName.setText(f"{gradient.name}  —  {len(gradient)} nodes" + (f"  ({source.name})" if source else ""))
        self.setWindowTitle(f"{config.APP_NAME} — {gradient.name}" if gradient.stops else config.APP_NAME)

    def _show_stop(self, index: int) -> None:
        stops = self.document.gradient.stops
        if 0 <= index < len(stops):
            stop = stops[index]
            self.statusBar().showMessage(f"Node {index + 1}/{len(stops)}  position {stop.position:.3f}  #{rgb_to_hex(stop.color)}")
