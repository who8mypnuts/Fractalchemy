"""*File ▸ Import from Shadertoy…*: paste the Image (and Buffer A) code, map the channels, get a fragment tab.

The conversion itself is `fragments.shadertoy.convert`. An Image-only shader opens as an unsaved tab; with a Buffer A
the two files (main + `-image.frag` buffer shader) must live next to each other, so the dialog asks for a folder and
writes them there before opening the main one. Channel rows offer a texture file, *Buffer A* (for Image) / *previous
frame* (for Buffer A) or nothing.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget)

from ...fragments.shadertoy import CHANNELS, Conversion, convert

NONE, FILE, SPECIAL = "none", "file", "special"


class ChannelRow(QWidget):
    """One `iChannelN`: nothing / a texture file / the special source (Buffer A or the previous frame)."""

    def __init__(self, index: int, special_label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.kind = QComboBox()
        self.kind.addItem("not used", NONE)
        self.kind.addItem("texture file", FILE)
        self.kind.addItem(special_label, SPECIAL)
        self.file = QLineEdit()
        self.file.setPlaceholderText("texture file name (next to the fragment)")
        browse = QPushButton("…")
        browse.setFixedWidth(28)
        browse.clicked.connect(self._browse)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(f"iChannel{index}"))
        layout.addWidget(self.kind)
        layout.addWidget(self.file, 1)
        layout.addWidget(browse)

    def _browse(self) -> None:
        chosen, _filter = QFileDialog.getOpenFileName(self, "Texture", "", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.hdr *.exr);;All files (*)")
        if chosen:
            self.file.setText(chosen)
            self.kind.setCurrentIndex(self.kind.findData(FILE))

    def source(self, special_value: str) -> str | None:
        kind = self.kind.currentData()
        if kind == FILE and self.file.text().strip():
            return self.file.text().strip()
        if kind == SPECIAL:
            return special_value
        return None


class ShadertoyDialog(QDialog):
    """Paste, map, import (see the module docstring). `result_conversion` and `target_folder` hold the outcome."""

    def __init__(self, parent: QWidget | None = None, start_folder: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("Import from Shadertoy")
        self.result_conversion: Conversion | None = None
        self.target_folder: Path | None = None
        self._start_folder = start_folder or Path.home()
        self._build()
        self.resize(820, 720)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit("Shadertoy shader")
        form.addRow("Name", self.name)
        layout.addLayout(form)
        self.tabs = QTabWidget()
        self.image_code = QPlainTextEdit()
        self.image_code.setPlaceholderText("Paste the Image tab here: void mainImage(out vec4 fragColor, in vec2 fragCoord) { … }")
        self.buffer_code = QPlainTextEdit()
        self.buffer_code.setPlaceholderText("Optional: paste the Buffer A tab here (its iChannel that reads itself becomes the previous frame)")
        self.tabs.addTab(self._pass_page(self.image_code, "Image channels", "Buffer A", "image"), "Image")
        self.tabs.addTab(self._pass_page(self.buffer_code, "Buffer A channels", "previous frame (feedback)", "buffer"), "Buffer A")
        layout.addWidget(self.tabs, 1)
        self.notes = QLabel()
        self.notes.setWordWrap(True)
        layout.addWidget(self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Import")
        buttons.accepted.connect(self._import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pass_page(self, editor: QPlainTextEdit, title: str, special_label: str, key: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(editor, 1)
        group = QGroupBox(title)
        rows = QVBoxLayout(group)
        setattr(self, f"{key}_channels", [ChannelRow(i, special_label) for i in range(CHANNELS)])
        for row in getattr(self, f"{key}_channels"):
            rows.addWidget(row)
        layout.addWidget(group)
        return page

    def _import(self) -> None:
        buffer_code = self.buffer_code.toPlainText()
        try:
            conversion = convert(self.name.text() or "Shadertoy shader", self.image_code.toPlainText(), buffer_code,
                                 [row.source("bufferA") for row in self.image_channels], [row.source("self") for row in self.buffer_channels])
        except ValueError as exc:
            self.notes.setText(f"Cannot import: {exc}")
            return
        if conversion.image is not None:
            chosen = QFileDialog.getExistingDirectory(self, "Folder for the two fragment files", str(self._start_folder))
            if not chosen:
                return
            self.target_folder = Path(chosen)
        self.result_conversion = conversion
        self.accept()


__all__ = ["ShadertoyDialog", "ChannelRow"]
