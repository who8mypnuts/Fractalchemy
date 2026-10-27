"""Random flames (after Apophysis's RandomFlame), the Random Batch window, and the generated batch in the library."""

import random

import pytest
from PySide6.QtCore import QSettings, Qt

from fractalchemy.fractal import variations as V
from fractalchemy.fractal.random_flame import RandomOptions, frame_camera, random_batch, random_flame, random_variations
from fractalchemy.render.compiled import CompiledFlame
from tests.conftest import spin, wait_until

NAMES = ["linear", "spherical", "julian", "bubble", "swirl", "polar", "pdj"]


def test_random_variations_follow_apophysis():
    rng = random.Random(1)
    for _ in range(50):
        chosen = random_variations(rng, NAMES)
        assert 1 <= len(chosen) <= 2 and set(chosen) <= set(NAMES) and sum(chosen.values()) == pytest.approx(1.0)
    assert random_variations(rng, ["swirl"]) == {"swirl": 1.0}


def test_random_batch_makes_framed_renderable_flames():
    flames = random_batch(5, RandomOptions(NAMES, 2, 4, 640, 480), seed=11)
    assert len(flames) == 5 and len({f.name for f in flames}) == 5
    for flame in flames:
        assert 2 <= len(flame.xforms) <= 4 and flame.final is None and flame.camera.width == 640
        assert sum(x.weight for x in flame.xforms) == pytest.approx(1.0)
        assert all(set(x.variations) <= set(NAMES) for x in flame.xforms)
        assert all(set(x.params) == {k for n in x.variations for k in V.REGISTRY[n].params} for x in flame.xforms)
        assert flame.camera.scale > 1 and len(flame.palette) == 256 and len({tuple(c) for c in flame.palette}) > 4
        CompiledFlame.build(flame)   # both engines can take it
    again = random_batch(2, RandomOptions(NAMES, 2, 4), seed=11)
    assert again[0].xforms[0].coefs == flames[0].xforms[0].coefs   # seeded: repeatable
    only_linear = random_flame(random.Random(3), RandomOptions([], 3, 3))
    assert all(x.variations == {"linear": 1.0} for x in only_linear.xforms) and len(only_linear.xforms) == 3


def test_frame_camera_rejects_systems_that_blow_up_or_collapse():
    from fractalchemy.fractal import Flame, XForm
    exploding = Flame("boom", [XForm(coefs=(3.0, 0, 0, 3.0, 1.0, 0)), XForm(coefs=(2.5, 0, 0, 2.5, -1.0, 0))])
    assert not frame_camera(exploding)
    point = Flame("dot", [XForm(coefs=(0.0, 0, 0, 0.0, 0.5, 0.5))])
    assert not frame_camera(point)


@pytest.fixture
def window(qapp, tmp_path):
    from fractalchemy.ui.random_batch_window import RandomBatchWindow
    settings = QSettings(str(tmp_path / "r.ini"), QSettings.Format.IniFormat)
    w = RandomBatchWindow(settings=settings)
    w.show()
    yield w, settings
    w.close()


def test_window_lists_every_formula_filters_and_checks(window):
    w, settings = window
    assert w.list.count() == len(V.REGISTRY) and len(w.checked_names()) == len(V.REGISTRY)
    w.search.setText("julia")
    assert not w.list.item(0).isHidden()          # debounced: nothing happened yet
    spin(400)
    visible = [w.list.item(i).text() for i in range(w.list.count()) if not w.list.item(i).isHidden()]
    assert visible and all("julia" in n.lower() for n in visible) and "julian" in visible
    w.uncheck_all_button.click()                   # only the listed (filtered) ones
    assert set(visible).isdisjoint(w.checked_names()) and "linear" in w.checked_names()
    w.search.clear()
    spin(400)
    w.check_all_button.click()
    assert len(w.checked_names()) == len(V.REGISTRY)
    w.set_checked(["linear", "swirl"], False)
    assert "linear" not in w.checked_names() and "swirl" not in w.checked_names()
    assert w.summary.text().startswith(f"{len(V.REGISTRY) - 2} of {len(V.REGISTRY)}")
    w.count_box.setValue(7)
    w.min_box.setValue(3)
    w.max_box.setValue(6)
    from fractalchemy.ui.random_batch_window import RandomBatchWindow
    again = RandomBatchWindow(settings=settings)
    assert "linear" not in again.checked_names() and len(again.checked_names()) == len(V.REGISTRY) - 2
    assert (again.count_box.value(), again.min_box.value(), again.max_box.value()) == (7, 3, 6)
    opts = again.options()
    assert (opts.min_transforms, opts.max_transforms) == (3, 6) and "swirl" not in opts.variations
    again.close()


def test_window_generates_in_the_background_and_emits_the_batch(window):
    w, _settings = window
    w.uncheck_all_button.click()
    w.set_checked(NAMES, True)
    w.count_box.setValue(3)
    batches = []
    w.batch_ready.connect(batches.append)
    w.generate_button.click()
    assert not w.generate_button.isEnabled()
    wait_until(lambda: bool(batches), timeout_ms=60000)
    assert len(batches[0]) == 3 and w.generate_button.isEnabled() and w.generate_button.text() == "Generate"
    assert all(set(n for x in f.xforms for n in x.variations) <= set(NAMES) for f in batches[0])


def test_main_window_shows_the_batch_in_the_temporary_area(qapp, tmp_path, samples, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from fractalchemy.fractal.formats import load_flames
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.items import Kind
    from fractalchemy.library.model import ITEM_ROLE
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.ui.main_window import MainWindow
    from fractalchemy.ui.random_batch_window import BATCH_NAME
    from tests.conftest import copy_samples

    library = copy_samples(samples, tmp_path / "lib")
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    roots = LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key)
    roots.add(library / "sample flames")
    win = MainWindow(LibraryRoots(settings), roots, prefer_gpu=False, settings=settings)
    win.show()
    try:
        wait_until(lambda: win.fractalLibraryPanel.model.rowCount() == 1 and not win.fractal_library._pending)
        assert "Random Batch…" in [a.text() for a in win.toolBar.actions()] and win.actionRandomBatch.shortcut().toString() == "F7"
        win.actionRandomBatch.trigger()
        w = win._random_window
        assert w.isVisible()
        flames = random_batch(4, RandomOptions(NAMES, 2, 3), seed=5)
        w.batch_ready.emit(flames)
        model = win.fractalLibraryPanel.model
        rows = [model.item(r).data(ITEM_ROLE) for r in range(model.rowCount())]
        assert [r.kind for r in rows] == [Kind.FILE, Kind.SEPARATOR, Kind.ROOT] and rows[0].virtual and rows[0].temporary
        assert model.item(0).text() == BATCH_NAME and model.open_file_is_virtual
        top = model.item(0)
        assert [top.child(i).text() for i in range(top.rowCount())] == [f.name for f in flames]
        assert not (top.child(0).flags() & Qt.ItemFlag.ItemIsDragEnabled)
        wait_until(lambda: win.document.flame is not None and win.document.flame.name == flames[0].name)
        assert win.document.source_path is None and win.actionSaveFractal.isEnabled()
        win.open_item(top.child(2).data(ITEM_ROLE))
        assert win.document.flame.name == flames[2].name and win._batch_showing == 2
        # thumbnails come from memory
        win.actionThumbnailView.setChecked(True)
        key = win.thumbnails._key(top.child(1).data(ITEM_ROLE))
        assert key is not None and key[0].name == BATCH_NAME
        # saving a generated flame asks for a file and keeps the batch on show
        target = tmp_path / "keeper.flame"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
        win.actionSaveFractal.trigger()
        wait_until(lambda: win.document.source_path == target)
        assert load_flames(target)[0].name == flames[2].name and model.item(0).text() == BATCH_NAME
        # a new batch replaces the old one; opening a file replaces the batch
        w.batch_ready.emit(random_batch(2, RandomOptions(NAMES, 2, 2), seed=9))
        assert model.item(0).rowCount() == 2 and len(win._batch) == 2
        win.open_file_path(target)
        wait_until(lambda: model.open_file == target and not win.fractal_library._pending)
        assert not model.open_file_is_virtual and win._batch == []
    finally:
        win.gradient_library.document.modified = False
        win.close()
