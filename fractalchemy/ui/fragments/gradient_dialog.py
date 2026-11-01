"""*Edit ▸ Insert gradient…*: turn a gradient into GLSL for the current fragment (FragM's ggr2glsl, generalised).

The source is the Gradient Library's current gradient or any gradient file the host reads (GIMP `.ggr` keeps its
exact segment shapes; other formats become linear RGB segments). The preview strip is drawn from the same
Python evaluator the GLSL mirrors. *Insert* puts the text at the editor's cursor, *Copy* on the clipboard; the
texture form also writes the PNG strip next to the fragment (or where the user picks when the tab is unsaved).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget)

from ...formats import FormatError, load_gradients, open_dialog_filter
from ...formats.ggr import Segment, read_ggr, sample_segments, segments_from_gradient
from ...fragments.gradient_glsl import DEFAULT_TABLE_SIZE, FORMS, ROLES, GradientGlslOptions, gradient_glsl, write_strip
from ...model import Gradient
from ...widgets.images import palette_pixmap

FORM_LABELS = {"segments": "Segments (exact, GIMP blend shapes)", "table": "Sampled table (const vec3[N])",
               "texture": "1-D texture (PNG strip + file[…])"}
ROLE_LABELS = {"function": "Function only", "object": "Object colour (baseColor)", "background": "Sky (backgroundColor)"}
STRIP_HEIGHT = 24


class GradientDialog(QDialog):
    """Pick a gradient and how to emit it; `result_text()` is the GLSL, `accepted_action` is 'insert' or 'copy'."""

    def __init__(self, parent: QWidget | None, library_gradient: Callable[[], Gradient | None] | None = None,
                 fragment_dir: Path | None = None):
        """Args:
            parent: The Fragments window.
            library_gradient: Returns the Gradient Library's current gradient (None when no library is around).
            fragment_dir: Where the texture form writes its strip (asked for when None).
        """
        super().__init__(parent)
        self.setWindowTitle("Insert gradient")
        self._library_gradient = library_gradient
        self._fragment_dir = fragment_dir
        self._name = "gradient"
        self._segments: list[Segment] = []
        self._entries: list[Gradient] = []
        self.accepted_action = "insert"
        self._build()
        self._pick_library() if library_gradient is not None else self._enable_file()

    # --- layout --------------------------------------------------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._source_group())
        self.preview = QLabel()
        self.preview.setMinimumHeight(STRIP_HEIGHT)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview)
        self.info = QLabel()
        layout.addWidget(self.info)
        layout.addWidget(self._output_group())
        buttons = QDialogButtonBox()
        self.insert_button = buttons.addButton("Insert", QDialogButtonBox.ButtonRole.AcceptRole)
        self.copy_button = buttons.addButton("Copy", QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.copy_button.clicked.connect(self._copy)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _source_group(self) -> QGroupBox:
        group = QGroupBox("Gradient")
        form = QVBoxLayout(group)
        self.library_radio = QRadioButton("The Gradient Library's current gradient")
        self.library_radio.setEnabled(self._library_gradient is not None)
        self.library_radio.toggled.connect(lambda on: on and self._pick_library())
        form.addWidget(self.library_radio)
        row = QHBoxLayout()
        self.file_radio = QRadioButton("File:")
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        self.entry_combo = QComboBox()
        self.entry_combo.currentIndexChanged.connect(self._entry_changed)
        row.addWidget(self.file_radio)
        row.addWidget(self.file_edit, 1)
        row.addWidget(browse)
        row.addWidget(self.entry_combo)
        form.addLayout(row)
        return group

    def _output_group(self) -> QGroupBox:
        group = QGroupBox("GLSL")
        form = QFormLayout(group)
        self.name_edit = QLineEdit("gradient")
        form.addRow("Function name", self.name_edit)
        self.form_combo = QComboBox()
        for key in FORMS:
            self.form_combo.addItem(FORM_LABELS[key], key)
        self.form_combo.currentIndexChanged.connect(self._form_changed)
        form.addRow("Form", self.form_combo)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(2, 4096)
        self.size_spin.setValue(DEFAULT_TABLE_SIZE)
        form.addRow("Samples", self.size_spin)
        self.texture_edit = QLineEdit("gradient.png")
        form.addRow("Texture file", self.texture_edit)
        self.role_combo = QComboBox()
        for key in ROLES:
            self.role_combo.addItem(ROLE_LABELS[key], key)
        form.addRow("Use as", self.role_combo)
        self._form_changed()
        return group

    # --- sources ------------------------------------------------------------------------------------------------------------
    def _enable_file(self) -> None:
        self.file_radio.setChecked(True)

    def _pick_library(self) -> None:
        self.library_radio.setChecked(True)
        gradient = self._library_gradient() if self._library_gradient else None
        if gradient is None or not gradient.stops:
            self._set_segments("gradient", [])
            return
        self._set_segments(gradient.name, segments_from_gradient(gradient))

    def _browse(self) -> None:
        chosen, _filter = QFileDialog.getOpenFileName(self, "Gradient file", self.file_edit.text(), open_dialog_filter())
        if chosen:
            self.load_file(Path(chosen))

    def load_file(self, path: Path) -> None:
        """Use `path` (a `.ggr` keeps its segment shapes; multi-entry files offer an entry combo)."""
        self.file_radio.setChecked(True)
        self.file_edit.setText(str(path))
        self._entries = []
        try:
            if path.suffix.lower() == ".ggr":
                name, segments = read_ggr(path)
                self._fill_entries([])
                self._set_segments(name, segments)
                return
            self._entries = load_gradients(path)
        except (OSError, FormatError, ValueError) as exc:
            self._fill_entries([])
            self._set_segments(path.stem, [])
            self.info.setText(f"Could not read {path.name}: {exc}")
            return
        self._fill_entries([g.name for g in self._entries])
        self._entry_changed(0)

    def _fill_entries(self, names: list[str]) -> None:
        self.entry_combo.blockSignals(True)
        self.entry_combo.clear()
        self.entry_combo.addItems(names)
        self.entry_combo.setVisible(len(names) > 1)
        self.entry_combo.blockSignals(False)

    def _entry_changed(self, index: int) -> None:
        if 0 <= index < len(self._entries):
            entry = self._entries[index]
            self._set_segments(entry.name, segments_from_gradient(entry))

    def _set_segments(self, name: str, segments: list[Segment]) -> None:
        self._name, self._segments = name, segments
        self._refresh_preview()

    # --- output --------------------------------------------------------------------------------------------------------------
    def _form_changed(self) -> None:
        form = self.form_combo.currentData()
        self.size_spin.setEnabled(form != "segments")
        self.texture_edit.setEnabled(form == "texture")

    def _refresh_preview(self) -> None:
        ok = bool(self._segments)
        self.insert_button.setEnabled(ok)
        self.copy_button.setEnabled(ok)
        if not ok:
            self.preview.clear()
            self.info.setText("No gradient selected")
            return
        colors = [tuple(int(round(c * 255)) for c in rgb) for rgb in sample_segments(self._segments, 256)]
        self.preview.setPixmap(palette_pixmap(colors, 480, STRIP_HEIGHT))
        self.info.setText(f"{self._name} — {len(self._segments)} segments")

    def options(self) -> GradientGlslOptions:
        """The emitter options as set in the dialog."""
        return GradientGlslOptions(self.name_edit.text() or "gradient", self.form_combo.currentData(), self.size_spin.value(),
                                   self.role_combo.currentData(), self.texture_edit.text() or "gradient.png")

    def result_text(self) -> str:
        """The GLSL for the chosen gradient and options ('' when nothing is selected)."""
        if not self._segments:
            return ""
        return gradient_glsl(self._name, self._segments, self.options())

    def write_texture_if_needed(self) -> Path | None:
        """For the texture form: write the PNG strip beside the fragment (or where the user says) and return its path."""
        options = self.options()
        if options.form != "texture" or not self._segments:
            return None
        directory = self._fragment_dir
        if directory is None:
            chosen, _filter = QFileDialog.getSaveFileName(self, "Save gradient strip", options.texture_file, "PNG (*.png)")
            if not chosen:
                return None
            target = Path(chosen)
            self.texture_edit.setText(target.name)
        else:
            target = directory / options.texture_file
        write_strip(self._segments, target, options.table_size)
        return target

    def _copy(self) -> None:
        self.accepted_action = "copy"
        self.accept()
