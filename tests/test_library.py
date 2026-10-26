"""Library: persistence, background scanning, search, drag/drop and file operations."""

import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QModelIndex, QSettings, Qt

from fractalchemy.formats import entry_names, format_for
from fractalchemy.library.items import Kind, LibraryItem
from fractalchemy.library.payload import from_mime, to_mime
from fractalchemy.library.roots import LibraryRoots
from fractalchemy.library.scanner import count_supported_files, scan_directory
from fractalchemy.ui.gradient_library_window import GradientLibraryWindow
from tests.conftest import copy_samples, wait_until


@pytest.fixture
def library_dir(samples, tmp_path) -> Path:
    root = tmp_path / "lib"
    copy_samples(samples, root)
    (root / "empty").mkdir()
    (root / "notes.txt").write_text("not a gradient")
    return root


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def window(qapp, settings, library_dir):
    roots = LibraryRoots(settings)
    roots.add(library_dir)
    win = GradientLibraryWindow(roots)
    win.resize(1100, 520)
    win.show()
    wait_until(lambda: win.libraryPanel.model.rowCount() == 1 and not win.library._pending)
    yield win
    win.close()


def file_item(win, name: str, index: int | None = None) -> LibraryItem:
    """The FILE row for `name`, or its GRADIENT entry row when `index` is given."""
    model = win.libraryPanel.model
    wanted = Kind.FILE if index is None else Kind.GRADIENT
    for item in model._walk(model.invisibleRootItem()):
        data = item.data(Qt.ItemDataRole.UserRole + 1)
        if data.path.name == name and data.kind == wanted and data.index == (index or 0):
            return data
    raise AssertionError(f"{name}[{index}] not in tree")


# --- scanning & persistence -------------------------------------------------
def test_scan_lists_only_supported_files_and_all_folders(library_dir):
    scanned = scan_directory(library_dir)
    assert {d.path.name for d in scanned.dirs} == {"sample flames", "sample gradients", "sample images", "empty"}
    assert scanned.files == []  # notes.txt ignored
    assert scanned.file_count() == sum(1 for p in library_dir.rglob("*") if p.is_file() and p.suffix != ".txt")
    ugr = next(f for d in scanned.dirs for f in d.files if f.path.name == "ag6.ugr")
    assert ugr.multi and ugr.names[:2] == ["001", "002"]


def test_roots_persist_across_instances(settings, library_dir):
    LibraryRoots(settings).add(library_dir)
    assert LibraryRoots(settings).paths() == [library_dir.resolve()]
    assert LibraryRoots(settings).add(library_dir) is False  # no duplicates
    LibraryRoots(settings).remove(library_dir)
    assert LibraryRoots(settings).paths() == []


def test_tree_is_built_in_background_and_counts_files(window, library_dir):
    model = window.libraryPanel.model
    assert model.file_counts() == {window.library.roots.paths()[0]: count_supported_files(library_dir)}
    root = model.item(0)
    assert [root.child(i).text() for i in range(root.rowCount())] == ["empty", "sample flames", "sample gradients", "sample images"]
    assert file_item(window, "candy.flame", 2).name == "rotated"


# --- search -----------------------------------------------------------------
def test_search_is_debounced_and_matches_gradient_names_inside_files(window):
    tree = window.libraryPanel.tree
    window.libraryPanel.search.setText("photon")
    assert not tree._proxy.active  # nothing happens until the typing pause
    wait_until(lambda: tree._proxy.active)
    visible = [tree._proxy.index(r, 0, QModelIndex()) for r in range(tree._proxy.rowCount())]
    assert len(visible) == 1
    flames = tree._proxy.index(0, 0, visible[0])
    assert tree._proxy.rowCount(flames) == 1 and tree._proxy.index(0, 0, flames).data() == "bel2.flame"
    window.libraryPanel.search.clear()
    wait_until(lambda: not tree._proxy.active)


# --- clicking loads gradients ----------------------------------------------
def test_choosing_an_entry_loads_it_without_blocking(window):
    tree = window.libraryPanel.tree
    item = file_item(window, "candy.flame", 2)
    tree.setCurrentIndex(tree._proxy.mapFromSource(window.libraryPanel.model.index_for(item)))
    wait_until(lambda: window.document.gradient.name == "rotated")
    assert window.document.source_index == 2
    assert window.document.source_path.name == "candy.flame"


# --- drag & drop through the model ------------------------------------------
def test_payload_round_trip():
    items = [LibraryItem(Kind.GRADIENT, Path("/x/a.ugr"), 3, "three"), LibraryItem(Kind.FILE, Path("/x/b.png"), 0, "b.png")]
    data = to_mime(items)
    assert from_mime(data) == items
    assert [u.toLocalFile() for u in data.urls()] == ["/x/b.png"]


def test_drop_gradient_onto_file_moves_it(window, library_dir):
    model = window.libraryPanel.model
    source = file_item(window, "ag6.ugr", 1)                   # "002"
    target = file_item(window, "saturated rainbox.gradient")
    data = model.mimeData([model.index_for(source)])
    assert model.canDropMimeData(data, Qt.DropAction.MoveAction, -1, -1, model.index_for(target))
    assert not model.canDropMimeData(data, Qt.DropAction.MoveAction, -1, -1, model.index_for(source))
    errors = []
    window.library.failed.connect(errors.append)
    model.dropMimeData(data, Qt.DropAction.MoveAction, -1, -1, model.index_for(target))
    wait_until(lambda: entry_names(target.path) == ["rainbow", "002"])
    wait_until(lambda: "002" not in entry_names(source.path))  # the move's second write
    assert errors == []
    wait_until(lambda: file_item(window, "saturated rainbox.gradient", 1).name == "002")  # tree refreshed


def test_drop_with_copy_action_keeps_source(window):
    model = window.libraryPanel.model
    source, target = file_item(window, "ag6.ugr", 1), file_item(window, "candy.flame")
    model.dropMimeData(model.mimeData([model.index_for(source)]), Qt.DropAction.CopyAction, -1, -1, model.index_for(target))
    wait_until(lambda: entry_names(target.path)[-1] == "002")
    assert entry_names(source.path)[1] == "002"


def test_drop_gradient_onto_folder_creates_new_ugr(window, library_dir):
    model = window.libraryPanel.model
    source = file_item(window, "bel2.flame", 0)  # "photon flower"
    target = LibraryItem(Kind.DIR, library_dir / "empty", name="empty")
    model.dropMimeData(model.mimeData([model.index_for(source)]), Qt.DropAction.CopyAction, -1, -1, model.index_for(target))
    wait_until(lambda: (library_dir / "empty" / "photon flower.ugr").exists())
    assert entry_names(library_dir / "empty" / "photon flower.ugr") == ["photon flower"]


def test_dropping_a_file_onto_a_file_always_copies(window):
    model = window.libraryPanel.model
    source, target = file_item(window, "saturated rainbox.gradient"), file_item(window, "ag6.ugr")
    model.dropMimeData(model.mimeData([model.index_for(source)]), Qt.DropAction.MoveAction, -1, -1, model.index_for(target))
    wait_until(lambda: entry_names(target.path)[-1] == "rainbow")
    assert source.path.exists() and entry_names(source.path) == ["rainbow"]


def test_moving_the_only_entry_is_refused_but_copy_allowed(samples, tmp_path):
    from fractalchemy.library import operations as ops

    source = shutil.copy(samples / "sample gradients" / "saturated rainbox.gradient", tmp_path / "one.gradient")
    target = shutil.copy(samples / "sample gradients" / "ag6.ugr", tmp_path / "many.ugr")
    with pytest.raises(ValueError, match="Hold Ctrl"):
        ops.transfer_entry(source, 0, target, move=True)
    ops.transfer_entry(source, 0, target, move=False)
    assert entry_names(target)[-1] == "rainbow" and entry_names(source) == ["rainbow"]
    with pytest.raises(ValueError):
        ops.delete_entry(source, 0)


# --- file operations --------------------------------------------------------
def test_duplicate_rename_delete(window, library_dir):
    ctl = window.library
    png = file_item(window, "idaho-001.png")
    ctl.duplicate(png)
    wait_until(lambda: file_item(window, "idaho-001 copy.png"))

    ctl.rename(file_item(window, "idaho-001 copy.png"), "dup.png")
    wait_until(lambda: file_item(window, "dup.png"))

    ctl.delete([file_item(window, "dup.png")])
    wait_until(lambda: not (library_dir / "sample images" / "dup.png").exists())

    entry = file_item(window, "candy.flame", 1)
    ctl.rename(entry, "outlined!")
    wait_until(lambda: entry_names(entry.path)[1] == "outlined!")
    ctl.delete([entry])
    wait_until(lambda: len(entry_names(entry.path)) == 4)
    ctl.new_folder(LibraryItem(Kind.ROOT, library_dir, name="lib"), "fresh")
    wait_until(lambda: (library_dir / "fresh").is_dir())


def test_remove_root_updates_tree_and_settings(window, settings):
    root = window.library.roots.paths()[0]
    window.library.remove_root(root)
    assert window.libraryPanel.model.rowCount() == 0
    assert LibraryRoots(settings).paths() == []


# --- collapse ---------------------------------------------------------------
def test_library_collapses_via_arrow_and_view_menu(window):
    splitter = window.splitter
    assert not splitter.is_collapsed() and window.actionToggleLibrary.isChecked()
    splitter.handle(1).button.click()
    assert splitter.is_collapsed() and not window.actionToggleLibrary.isChecked()
    window.actionToggleLibrary.trigger()
    assert not splitter.is_collapsed() and splitter.sizes()[0] > 0


# --- expansion survives rescans ---------------------------------------------
def test_expansion_is_restored_after_rescan(window, library_dir):
    tree, model = window.libraryPanel.tree, window.libraryPanel.model
    flames_dir = LibraryItem(Kind.DIR, library_dir / "sample flames", name="sample flames")
    root_index = lambda: tree._proxy.mapFromSource(model.index_for(LibraryItem(Kind.ROOT, library_dir.resolve())))  # noqa: E731
    wait_until(lambda: tree.isExpanded(root_index()))  # restore is deferred to the event loop
    tree.expand(tree._proxy.mapFromSource(model.index_for(flames_dir)))
    window.library.rescan_all()
    wait_until(lambda: not window.library._pending)
    wait_until(lambda: tree.isExpanded(tree._proxy.mapFromSource(model.index_for(flames_dir))))
    assert not tree.isExpanded(tree._proxy.mapFromSource(model.index_for(file_item(window, "candy.flame"))))


# --- edit library dialog ----------------------------------------------------
def test_edit_library_dialog_lists_roots_with_counts_and_removes(window, library_dir, tmp_path):
    from fractalchemy.library.dialog import EditLibraryDialog

    extra = tmp_path / "extra"
    extra.mkdir()
    added = []
    dialog = EditLibraryDialog(window.library, lambda: added.append(window.library.roots.add(extra)), window)
    dialog.show()
    table = dialog.table
    assert table.topLevelItemCount() == 1
    assert table.topLevelItem(0).text(0) == str(library_dir.resolve())
    assert table.topLevelItem(0).text(1) == str(count_supported_files(library_dir))

    dialog._add_folder()
    assert added == [True] and table.topLevelItemCount() == 2
    wait_until(lambda: table.topLevelItem(1).text(1) == "0")  # count arrives after the background scan

    table.itemWidget(table.topLevelItem(0), 2).click()
    assert table.topLevelItemCount() == 1 and window.library.roots.paths() == [extra.resolve()]
    assert window.libraryPanel.model.root_paths() == [extra.resolve()]
    dialog.close()


# --- external changes -------------------------------------------------------
def test_external_file_changes_are_picked_up(window, library_dir, samples):
    with pytest.raises(AssertionError):
        file_item(window, "newcomer.ugr")
    shutil.copy(samples / "sample gradients" / "ag6.ugr", library_dir / "empty" / "newcomer.ugr")
    wait_until(lambda: file_item(window, "newcomer.ugr"), timeout_ms=8000)

    (library_dir / "empty" / "newcomer.ugr").unlink()
    wait_until(lambda: not _has(window, "newcomer.ugr"), timeout_ms=8000)

    target = library_dir / "sample gradients" / "saturated rainbox.gradient"
    format_for(target).rename(target, 0, "renamed-outside")
    wait_until(lambda: file_item(window, "saturated rainbox.gradient").name and
               "renamed-outside" in _search_text(window, "saturated rainbox.gradient"), timeout_ms=8000)


def _has(window, name: str) -> bool:
    try:
        file_item(window, name)
        return True
    except AssertionError:
        return False


def _search_text(window, name: str) -> str:
    model = window.libraryPanel.model
    for item in model._walk(model.invisibleRootItem()):
        if item.data(Qt.ItemDataRole.UserRole + 1).path.name == name:
            return item.data(Qt.ItemDataRole.UserRole + 2)
    return ""
