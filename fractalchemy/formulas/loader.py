"""Discovers and registers formulas: bundled Python modules, bundled `.c` sources, user folders.

Load order (later wins, so a user file can override a bundled formula of the same name):

1. `fractalchemy/formulas/builtin/*.py` — native numpy + GLSL definitions;
2. `fractalchemy/formulas/library/**/*.c` — the formula library in the plugin dialect;
3. user folders: `$FRACTALCHEMY_FORMULAS` (path-list) and the per-user formulas folder
   (`user_formula_dir()`), `.c` and `.py` files.

Problems never abort loading: they are collected in the `LoadReport` and logged, so a
broken user formula cannot take the application down.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import logging
import os
import pickle
import pkgutil
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..fractal import variations as V
from .lang import FormulaError, compile_artefacts, variation_from_artefacts
from .lang.compile import CACHE_VERSION, Artefacts

log = logging.getLogger(__name__)
PACKAGE_DIR = Path(__file__).resolve().parent
LIBRARY_DIR = PACKAGE_DIR / "library"
ENV_VAR = "FRACTALCHEMY_FORMULAS"


@dataclass
class LoadReport:
    """What `load_all` did."""
    loaded: list[str] = field(default_factory=list)        # variation names, in load order
    errors: list[tuple[str, str]] = field(default_factory=list)   # (source, message)
    seconds: float = 0.0

    def summary(self) -> str:
        text = f"{len(self.loaded)} formulas loaded in {self.seconds:.2f}s"
        return text if not self.errors else f"{text}; {len(self.errors)} failed"


def user_formula_dir() -> Path:
    """The per-user folder scanned for extra formulas (created on demand by the UI, not here)."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "Fractalchemy" / "formulas"


def cache_dir() -> Path:
    """The per-user cache folder (compiled formulas, GPU diagnostics)."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "Fractalchemy"


def cache_file() -> Path:
    """Where compiled formula artefacts are cached between runs."""
    return cache_dir() / f"formulas-py{sys.version_info[0]}{sys.version_info[1]}.cache"


class _Cache:
    """Compiled artefacts keyed by source hash; saved when something new was compiled."""

    def __init__(self, path: Path | None):
        self.path = path
        self.entries: dict[str, Artefacts] = {}
        self.dirty = False
        if path is not None and path.exists():
            try:
                data = pickle.loads(path.read_bytes())
                if data.get("version") == CACHE_VERSION:
                    self.entries = data["entries"]
            except Exception:  # noqa: BLE001 - a corrupt cache is simply rebuilt
                self.entries = {}

    def get(self, text: str) -> Artefacts | None:
        return self.entries.get(hashlib.sha1(text.encode("utf-8")).hexdigest())

    def put(self, text: str, art: Artefacts) -> None:
        self.entries[hashlib.sha1(text.encode("utf-8")).hexdigest()] = art
        self.dirty = True

    def save(self) -> None:
        if self.path is None or not self.dirty:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_bytes(pickle.dumps({"version": CACHE_VERSION, "entries": self.entries}))
            tmp.replace(self.path)
        except OSError as exc:
            log.warning("cannot write the formula cache %s: %s", self.path, exc)


def user_formula_dirs() -> list[Path]:
    """`$FRACTALCHEMY_FORMULAS` entries followed by `user_formula_dir()` (existing ones only)."""
    dirs = [Path(p) for p in os.environ.get(ENV_VAR, "").split(os.pathsep) if p]
    dirs.append(user_formula_dir())
    return [d for d in dirs if d.is_dir()]


def load_python_module(path: Path, report: LoadReport) -> None:
    """Import a `.py` formula file as a module (its `@variation` decorators register on import)."""
    name = f"fractalchemy_user_formula_{path.stem}_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        report.errors.append((str(path), "cannot import"))
        return
    module = importlib.util.module_from_spec(spec)
    before = set(dict.keys(V.REGISTRY))
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - user code; report, don't crash
        report.errors.append((str(path), f"{type(exc).__name__}: {exc}"))
        return
    report.loaded.extend(sorted(set(dict.keys(V.REGISTRY)) - before))


_INCLUDE_RE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)


def _included_files(path: Path) -> list[Path]:
    """Sibling files a formula includes (so the cache notices when they change)."""
    out = []
    for name in _INCLUDE_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
        target = path.parent / name
        if target.is_file():
            out.append(target)
    return out


def load_source_file(path: Path, report: LoadReport, override: bool = True, cache: _Cache | None = None) -> V.Variation | None:
    """Compile one `.c` formula (or take it from the cache) and register it.

    `override=False` keeps an existing definition of the same name and reports the clash.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    key = text + "".join(p.read_text(encoding="utf-8", errors="replace") for p in _included_files(path))
    art = cache.get(key) if cache is not None else None
    try:
        fresh = art is None
        if fresh:
            _, art = compile_artefacts(text, origin=str(path), include_dir=path.parent)
        variation = variation_from_artefacts(art, origin=str(path))   # also fills art.numpy_code
        if fresh and cache is not None:
            cache.put(key, art)
    except FormulaError as exc:
        report.errors.append((str(path), str(exc).split(": ", 1)[-1]))
        return None
    except Exception as exc:  # noqa: BLE001 - compiler bug on unusual input; report, don't crash
        report.errors.append((str(path), f"internal error: {type(exc).__name__}: {exc}"))
        return None
    existing = dict.get(V.REGISTRY, variation.name)
    if existing is not None and not override:
        report.errors.append((str(path), f"{variation.name} is already defined by {existing.origin or 'a builtin'}; ignored"))
        return existing
    V.register(variation)
    report.loaded.append(variation.name)
    return variation


def load_directory(directory: Path, report: LoadReport, override: bool = True, cache: _Cache | None = None) -> None:
    """Load every `.c` / `.py` under `directory` (recursively, sorted for a stable override order)."""
    for path in sorted(directory.rglob("*")):
        if path.name.startswith((".", "_")) or not path.is_file():
            continue
        if path.suffix == ".c":
            load_source_file(path, report, override, cache)
        elif path.suffix == ".py":
            load_python_module(path, report)


def load_builtin_modules(report: LoadReport) -> None:
    package = importlib.import_module(f"{__package__}.builtin")
    for info in pkgutil.iter_modules(package.__path__):
        before = set(dict.keys(V.REGISTRY))
        name = f"{package.__name__}.{info.name}"
        if name in sys.modules:
            importlib.reload(sys.modules[name])   # a forced reload starts from an empty registry
        else:
            importlib.import_module(name)
        report.loaded.extend(sorted(set(dict.keys(V.REGISTRY)) - before))


_loaded: LoadReport | None = None


def load_all(user_dirs: list[Path] | None = None, force: bool = False, use_cache: bool = True) -> LoadReport:
    """Populate the registry (once per process unless `force`).

    Args:
        user_dirs: Folders to scan after the bundled formulas; defaults to `user_formula_dirs()`.
        force: Reload even if already loaded.
        use_cache: Read / write the on-disk artefact cache (`cache_file()`).
    """
    global _loaded
    if _loaded is not None and not force:
        return _loaded
    started = time.perf_counter()
    report = LoadReport()
    cache = _Cache(cache_file() if use_cache else None)
    V.REGISTRY._loading = True   # registry reads during loading must not re-enter
    try:
        dict.clear(V.REGISTRY)
        V.ALIASES.clear()
        load_builtin_modules(report)
        if LIBRARY_DIR.is_dir():
            load_directory(LIBRARY_DIR, report, override=False, cache=cache)
        for directory in (user_formula_dirs() if user_dirs is None else user_dirs):
            load_directory(directory, report, cache=cache)
        from .apophysis_depth import apply_depth_rules
        apply_depth_rules()
    finally:
        V.REGISTRY._loading = False
    cache.save()
    report.seconds = time.perf_counter() - started
    for source, message in report.errors:
        log.warning("formula %s: %s", source, message)
    log.info("%s", report.summary())
    _loaded = report
    return report


def last_report() -> LoadReport | None:
    """The report of the last `load_all`, if any."""
    return _loaded
