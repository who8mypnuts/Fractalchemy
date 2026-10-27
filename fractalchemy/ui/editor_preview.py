"""The Transform Editor's own small preview: renders the flame being edited, quickly, on every change.

It is what makes dragging feel live: a low-quality render at a small size that follows the mouse, while
the main viewport waits until the edits pause. Only one preview render is in flight at a time — a change
arriving while one runs is rendered as soon as it lands (never sooner than `EDITOR_PREVIEW_THROTTLE_MS`
after the previous start), so every frame delivered is a complete picture and the preview keeps up at
whatever rate the engine manages. Renders go through the shared `RenderService` at `PRIORITY_EDITOR`,
ahead of the viewport. Right-click for the quality — Apophysis's low / medium / high, as `QualityLevel`s:
samples per pixel, supersampling and filter radius (the anti-aliasing the main viewport uses), passes.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QImage, QPainter, QPaintEvent
from PySide6.QtWidgets import QMenu, QSizePolicy, QWidget

from .. import config
from ..render.service import PRIORITY_EDITOR, RenderService
from ..render.settings import RenderSettings, RenderStats
from ..widgets.fractal_preview import _fitted
from .fractal_document import FractalDocument

BACKGROUND = QColor(24, 24, 24)
TEXT = QColor(110, 110, 110)


@dataclass(frozen=True)
class QualityLevel:
    """One entry of the preview's quality menu."""
    name: str
    quality: float          # samples per pixel (Apophysis "density")
    oversample: int         # buckets per pixel side (2 = the viewport's 2×2 anti-aliasing)
    filter_radius: float
    passes: int             # progressive passes: more than one shows a rough picture sooner


QUALITIES = (QualityLevel("Low", 2.0, 1, 0.0, 1), QualityLevel("Medium", 5.0, 2, 0.5, 1), QualityLevel("High", 15.0, 2, 0.5, 2))
DEFAULT_QUALITY = QUALITIES[1]
KEY = ("editor-preview",)
WATCHDOG_MS = 10000


class EditorPreview(QWidget):
    """Renders the document's flame into a small box; `solo` shows one transform alone.

    Signals:
        rendered(RenderStats): After every delivered pass.
        quality_changed(str): The name of the chosen quality level (`Low` / `Medium` / `High`).
    """
    rendered = Signal(object)
    quality_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None, size: tuple[int, int] = config.EDITOR_PREVIEW_SIZE):
        super().__init__(parent)
        self._document: FractalDocument | None = None
        self._service: RenderService | None = None
        self._image: QImage | None = None
        self._stats: RenderStats | None = None
        self._generation = 0
        self._pending = False
        self._busy = False
        self._solo: int | None = None
        self.level: QualityLevel = DEFAULT_QUALITY
        self._throttle = QTimer(self, singleShot=True, interval=config.EDITOR_PREVIEW_THROTTLE_MS)
        self._throttle.timeout.connect(self._flush)
        self._watchdog = QTimer(self, singleShot=True, interval=WATCHDOG_MS)   # a render that never reports frees the slot
        self._watchdog.timeout.connect(self._release)
        self.setFixedSize(QSize(*size))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.setToolTip("The fractal being edited (right-click for the preview quality)")

    def bind(self, document: FractalDocument, service: RenderService) -> None:
        self._document = document
        self._service = service
        service.pass_done.connect(self._on_pass)
        service.job_finished.connect(self._on_finished)
        service.job_failed.connect(self._on_failed)

    # --- state ----------------------------------------------------------------------------------------------
    @property
    def image(self) -> QImage | None:
        return self._image

    @property
    def stats(self) -> RenderStats | None:
        return self._stats

    @property
    def generation(self) -> int:
        """Increments with every render actually submitted (tests wait on it)."""
        return self._generation

    def set_solo(self, index: int | None) -> None:
        """Render only transform `index` (None = all); nothing in the document changes."""
        if index != self._solo:
            self._solo = index
            self.request()

    def set_quality(self, level: "QualityLevel | str | float") -> None:
        """Choose a quality level by object, name, or samples per pixel (the nearest level)."""
        level = quality_level(level)
        if level != self.level:
            self.level = level
            self.quality_changed.emit(level.name)
            self.request()

    # --- rendering ------------------------------------------------------------------------------------------
    def request(self) -> None:
        """Render the current flame: now if nothing is in flight, else as soon as the running render lands."""
        self._pending = True
        if self._document is None or self._service is None or not self.isVisible():
            return
        if not self._busy and not self._throttle.isActive():
            self._flush()

    @property
    def busy(self) -> bool:
        """True while a preview render is in flight (tests)."""
        return self._busy

    def clear(self) -> None:
        self._image = None
        self._stats = None
        self.update()

    def _release(self) -> None:
        """The running render is over (or gave up): start the next one if a change is waiting."""
        self._busy = False
        self._watchdog.stop()
        if self._pending and not self._throttle.isActive():
            self._flush()

    def _flush(self) -> None:
        if not self._pending or self._busy or not self.isVisible():
            return
        self._pending = False
        if self._document is None or self._service is None or self._document.flame is None:
            self.clear()
            return
        flame = self._document.flame.copy()
        if self._solo is not None and 0 <= self._solo < len(flame.xforms):
            for i, x in enumerate(flame.xforms):
                x.opacity = x.opacity if i == self._solo else 0.0
        if not flame.renderable():
            self.clear()
            return
        rect = _fitted(QSize(max(1, flame.camera.width), max(1, flame.camera.height)), self.rect())
        flame.camera = flame.camera.at_size(rect.width(), rect.height())
        level = self.level
        settings = RenderSettings(rect.width(), rect.height(), passes=level.passes, quality=level.quality,
                                  points=config.EDITOR_PREVIEW_POINTS, fuse=config.EDITOR_PREVIEW_FUSE,
                                  oversample=level.oversample, filter_radius=level.filter_radius, refine_to=0.0)
        self._generation += 1
        self._busy = True
        self._service.submit(KEY, flame, settings, PRIORITY_EDITOR)
        self._throttle.start()
        self._watchdog.start()

    def _on_pass(self, key: object, image, stats: RenderStats) -> None:
        if key != KEY:
            return
        h, w = image.shape[:2]
        data = np.ascontiguousarray(image)
        self._image = QImage(data.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        self._stats = stats
        self.rendered.emit(stats)
        self.update()
        if stats.finished:
            self._release()

    def _on_finished(self, key: object, _stats: RenderStats) -> None:
        if key == KEY:
            self._release()

    def _on_failed(self, key: object, _message: str) -> None:
        if key == KEY:
            self.clear()
            self._release()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._pending:
            self.request()

    # --- painting -------------------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND)
        if self._image is None or self._image.isNull():
            painter.setPen(TEXT)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No fractal" if self._document is None or self._document.flame is None else "Rendering…")
        else:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(_fitted(self._image.size(), self.rect()), self._image)
        painter.end()

    def _menu(self, pos) -> None:
        menu = QMenu(self)
        group = QActionGroup(menu)
        for level in QUALITIES:
            action = QAction(f"{level.name} quality", menu)
            action.setToolTip(f"{level.quality:g} samples per pixel" + (", anti-aliased" if level.oversample > 1 else ""))
            action.setCheckable(True)
            action.setChecked(level == self.level)
            action.triggered.connect(lambda _c=False, lv=level: self.set_quality(lv))
            group.addAction(action)
            menu.addAction(action)
        menu.exec(self.mapToGlobal(pos))


def quality_level(value: "QualityLevel | str | float") -> QualityLevel:
    """The level for a name (`High`), a level, or a samples-per-pixel number (the nearest level)."""
    if isinstance(value, QualityLevel):
        return value
    if isinstance(value, str):
        for level in QUALITIES:
            if level.name.lower() == value.strip().lower():
                return level
        try:
            value = float(value)
        except ValueError:
            return DEFAULT_QUALITY
    return min(QUALITIES, key=lambda level: abs(level.quality - float(value)))


__all__ = ["EditorPreview", "QualityLevel", "QUALITIES", "DEFAULT_QUALITY", "quality_level"]
