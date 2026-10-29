"""The formula being worked on in the Formula Editor: its text, where it came from, and its live compilation.

The window owns the widgets; this object owns the *state* — so the compile pipeline, the save / delete
file operations and the registry bookkeeping can be driven (and tested) without a window:

    session = FormulaSession()
    session.load_registered("whorl")          # text from the library file; the real whorl is in the scratch slot
    session.set_text(edited)                  # debounced: compiles on the thread pool, then `compiled` / `failed`
    session.save()                            # writes the per-user .c file and registers the formula for real

Compiles run through `run_in_background`; only the newest text counts — a result that arrives for an older
text is dropped, and a change made while a compile runs is compiled as soon as it lands. The last good
variation stays in the scratch slot (`workbench.SCRATCH_NAME`) while the text is broken, so the previews
keep showing something sensible and the error is reported beside them.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from ..formulas import loader, workbench as W
from ..fractal import variations as V
from .background import run_in_background

COMPILE_DEBOUNCE_MS = 350
ORIGIN_NEW, ORIGIN_REGISTERED, ORIGIN_FILE = "new", "registered", "file"
log = logging.getLogger(__name__)


class FormulaSession(QObject):
    """State and compile pipeline of the formula in the editor.

    Signals:
        text_loaded(): A different formula was loaded; the editor should show `text`.
        compiled(object): The text compiled; the scratch `Variation` (registered already).
        failed(str, object): The text does not compile: (message, 1-based line or None).
        state_changed(): Name, file, origin or modified flag changed (title bar, buttons).
        formulas_changed(): The registry changed — a formula was saved or deleted.
    """
    text_loaded = Signal()
    compiled = Signal(object)
    failed = Signal(str, object)
    state_changed = Signal()
    formulas_changed = Signal()

    def __init__(self, parent: QObject | None = None, user_dir: Path | None = None):
        """Args:
            parent: Qt owner.
            user_dir: Where saved formulas go (the per-user formulas folder by default).
        """
        super().__init__(parent)
        self.user_dir = user_dir
        self.text = ""
        self.name = ""
        self.path: Path | None = None
        self.origin = ORIGIN_NEW
        self.modified = False
        self.variation: V.Variation | None = None     # the last good compile (scratch-named), or the native original
        self.compiled_real: V.Variation | None = None  # the last good compile under its own name (what Save registers)
        self.error: str | None = None
        self.error_line: int | None = None
        self._include_dir: Path | None = None
        self._generation = 0            # bumped per compile request; results of older requests are dropped
        self._running: int | None = None
        self._pending = False
        self._timer = QTimer(self, singleShot=True, interval=COMPILE_DEBOUNCE_MS)
        self._timer.timeout.connect(self.compile_now)

    # --- where saved formulas go ------------------------------------------------------------------------------
    @property
    def folder(self) -> Path:
        """The folder Save writes to."""
        return self.user_dir or loader.user_formula_dir()

    def default_path(self) -> Path:
        """Where Save would write the formula without a file of its own."""
        return self.folder / f"{W.safe_file_name(self.name or W.DEFAULT_NEW_NAME)}.c"

    @property
    def is_user_file(self) -> bool:
        """True when the formula's file is in the user's formulas folder."""
        if self.path is None:
            return False
        return (self.user_dir is not None and self.path.parent == self.user_dir) or W.is_user_file(self.path)

    @property
    def own_file(self) -> Path | None:
        """The file Save writes back to and Delete removes: the user's own (never a bundled library file)."""
        return self.path if self.path is not None and (self.origin == ORIGIN_FILE or self.is_user_file) else None

    @property
    def compiling(self) -> bool:
        """True while a compile is running or scheduled."""
        return self._running is not None or self._timer.isActive()

    @property
    def kind(self) -> str:
        """`normal`, `pre` or `post` for the current variation (normal when there is none)."""
        return self.variation.kind if self.variation is not None else V.NORMAL

    # --- loading ----------------------------------------------------------------------------------------------
    def load_new(self, name: str = W.DEFAULT_NEW_NAME) -> None:
        """The boilerplate for a new formula; compiled at once."""
        self._load(W.new_formula_text(name), W.safe_file_name(name), None, ORIGIN_NEW, compile_now=True)

    def load_blank(self) -> None:
        """An empty editor with nothing in the scratch slot (the window's first state)."""
        self._set_variation(None, None)
        self._load("", "", None, ORIGIN_NEW, compile_now=False)

    def load_registered(self, name: str) -> bool:
        """Load a formula from the registry: its source (or a skeleton for a native one), and itself into the scratch slot
        so the previews show the real thing until the text is changed. False for an unknown name."""
        var = V.REGISTRY.get(name)
        if var is None:
            return False
        path = W.origin_path(var)
        self._set_variation(var, var)
        self._load(W.source_of(var), var.name, path, ORIGIN_REGISTERED, compile_now=False)
        return True

    def load_file(self, path: Path) -> None:
        """Load a `.c` file from anywhere (compiled at once).

        Raises:
            OSError: When the file cannot be read.
        """
        text = path.read_text(encoding="utf-8", errors="replace")
        self._load(text, W.formula_name(text) or path.stem, path, ORIGIN_FILE, compile_now=True)

    def _load(self, text: str, name: str, path: Path | None, origin: str, compile_now: bool) -> None:
        self._timer.stop()
        self._generation += 1          # anything compiling for the old text is stale now
        self._pending = False
        self.text, self.name, self.path, self.origin = text, name, path, origin
        self._include_dir = path.parent if path is not None else self.folder
        self.modified = False
        self.error = self.error_line = None
        self.text_loaded.emit()
        self.state_changed.emit()
        if compile_now:
            self.compile_now()

    def restore(self, text: str, name: str, path: str, origin: str, modified: bool) -> None:
        """Put back a draft saved with `draft()` (the previous run's state); compiled at once when there is text.

        An unchanged registered formula is loaded afresh from the registry (so a native built-in is its real self again).
        """
        if origin == ORIGIN_REGISTERED and not modified and self.load_registered(name):
            return
        self._load(text, name, Path(path) if path else None, origin if origin in (ORIGIN_NEW, ORIGIN_REGISTERED, ORIGIN_FILE) else ORIGIN_NEW,
                   compile_now=bool(text.strip()))
        if not text.strip():
            self._set_variation(None, None)
        self.modified = modified
        self.state_changed.emit()

    def draft(self) -> dict:
        """What `restore()` needs, as plain values (for QSettings)."""
        return {"text": self.text, "name": self.name, "path": str(self.path) if self.path else "", "origin": self.origin,
                "modified": self.modified}

    # --- editing ----------------------------------------------------------------------------------------------
    def set_text(self, text: str) -> None:
        """The editor's text changed: mark the session modified and schedule a compile."""
        if text == self.text:
            return
        self.text = text
        name = W.formula_name(text)
        if name and name != self.name:
            self.name = name
        if not self.modified:
            self.modified = True
        self.state_changed.emit()
        self._timer.start()

    def compile_now(self) -> None:
        """Compile the current text without waiting for the debounce (a compile in flight makes this one wait its turn)."""
        self._timer.stop()
        if self._running is not None:
            self._pending = True
            return
        if not self.text.strip():
            self._set_variation(None, None)
            self.error = self.error_line = None
            self.failed.emit("", None)
            return
        self._generation += 1
        generation = self._generation
        self._running = generation
        text, include_dir = self.text, self._include_dir
        run_in_background(W.compile_formula, text, include_dir,
                          on_done=lambda result: self._on_compiled(generation, result),
                          on_error=lambda exc: self._on_failed(generation, text, exc))

    def _finish_compile(self, generation: int) -> bool:
        """Bookkeeping after a compile lands; False when the result belongs to older text and must be dropped."""
        if self._running == generation:
            self._running = None
        stale = generation != self._generation
        if self._pending and self._running is None:
            self._pending = False
            QTimer.singleShot(0, self.compile_now)
        return not stale

    def _on_compiled(self, generation: int, result) -> None:
        if not self._finish_compile(generation):
            return
        self.error = self.error_line = None
        self._set_variation(result.variation, result.variation)
        self.compiled.emit(self.variation)

    def _on_failed(self, generation: int, text: str, exc: Exception) -> None:
        if not self._finish_compile(generation):
            return
        message = W.error_text(exc) if isinstance(exc, W.FormulaError) else f"{type(exc).__name__}: {exc}"
        if not isinstance(exc, W.FormulaError):
            log.warning("formula editor: compile failed unexpectedly: %s", exc)
        self.error, self.error_line = message, W.error_line(message, text)
        self.failed.emit(message, self.error_line)

    def _set_variation(self, real: V.Variation | None, scratch_source: V.Variation | None) -> None:
        self.compiled_real = real
        if scratch_source is None:
            self.variation = None
            W.unregister_scratch()
        else:
            self.variation = W.register_scratch(scratch_source)

    def ensure_registered(self) -> None:
        """Put the current variation back in the scratch slot if a formula reload emptied it (call before rendering)."""
        if self.variation is not None and W.scratch_variation() is not self.variation:
            W.register_scratch(self.variation)

    # --- files ------------------------------------------------------------------------------------------------
    def save(self, path: Path | None = None) -> Path:
        """Write the text to `path` (the formula's own file, else `default_path()` — never a bundled library file), and
        register the formula under its real name so every window can use it at once (the file is what the next
        start-up loads).

        Raises:
            OSError: When the file cannot be written.
        """
        target = path or self.own_file or self.default_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.text, encoding="utf-8")
        self.path = target
        self._include_dir = target.parent
        self.origin = ORIGIN_FILE
        self.modified = False
        if self.error is None and self.compiled_real is not None and self.compiled_real.style == V.FORMULA:
            V.register(replace(self.compiled_real, origin=str(target)))   # (broken text is written but not registered)
            self.name = self.compiled_real.name
        self.state_changed.emit()
        self.formulas_changed.emit()
        return target

    def overrides_bundled(self) -> str | None:
        """The origin of a non-user formula of the same name that a save would shadow, or None."""
        existing = V.REGISTRY.get(self.name) if self.name else None
        if existing is None or existing.name == W.SCRATCH_NAME:
            return None
        if W.origin_path(existing) is not None and W.is_user_file(W.origin_path(existing)):
            return None
        if self.path is not None and existing.origin == str(self.path):
            return None
        return existing.origin or "a built-in formula"

    def delete(self) -> bool:
        """Delete the formula's file and take it out of the registry; the formula folders are re-read, so a bundled
        formula the file shadowed comes back. The text stays in the editor (unsaved) in case it was a slip.

        Returns False when there is no file to delete.

        Raises:
            OSError: When the file cannot be removed.
        """
        path = self.own_file
        if path is None:
            return False
        path.unlink(missing_ok=True)
        existing = V.REGISTRY.get(self.name) if self.name else None
        if existing is not None and existing.origin == str(path):
            loader.load_all(force=True)            # a quarter of a second with a warm cache
            self.ensure_registered()
        self.path = None
        self.origin = ORIGIN_NEW
        self.modified = True
        self.state_changed.emit()
        self.formulas_changed.emit()
        return True


__all__ = ["FormulaSession", "COMPILE_DEBOUNCE_MS", "ORIGIN_NEW", "ORIGIN_REGISTERED", "ORIGIN_FILE"]
