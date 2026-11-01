"""*Export DE…*: the current fragment's distance estimator as GLSL, a Shadertoy, a Unity shader or an Unreal include.

A target combo, the generated code in a read-only editor (regenerated when the target changes), the translation's
notes underneath, and *Copy* / *Save…*. The code comes from `fragments/export_de.py` with the document's current
values baked in, so what is exported is what the viewport shows.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from ...fragments.export_de import TARGET_LABELS, TARGETS, DEExport, export_de
from .code_editor import GlslCodeEditor


class ExportDEDialog(QDialog):
    """The export window (see the module docstring)."""

    def __init__(self, parent: QWidget | None, fragment_text: str, values: dict, name: str, folder: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Export DE — {name}")
        self._text, self._values, self._name, self._folder = fragment_text, dict(values), name, folder
        self.result_export: DEExport | None = None
        self.target = QComboBox(self)
        for key in TARGETS:
            self.target.addItem(TARGET_LABELS[key], key)
        self.editor = GlslCodeEditor(self)
        self.editor.setReadOnly(True)
        self.notes = QLabel(self)
        self.notes.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        self.copy_button = buttons.addButton("Copy", QDialogButtonBox.ButtonRole.ActionRole)
        self.save_button = buttons.addButton("Save…", QDialogButtonBox.ButtonRole.ActionRole)
        self.copy_button.clicked.connect(self.copy)
        self.save_button.clicked.connect(self.save)
        buttons.rejected.connect(self.reject)
        top = QHBoxLayout()
        top.addWidget(QLabel("Target:", self))
        top.addWidget(self.target, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.editor, 1)
        layout.addWidget(self.notes)
        layout.addWidget(buttons)
        self.resize(900, 700)
        self.target.currentIndexChanged.connect(lambda _i: self.regenerate())
        self.regenerate()

    def regenerate(self) -> None:
        try:
            self.result_export = export_de(self._text, self._values, str(self.target.currentData()), self._name)
        except ValueError as exc:
            self.result_export = None
            self.editor.set_text(f"// {exc}")
            self.notes.setText(str(exc))
            return
        self.editor.set_text(self.result_export.code)
        self.notes.setText("<br>".join(f"• {note}" for note in self.result_export.notes) or "No remarks — the code is complete as exported.")

    def copy(self) -> None:
        if self.result_export is not None:
            QGuiApplication.clipboard().setText(self.result_export.code)

    def save(self) -> None:
        if self.result_export is None:
            return
        start = (self._folder or Path.home()) / f"{self._name.replace(' ', '_')}_DE{self.result_export.suffix}"
        chosen, _filter = QFileDialog.getSaveFileName(self, "Save the exported DE", str(start))
        if not chosen:
            return
        try:
            Path(chosen).write_text(self.result_export.code, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Export DE", f"Cannot write {chosen}:\n{exc}")


__all__ = ["ExportDEDialog"]
