"""The History dock: a strip of thumbnails of earlier looks, and the *Mutate* controls that explore from the current one.

Exploring a fractal is a random walk: nudge the sliders, look, keep or go back. Every snapshot holds the viewport's
image and the settings text; clicking one applies those settings again (an undoable step). Snapshots are taken by
hand (*Snapshot*), before every *Mutate* / *Randomize* (so the look before the jump is never lost), and — with *Auto*
on — a moment after any parameter change once the viewport shows it. The strip is per document; it is not saved.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSlider, QToolButton, QVBoxLayout, QWidget

THUMB = QSize(120, 75)
CAPACITY = 80
AUTO_DELAY_MS = 2500
SETTINGS_ROLE = Qt.ItemDataRole.UserRole + 1


class HistoryStrip(QWidget):
    """The strip and the mutate row (see the module docstring).

    Signals:
        restore_requested(str): A thumbnail was clicked: apply this settings text.
        snapshot_requested(): *Snapshot*.
        mutate_requested(float, bool): *Mutate* by strength (0..1), current group only?
        randomize_requested(bool): *Randomize* (current group only?).
    """
    restore_requested = Signal(str)
    snapshot_requested = Signal()
    mutate_requested = Signal(float, bool)
    randomize_requested = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.list = QListWidget(self)
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setFlow(QListWidget.Flow.LeftToRight)
        self.list.setWrapping(False)
        self.list.setIconSize(THUMB)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setFixedHeight(THUMB.height() + 44)
        self.list.itemClicked.connect(self._on_clicked)
        self.snapshot = QToolButton(self)
        self.snapshot.setText("Snapshot")
        self.snapshot.setToolTip("Keep the current look in the strip")
        self.auto = QCheckBox("Auto", self)
        self.auto.setToolTip("Take a snapshot by itself a moment after the parameters change")
        self.clear_button = QToolButton(self)
        self.clear_button.setText("Clear")
        self.strength = QSlider(Qt.Orientation.Horizontal, self)
        self.strength.setRange(1, 100)
        self.strength.setValue(10)
        self.strength.setToolTip("Mutation strength: how far a slider may move, as a share of its range")
        self.strength_label = QLabel("10%", self)
        self.strength.valueChanged.connect(lambda v: self.strength_label.setText(f"{v}%"))
        self.group_only = QCheckBox("Current group only", self)
        self.mutate = QPushButton("Mutate", self)
        self.mutate.setToolTip("Nudge the unlocked parameters at random by up to the strength (Shift+F6); a snapshot is taken first")
        self.randomize = QPushButton("Randomize", self)
        self.randomize.setToolTip("Random values over the whole ranges (F6); a snapshot is taken first")
        self.snapshot.clicked.connect(self.snapshot_requested)
        self.clear_button.clicked.connect(self.clear)
        self.mutate.clicked.connect(lambda: self.mutate_requested.emit(self.strength.value() / 100.0, self.group_only.isChecked()))
        self.randomize.clicked.connect(lambda: self.randomize_requested.emit(self.group_only.isChecked()))
        row = QHBoxLayout()
        row.addWidget(self.snapshot)
        row.addWidget(self.auto)
        row.addWidget(self.clear_button)
        row.addSpacing(12)
        row.addWidget(QLabel("Strength", self))
        row.addWidget(self.strength, 1)
        row.addWidget(self.strength_label)
        row.addWidget(self.group_only)
        row.addWidget(self.mutate)
        row.addWidget(self.randomize)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.addLayout(row)
        layout.addWidget(self.list)
        self._last_settings = ""
        self.auto_timer = QTimer(self, singleShot=True, interval=AUTO_DELAY_MS)

    # --- entries ---------------------------------------------------------------------------------------------------------
    def add_entry(self, image: QImage | None, settings_text: str, label: str = "") -> bool:
        """Append a snapshot (skipped when the settings equal the last entry's); the strip keeps the newest `CAPACITY`."""
        if not settings_text or settings_text == self._last_settings:
            return False
        self._last_settings = settings_text
        item = QListWidgetItem(label or f"{self.list.count() + 1}")
        pixmap = QPixmap.fromImage(image.scaled(THUMB, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)) \
            if image is not None and not image.isNull() else QPixmap(THUMB)
        item.setIcon(QIcon(pixmap))
        item.setData(SETTINGS_ROLE, settings_text)
        item.setToolTip(label or "Click to restore these settings")
        self.list.addItem(item)
        while self.list.count() > CAPACITY:
            self.list.takeItem(0)
        self.list.scrollToItem(item)
        return True

    def clear(self) -> None:
        self.list.clear()
        self._last_settings = ""

    @property
    def count(self) -> int:
        return self.list.count()

    def entries(self) -> list[str]:
        return [self.list.item(i).data(SETTINGS_ROLE) for i in range(self.list.count())]

    def _on_clicked(self, item: QListWidgetItem) -> None:
        text = item.data(SETTINGS_ROLE)
        if text:
            self._last_settings = text
            self.restore_requested.emit(text)


__all__ = ["HistoryStrip", "THUMB", "CAPACITY"]
