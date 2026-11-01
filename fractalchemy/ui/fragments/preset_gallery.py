"""*Preset gallery…*: every preset of the current fragment rendered small, side by side; double-click applies one.

Each preset's values are laid over the document's current state and rendered through the window's render service
at thumbnail priority (a few subframes at a small size, one job per preset, dropped surfaces), so the viewport
keeps its accumulation and the editor stays responsive. Presets that carry locks render with the current program —
their locked values cannot change without a rebuild, which the caption notes.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ...fragments.gl.job import FragRenderSettings
from ...render.service import PRIORITY_THUMBNAIL
from ...widgets.images import rgba_to_qimage
from .document import FragDocument

THUMB = QSize(220, 138)
SUBFRAMES = 6
NAME_ROLE = Qt.ItemDataRole.UserRole + 1


class PresetGalleryDialog(QDialog):
    """The gallery (see the module docstring).

    Signals:
        preset_chosen(str): Double-click / OK on a preset.
    """
    preset_chosen = Signal(str)

    def __init__(self, parent: QWidget | None, document: FragDocument, service):
        super().__init__(parent)
        self.setWindowTitle(f"Presets of {document.name}")
        self.document = document
        self.service = service
        self.list = QListWidget(self)
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(THUMB)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setSpacing(8)
        self.list.setWordWrap(True)
        self.list.itemDoubleClicked.connect(self._choose)
        self.summary = QLabel(self)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close, self)
        buttons.accepted.connect(lambda: self._choose(self.list.currentItem()))
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary)
        layout.addWidget(self.list, 1)
        layout.addWidget(buttons)
        self.resize(1000, 640)
        self._items: dict[str, QListWidgetItem] = {}
        self._pending: set[str] = set()
        service.pass_done.connect(self._on_pass)
        service.job_failed.connect(self._on_failed)
        self._populate()

    def _populate(self) -> None:
        source, request = self.document.source, self.document.request()
        names = list(source.presets) if source is not None else []
        self.summary.setText(f"{len(names)} presets — double-click to apply" if names else "The fragment has no presets")
        placeholder = QPixmap(THUMB)
        placeholder.fill(Qt.GlobalColor.darkGray)
        for name in names:
            item = QListWidgetItem(QIcon(placeholder), name)
            item.setData(NAME_ROLE, name)
            item.setSizeHint(QSize(THUMB.width() + 16, THUMB.height() + 40))
            self.list.addItem(item)
            self._items[name] = item
            if request is not None:
                self._render(name, request, source.presets[name])

    def _render(self, name: str, request, body: str) -> None:
        state = self.document.state.copy()
        result = state.apply_settings(body)
        if result.recompile:
            self._items[name].setToolTip("This preset carries locks; shown with the current program's locked values")
        payload = request.copy()
        payload.values.update(state.values)
        key = ("preset-gallery", id(self), name)
        self._pending.add(name)
        settings = FragRenderSettings(THUMB.width(), THUMB.height(), subframe_max=SUBFRAMES, subframes_per_pass=SUBFRAMES,
                                      surface_key=key, drop_surface=True)
        self.service.submit(key, payload, settings, PRIORITY_THUMBNAIL)

    def _on_pass(self, key: object, image, _stats) -> None:
        if not (isinstance(key, tuple) and key[0] == "preset-gallery" and key[1] == id(self)):
            return
        item = self._items.get(key[2])
        if item is not None:
            item.setIcon(QIcon(QPixmap.fromImage(rgba_to_qimage(image))))
        self._pending.discard(key[2])

    def _on_failed(self, key: object, message: str) -> None:
        if isinstance(key, tuple) and key[0] == "preset-gallery" and key[1] == id(self):
            self._pending.discard(key[2])
            item = self._items.get(key[2])
            if item is not None:
                item.setToolTip(f"Could not render: {message}")

    def _choose(self, item: QListWidgetItem | None) -> None:
        if item is not None:
            self.preset_chosen.emit(item.data(NAME_ROLE))
            self.accept()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.service.cancel_where(lambda key: isinstance(key, tuple) and key[0] == "preset-gallery" and key[1] == id(self))
        super().closeEvent(event)


__all__ = ["PresetGalleryDialog"]
