"""Behaviour on the unhappy paths: missing files, refused operations, cancelled prompts."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from fractalchemy.library import operations as ops
from fractalchemy.library.catalog import GRADIENT_CATALOG
from fractalchemy.library.items import Kind, LibraryItem
from fractalchemy.library.roots import LibraryRoots
from fractalchemy.model import Gradient
from fractalchemy.ui import file_actions
from fractalchemy.ui.gradient_library_window import GradientLibraryWindow
from tests.conftest import wait_until

RGB3 = [(0, 0, 0), (255, 0, 0), (255, 255, 255)]


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    monkeypatch.setattr(file_actions.QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Ok)
    win = GradientLibraryWindow(LibraryRoots(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)))
    win.show()
    yield win
    win.close()


def test_opening_a_missing_file_reports_and_keeps_state(window, tmp_path):
    window.document.replace(Gradient.from_colors("keep", RGB3))
    window.files.open_path(tmp_path / "gone.ugr")
    wait_until(lambda: "Could not open" in window.statusBar().currentMessage())
    assert window.document.gradient.name == "keep"


def test_opening_an_unsupported_file_reports_the_reason(window, tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("hello")
    window.files.open_path(bad)
    wait_until(lambda: "No reader for '.txt'" in window.statusBar().currentMessage())


def test_cancelling_the_unsaved_prompt_aborts_the_open(window, tmp_path, samples, monkeypatch):
    window.document.replace(Gradient.from_colors("edited", RGB3))
    window.document.set_color(0, (1, 1, 1))
    monkeypatch.setattr(file_actions.QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    window.open_item(LibraryItem(Kind.FILE, samples / "sample gradients" / "saturated rainbox.gradient"))
    assert window.document.gradient.name == "edited" and window.document.modified
    monkeypatch.setattr(file_actions.QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    window.open_item(LibraryItem(Kind.FILE, samples / "sample gradients" / "saturated rainbox.gradient"))
    wait_until(lambda: window.document.gradient.name == "rainbow")
    assert not window.document.modified


def test_library_operation_failure_is_reported_not_raised(window, tmp_path, monkeypatch):
    monkeypatch.setattr("fractalchemy.ui.gradient_library_window.QMessageBox.warning", lambda *a, **k: None)
    (tmp_path / "a.ugr").write_text("a {\ngradient:\n index=0 color=0\n}\n")
    (tmp_path / "b.ugr").write_text("b {\ngradient:\n index=0 color=0\n}\n")
    errors = []
    window.library.failed.connect(errors.append)
    window.library.rename(LibraryItem(Kind.FILE, tmp_path / "a.ugr", name="a.ugr"), "b.ugr")
    wait_until(lambda: errors)
    assert "already exists" in errors[0] and (tmp_path / "a.ugr").exists()


def test_unique_path_sequence(tmp_path):
    base = tmp_path / "g.ugr"
    assert ops.unique_path(base) == base
    base.write_text("")
    assert ops.unique_path(base) == tmp_path / "g copy.ugr"
    (tmp_path / "g copy.ugr").write_text("")
    assert ops.unique_path(base) == tmp_path / "g copy 2.ugr"


def test_roots_reject_files_and_missing_folders(tmp_path):
    from PySide6.QtCore import QSettings

    roots = LibraryRoots(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    (tmp_path / "f.txt").write_text("")
    assert roots.add(tmp_path / "f.txt") is False
    assert roots.add(tmp_path / "nope") is False
    assert roots.remove(tmp_path / "nope") is False
    assert roots.paths() == []


def test_document_refuses_to_drop_below_two_nodes(qapp):
    from fractalchemy.ui.document import GradientDocument

    doc = GradientDocument()
    doc.replace(Gradient.from_colors("g", RGB3[:2]))
    with pytest.raises(ValueError, match="at least 2"):
        doc.remove_stop(0)
    assert len(doc.gradient) == 2 and not doc.modified


def test_drop_of_unsupported_combination_is_a_clean_error(tmp_path):
    entry = LibraryItem(Kind.ENTRY, Path("/x/b.ugr"), 0, "b")
    with pytest.raises(ValueError, match="Can't drop"):
        ops.drop_items(GRADIENT_CATALOG, [entry], entry, move=False)
    with pytest.raises(ValueError, match="cannot be saved as new Image"):
        ops.transfer_entry(GRADIENT_CATALOG, Path("/x/b.ugr"), 0, tmp_path / "a.png", move=False)


def test_cancelling_the_save_dialog_during_discard_prompt_aborts(window, samples, monkeypatch):
    window.document.replace(Gradient.from_colors("from-nowhere", RGB3))  # no source → Save needs a dialog
    window.document.set_color(0, (1, 1, 1))
    monkeypatch.setattr(file_actions.QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Save)
    monkeypatch.setattr(file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    assert window.files.confirm_discard() is False
    assert window.document.modified and window.document.gradient.name == "from-nowhere"
