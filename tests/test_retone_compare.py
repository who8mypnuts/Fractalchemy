"""Instant re-colouring (the render's histogram tone-mapped again instead of a new render) and the before / after view."""

import numpy as np
import pytest

from fractalchemy.fractal.formats import load_flame
from fractalchemy.render.cpu_engine import CpuEngine
from fractalchemy.render.service import RenderService
from fractalchemy.render.settings import RenderSettings
from fractalchemy.render.tonemap import ToneParams, curve_luts, tonemap
from tests.conftest import open_flame_and_wait, wait_for_render, wait_until


@pytest.fixture
def candy(samples):
    return load_flame(samples / "sample flames" / "candy.flame", 2)


def _settings():
    return RenderSettings().with_size(160, 100).with_effort(3, 4.0).with_refine(0.0)


def test_a_cpu_job_retones_its_histogram_exactly(candy):
    job = CpuEngine(threads=2).start(candy, _settings())
    while not job.stats.finished:
        job.run_pass()
    samples = job.stats.samples
    coloring = candy.coloring.copy()
    coloring.gamma, coloring.brightness = 2.0, 9.0
    coloring.curves.set_points("red", [(0, 0), (0.5, 0.8), (1, 1)])
    image = job.retone(coloring)
    s = job.settings
    expected = tonemap(job.histogram, ToneParams.derive(coloring, job.ppu, samples, s.oversample), s.oversample, s.filter_radius,
                       (s.width, s.height), curve_luts(coloring.curves))
    assert np.array_equal(image, expected) and job.stats.samples == samples
    job.close()


def test_a_gpu_job_retones_too(candy):
    from fractalchemy.render.gpu_engine import gpu_available
    if not gpu_available()[0]:
        pytest.skip("no OpenGL")
    from fractalchemy.render.gpu_engine import GpuEngine
    engine = GpuEngine()
    try:
        job = engine.start(candy, _settings())
        while not job.stats.finished:
            job.run_pass()
        before = job.image()
        coloring = candy.coloring.copy()
        coloring.gamma = 1.5
        retoned = job.retone(coloring)
        assert retoned.shape == before.shape and not np.array_equal(retoned, before)
        job.coloring = coloring
        assert np.array_equal(job.image(), retoned)
        job.close()
    finally:
        engine.close()


def test_the_service_retones_a_retained_job_and_reports_a_missing_one(qapp, candy):
    service = RenderService(prefer_gpu=False)
    passes, missed = [], []
    service.pass_done.connect(lambda key, image, stats: passes.append((key, stats.samples)))
    service.retone_missed.connect(missed.append)
    service.start()
    try:
        service.submit("v", candy, _settings(), retain=True)
        wait_until(lambda: passes and passes[-1][0] == "v" and len(passes) >= 3)
        wait_until(lambda: service.pending() == 0)
        done = len(passes)
        samples = passes[-1][1]
        coloring = candy.coloring.copy()
        coloring.gamma = 1.5
        service.retone("v", coloring)
        wait_until(lambda: len(passes) == done + 1)
        assert passes[-1] == ("v", samples)                        # a new picture, no new samples
        service.retone("nothing", coloring)
        wait_until(lambda: missed == ["nothing"])
        service.cancel("v")                                         # released: nothing left to re-colour
        service.retone("v", coloring)
        wait_until(lambda: missed == ["nothing", "v"])
    finally:
        service.stop()


def test_the_viewport_recolours_instead_of_rendering_again(main_window_factory, samples):
    win = main_window_factory()
    open_flame_and_wait(win, samples / "sample flames" / "candy.flame", 2)
    wait_for_render(win)
    view = win.viewport
    submits, retones = view.submits, view.retones
    image = view._image
    win.document.set_coloring(gamma=1.7)
    wait_until(lambda: view._image is not image)
    assert view.submits == submits and view.retones == retones + 1
    win.document.undo()                                             # undoing a colouring edit re-colours too
    assert view.retones == retones + 2 and view.submits == submits
    win.document.set_gradient(__import__("fractalchemy.model", fromlist=["Gradient"]).Gradient.from_colors("g", [(1, 2, 3), (200, 9, 9)]))
    assert view.submits == submits + 1                             # the palette is in the histogram: a new render


def test_holding_backslash_compares_with_the_saved_state(main_window_factory, samples):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication
    win = main_window_factory()
    open_flame_and_wait(win, samples / "sample flames" / "candy.flame", 2)
    wait_for_render(win)
    win.document.set_coloring(gamma=1.5)
    view = win.viewport
    QApplication.sendEvent(win, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backslash, Qt.KeyboardModifier.NoModifier, "\\"))
    assert view.comparing and view.compare_renders == 1
    wait_until(lambda: view._compare_image is not None, 60000)
    QApplication.sendEvent(win, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Backslash, Qt.KeyboardModifier.NoModifier, "\\"))
    assert not view.comparing
    QApplication.sendEvent(win, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backslash, Qt.KeyboardModifier.NoModifier, "\\"))
    assert view.compare_renders == 1                                # the same comparison: cached
    QApplication.sendEvent(win, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Backslash, Qt.KeyboardModifier.NoModifier, "\\"))
    win.actionCompare.setChecked(True)                              # sticky
    assert view.comparing and view._compare[0] == "As loaded"
    win.actionCompare.setChecked(False)
    assert not view.comparing
    win.compare(True, before_last_edit=True)                        # one edit so far: "before it" is the loaded state (cached)
    assert view._compare[0] == "Before: Gamma" and view.compare_renders == 1
    win.document.set_coloring(brightness=8.0)
    win.compare(True, before_last_edit=True)
    assert view._compare[0] == "Before: Brightness" and view.compare_renders == 2
    win.compare(False)
