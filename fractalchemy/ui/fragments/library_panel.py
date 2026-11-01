"""The Fragments window's library pane: folders of `.frag` / `.fafrag` files with thumbnails rendered by the fragment engine.

The host's library machinery (`library/`: model, tree, scanner, controller, context menu) with the fragment catalog.
The bundled example library is always the first root and is read-only — the controller refuses to delete, rename or
drop into it. Thumbnails come from `FragThumbnailProvider`: the fragment is preprocessed on the thread pool, rendered
through the window's render service at thumbnail priority (a few subframes at 160 × 100, the `Default` preset),
and cached in memory and under the cache folder; a `.fafrag` whose metadata carries a thumbnail shows that at once.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QSettings, QSize, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import QWidget

from ... import config
from ...formulas.loader import cache_dir
from ...fragments.document_format import read_fragment
from ...fragments.examples import EXAMPLES_DIR, is_include
from ...fragments.files import FileManager
from ...fragments.gl.job import FragRenderSettings, FragRequest
from ...fragments.glsl_compat import CompatOptions, modernise
from ...fragments.library_format import is_bundled_path
from ...fragments.preprocessor import Preprocessor
from ...fragments.state import ParameterState
from ...fragments.textures import texture_specs
from ...library.catalog import FRAGMENT_CATALOG
from ...library.controller import LibraryController
from ...library.items import LibraryItem
from ...library.model import LibraryModel
from ...library.roots import LibraryRoots
from ...render.service import PRIORITY_THUMBNAIL, RenderService
from ...widgets.images import rgba_to_qimage
from ..background import run_in_background
from ..fractal_library_panel import FractalLibraryPanel

CACHE_LIMIT = 1000
READ_ONLY_MESSAGE = "The bundled example library is read-only — add your own folder for your fragments"


class FragmentLibraryPanel(FractalLibraryPanel):
    """The library tree with the list / thumbnail toggle, for the fragment catalog."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, FRAGMENT_CATALOG)
        self.search.setPlaceholderText("Search fragments…")


class FragmentLibraryController(LibraryController):
    """The generic controller, refusing to change anything inside the bundled library."""

    def _bundled(self, *items: LibraryItem) -> bool:
        """True (with a status message, not a dialog) when any item lives in the bundled library."""
        if any(is_bundled_path(item.path) for item in items):
            self.status.emit(READ_ONLY_MESSAGE)
            return True
        return False

    def drop(self, items, target, move: bool) -> None:
        if self._bundled(target) or (move and self._bundled(*items)):
            return
        super().drop(items, target, move)

    def delete(self, items) -> None:
        if not self._bundled(*items):
            super().delete(items)

    def rename(self, item, new_name: str) -> None:
        if not self._bundled(item):
            super().rename(item, new_name)

    def new_folder(self, target, name: str) -> None:
        if not self._bundled(target):
            super().new_folder(target, name)

    def duplicate(self, item) -> None:
        if not self._bundled(item):
            super().duplicate(item)

    def remove_root(self, path: Path) -> None:
        if is_bundled_path(path):
            self.status.emit("The bundled examples stay in the library")
            return
        super().remove_root(path)


def make_roots(settings: QSettings, parent: QObject | None = None) -> LibraryRoots:
    """The fragment library's folders, the bundled examples always first."""
    roots = LibraryRoots(settings, parent, key=FRAGMENT_CATALOG.roots_key)
    if EXAMPLES_DIR not in roots.paths():
        roots.add(EXAMPLES_DIR)
    return roots


class FragThumbnailProvider(QObject):
    """Renders and caches fragment thumbnails for library rows (see the module docstring).

    Signals:
        thumbnail_ready(LibraryItem): A thumbnail was rendered and stored.
    """
    thumbnail_ready = Signal(object)

    def __init__(self, service: RenderService, model: LibraryModel, capabilities_provider, parent: QObject | None = None):
        """Args:
            service: The window's fragment render service.
            model: The library model to hand icons to.
            capabilities_provider: Returns the engine's `Capabilities` (None while the engine is not ready).
        """
        super().__init__(parent)
        self._service = service
        self._model = model
        self._capabilities = capabilities_provider
        self._cache: OrderedDict[tuple, QIcon] = OrderedDict()
        self._pending: dict[tuple, LibraryItem] = {}
        self._enabled = False
        width, height, self._subframes = config.FRAG_THUMBNAIL
        self._size = QSize(width, height)
        self._placeholder = _placeholder(self._size)
        self._disk = cache_dir() / "fragments" / "thumbs"
        service.pass_done.connect(self._on_pass)
        service.job_failed.connect(self._on_failed)

    @property
    def size(self) -> QSize:
        return self._size

    def set_enabled(self, enabled: bool) -> None:
        """Turn thumbnails on / off (off drops queued renders and shows plain icons)."""
        self._enabled = enabled
        self._model.set_thumbnail_provider(self if enabled else None)
        if not enabled:
            self._service.cancel_where(lambda key: isinstance(key, tuple) and key[0] == "fragthumb")
            self._pending.clear()

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
            run_in_background(self._prepare, item.path, key,
                              on_done=lambda result, k=key: self._prepared(k, result),
                              on_error=lambda exc, k=key: self._pending.pop(k, None))
        return self._placeholder

    def cached(self, item: LibraryItem) -> QIcon | None:
        key = self._key(item)
        return self._cache.get(key) if key else None

    # --- internals ----------------------------------------------------------------------------------------------------
    def _key(self, item: LibraryItem) -> tuple | None:
        try:
            return (item.path, item.path.stat().st_mtime_ns)
        except OSError:
            return None

    def _disk_path(self, key: tuple) -> Path:
        digest = hashlib.sha1(f"{key[0]}:{key[1]}:{self._size.width()}x{self._size.height()}".encode()).hexdigest()
        return self._disk / f"{digest}.png"

    def _prepare(self, path: Path, key: tuple):
        """On the thread pool: an embedded or cached thumbnail as PNG bytes, else the render request."""
        cached = self._disk_path(key)
        if cached.is_file():
            return ("png", cached.read_bytes())
        text, metadata = read_fragment(path)
        if metadata is not None and metadata.thumbnail_png:
            return ("png", metadata.thumbnail_png)
        if is_include(path):
            return None
        caps = self._capabilities()
        if caps is None:
            return None
        source = Preprocessor(FileManager(original=path)).parse(text, path)
        options = CompatOptions("modernise", caps.glsl_version, caps.has_fp64)
        state = ParameterState(source.all_params)
        if "Default" in source.presets:
            state.apply_settings(source.presets["Default"])
        request = FragRequest(modernise(source, options), modernise(source.buffer_shader, options) if source.buffer_shader else None,
                              dict(state.values), source.buffer, source.clear_on_change, source.subframes_between_redraws,
                              source.depth_to_alpha, dict(source.texture_params.get("backbuffer", {})),
                              texture_specs(source, state, FileManager(original=path)))
        return ("render", request)

    def _prepared(self, key: tuple, result) -> None:
        item = self._pending.get(key)
        if item is None or not self._enabled:
            self._pending.pop(key, None)
            return
        if result is None:
            self._pending.pop(key, None)
            return
        kind, payload = result
        if kind == "png":
            image = QImage.fromData(payload)
            self._store(key, item, QIcon(QPixmap.fromImage(image.scaled(self._size))), write=False)
            return
        settings = FragRenderSettings(self._size.width(), self._size.height(), subframe_max=self._subframes,
                                      subframes_per_pass=self._subframes, surface_key=("fragthumb", key), drop_surface=True)
        self._service.submit(("fragthumb", key), payload, settings, PRIORITY_THUMBNAIL)

    def _on_pass(self, key: object, image: np.ndarray, stats) -> None:
        if not (isinstance(key, tuple) and key[0] == "fragthumb"):
            return
        item = self._pending.get(key[1])
        if item is None:
            return
        qimage = rgba_to_qimage(image)
        self._store(key[1], item, QIcon(QPixmap.fromImage(qimage)), write=True, qimage=qimage)

    def _store(self, key: tuple, item: LibraryItem, icon: QIcon, write: bool, qimage: QImage | None = None) -> None:
        self._pending.pop(key, None)
        self._cache[key] = icon
        while len(self._cache) > CACHE_LIMIT:
            self._cache.popitem(last=False)
        if write and qimage is not None:
            try:
                self._disk.mkdir(parents=True, exist_ok=True)
                qimage.save(str(self._disk_path(key)))
            except OSError:
                pass
        self._model.set_thumbnail(item, icon)
        self.thumbnail_ready.emit(item)

    def _on_failed(self, key: object, message: str) -> None:
        if isinstance(key, tuple) and key[0] == "fragthumb":
            self._pending.pop(key[1], None)


def _placeholder(size: QSize) -> QIcon:
    pixmap = QPixmap(size)
    pixmap.fill(QColor(40, 40, 40))
    return QIcon(pixmap)


__all__ = ["FragmentLibraryPanel", "FragmentLibraryController", "FragThumbnailProvider", "make_roots"]
