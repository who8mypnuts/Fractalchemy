"""The Mutate & Breed window's option panels: `MutatePanel` (how mutants are made) and `BreedPanel` (the second parent
and how children are made). They only gather options and announce requests; the window does the work.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout,
                               QWidget)

from ..fractal import breeding as B
from ..fractal import mutation as M
from ..fractal import variations as V
from ..fractal.scene import Flame
from ..library.catalog import FRACTAL_CATALOG
from ..library.items import LibraryItem
from ..library.payload import from_mime
from ..widgets.silent import updating
from ..widgets.theming import set_themed_style

RANDOM_TREND = "Random"
PARENT_THUMB = (150, 100)


class MutatePanel(QWidget):
    """Strength, which kinds of change, a trend variation and the two Apophysis switches.

    Signals:
        options_changed(): Any option changed (the window saves them).
        regenerate_requested(): *New mutants*.
    """
    options_changed = Signal()
    regenerate_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._updating = False
        self.strength = QSlider(Qt.Orientation.Horizontal, self)
        self.strength_label = QLabel(self)
        self.kind_boxes: dict[str, QCheckBox] = {}
        self.trend = QComboBox(self)
        self.keep_count = QCheckBox("Same number of transforms", self)
        self.keep_symmetry = QCheckBox("Keep symmetry", self)
        self.regenerate_button = QPushButton("New mutants", self)
        self._build()
        self.populate_trends()
        self.set_options(M.MutationOptions())

    def _build(self) -> None:
        self.strength.setRange(1, 100)
        self.strength.setToolTip("How far the mutants stray from the parent: a little (left) to wildly (right)")
        self.trend.setToolTip("A variation the mutations favour when they swap or add one (Apophysis's Trend)")
        self.keep_count.setToolTip("Never add or remove transforms (drift stays within the parent's transforms)")
        self.keep_symmetry.setToolTip("Leave symmetry transforms alone (colour speed 0 — Apophysis's symmetry = 1)")
        self.regenerate_button.setToolTip("Make a new set of mutants of the current fractal (Space in the grid, or F5)")
        strength_row = QHBoxLayout()
        strength_row.addWidget(self.strength, 1)
        strength_row.addWidget(self.strength_label)
        kinds = QGroupBox("What may change", self)
        kinds_layout = QVBoxLayout(kinds)
        for kind in M.ORDER:
            box = QCheckBox(M.KIND_LABELS[kind], kinds)
            box.setToolTip(M.KIND_TIPS[kind])
            box.toggled.connect(self._changed)
            kinds_layout.addWidget(box)
            self.kind_boxes[kind] = box
        form = QFormLayout()
        form.addRow("Strength", strength_row)
        form.addRow("Trend", self.trend)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(kinds)
        layout.addWidget(self.keep_count)
        layout.addWidget(self.keep_symmetry)
        layout.addWidget(self.regenerate_button)
        layout.addStretch(1)
        self.strength.valueChanged.connect(self._changed)
        self.trend.currentIndexChanged.connect(self._changed)
        self.keep_count.toggled.connect(self._changed)
        self.keep_symmetry.toggled.connect(self._changed)
        self.regenerate_button.clicked.connect(self.regenerate_requested)

    def populate_trends(self) -> None:
        """(Re)list the trend choices: *Random*, then every loaded formula (call when formulas change)."""
        current = self.trend.currentText() or RANDOM_TREND
        with updating(self):
            self.trend.clear()
            self.trend.addItem(RANDOM_TREND, None)
            for name in V.catalogue():
                self.trend.addItem(name, name)
            self.trend.setCurrentIndex(max(0, self.trend.findText(current)))

    def options(self) -> M.MutationOptions:
        """The options as set."""
        kinds = frozenset(kind for kind, box in self.kind_boxes.items() if box.isChecked())
        return M.MutationOptions(strength=self.strength.value() / 100.0, kinds=kinds, trend=self.trend.currentData(),
                                 keep_count=self.keep_count.isChecked(), keep_symmetry=self.keep_symmetry.isChecked())

    def set_options(self, options: M.MutationOptions) -> None:
        """Show `options` (emits nothing)."""
        with updating(self):
            self.strength.setValue(round(options.strength * 100))
            for kind, box in self.kind_boxes.items():
                box.setChecked(kind in options.kinds)
            self.trend.setCurrentIndex(max(0, self.trend.findData(options.trend)) if options.trend else 0)
            self.keep_count.setChecked(options.keep_count)
            self.keep_symmetry.setChecked(options.keep_symmetry)
        self._show_strength()

    def _show_strength(self) -> None:
        self.strength_label.setText(f"{self.strength.value()} %")

    def _changed(self, *_args) -> None:
        self._show_strength()
        if not self._updating:
            self.options_changed.emit()

    # --- persistence ----------------------------------------------------------------------------------------------
    def save(self, settings: QSettings, prefix: str) -> None:
        """Write the options under `prefix`."""
        o = self.options()
        settings.setValue(f"{prefix}/strength", o.strength)
        settings.setValue(f"{prefix}/kinds", ",".join(sorted(o.kinds)))
        settings.setValue(f"{prefix}/trend", o.trend or "")
        settings.setValue(f"{prefix}/keep_count", o.keep_count)
        settings.setValue(f"{prefix}/keep_symmetry", o.keep_symmetry)

    def load(self, settings: QSettings, prefix: str) -> None:
        """Read the options written by `save` (defaults for anything missing or broken)."""
        default = M.MutationOptions()
        try:
            strength = float(settings.value(f"{prefix}/strength", default.strength))
        except (TypeError, ValueError):
            strength = default.strength
        kinds = settings.value(f"{prefix}/kinds", None)
        kinds = frozenset(k for k in str(kinds).split(",") if k in M.OPERATORS) if kinds is not None else default.kinds
        trend = str(settings.value(f"{prefix}/trend", "") or "") or None
        self.set_options(M.MutationOptions(strength=min(1.0, max(0.01, strength)), kinds=kinds,
                                           trend=trend if trend in V.REGISTRY else None,
                                           keep_count=_flag(settings.value(f"{prefix}/keep_count", default.keep_count)),
                                           keep_symmetry=_flag(settings.value(f"{prefix}/keep_symmetry", default.keep_symmetry))))


class ParentSlot(QLabel):
    """The second parent's picture; accepts Fractal Library rows dropped on it.

    Signals:
        dropped(list): The `LibraryItem`s dropped.
    """
    dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedSize(*PARENT_THUMB)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setToolTip("The second parent: drag a fractal here from the Fractal Library, or use the buttons")
        set_themed_style(self, "QLabel {{ background: {canvas_bg}; color: {canvas_text}; border: 1px solid {border}; }}")
        self.setText("Drop a fractal here")

    def show_image(self, image: QImage | None) -> None:
        """The parent's rendered picture (None: the drop hint)."""
        if image is None:
            self.setPixmap(QPixmap())
            self.setText("Drop a fractal here")
        else:
            self.setPixmap(QPixmap.fromImage(image).scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                           Qt.TransformationMode.SmoothTransformation))

    def _items(self, event) -> list[LibraryItem]:
        return [i for i in from_mime(event.mimeData(), FRACTAL_CATALOG.key) if i.opens_entry and not i.virtual]

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._items(event):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        items = self._items(event)
        if items:
            event.acceptProposedAction()
            self.dropped.emit(items)


class BreedPanel(QWidget):
    """The second parent (B; the current fractal is A) and how children are made.

    Signals:
        options_changed(): Any option changed.
        regenerate_requested(): *New children*.
        use_current_requested(): *Use current fractal* as parent B.
        open_requested(): *Open…* a file for parent B.
        dropped(list): Fractal Library rows were dropped on the parent slot.
    """
    options_changed = Signal()
    regenerate_requested = Signal()
    use_current_requested = Signal()
    open_requested = Signal()
    dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._updating = False
        self.parent_b: Flame | None = None
        self.slot = ParentSlot(self)
        self.parent_name = QLabel("No second parent yet", self)
        self.use_current_button = QPushButton("Use current fractal", self)
        self.open_button = QPushButton("Open…", self)
        self.mode = QComboBox(self)
        self.gradient = QComboBox(self)
        self.camera = QComboBox(self)
        self.regenerate_button = QPushButton("New children", self)
        self._build()

    def _build(self) -> None:
        self.parent_name.setWordWrap(True)
        self.use_current_button.setToolTip("Take the fractal shown in the main window as parent B (then show another one as A)")
        self.open_button.setToolTip("Load parent B from a fractal file (the first fractal in it)")
        self.regenerate_button.setToolTip("Make a new set of children of the current fractal (A) and parent B (Space in the grid, or F5)")
        for combo, values, labels, tip in ((self.mode, B.MODES, B.MODE_LABELS, "How the parents' transforms combine"),
                                           (self.gradient, B.GRADIENT_SOURCES, B.SOURCE_LABELS, "Where the children's gradient comes from"),
                                           (self.camera, B.CAMERA_SOURCES, B.SOURCE_LABELS, "Where the children's camera and colouring come from")):
            for value in values:
                combo.addItem(labels[value], value)
                if labels is B.MODE_LABELS:
                    combo.setItemData(combo.count() - 1, B.MODE_TIPS[value], Qt.ItemDataRole.ToolTipRole)
            combo.setToolTip(tip)
            combo.currentIndexChanged.connect(self._changed)
        parent_box = QGroupBox("Parent B", self)
        buttons = QHBoxLayout()
        buttons.addWidget(self.use_current_button)
        buttons.addWidget(self.open_button)
        parent_layout = QVBoxLayout(parent_box)
        parent_layout.addWidget(self.slot, 0, Qt.AlignmentFlag.AlignHCenter)
        parent_layout.addWidget(self.parent_name)
        parent_layout.addLayout(buttons)
        form = QFormLayout()
        form.addRow("Combine", self.mode)
        form.addRow("Gradient", self.gradient)
        form.addRow("Camera", self.camera)
        note = QLabel("Parent A is the fractal shown in the main window.", self)
        note.setWordWrap(True)
        set_themed_style(note, "color: {dim_text};")
        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addWidget(parent_box)
        layout.addLayout(form)
        layout.addWidget(self.regenerate_button)
        layout.addStretch(1)
        self.use_current_button.clicked.connect(self.use_current_requested)
        self.open_button.clicked.connect(self.open_requested)
        self.regenerate_button.clicked.connect(self.regenerate_requested)
        self.slot.dropped.connect(self.dropped)

    def set_parent_b(self, flame: Flame | None, where: str = "") -> None:
        """The second parent (the picture arrives with `show_parent_image`)."""
        self.parent_b = flame.copy() if flame is not None else None
        self.parent_name.setText(f"{flame.name}" + (f"\n{where}" if where else "") if flame is not None else "No second parent yet")
        self.slot.show_image(None)
        if flame is not None:
            self.slot.setText("rendering…")

    def show_parent_image(self, image: QImage) -> None:
        """Parent B's rendered picture."""
        self.slot.show_image(image)

    def options(self) -> B.BreedOptions:
        """The options as set."""
        return B.BreedOptions(mode=self.mode.currentData(), gradient=self.gradient.currentData(), camera=self.camera.currentData())

    def set_options(self, options: B.BreedOptions) -> None:
        """Show `options` (emits nothing)."""
        with updating(self):
            for combo, value in ((self.mode, options.mode), (self.gradient, options.gradient), (self.camera, options.camera)):
                combo.setCurrentIndex(max(0, combo.findData(value)))

    def _changed(self, *_args) -> None:
        if not self._updating:
            self.options_changed.emit()

    def save(self, settings: QSettings, prefix: str) -> None:
        """Write the options under `prefix`."""
        o = self.options()
        for key, value in (("mode", o.mode), ("gradient", o.gradient), ("camera", o.camera)):
            settings.setValue(f"{prefix}/{key}", value)

    def load(self, settings: QSettings, prefix: str) -> None:
        """Read the options written by `save`."""
        default = B.BreedOptions()
        self.set_options(B.BreedOptions(mode=_choice(settings.value(f"{prefix}/mode"), B.MODES, default.mode),
                                        gradient=_choice(settings.value(f"{prefix}/gradient"), B.GRADIENT_SOURCES, default.gradient),
                                        camera=_choice(settings.value(f"{prefix}/camera"), B.CAMERA_SOURCES, default.camera)))


def _flag(value) -> bool:
    return value in (True, "true", "True", 1, "1")


def _choice(value, allowed: tuple[str, ...], default: str) -> str:
    return value if value in allowed else default


__all__ = ["MutatePanel", "BreedPanel", "ParentSlot", "RANDOM_TREND"]
