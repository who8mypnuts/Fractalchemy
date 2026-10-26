"""Run blocking work on Qt's thread pool and deliver the outcome via signals.

    run_in_background(load_gradient, path, on_done=show, on_error=report)

`on_done` / `on_error` are invoked on the GUI thread (queued connection), so
they may touch widgets freely. Keep the worker callable free of Qt widgets.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class TaskSignals(QObject):
    """Signals a BackgroundTask emits from the worker thread."""
    done = Signal(object)
    failed = Signal(object)  # the Exception instance


class BackgroundTask(QRunnable):
    """QRunnable wrapper that reports a callable's result or exception via signals."""
    def __init__(self, fn: Callable, *args, **kwargs):
        """Args:
            fn: The callable to run on the pool.
            *args: Positional arguments for `fn`.
            **kwargs: Keyword arguments for `fn`.
        """
        super().__init__()
        self._fn, self._args, self._kwargs = fn, args, kwargs
        self.signals = TaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001 - forwarded to the caller's handler
            self.signals.failed.emit(exc)
        else:
            self.signals.done.emit(result)


_live_tasks: set[BackgroundTask] = set()  # keep signal objects alive until delivered


def run_in_background(
    fn: Callable,
    *args,
    on_done: Callable | None = None,
    on_error: Callable | None = None,
    **kwargs,
) -> BackgroundTask:
    """Start `fn(*args, **kwargs)` on the global thread pool.

    Args:
        fn: Work to run; must not touch widgets.
        *args: Positional arguments for `fn`.
        on_done: Called on the GUI thread with the result.
        on_error: Called on the GUI thread with the raised exception.
        **kwargs: Keyword arguments for `fn`.

    Returns:
        The task, mainly for tests; it is kept alive until a handler has run.
    """
    task = BackgroundTask(fn, *args, **kwargs)
    task.setAutoDelete(False)
    _live_tasks.add(task)

    def finish(callback, payload):
        _live_tasks.discard(task)
        if callback is not None:
            callback(payload)

    task.signals.done.connect(lambda result: finish(on_done, result))
    task.signals.failed.connect(lambda exc: finish(on_error, exc))
    QThreadPool.globalInstance().start(task)
    return task
