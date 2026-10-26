"""Gradient browser strip + Save / Save As flows on multi-gradient files."""

import shutil

import pytest
from PySide6.QtCore import QSettings

from hueclid.formats import entry_names, load_gradients
from hueclid.library.roots import LibraryRoots
from hueclid.ui import file_actions
from hueclid.ui.main_window import MainWindow
from tests.conftest import wait_until


@pytest.fixture
def workdir(samples, tmp_path):
    for name in ("candy.flame", "brainfibres.ufr"):
        shutil.copy(samples / "sample flames" / name, tmp_path / name)
    shutil.copy(samples / "sample gradients" / "saturated rainbox.gradient", tmp_path / "one.gradient")
    shutil.copy(samples / "sample images" / "idaho-001.png", tmp_path / "pic.png")
    return tmp_path


@pytest.fixture
def window(qapp, workdir):
    win = MainWindow(LibraryRoots(QSettings(str(workdir / "s.ini"), QSettings.Format.IniFormat)))
    win.resize(1100, 600)
    win.show()
    yield win
    win.close()


def open_and_wait(win, path, index=0):
    win.files.open_path(path, index)
    wait_until(lambda: win.document.source_path == path and win.document.source_index == index
               and win.gradientBrowser.path == path)


def test_browser_shows_every_entry_and_tracks_current(window, workdir):
    open_and_wait(window, workdir / "candy.flame", 2)
    browser = window.gradientBrowser
    assert browser.count() == 5 and browser.currentRow() == 2
    assert [browser.item(i).text() for i in range(5)] == entry_names(workdir / "candy.flame")
    assert not browser.item(0).icon().isNull()

    open_and_wait(window, workdir / "pic.png")
    assert browser.count() == 1 and browser.currentRow() == 0


def test_clicking_a_thumbnail_switches_entry_without_reading_disk(window, workdir, monkeypatch):
    open_and_wait(window, workdir / "candy.flame", 0)
    monkeypatch.setattr(file_actions, "load_gradients", lambda *a, **k: pytest.fail("disk read"))
    window.gradientBrowser.entry_chosen.emit(3)
    assert window.document.gradient.name == "pearl" and window.document.source_index == 3
    assert window.gradientBrowser.currentRow() == 3


def test_save_writes_in_place_and_refreshes_thumbnail(window, workdir):
    path = workdir / "candy.flame"
    open_and_wait(window, path, 1)
    before_icon = window.gradientBrowser.item(1).icon().pixmap(110, 36).toImage()
    for i in range(len(window.document.gradient)):
        window.document.set_color(i, (255, 0, 255))
    assert window.document.modified
    window.files.save()
    wait_until(lambda: not window.document.modified)
    assert load_gradients(path, 0)[1].stops[0].color == (255, 0, 255)
    assert entry_names(path) == ["original", "outlined", "rotated", "pearl", "obsession"]
    assert window.gradientBrowser.item(1).icon().pixmap(110, 36).toImage() != before_icon
    assert window.gradientBrowser.count() == 5 and window.gradientBrowser.currentRow() == 1


def test_save_on_ufr_keeps_file_valid(window, workdir):
    path = workdir / "brainfibres.ufr"
    open_and_wait(window, path, 1)
    window.document.set_color(0, (1, 2, 3))
    window.files.save()
    wait_until(lambda: not window.document.modified)
    assert load_gradients(path, 0)[1].stops[0].color == (1, 2, 3)
    assert path.read_bytes().startswith(b"UltraFractal")


def test_add_to_this_file_appends_and_selects_new_entry(window, workdir, monkeypatch):
    path = workdir / "candy.flame"
    open_and_wait(window, path, 0)
    monkeypatch.setattr(file_actions.QInputDialog, "getText", lambda *a, **k: ("fresh one", True))
    window.document.set_color(0, (9, 9, 9))
    window.files.save_as_new_entry()
    wait_until(lambda: window.document.source_index == 5)
    assert entry_names(path)[-1] == "fresh one"
    assert window.gradientBrowser.count() == 6 and window.gradientBrowser.currentRow() == 5
    assert window.document.gradient.name == "fresh one" and not window.document.modified
    assert load_gradients(path, 0)[0].stops[0].color != (9, 9, 9)  # original entry untouched


def test_add_to_this_file_is_unavailable_for_ufr(window, workdir):
    open_and_wait(window, workdir / "brainfibres.ufr", 0)
    assert not window.actionSaveAsNewEntry.isEnabled() and window.btnSave.isEnabled()
    open_and_wait(window, workdir / "candy.flame", 0)
    assert window.actionSaveAsNewEntry.isEnabled()


def test_save_as_new_file_then_save_targets_the_new_file(window, workdir, monkeypatch):
    open_and_wait(window, workdir / "pic.png")
    target = workdir / "from-image.ugr"
    monkeypatch.setattr(file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.files.save()  # images aren't writable -> falls through to "new file"
    wait_until(lambda: window.document.source_path == target)
    assert entry_names(target) == ["pic"] and window.gradientBrowser.count() == 1
    window.document.set_color(0, (7, 7, 7))
    window.files.save()
    wait_until(lambda: not window.document.modified)
    assert load_gradients(target, 0)[0].stops[0].color == (7, 7, 7)


def test_add_to_another_file(window, workdir, monkeypatch):
    source, target = workdir / "one.gradient", workdir / "candy.flame"
    open_and_wait(window, source)
    monkeypatch.setattr(file_actions.QFileDialog, "getOpenFileName", lambda *a, **k: (str(target), ""))
    monkeypatch.setattr(file_actions.QInputDialog, "getText", lambda *a, **k: ("rainbow in flame", True))
    window.files.save_as_into_file()
    wait_until(lambda: window.document.source_path == target and window.document.source_index == 5)
    assert entry_names(target)[-1] == "rainbow in flame"
    assert entry_names(source) == ["rainbow"]


# --- regression: flames must survive every save route -----------------------------
def _xforms(path):
    return path.read_bytes().count(b"<xform")


def test_save_as_new_file_onto_the_open_flame_saves_in_place(window, workdir, monkeypatch):
    path = workdir / "candy.flame"
    open_and_wait(window, path, 1)
    before_xforms = _xforms(path)
    window.document.set_color(0, (1, 2, 3))
    monkeypatch.setattr(file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(path), ""))
    window.files.save_as_new_file()  # user picked the same file and confirmed Qt's "replace?"
    wait_until(lambda: not window.document.modified)
    assert _xforms(path) == before_xforms and entry_names(path) == ["original", "outlined", "rotated", "pearl", "obsession"]
    assert load_gradients(path, 0)[1].stops[0].color == (1, 2, 3)
    assert window.document.source_index == 1 and "saved in place" in window.statusBar().currentMessage()


def test_save_as_new_file_onto_another_existing_flame_appends(window, workdir, samples, monkeypatch):
    other = shutil.copy(samples / "sample flames" / "bel2.flame", workdir / "bel2.flame")
    open_and_wait(window, workdir / "candy.flame", 2)
    before = _xforms(other)
    monkeypatch.setattr(file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(other), ""))
    window.files.save_as_new_file()
    wait_until(lambda: window.document.source_path == other)
    assert _xforms(other) > before and entry_names(other)[-1] == "rotated" and len(entry_names(other)) == 6
    assert window.document.source_index == 5


def test_save_as_new_file_onto_existing_ugr_keeps_its_gradients(window, workdir, samples, monkeypatch):
    ugr = shutil.copy(samples / "sample gradients" / "ag6.ugr", workdir / "ag6.ugr")
    count = len(entry_names(ugr))
    open_and_wait(window, workdir / "one.gradient")
    monkeypatch.setattr(file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(ugr), ""))
    window.files.save_as_new_file()
    wait_until(lambda: window.document.source_path == ugr)
    assert len(entry_names(ugr)) == count + 1 and entry_names(ugr)[-1] == "rainbow"


def test_add_to_this_file_clones_the_fractal_not_a_bare_template(window, workdir, monkeypatch):
    path = workdir / "candy.flame"
    open_and_wait(window, path, 1)  # "outlined" has 6 xforms
    text_before = path.read_text()
    outlined = text_before[text_before.index('<flame name="outlined"'):text_before.index("</flame>", text_before.index('<flame name="outlined"'))]
    monkeypatch.setattr(file_actions.QInputDialog, "getText", lambda *a, **k: ("outlined v2", True))
    window.document.set_color(0, (250, 0, 250))
    window.files.save_as_new_entry()
    wait_until(lambda: window.document.source_index == 5)
    text = path.read_text()
    new = text[text.index('<flame name="outlined v2"'):]
    assert new.count("<xform") == outlined.count("<xform") == 6
    assert 'post="0 -0.001 1 0 0 -1"' in new          # a distinctive attribute of "outlined" survived
    assert load_gradients(path, 0)[5].stops[0].color == (250, 0, 250)
    assert load_gradients(path, 0)[1].stops[0].color != (250, 0, 250)  # original entry untouched
    assert text.startswith(text_before[:text_before.index("</Flames>")])  # nothing before the new flame changed


def test_new_flame_file_from_a_flame_gradient_keeps_xforms(window, workdir, monkeypatch):
    target = workdir / "variant.flame"
    open_and_wait(window, workdir / "candy.flame", 0)
    monkeypatch.setattr(file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.files.save_as_new_file()
    wait_until(lambda: window.document.source_path == target)
    assert _xforms(target) == 5 and entry_names(target) == ["original"]
