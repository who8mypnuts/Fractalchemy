"""The Gradient Library's Batch Open: folder scan, image extraction, batch writing and the button flow."""

import shutil

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from fractalchemy.formats import entry_names, load_gradients
from fractalchemy.library.roots import LibraryRoots
from fractalchemy.model import Gradient
from fractalchemy.ui import gradient_batch
from fractalchemy.ui.gradient_batch import (
    BatchError, batch_dialog_filter, batch_import, extract_images, image_files_in, write_gradients,
)
from fractalchemy.ui.gradient_library_window import GradientLibraryWindow
from tests.conftest import wait_until

STEMS = ["idaho-001", "idaho-002", "idaho-003", "idaho-004"]


@pytest.fixture
def imagedir(samples, tmp_path):
    """A folder with the sample images plus one copy nested in a subfolder."""
    shutil.copytree(samples / "sample images", tmp_path, dirs_exist_ok=True)
    nested = tmp_path / "more"
    nested.mkdir()
    shutil.copy(tmp_path / "idaho-001.png", nested / "idaho-001.png")
    return tmp_path


@pytest.fixture
def window(qapp, imagedir):
    win = GradientLibraryWindow(LibraryRoots(QSettings(str(imagedir / "s.ini"), QSettings.Format.IniFormat)))
    win.show()
    yield win
    win.close()


def fake_dialog(monkeypatch, target):
    """The Save-As dialog answers `target` ('' = cancelled)."""
    monkeypatch.setattr(gradient_batch.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))


def fake_boxes(monkeypatch):
    """Message boxes are recorded instead of blocking the test."""
    shown = []

    def record(parent, title, text, *args, **kwargs):
        shown.append(text)
        return QMessageBox.StandardButton.Ok

    for name in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, name, record)
    return shown


# --- workers (Qt-free) -----------------------------------------------------------------------
def test_folder_scan_is_recursive_and_sorted(imagedir):
    found = [(path.parent.name, path.name) for path in image_files_in(imagedir)]
    top = imagedir.name
    assert found == [(top, "idaho-001.png"), (top, "idaho-002.jpeg"), (top, "idaho-003.jpg"),
                     (top, "idaho-004.jpg"), ("more", "idaho-001.png")]


def test_extract_images_reports_failures(imagedir):
    (imagedir / "broken.png").write_bytes(b"not an image")
    gradients, failures = extract_images(image_files_in(imagedir))
    assert [g.name for g in gradients] == STEMS + ["idaho-001"]
    assert all(len(g.stops) >= 2 for g in gradients)
    assert len(failures) == 1 and failures[0][0] == "broken.png"


def test_batch_import_writes_every_gradient(tmp_path, samples):
    shutil.copytree(samples / "sample images", tmp_path, dirs_exist_ok=True)
    target = tmp_path / "imported.ugr"
    result = batch_import(target)
    assert (result.images, result.gradients) == (4, 4) and not result.failures and not result.note
    assert entry_names(target) == STEMS
    assert len(load_gradients(target, 0)) == 4


def test_batch_import_appends_to_an_existing_file(tmp_path, samples):
    shutil.copytree(samples / "sample images", tmp_path, dirs_exist_ok=True)
    target = tmp_path / "imported.ugr"
    first = batch_import(target)
    second = batch_import(target)
    assert first.note == ""
    assert second.gradients == 4 and "already existed" in second.note
    assert entry_names(target) == STEMS * 2


def test_batch_import_without_images_raises(tmp_path):
    with pytest.raises(BatchError, match="No supported images"):
        batch_import(tmp_path / "empty.ugr")


def test_batch_import_with_only_bad_images_raises(imagedir):
    for image in image_files_in(imagedir):
        image.write_bytes(b"corrupt")
    with pytest.raises(BatchError, match="None of the images could be read"):
        batch_import(imagedir / "out.ugr")


def test_write_gradients_rejects_non_batch_formats(tmp_path):
    gradient = Gradient.from_colors("one", [(255, 0, 0), (0, 0, 255)])
    with pytest.raises(ValueError, match="batched"):
        write_gradients([gradient], tmp_path / "single.map")   # .map holds one gradient


def test_write_gradients_creates_a_new_file(tmp_path):
    gradient = Gradient.from_colors("one", [(255, 0, 0), (0, 0, 255)])
    target = tmp_path / "made.ugr"
    assert write_gradients([gradient], target) == ""
    assert entry_names(target) == ["one"]


def test_dialog_filter_offers_multi_gradient_formats_first():
    assert batch_dialog_filter().startswith("Ultra Fractal gradient (")
    assert "Flame (" in batch_dialog_filter() and "Fractalchemy (" in batch_dialog_filter()


# --- the Gradient Library button flow ---------------------------------------------------------
def test_button_batches_a_folder_into_one_file(window, imagedir, monkeypatch):
    target = imagedir / "batch.ugr"
    fake_dialog(monkeypatch, target)
    shown = fake_boxes(monkeypatch)
    window.btnBatchOpen.click()
    wait_until(lambda: window.document.source_path == target and window.gradientBrowser.path == target
               and window.statusBar().currentMessage().startswith("Imported 5 gradients from 5 images"), 15000)
    assert entry_names(target) == STEMS + ["idaho-001"]
    assert window.gradientBrowser.count() == 5 and window.gradientBrowser.currentRow() == 0
    assert not window.document.modified
    assert len(shown) == 1 and shown[0].startswith("Imported 5 gradients from 5 images")


def test_second_batch_into_the_same_file_appends(window, imagedir, monkeypatch):
    target = imagedir / "batch.ugr"
    fake_dialog(monkeypatch, target)
    shown = fake_boxes(monkeypatch)
    window.btnBatchOpen.click()
    wait_until(lambda: entry_names(target) == STEMS + ["idaho-001"], 15000)
    window.btnBatchOpen.click()
    wait_until(lambda: entry_names(target) == (STEMS + ["idaho-001"]) * 2, 15000)
    wait_until(lambda: len(shown) == 2, 15000)
    assert "already existed" in shown[1]


def test_cancelling_the_dialog_changes_nothing(window, imagedir, monkeypatch):
    fake_dialog(monkeypatch, "")
    target = imagedir / "never.ugr"
    window.btnBatchOpen.click()
    assert not target.exists()
    assert window.document.source_path is None
    assert window.windowTitle().startswith("Gradient Library")


def test_folder_without_images_warns(window, imagedir, tmp_path, monkeypatch):
    fake_dialog(monkeypatch, tmp_path / "subset" / "empty.ugr")
    fake_boxes(monkeypatch)
    window.btnBatchOpen.click()
    wait_until(lambda: "Batch Open" in window.statusBar().currentMessage(), 5000)
    assert not (tmp_path / "subset" / "empty.ugr").exists()
