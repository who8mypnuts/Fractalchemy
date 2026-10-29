"""The formula being worked on in the Formula Editor: its text, where it came from, and its live compilation.

The window owns the widgets; this object owns the *state* — so the compile pipeline, the save / delete
file operations and the registry bookkeeping can be driven (and tested) without a window:

    session = FormulaSession()
    session.load_registered("whorl")          # text from the library file; the real whorl is in the scratch slot
    session.set_text(edited)                  # debounced: compiles on the thread pool, then `compiled` / `failed`
    session.save()                            # writes the per-user .c file and registers the formula for real
                                              # (FormulaNameTaken for a bundled / built-in name: those are read-only)

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

from ..formulas import authoring as A, loader, workbench as W
from ..formulas.lang import CompiledFormula
from ..fractal import variations as V
from .background import run_in_background

COMPILE_DEBOUNCE_MS = 350
ORIGIN_NEW, ORIGIN_REGISTERED, ORIGIN_FILE = "new", "registered", "file"
log = logging.getLogger(__name__)


class FormulaNameTaken(ValueError):
    """Save refused: the name belongs to a bundled / built-in formula (`origin` says which), and those are read-only."""

    def __init__(self, name: str, origin: str):
        super().__init__(f"'{name}' is a bundled formula ({origin}); bundled and built-in formulas cannot be overwritten")
        self.name = name
        self.origin = origin


class FormulaSession(QObject):
    """State and compile pipeline of the formula in the editor.

    Signals:
        text_loaded(): A different formula was loaded; the editor should show `text`.
        text_replaced(): The session rewrote the text itself (a rename); the editor should take `text` as an edit.
        compiled(object): The text compiled; the scratch `Variation` (registered already).
        failed(str, object): The text does not compile: (message, 1-based line or None).
        state_changed(): Name, file, origin or modified flag changed (title bar, buttons).
        formulas_changed(): The registry changed — a formula was saved or deleted.
    """
    text_loaded = Signal()
    text_replaced = Signal()
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
        self.build: CompiledFormula | None = None      # the last good compile's artefacts (generated code, warnings)
        self.original: V.Variation | None = None      # the registered formula the edit started from (None for new / file)
        self.error: str | None = None
        self.error_line: int | None = None
        self._compiled_text: str | None = None       # the text the last good build came from
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
        """The file Save writes back to and Delete removes: the user's own — never a file inside the package."""
        if self.path is None or W.is_bundled_path(self.path):
            return None
        return self.path if self.origin == ORIGIN_FILE or self.is_user_file else None

    @property
    def kind_label(self) -> str:
        """`normal`, `pre` or `post` — a readable form of `kind`."""
        return {V.PRE: "pre", V.POST: "post"}.get(self.kind, "normal")

    @property
    def compiling(self) -> bool:
        """True while a compile is running or scheduled."""
        return self._running is not None or self._timer.isActive()

    @property
    def kind(self) -> str:
        """`normal`, `pre` or `post` for the current variation (normal when there is none)."""
        return self.variation.kind if self.variation is not None else V.NORMAL

    # --- loading ----------------------------------------------------------------------------------------------
    def load_new(self, name: str = W.DEFAULT_NEW_NAME, kind: str = "normal") -> None:
        """The boilerplate for a new formula of `kind` (an `authoring.TEMPLATES` key); compiled at once."""
        text = A.new_formula_text(name, kind)
        self._set_original(None)
        self._load(text, W.formula_name(text) or W.safe_file_name(name), None, ORIGIN_NEW, compile_now=True)

    def load_blank(self) -> None:
        """An empty editor with nothing in the scratch slot (the window's first state)."""
        self._set_variation(None, None)
        self._set_original(None)
        self._load("", "", None, ORIGIN_NEW, compile_now=False)

    def load_registered(self, name: str) -> bool:
        """Load a formula from the registry: its source (or a skeleton for a native one), and itself into the scratch slot
        so the previews show the real thing until the text is changed. False for an unknown name."""
        var = V.REGISTRY.get(name)
        if var is None:
            return False
        path = W.origin_path(var)
        self._set_variation(var, var)
        self._set_original(var)
        self._load(W.source_of(var), var.name, path, ORIGIN_REGISTERED, compile_now=False)
        return True

    def load_file(self, path: Path) -> None:
        """Load a `.c` file from anywhere (compiled at once).

        Raises:
            OSError: When the file cannot be read.
        """
        text = path.read_text(encoding="utf-8", errors="replace")
        self._set_original(None)
        self._load(text, W.formula_name(text) or path.stem, path, ORIGIN_FILE, compile_now=True)

    def revert(self) -> bool:
        """Throw the edits away: back to the file (a user file) or the registry entry the formula came from.
        False when there is nothing to go back to (a new formula)."""
        if self.own_file is not None and self.own_file.is_file():
            self.load_file(self.own_file)
            return True
        if self.origin == ORIGIN_REGISTERED and self.original is not None:
            return self.load_registered(self.original.name)
        return False

    def _load(self, text: str, name: str, path: Path | None, origin: str, compile_now: bool) -> None:
        self._timer.stop()
        self._generation += 1          # anything compiling for the old text is stale now
        self._pending = False
        self.text, self.name, self.path, self.origin = text, name, path, origin
        self._compiled_text = text if origin == ORIGIN_REGISTERED else None   # a registered formula is its own compile
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

    def rename(self, new_name: str, variables: bool = True) -> str:
        """Rename the formula in the text (`APO_PLUGIN` and, with `variables`, the variable prefixes); returns the new name."""
        new_name = W.safe_file_name(new_name)
        self.set_text(A.rename_formula(self.text, self.name, new_name, variables))
        self.name = new_name
        self.text_replaced.emit()
        self.state_changed.emit()
        return new_name

    def duplicate_as_new(self, taken: set[str] | None = None) -> str:
        """Turn the text into a new, unsaved formula of the user's own: renamed `name_mine` (or the next free suffix),
        without a file, so Save goes to the user's folder. Returns the new name."""
        taken = set(taken or ()) | set(dict.keys(V.REGISTRY))
        new_name = A.derived_name(self.name or W.DEFAULT_NEW_NAME, taken)
        self.path = None
        self.origin = ORIGIN_NEW
        self._include_dir = self.folder
        self.rename(new_name)
        self.modified = True
        self.state_changed.emit()
        return new_name

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

    def _on_compiled(self, generation: int, result: CompiledFormula) -> None:
        if not self._finish_compile(generation):
            return
        self._accept(result, self.text)
        self.compiled.emit(self.variation)

    def _accept(self, result: CompiledFormula, text: str) -> None:
        """A good compile of `text`: into the scratch slot, error cleared."""
        self.error = self.error_line = None
        self._set_variation(result.variation, result.variation)
        self.build = result
        self._compiled_text = text

    def _on_failed(self, generation: int, text: str, exc: Exception) -> None:
        if not self._finish_compile(generation):
            return
        self._record_failure(text, exc)
        self.failed.emit(self.error, self.error_line)

    def _record_failure(self, text: str, exc: Exception) -> None:
        message = W.error_text(exc) if isinstance(exc, W.FormulaError) else f"{type(exc).__name__}: {exc}"
        if not isinstance(exc, W.FormulaError):
            log.warning("formula editor: compile failed unexpectedly: %s", exc)
        self.error, self.error_line = message, W.error_line(message, text)

    def compile_sync(self) -> bool:
        """Compile the current text on the calling thread, now (Save uses it so the registry never lags the file).
        True when it compiled; a compile in flight for older text is dropped."""
        self._timer.stop()
        self._generation += 1
        self._pending = False
        text = self.text
        if not text.strip():
            self._set_variation(None, None)
            return False
        try:
            result = W.compile_formula(text, self._include_dir)
        except Exception as exc:  # noqa: BLE001 - reported like a background failure
            self._record_failure(text, exc)
            self.failed.emit(self.error, self.error_line)
            return False
        self._accept(result, text)
        self.compiled.emit(self.variation)
        return True

    def _set_variation(self, real: V.Variation | None, scratch_source: V.Variation | None) -> None:
        self.compiled_real = real
        if scratch_source is None:
            self.variation = None
            self.build = None
            W.unregister_scratch()
        else:
            self.variation = W.register_scratch(scratch_source)

    def _set_original(self, var: V.Variation | None) -> None:
        self.original = var
        W.register_original(var)

    @property
    def warnings(self) -> list[str]:
        """The compiler's remarks about the last good compile (stateful plugin, approximations …)."""
        return list(self.build.artefacts.warnings) if self.build is not None else []

    @property
    def generated_numpy(self) -> str:
        """The numpy module the last good compile produced (empty for a native built-in)."""
        return self.build.numpy_source if self.build is not None else ""

    @property
    def generated_glsl(self) -> str:
        """The GLSL the last good compile produced: declarations, then the function body."""
        if self.build is not None:
            art = self.build.artefacts
            return (art.glsl_decls + "\n\n" if art.glsl_decls else "") + art.glsl_body
        return self.variation.glsl if self.variation is not None else ""

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
            FormulaNameTaken: When the name is a bundled / built-in formula's, or `path` lies inside the package.
            OSError: When the file cannot be written.
        """
        taken = self.taken_by()
        if taken:
            raise FormulaNameTaken(self.name, taken)
        target = path or self.own_file or self.default_path()
        if W.is_bundled_path(target):
            raise FormulaNameTaken(self.name, f"{target} is inside the package")
        if self._compiled_text != self.text:
            self.compile_sync()                  # what gets registered is what gets written
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.text, encoding="utf-8")
        self.path = target
        self._include_dir = target.parent
        self.origin = ORIGIN_FILE
        self.modified = False
        if self.error is None and self._compiled_text == self.text and self.compiled_real is not None and self.compiled_real.style == V.FORMULA:
            V.register(replace(self.compiled_real, origin=str(target)))   # (broken text is written but not registered)
            self.name = self.compiled_real.name
        self.state_changed.emit()
        self.formulas_changed.emit()
        return target

    def taken_by(self) -> str | None:
        """The origin of the bundled / built-in formula whose name the text carries — the reason Save would be refused —
        or None when the name is free or the user's own."""
        return W.bundled_origin(self.name) if self.name else None

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


__all__ = ["FormulaSession", "FormulaNameTaken", "COMPILE_DEBOUNCE_MS", "ORIGIN_NEW", "ORIGIN_REGISTERED", "ORIGIN_FILE"]
