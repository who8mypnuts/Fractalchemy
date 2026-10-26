import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


@pytest.fixture(scope="session")
def samples() -> Path:
    return SAMPLES


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
