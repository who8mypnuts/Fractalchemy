import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fractalchemy import config  # noqa: E402

config.PREVIEW_REFINE_TO = 0.0   # windows built by the tests stop at their configured passes (render tests opt in)

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
NOT_SAMPLES = ("aposource",)  # reference source code kept under samples/, not gradient files


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
