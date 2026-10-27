import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fractalchemy import config  # noqa: E402

config.PREVIEW_REFINE_TO = 0.0   # windows built by the tests stop at their configured passes (render tests opt in)

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
NOT_SAMPLES = ("aposource", "apophysis-7x")  # reference source code kept under samples/, not gradient files


@pytest.fixture(scope="session")
def samples() -> Path:
    return SAMPLES


def sample_files(root: Path) -> list[Path]:
    """Every gradient-bearing sample file under `root`, skipping the reference source trees."""
    return [p for p in root.rglob("*") if p.is_file() and not set(p.relative_to(root).parts) & set(NOT_SAMPLES)]


def copy_samples(root: Path, destination: Path) -> Path:
    """Copy the sample files (not the reference source trees) to `destination`."""
    import shutil

    shutil.copytree(root, destination, ignore=shutil.ignore_patterns(*NOT_SAMPLES))
    return destination


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def spin(ms: int = 400) -> None:
    """Run the Qt event loop for a while so queued signals / background results arrive."""
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def wait_until(predicate, timeout_ms: int = 5000) -> None:
    """Poll until `predicate()` is truthy; exceptions (e.g. reading a file mid-write) count as 'not yet'."""
    for _ in range(timeout_ms // 50):
        try:
            if predicate():
                return
        except Exception:  # noqa: BLE001
            pass
        spin(50)
    raise AssertionError("timed out waiting for condition")


@pytest.fixture(scope="session")
def _shared_gl_context():
    from fractalchemy.render.gpu_engine import create_context

    ctx = create_context()
    yield ctx
    ctx.release()


@pytest.fixture
def gl_context(_shared_gl_context):
    """A standalone OpenGL context, made current for the test (other tests' GpuEngines have their own)."""
    with _shared_gl_context:
        yield _shared_gl_context


# --- main-window helpers shared by the UI test modules ---------------------------------------
@pytest.fixture
def main_window_factory(qapp, tmp_path):
    """Builds MainWindows on the CPU engine with private settings, and closes them without prompts."""
    from PySide6.QtCore import QSettings

    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.ui.main_window import MainWindow

    windows = []

    def make(fractal_root: Path | None = None, size: tuple[int, int] = (640, 420), cheap_renders: bool = False):
        settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
        roots = LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key)
        if fractal_root is not None:
            roots.add(fractal_root)
        win = MainWindow(LibraryRoots(settings), roots, prefer_gpu=False, settings=settings)
        win.resize(*size)
        win.show()
        if cheap_renders:
            win.settingsPanel.set_values(1, 1.0)
        if fractal_root is not None:
            wait_until(lambda: win.fractalLibraryPanel.model.rowCount() == 1 and not win.fractal_library._pending)
        windows.append(win)
        return win

    yield make
    for win in windows:
        win.gradient_library.document.modified = False
        win.close()


def open_flame_and_wait(win, path: Path, index: int = 0, announce: bool = False, gradient_too: bool = False) -> None:
    """Open flame `index` of `path` in a MainWindow and wait until the document (and optionally the gradient editor) shows it."""
    win.open_path(path, index)
    wait_until(lambda: win.document.is_showing(path, index)
               and (not gradient_too or win.gradient_library.document.is_showing(path, index)))


def wait_for_render(win, timeout_ms: int = 60000) -> None:
    """Wait until the viewport has a finished render of what it currently shows."""
    wait_until(lambda: win.viewport.stats is not None and win.viewport.stats.finished
               and win.viewport.stats.width == win.viewport.image_rect.width(), timeout_ms=timeout_ms)
