"""Renders a list of in-memory flames into small images through the shared render service (the Mutate & Breed grid).

    renderer = GridRenderer(service, QSize(200, 150), parent)
    renderer.image_ready.connect(lambda slot, image: grid.set_image(slot, image))
    renderer.render({0: flame_a, 1: flame_b, …})     # a new call cancels whatever the previous one still had queued

Renders run at `PRIORITY_THUMBNAIL`, so the main viewport and the editors' previews always go first. Every call to
`render` starts a new *generation*; passes from an older generation are ignored, so a regenerated grid never shows a
stale picture.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, QSize, Signal
from PySide6.QtGui import QImage

from .. import config
from ..fractal.scene import Flame
from ..render.service import PRIORITY_THUMBNAIL, RenderService
from ..render.settings import RenderSettings
from ..widgets.images import rgba_to_qimage

GRID_POINTS = 8192           # a small population, as for the library thumbnails


class GridRenderer(QObject):
    """Small renders of several flames at once (see the module docstring).

    Signals:
        image_ready(int, QImage): A pass of slot `int` arrived (each slot may report more than once as it refines).
    """
    image_ready = Signal(int, QImage)

    def __init__(self, service: RenderService, size: QSize, parent: QObject | None = None):
        super().__init__(parent)
        self._service = service
        self._size = QSize(size)
        self._generation = 0
        service.pass_done.connect(self._on_pass)

    @property
    def generation(self) -> int:
        """Increments with every `render` call."""
        return self._generation

    def set_size(self, size: QSize) -> None:
        """The image size of later renders."""
        self._size = QSize(max(16, size.width()), max(16, size.height()))

    def render(self, flames: dict[int, Flame]) -> None:
        """Render `flames` (slot → flame), cancelling the previous generation."""
        self.cancel()
        self._generation += 1
        for slot, flame in flames.items():
            self.render_slot(slot, flame)

    def render_slot(self, slot: int, flame: Flame) -> None:
        """Render one more slot in the current generation (the offspring, once they are made)."""
        settings = RenderSettings(self._size.width(), self._size.height(), passes=config.MUTATION_PASSES,
                                  quality=config.MUTATION_QUALITY, points=GRID_POINTS)
        self._service.submit(self._key(slot), flame, settings, PRIORITY_THUMBNAIL)

    def cancel(self) -> None:
        """Drop every queued or running render of this renderer."""
        mine = ("grid", id(self))
        self._service.cancel_where(lambda key: isinstance(key, tuple) and key[:2] == mine)

    def _key(self, slot: int) -> tuple:
        return ("grid", id(self), self._generation, slot)

    def _on_pass(self, key: object, image: np.ndarray, _stats) -> None:
        if isinstance(key, tuple) and key[:3] == ("grid", id(self), self._generation):
            self.image_ready.emit(key[3], rgba_to_qimage(image))


__all__ = ["GridRenderer"]
