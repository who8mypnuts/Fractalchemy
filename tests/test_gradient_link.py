"""The Gradient Library ⇄ fractal viewport link, the .fa gradient format and the preview mirror."""

import shutil

import pytest
from PySide6.QtCore import QSettings, QSize
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QMessageBox

from fractalchemy.formats import entry_names, format_for, load_gradients, save_gradient
from fractalchemy.fractal.formats import fa, load_flame, load_flames
from fractalchemy.library.catalog import FRACTAL_CATALOG
from fractalchemy.library.roots import LibraryRoots
from fractalchemy.model import Gradient
from fractalchemy.model.adjust import Adjustments
from fractalchemy.ui.main_window import MainWindow
from fractalchemy.widgets.fractal_preview import FractalPreview
from tests.conftest import spin, wait_until


@pytest.fixture
def workdir(samples, tmp_path):
    shutil.copy(samples / "sample flames" / "candy.flame", tmp_path / "candy.flame")
    fa.write_file(load_flames(samples / "sample flames" / "stuff.flame")[:3], tmp_path / "three.fa")
    return tmp_path


@pytest.fixture
def window(qapp, workdir):
    settings = QSettings(str(workdir / "s.ini"), QSettings.Format.IniFormat)
    roots = LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key)
    roots.add(workdir)
    win = MainWindow(LibraryRoots(settings), roots, prefer_gpu=False, settings=settings)
    win.resize(520, 400)
    win.show()
    yield win
    win.gradient_library.document.modified = False
    win.document.undo_stack.setClean()   # never prompt on teardown
    win.close()


def open_and_wait(win, path, index):
    win.open_path(path, index)
    wait_until(lambda: win.document.is_showing(path, index) and win.gradient_library.document.is_showing(path, index))


def wait_for_render(win, timeout_ms=60000):
    wait_until(lambda: win.viewport.stats is not None and win.viewport.stats.finished
               and win.viewport.stats.width == win.viewport.image_rect.width(), timeout_ms=timeout_ms)


# --- fractal → gradient ----------------------------------------------------------
def test_choosing_a_fractal_loads_its_gradient_entry(window, workdir):
    open_and_wait(window, workdir / "candy.flame", 3)
    gradient_window = window.gradient_library
    assert gradient_window.document.gradient.name == "pearl"
    assert gradient_window.gradientBrowser.count() == 5 and gradient_window.gradientBrowser.currentRow() == 3
    open_and_wait(window, workdir / "three.fa", 2)
    assert gradient_window.document.gradient.name == load_flame(workdir / "three.fa", 2).name
    assert gradient_window.gradientBrowser.count() == 3


def test_a_loose_flame_gives_the_editor_a_loose_copy_of_its_palette(window, workdir):
    flame = load_flame(workdir / "candy.flame", 1)
    window.show_flame(flame)
    document = window.gradient_library.document
    assert document.gradient.name == "outlined" and document.source_path is None and not document.modified
    assert window.gradient_library.gradientBrowser.count() == 1
    assert [s.color for s in document.gradient.stops][0] == flame.palette[0]


def test_switching_fractals_with_unsaved_gradient_edits_asks_first(window, workdir, monkeypatch):
    open_and_wait(window, workdir / "candy.flame", 0)
    document = window.gradient_library.document
    document.set_color(0, (1, 2, 3))
    assert document.modified
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    window.open_path(workdir / "candy.flame", 2)
    wait_until(lambda: window.document.source_index == 2)
    spin(200)
    assert document.source_index == 0 and document.modified      # the editor kept the edits
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    window.open_path(workdir / "candy.flame", 4)
    wait_until(lambda: document.is_showing(workdir / "candy.flame", 4))
    assert not document.modified


# --- gradient → fractal ----------------------------------------------------------
def test_editing_the_gradient_recolours_the_fractal_and_rerenders(window, workdir):
    open_and_wait(window, workdir / "candy.flame", 0)
    wait_for_render(window)
    before = list(window.document.flame.palette)
    changes = []
    window.document.palette_changed.connect(lambda: changes.append(1))
    generation = window.viewport.generation
    window.gradient_library.document.set_adjustments(Adjustments(hue=180))
    assert changes == [1] and window.document.flame.palette != before
    assert window.viewport.generation == generation + 1 and window.viewport._settle.isActive()   # interactive re-render
    window.gradient_library.document.set_color(0, (255, 255, 255))
    assert window.document.flame.palette[0] == (255, 255, 255) and len(changes) == 2


def test_choosing_another_gradient_in_the_library_applies_it(window, workdir):
    open_and_wait(window, workdir / "candy.flame", 0)
    original = list(window.document.flame.palette)
    window.gradient_library.files.show_entry(3)            # click "pearl" in the strip
    assert window.gradient_library.document.source_index == 3
    assert window.document.flame.palette != original
    pearl = load_flame(workdir / "candy.flame", 3).palette   # the editor simplifies stops on import, so "close"
    assert max(abs(a - b) for ours, theirs in zip(window.document.flame.palette, pearl) for a, b in zip(ours, theirs)) <= 12


def test_loading_the_fractals_own_entry_does_not_touch_its_palette(window, workdir):
    open_and_wait(window, workdir / "candy.flame", 2)
    assert window.document.flame.palette == load_flame(workdir / "candy.flame", 2).palette


def test_saving_the_gradient_writes_into_the_flame_without_reloading_the_view(window, workdir):
    path = workdir / "candy.flame"
    open_and_wait(window, path, 1)
    window.document.set_view(zoom=2.0)
    window.gradient_library.document.set_color(0, (9, 8, 7))
    window.gradient_library.files.save()
    wait_until(lambda: not window.gradient_library.document.modified)
    assert load_flame(path, 1).palette[0] == (9, 8, 7)
    spin(900)   # the library watcher would reload the flame if we did not recognise our own write
    assert window.document.flame.camera.zoom == 2.0


# --- preview mirror ------------------------------------------------------------------
def test_gradient_window_preview_mirrors_the_viewport(window, workdir):
    preview = window.gradient_library.fractalPreview
    assert isinstance(preview, FractalPreview) and preview.image is None
    open_and_wait(window, workdir / "candy.flame", 0)
    wait_for_render(window)
    assert preview.image is not None and preview.image.size() == window.viewport.image.size()
    window.show_flame(load_flame(workdir / "candy.flame", 4))
    assert preview.image is None   # cleared until the new flame's first pass arrives


def test_preview_letterboxes_and_paints_placeholder(qapp):
    preview = FractalPreview(size=QSize(150, 84))
    preview.show()
    preview.grab()   # placeholder path
    image = QImage(300, 300, QImage.Format.Format_RGBA8888)
    image.fill(QColor(200, 50, 50))
    preview.set_image(image)
    shot = preview.grab().toImage()
    assert shot.pixelColor(75, 42).red() > 150          # centre shows the image
    assert shot.pixelColor(5, 42).red() < 60            # sides are letterboxed background


# --- .fa palettes in the gradient library ----------------------------------------------
def test_fa_files_are_gradient_sources_too(workdir):
    path = workdir / "three.fa"
    fmt = format_for(path)
    assert fmt.name == "Fractalchemy" and fmt.can_append and fmt.multi_entry
    assert entry_names(path) == [f.name for f in load_flames(path)]
    gradient = Gradient.from_colors("solid", [(10, 20, 30), (40, 50, 60)])
    save_gradient(gradient, path, 1)
    assert load_flame(path, 1).palette[0] == (10, 20, 30) and len(load_flame(path, 1).xforms) > 0
    fmt.append(gradient, path, template=(path, 0))
    assert entry_names(path)[-1] == "solid" and len(load_flame(path, 3).xforms) == len(load_flame(path, 0).xforms)
    fmt.rename(path, 3, "renamed")
    fmt.remove(path, 0)
    assert entry_names(path)[-1] == "renamed" and len(load_gradients(path)) == 3
    fmt.copy_entry(path, 2, workdir / "copy.fa")
    assert entry_names(workdir / "copy.fa") == ["renamed"]
    new = workdir / "new.fa"
    save_gradient(gradient, new)
    assert entry_names(new) == ["solid"] and load_flame(new).renderable()
