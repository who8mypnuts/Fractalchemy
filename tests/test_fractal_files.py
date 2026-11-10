"""Undo/redo, copy/paste in every format, Save / Save As, and the opened file at the top of the library.

(Ported in round 13 from the pre-`FractalDocument` architecture: `undo_stack` → `can_undo` / `undo()`, the library's
`opened_file()` → `open_file`, the *Copy As* actions → *Edit ▸ Copy Parameters As*. Two tests were retired: the prompt
when switching fractals with unsaved edits — the unsaved-edits shelf replaces it, see `test_recovery.py` — and the dated
new-file names, which the current *Save As* deliberately replaced by the flame's own name.)"""

import shutil

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QGuiApplication

from fractalchemy.fractal.formats import fa, flame_names, load_flame, load_flames
from fractalchemy.fractal.formats.chaos_world import parse_text as parse_chaos
from fractalchemy.fractal.formats.chaos_writer import flames_to_world
from fractalchemy.fractal.formats.clipboard import ClipboardError, detect_format, flame_to_text, text_to_flames
from fractalchemy.library.items import Kind
from fractalchemy.library.model import ITEM_ROLE
from fractalchemy.model import Gradient
from fractalchemy.ui import file_actions_base, fractal_file_actions
from fractalchemy.ui.fractal_document import FractalDocument
from tests.conftest import open_flame_and_wait, spin, wait_until


@pytest.fixture
def workdir(samples, tmp_path):
    for name in ("candy.flame", "tatasz_tram_rails.chaos"):
        shutil.copy(samples / "sample flames" / name, tmp_path / name)
    fa.write_file(load_flames(samples / "sample flames" / "stuff.flame")[:2], tmp_path / "two.fa")
    (tmp_path / "lib").mkdir()
    shutil.copy(samples / "sample flames" / "bel2.flame", tmp_path / "lib" / "bel2.flame")
    return tmp_path


@pytest.fixture
def window(main_window_factory, workdir):
    return main_window_factory(workdir / "lib", cheap_renders=True)


def open_and_wait(win, path, index=0, announce=False):
    """Open a flame; with `announce` the way *File ▸ Open* does it (the file shown in the library's temporary area)."""
    if announce:
        win.open_file_path(path, index)
        wait_until(lambda: win.document.is_showing(path, index))
    else:
        open_flame_and_wait(win, path, index)


# --- undo / redo -------------------------------------------------------------------------
def test_document_records_edits_and_merges_rapid_ones(samples):
    document = FractalDocument()
    document.replace(load_flame(samples / "sample flames" / "candy.flame", 0))
    assert not document.modified and not document.can_undo
    document.set_view(zoom=1.0)
    document.set_view(zoom=2.0)                      # within the merge window: one step
    assert len(document._undo) == 1 and document.undo_label == "Camera"
    document.set_gradient(Gradient.from_colors("g", [(1, 2, 3), (4, 5, 6)]))
    assert len(document._undo) == 2 and document.modified
    document.undo()
    assert document.flame.palette[0] != (1, 2, 3) and document.flame.camera.zoom == 2.0
    document.undo()
    assert document.flame.camera.zoom == -0.544 and not document.modified
    document.redo()
    assert document.flame.camera.zoom == 2.0 and document.modified
    document.set_view(zoom=2.0)                      # no change → no new step
    assert len(document._undo) == 1
    document.mark_saved()
    assert not document.modified and document.can_undo


def test_undo_redo_actions_in_toolbar_and_menu_follow_the_document(window, workdir):
    open_and_wait(window, workdir / "candy.flame", 0)
    assert not window.actionUndo.isEnabled() and not window.actionRedo.isEnabled()
    assert window.actionUndo in window.toolBar.actions() and window.actionRedo in window.toolBar.actions()
    assert window.menuEdit.actions()[0] is window.actionUndo
    window.viewport.zoom_camera_at(QPointF(window.viewport.width() / 2, window.viewport.height() / 2), 1.0)
    assert window.actionUndo.isEnabled() and window.actionUndo.text() == "Undo Camera"
    assert window.windowTitle().endswith("*")
    window.actionUndo.trigger()
    assert window.document.flame.camera.zoom == -0.544 and window.actionRedo.text() == "Redo Camera"
    assert not window.windowTitle().endswith("*")
    window.actionRedo.trigger()
    assert window.document.flame.camera.zoom == pytest.approx(0.456)


def test_undoing_a_gradient_edit_refreshes_the_gradient_editor(window, workdir):
    open_and_wait(window, workdir / "candy.flame", 0)
    wait_until(lambda: window.gradient_library.document.is_showing(workdir / "candy.flame", 0))
    editor = window.gradient_library.document
    original = list(window.document.flame.palette)
    editor.set_color(0, (250, 250, 250))
    assert window.document.flame.palette[0] == (250, 250, 250)
    window.actionUndo.trigger()
    assert window.document.flame.palette == original
    assert editor.gradient.stops[0].color == original[0]          # followed without asking, so not "modified" any more
    window.actionRedo.trigger()
    assert window.document.flame.palette[0] == (250, 250, 250) and editor.gradient.stops[0].color == (250, 250, 250)


# --- clipboard ------------------------------------------------------------------------------
def test_clipboard_text_round_trips_in_all_three_formats(samples):
    flame = load_flame(samples / "sample flames" / "candy.flame", 2)
    for fmt, marker in (("fa", '"fractalchemy"'), ("flame", "<flame "), ("chaos", "<world ")):
        text = flame_to_text(flame, fmt)
        assert marker in text and detect_format(text) == fmt
        back = text_to_flames(text)[0]
        assert back.name == "rotated" and len(back.xforms) == 6 and back.final is not None
        assert back.palette == flame.palette
    with pytest.raises(ClipboardError):
        text_to_flames("hello world")
    with pytest.raises(ClipboardError):
        text_to_flames('{"format": "fractalchemy", "flames": "nope"}')


def test_chaotica_writer_round_trips_through_our_reader(samples):
    tram = load_flame(samples / "sample flames" / "tatasz_tram_rails.chaos")
    back = parse_chaos(flames_to_world([tram]))[0]
    assert [x.variations for x in back.xforms] == [x.variations for x in tram.xforms]
    assert [x.chaos for x in back.xforms] == [x.chaos for x in tram.xforms]
    assert back.final.variations == tram.final.variations and back.camera.rotate == tram.camera.rotate
    assert back.camera.scale == pytest.approx(tram.camera.scale)
    assert back.coloring.brightness == pytest.approx(tram.coloring.brightness)


def test_copy_paste_and_copy_as(window, workdir):
    open_and_wait(window, workdir / "candy.flame", 1)
    window.actionCopyParameters.trigger()
    text = QGuiApplication.clipboard().text()
    assert detect_format(text) == "fa" and '"outlined"' in text
    as_flame, as_chaos = window.menuCopyAs.actions()[1], window.menuCopyAs.actions()[2]
    as_flame.trigger()
    assert QGuiApplication.clipboard().text().startswith('<flame name="outlined"')
    as_chaos.trigger()
    assert '<IFS name="outlined">' in QGuiApplication.clipboard().text()
    QGuiApplication.clipboard().setText(text.replace('"outlined"', '"pasted"'))
    window.actionPasteParameters.trigger()
    assert window.document.flame.name == "pasted" and window.document.source_path == workdir / "candy.flame"   # link kept
    assert window.document.modified and window.document.undo_label == "Paste parameters"
    errors = []
    window._report_error = lambda title, exc: errors.append(str(exc))
    QGuiApplication.clipboard().setText("not a fractal")
    window.actionPasteParameters.trigger()
    assert errors and window.document.flame.name == "pasted"


# --- save / save as ---------------------------------------------------------------------------
def test_save_writes_back_into_the_flames_own_entry(window, workdir):
    path = workdir / "candy.flame"
    open_and_wait(window, path, 1)
    window.document.set_view(zoom=1.5)
    assert window.document.modified
    assert window.files.save()
    wait_until(lambda: not window.document.modified)
    assert load_flame(path, 1).camera.zoom == 1.5 and flame_names(path) == ["original", "outlined", "rotated", "pearl", "obsession"]
    assert load_flame(path, 0).camera.zoom == -0.544


def test_save_as_new_file_defaults_to_fa_and_appends_to_existing_multi_flame_files(window, workdir, monkeypatch):
    open_and_wait(window, workdir / "candy.flame", 3)
    target = workdir / "mine.fa"
    monkeypatch.setattr(fractal_file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    assert window.files.save_as_new_file()
    wait_until(lambda: window.document.source_path == target)
    assert flame_names(target) == ["pearl"] and window.document.source_index == 0 and not window.document.modified
    wait_until(lambda: window.fractal_library.model.open_file == target)   # the new file is listed at the top
    monkeypatch.setattr(fractal_file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(workdir / "two.fa"), ""))
    window.actionSaveAsNewFile.trigger()
    wait_until(lambda: window.document.source_path == workdir / "two.fa")
    assert flame_names(workdir / "two.fa")[-1] == "pearl" and window.document.source_index == 2   # added, not replaced
    monkeypatch.setattr(fractal_file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(workdir / "noext"), ""))
    window.files.save_as_new_file()
    wait_until(lambda: (workdir / "noext.fa").exists())


def test_several_fractals_collect_in_one_fa_file(window, workdir, monkeypatch):
    """Add to This File as New Fractal… / Add to Another File… — the gradient window's flows, for fractals."""
    collection = workdir / "collection.fa"
    open_and_wait(window, workdir / "candy.flame", 0)
    monkeypatch.setattr(fractal_file_actions.QFileDialog, "getSaveFileName", lambda *a, **k: (str(collection), ""))
    window.files.save_as_new_file()
    wait_until(lambda: window.document.source_path == collection)
    assert window.actionSaveAsNewEntry.isEnabled()
    # Add to This File: the edited flame joins its own file under a new name and becomes that entry
    window.document.set_view(zoom=1.0)
    monkeypatch.setattr(file_actions_base.QInputDialog, "getText", lambda *a, **k: ("original, zoomed", True))
    window.actionSaveAsNewEntry.trigger()
    wait_until(lambda: window.document.source_index == 1 and not window.document.modified)
    assert flame_names(collection) == ["original", "original, zoomed"]
    assert window.document.flame.name == "original, zoomed" and window.windowTitle().startswith("Fractalchemy — original, zoomed")
    assert load_flame(collection, 0).camera.zoom == -0.544 and load_flame(collection, 1).camera.zoom == 1.0
    # Add to Another File: a flame from a different file joins the collection too
    open_and_wait(window, workdir / "candy.flame", 3)
    monkeypatch.setattr(fractal_file_actions.QFileDialog, "getOpenFileName", lambda *a, **k: (str(collection), ""))
    monkeypatch.setattr(file_actions_base.QInputDialog, "getText", lambda *a, **k: ("pearl in collection", True))
    window.actionSaveAsIntoFile.trigger()
    wait_until(lambda: window.document.source_path == collection and window.document.source_index == 2)
    assert flame_names(collection) == ["original", "original, zoomed", "pearl in collection"]
    assert [f.name for f in load_flames(collection)] == flame_names(collection)
    model = window.fractal_library.model
    wait_until(lambda: model.open_file == collection and model.item(0).rowCount() == 3)
    # a Chaotica world can take a new entry too (an <IFS> added to the world; its own entries are never rewritten)
    open_and_wait(window, workdir / "tatasz_tram_rails.chaos", 0)
    assert window.files.can_append_to_source() and not window.files.can_save_in_place()
    # a cancelled name prompt starts no write
    open_and_wait(window, collection, 0)
    monkeypatch.setattr(file_actions_base.QInputDialog, "getText", lambda *a, **k: ("", False))
    assert not window.files.save_as_new_entry() and len(flame_names(collection)) == 3


def test_save_as_can_write_flame_and_chaotica_files(window, workdir, monkeypatch):
    open_and_wait(window, workdir / "candy.flame", 2)
    for name in ("out.flame", "out.chaos"):
        target = workdir / name
        monkeypatch.setattr(fractal_file_actions.QFileDialog, "getSaveFileName", lambda *a, t=target, **k: (str(t), ""))
        window.files.save_as_new_file()
        wait_until(lambda: target.exists() and window.document.source_path == target)
        assert flame_names(target) == ["rotated"] and load_flame(target).final is not None
    # .chaos entries can't be replaced in place: Save falls through to Save As
    saved = []
    monkeypatch.setattr(window.files, "save_as_new_file", lambda: saved.append(1) or True)
    window.document.set_view(zoom=0.5)
    window.files.save()
    assert saved == [1]


def test_saving_a_flame_with_unsupported_variations_warns_first(window, workdir, monkeypatch):
    path = workdir / "lib" / "bel2.flame"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("crackle=", "notavariation=", 1), encoding="utf-8")
    open_and_wait(window, path, 1)            # "power source" now uses a variation nobody provides
    assert window.document.flame.unsupported == ["notavariation"]
    window.document.set_view(zoom=0.25)
    monkeypatch.setattr(window.files, "_confirm_lossy_save", lambda flame: False)
    assert not window.files.save() and window.document.modified
    monkeypatch.setattr(window.files, "_confirm_lossy_save", lambda flame: True)
    assert window.files.save()
    wait_until(lambda: not window.document.modified)
    assert load_flame(path, 1).camera.zoom == 0.25


# --- the opened file section ----------------------------------------------------------------------
def test_opened_file_is_listed_above_the_library_with_a_separator(window, workdir):
    model = window.fractalLibraryPanel.model
    open_and_wait(window, workdir / "candy.flame", 0, announce=True)
    wait_until(lambda: model.open_file == workdir / "candy.flame")
    assert model.rowCount() == 3
    file_item, separator, root = (model.item(r).data(ITEM_ROLE) for r in range(3))
    assert file_item.kind == Kind.FILE and separator.kind == Kind.SEPARATOR and root.kind == Kind.ROOT
    assert [model.item(0).child(i).text() for i in range(5)] == ["original", "outlined", "rotated", "pearl", "obsession"]
    assert not (model.item(1).flags() & Qt.ItemFlag.ItemIsSelectable)   # the separator is not selectable
    assert model.root_paths() == [workdir / "lib"]
    # another file replaces it; a library click does not touch it
    open_and_wait(window, workdir / "two.fa", 1, announce=True)
    wait_until(lambda: model.open_file == workdir / "two.fa")
    assert model.rowCount() == 3 and model.item(0).rowCount() == 2
    open_and_wait(window, workdir / "lib" / "bel2.flame", 0)
    spin(100)
    assert model.open_file == workdir / "two.fa"
    window.fractal_library.show_file(None)
    assert model.rowCount() == 1 and model.open_file is None


def test_opened_file_refreshes_after_entry_operations(window, workdir):
    model = window.fractalLibraryPanel.model
    path = workdir / "two.fa"
    open_and_wait(window, path, 0, announce=True)
    wait_until(lambda: model.open_file == path)
    entry = model.item(0).child(1).data(ITEM_ROLE)
    window.fractal_library.rename(entry, "renamed flame")
    wait_until(lambda: model.item(0).rowCount() == 2 and model.item(0).child(1).text() == "renamed flame")
    assert flame_names(path)[1] == "renamed flame"


def test_opened_file_refresh_never_raises_a_dialog(window, workdir, monkeypatch):
    """A watcher event can catch the file mid-write: the section must cope quietly, not pop a modal box."""
    model = window.fractal_library.model
    path = workdir / "two.fa"
    open_and_wait(window, path, 0, announce=True)
    wait_until(lambda: model.open_file == path)
    boxes = []
    for module in ("library_host", "file_actions_base"):
        monkeypatch.setattr(f"fractalchemy.ui.{module}.QMessageBox.warning", lambda *a, **k: boxes.append(a))
    messages = []
    window.fractal_library.status.connect(messages.append)
    path.write_text("{ not json")                      # half-written file
    window.fractal_library.rescan_open_file()
    wait_until(lambda: any("Could not re-read" in m for m in messages))
    assert model.open_file == path and model.item(0).rowCount() == 2 and not boxes   # section kept
    path.write_text('{"format": "fractalchemy", "version": 1, "flames": []}')
    window.fractal_library.rescan_open_file()
    wait_until(lambda: model.open_file is None)
    assert not boxes and any("holds no fractals" in m for m in messages)


def test_paste_copes_with_every_kind_of_bad_clipboard_text(window):
    errors = []
    window._report_error = lambda title, exc: errors.append(str(exc))
    for text in ("", "hello", '{"format": "fractalchemy", "flames": [1]}', '{"format": "fractalchemy", "flames": [{"xforms": [{"coefs": 1}]}]}',
                 '<flame name="x"><xform weight="1"/>', "<world><IFS", '{"format": "fractalchemy", "flames": []}'):
        QGuiApplication.clipboard().setText(text)
        window.paste_parameters()
    assert len(errors) == 7 and window.document.flame is None


def test_destroying_an_edited_document_is_silent(qapp, samples, capfd):
    """Regression (old architecture): a lambda on QUndoStack.cleanChanged outlived the document and raised at shutdown."""
    import gc

    document = FractalDocument()
    document.replace(load_flame(samples / "sample flames" / "candy.flame", 0))
    document.set_view(zoom=1.0)                     # non-clean: destruction clears the stack and emits cleanChanged
    del document
    gc.collect()
    spin(50)
    assert "Signal source has been deleted" not in capfd.readouterr().err
