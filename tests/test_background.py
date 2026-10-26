"""The thread-pool helper: results and errors arrive on the GUI thread, never lost."""

import threading

from PySide6.QtCore import QCoreApplication

from hueclid.ui.background import run_in_background
from tests.conftest import wait_until


def test_result_and_error_are_delivered_on_the_gui_thread(qapp):
    gui_thread = threading.get_ident()
    seen = {}

    def work(x):
        seen["worker"] = threading.get_ident()
        return x * 2

    def boom():
        raise ValueError("nope")

    run_in_background(work, 21, on_done=lambda r: seen.update(result=r, done_thread=threading.get_ident()))
    run_in_background(boom, on_error=lambda e: seen.update(error=e, err_thread=threading.get_ident()))
    wait_until(lambda: "result" in seen and "error" in seen)
    assert seen["result"] == 42 and seen["worker"] != gui_thread
    assert seen["done_thread"] == gui_thread and seen["err_thread"] == gui_thread
    assert isinstance(seen["error"], ValueError) and str(seen["error"]) == "nope"
    assert QCoreApplication.instance() is qapp


def test_missing_handlers_do_not_crash(qapp):
    task = run_in_background(lambda: 1)
    failing = run_in_background(lambda: 1 / 0)
    wait_until(lambda: not _still_tracked(task) and not _still_tracked(failing))


def _still_tracked(task) -> bool:
    from hueclid.ui import background

    return task in background._live_tasks
