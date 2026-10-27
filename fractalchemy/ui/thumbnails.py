"""Thumbnails for the Fractal Library, rendered by the preview engine at low priority.

The model asks `icon_for(item)` while painting rows; unknown items get a placeholder
and a background load + render is started. Results are cached in memory keyed by
(path, index, mtime), so edited files get fresh thumbnails after a rescan.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QSize, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap

from .. import config
from ..fractal.formats import load_flame
from ..library.items import LibraryItem
from ..library.model import LibraryModel
from ..render.service import PRIORITY_THUMBNAIL, RenderService
from ..render.settings import RenderSettings
from .background import run_in_background

CACHE_LIMIT = 2000
THUMBNAIL_POINTS = 8192


class ThumbnailProvider(QObject):
    """Lazily renders and caches flame thumbnails for library rows.

    Signals:
        thumbnail_ready(LibraryItem): A thumbnail was rendered and stored.
    """
    thumbnail_ready = Signal(object)

    def __init__(self, service: RenderService, model: LibraryModel, parent: QObject | None = None):
        super().__init__(parent)
        self._service = service
        self._model = model
        self._cache: OrderedDict[tuple, QIcon] = OrderedDict()
        self._pending: dict[tuple, LibraryItem] = {}
        self._enabled = False
        self._size = QSize(*config.THUMBNAIL_SIZE)
        self._placeholder = _placeholder(self._size)
        self._virtual: dict[Path, tuple[int, list]] = {}   # path of in-memory entries -> (batch id, flames)
        self._virtual_id = 0
        service.pass_done.connect(self._on_pass)
        service.job_failed.connect(self._on_failed)

    @property
    def size(self) -> QSize:
        return self._size

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Turn thumbnail rendering on/off (off drops queued renders and shows plain icons)."""
        self._enabled = enabled
        self._model.set_thumbnail_provider(self if enabled else None)
        if not enabled:
            self._service.cancel_where(lambda key: isinstance(key, tuple) and key[0] == "thumb")
            self._pending.clear()

    def set_virtual(self, path: Path | None, flames: list | None = None) -> None:
        """Serve thumbnails for in-memory `flames` listed under `path` (None forgets every virtual source)."""
        self._virtual_id += 1
        self._virtual = {} if path is None or flames is None else {Path(path): (self._virtual_id, list(flames))}

    def icon_for(self, item: LibraryItem) -> QIcon | None:
        """Cached thumbnail, or a placeholder after scheduling a render."""
        key = self._key(item)
        if key is None:
            return None
        icon = self._cache.get(key)
        if icon is not None:
            self._cache.move_to_end(key)
            return icon
        if key not in self._pending:
            self._pending[key] = item
            virtual = self._virtual.get(item.path)
            if virtual is not None:
                if 0 <= item.index < len(virtual[1]):
                    self._render(key, virtual[1][item.index])
                else:
                    self._pending.pop(key, None)
            else:
                run_in_background(load_flame, item.path, item.index,
                                  on_done=lambda flame, k=key: self._render(k, flame),
                                  on_error=lambda exc, k=key: self._pending.pop(k, None))
        return self._placeholder

    def cached(self, item: LibraryItem) -> QIcon | None:
        key = self._key(item)
        return self._cache.get(key) if key else None

    # --- internals ----------------------------------------------------------
    def _key(self, item: LibraryItem) -> tuple | None:
        virtual = self._virtual.get(item.path)
        if virtual is not None:
            return (item.path, item.index, -virtual[0])
        try:
            mtime = item.path.stat().st_mtime_ns
        except OSError:
            return None
        return (item.path, item.index, mtime)

    def _render(self, key: tuple, flame) -> None:
        if key not in self._pending or not self._enabled:
            self._pending.pop(key, None)
            return
        settings = RenderSettings(self._size.width(), self._size.height(), passes=config.THUMBNAIL_PASSES,
                                  quality=config.THUMBNAIL_QUALITY, points=THUMBNAIL_POINTS)
        self._service.submit(("thumb", key), flame, settings, PRIORITY_THUMBNAIL)

    def _on_pass(self, key: object, image: np.ndarray, stats) -> None:
        if not (isinstance(key, tuple) and key[0] == "thumb"):
            return
        item = self._pending.pop(key[1], None)
        if item is None:
            return
        h, w = image.shape[:2]
        qimage = QImage(np.ascontiguousarray(image).data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        icon = QIcon(QPixmap.fromImage(qimage))
        self._cache[key[1]] = icon
        while len(self._cache) > CACHE_LIMIT:
            self._cache.popitem(last=False)
        self._model.set_thumbnail(item, icon)
        self.thumbnail_ready.emit(item)

    def _on_failed(self, key: object, message: str) -> None:
        if isinstance(key, tuple) and key[0] == "thumb":
            self._pending.pop(key[1], None)


def _placeholder(size: QSize) -> QIcon:
    pixmap = QPixmap(size)
    pixmap.fill(QColor(40, 40, 40))
    return QIcon(pixmap)


__all__ = ["ThumbnailProvider"]
