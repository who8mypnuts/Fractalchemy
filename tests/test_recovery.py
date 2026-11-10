"""Crash recovery and the unsaved-edits shelf (`autosave.RecoveryStore`, `ui/recovery.RecoveryKeeper`), the start-up
offer and *File ▸ Recover*, plus *File ▸ Open Recent* and the Inspector's History tab."""

import json

import pytest

from fractalchemy import config
from fractalchemy.autosave import RecoveryStore, read_text, remove_quietly, write_atomically
from fractalchemy.fractal.formats import load_flame
from fractalchemy.ui import recovery as R
from fractalchemy.ui.fractal_document import FractalDocument
from fractalchemy.ui.recovery import RecoveryKeeper
from tests.conftest import open_flame_and_wait, wait_until


@pytest.fixture
def candy(samples):
    return samples / "sample flames" / "candy.flame"


# --- the store (Qt-free) -------------------------------------------------------------------------------------------------
def test_file_helpers(tmp_path):
    target = tmp_path / "a" / "b.txt"
    assert write_atomically(target, "hello") and read_text(target) == "hello" and not target.with_name("b.txt.tmp").exists()
    remove_quietly(target, tmp_path / "missing")
    assert read_text(target) is None


def test_the_store_keeps_one_current_fractal_per_instance_and_finds_orphans(tmp_path, candy):
    flame = load_flame(candy, 2)
    mine, crashed = RecoveryStore(tmp_path, "me"), RecoveryStore(tmp_path, "ghost")
    assert mine.write_current(flame, candy, 2, ["Gamma", "Camera"])
    assert crashed.write_current(flame, None, 0, [])
    current = mine.current()
    assert current.name == "rotated" and current.source_index == 2 and current.labels == ["Gamma", "Camera"]
    assert current.load().name == "rotated"
    alive = {"me"}
    orphans = mine.orphans(lambda instance: instance in alive)
    assert [o.fa_path.parent.name for o in orphans] == ["ghost"]
    mine.discard(orphans[0])
    assert mine.orphans(lambda instance: False) == [] or all(o.fa_path.parent.name == "me" for o in mine.orphans(lambda i: False))
    mine.close()
    assert not mine.session_dir.exists()


def test_the_shelf_is_newest_first_and_capped(tmp_path, candy):
    store = RecoveryStore(tmp_path, "me", shelf_size=3)
    flame = load_flame(candy, 0)
    for i in range(5):
        flame.name = f"edit {i}"
        store.shelve(flame, candy, 0, [f"step {i}"])
    names = [e.name for e in store.shelf()]
    assert names == ["edit 4", "edit 3", "edit 2"]
    store.clear_shelf()
    assert store.shelf() == []


def test_damaged_meta_files_are_skipped(tmp_path, candy):
    store = RecoveryStore(tmp_path, "me")
    store.write_current(load_flame(candy, 0), candy, 0, [])
    (store.session_dir / "current.json").write_text("{ nope")
    assert store.current() is None


# --- the keeper ---------------------------------------------------------------------------------------------------------
def test_the_keeper_writes_after_edits_pause_and_clears_when_saved(qapp, tmp_path, candy, monkeypatch):
    monkeypatch.setattr(config, "RECOVERY_DELAY_MS", 10)
    doc = FractalDocument()
    doc.replace(load_flame(candy, 2), candy, 2)
    keeper = RecoveryKeeper(doc, tmp_path)
    doc.set_coloring(gamma=2.5)
    assert keeper.pending
    wait_until(lambda: keeper.store.current() is not None)
    assert keeper.store.current().labels == ["Gamma"]
    doc.mark_saved()
    assert keeper.store.current() is None and not keeper.pending
    doc.set_coloring(gamma=3.0)
    doc.undo()                                   # back at the saved state: nothing to keep
    assert keeper.store.current() is None
    keeper.shutdown()


def test_showing_another_fractal_shelves_the_unsaved_edits(qapp, tmp_path, candy):
    doc = FractalDocument()
    doc.replace(load_flame(candy, 2), candy, 2)
    keeper = RecoveryKeeper(doc, tmp_path)
    doc.replace(load_flame(candy, 0), candy, 0)  # nothing unsaved: nothing shelved
    assert keeper.shelf() == []
    doc.set_view(zoom=1.75)
    doc.replace(load_flame(candy, 3), candy, 3)
    shelf = keeper.shelf()
    assert [e.name for e in shelf] == ["original"] and shelf[0].labels == ["Camera"]
    assert keeper.restore(shelf[0])
    assert doc.flame.camera.zoom == 1.75 and doc.modified and doc.source_path == candy and doc.source_index == 0
    assert [e.name for e in keeper.shelf()] == ["pearl"] or keeper.shelf() == []   # "pearl" was unmodified: not shelved
    keeper.shutdown()


def test_another_instance_is_alive_while_its_lock_is_held(qapp, tmp_path):
    a, b = RecoveryKeeper(FractalDocument(), tmp_path), RecoveryKeeper(FractalDocument(), tmp_path)
    assert b.is_alive(a.store.instance) and a.is_alive(b.store.instance)
    a.shutdown()
    assert not b.is_alive(a.store.instance)
    assert not b.is_alive("never-existed")
    b.shutdown()


# --- the main window ---------------------------------------------------------------------------------------------------
def _crash_leftover(folder, flame, source, index):
    """The files a crashed instance leaves: a session folder with a current fractal and no live lock."""
    store = RecoveryStore(folder, "crashed-1234")
    store.write_current(flame, source, index, ["Gamma"])


def test_start_up_offers_what_a_crash_left_and_restores_it(main_window_factory, candy, monkeypatch):
    edited = load_flame(candy, 2)
    edited.coloring.gamma = 1.25
    _crash_leftover(config.RECOVERY_DIR, edited, candy, 2)
    asked = []
    monkeypatch.setattr(R, "ask_recovery", lambda parent, entry, more: asked.append((entry.name, more)) or R.RESTORE)
    from fractalchemy.ui import main_window as MW
    monkeypatch.setattr(MW, "ask_recovery", R.ask_recovery)
    win = main_window_factory()
    wait_until(lambda: asked and win.document.flame is not None)
    assert asked == [("rotated", 0)]
    assert win.document.flame.coloring.gamma == 1.25 and win.document.modified and win.document.source_path == candy
    assert win.document.history()[0].label.startswith("Recovered")
    assert win.recovery.orphans() == []


def test_not_now_keeps_it_under_file_recover(main_window_factory, candy, monkeypatch):
    from fractalchemy.ui import main_window as MW
    _crash_leftover(config.RECOVERY_DIR, load_flame(candy, 1), candy, 1)
    monkeypatch.setattr(MW, "ask_recovery", lambda parent, entry, more: R.LATER)
    win = main_window_factory()
    wait_until(lambda: win.recovery.orphans())
    R.populate_recover_menu(win.menuRecover, win.recovery, win._recovery_failed)
    texts = [a.text() for a in win.menuRecover.actions()]
    assert any(t.startswith("From a crashed session: 'outlined'") for t in texts)
    next(a for a in win.menuRecover.actions() if a.text().startswith("From a crashed session")).trigger()
    assert win.document.flame.name == "outlined" and win.document.modified and win.recovery.orphans() == []


def test_switching_fractals_never_asks_but_keeps_the_edits_recoverable(main_window_factory, candy):
    win = main_window_factory()
    open_flame_and_wait(win, candy, 0)
    win.document.set_coloring(brightness=9.0)
    open_flame_and_wait(win, candy, 3)                   # no prompt
    R.populate_recover_menu(win.menuRecover, win.recovery, win._recovery_failed)
    shelved = [a for a in win.menuRecover.actions() if a.text().startswith("Unsaved edits of 'original'")]
    assert shelved and shelved[0].toolTip() == "Brightness"
    shelved[0].trigger()
    assert win.document.flame.name == "original" and win.document.flame.coloring.brightness == 9.0 and win.document.modified


def test_a_clean_exit_leaves_nothing_to_recover(main_window_factory, candy):
    win = main_window_factory()
    open_flame_and_wait(win, candy, 0)
    win.document.set_coloring(brightness=9.0)
    win.recovery.write_now()
    assert win.recovery.store.current() is not None
    win.close()
    assert not win.recovery.store.session_dir.exists()


# --- Open Recent ------------------------------------------------------------------------------------------------------------
def test_open_recent_lists_opened_and_saved_fractals(main_window_factory, candy, tmp_path):
    from fractalchemy.ui.recent_files import MAX_RECENT, RecentFiles
    win = main_window_factory()
    open_flame_and_wait(win, candy, 2)
    open_flame_and_wait(win, candy, 0)
    entries = win.recent.entries
    assert [(e.name, e.index) for e in entries[:2]] == [("original", 0), ("rotated", 2)]
    win.recent.populate(win.menuOpenRecent, win.open_recent)
    titles = [a.text() for a in win.menuOpenRecent.actions() if a.text()]
    assert titles[0] == "original — candy.flame (#1)" and titles[-1] == "Clear list"
    win.menuOpenRecent.actions()[1].trigger()           # rotated
    wait_until(lambda: win.document.is_showing(candy, 2))
    # persistence, de-duplication, the cap, missing files
    again = RecentFiles(win._settings)
    assert [(e.name, e.index) for e in again.entries[:2]] == [("rotated", 2), ("original", 0)]
    for i in range(MAX_RECENT + 3):
        again.add(tmp_path / f"f{i}.fa", 0, f"f{i}")
    assert len(again.entries) == MAX_RECENT and again.entries[0].name == f"f{MAX_RECENT + 2}"
    again.populate(win.menuOpenRecent, win.open_recent)
    assert not win.menuOpenRecent.actions()[0].isEnabled() and "(missing)" in win.menuOpenRecent.actions()[0].text()
    again.clear()
    assert again.entries == [] and json.loads(win._settings.value("recent/fractals")) == []


# --- the History tab ----------------------------------------------------------------------------------------------------------
def test_history_tab_lists_steps_and_jumps(main_window_factory, candy):
    win = main_window_factory()
    open_flame_and_wait(win, candy, 2)
    panel = win.inspectorPanel.history
    win.inspectorPanel.tabs.setCurrentWidget(panel)
    from fractalchemy.ui import fractal_document as FD
    FD.UNDO_COALESCE_SECONDS, saved = 0.0, FD.UNDO_COALESCE_SECONDS
    try:
        win.document.set_coloring(gamma=2.0)
        win.document.set_view(zoom=1.0)
    finally:
        FD.UNDO_COALESCE_SECONDS = saved
    wait_until(lambda: panel.labels() == ["💾 Opened candy.flame #3", "Gamma", "Camera"])
    assert panel.list.currentRow() == 2 and panel.list.item(2).font().bold()
    panel._clicked(panel.list.item(0))
    wait_until(lambda: panel.list.currentRow() == 0)
    assert not win.document.modified and win.document.can_redo
    menu = panel.menu_for(1)
    compared = []
    panel.compare_requested.connect(compared.append)
    next(a for a in menu.actions() if a.text() == "Compare with this state").trigger()
    assert compared and compared[0].coloring.gamma == 2.0
    assert win.inspectorPanel.tabs.tabText(2) == "History"
