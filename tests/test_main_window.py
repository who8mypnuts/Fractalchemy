"""Main window shell: menus, toolbar, and the tool windows."""

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QMessageBox, QToolButton

from fractalchemy import config
from fractalchemy.library.roots import LibraryRoots
from fractalchemy.model import Gradient
from fractalchemy.fractal.formats import load_flame
from fractalchemy.ui.gradient_library_window import GradientLibraryWindow
from fractalchemy.ui.main_window import MainWindow
from tests.conftest import spin, wait_until


@pytest.fixture
def window(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    win = MainWindow(LibraryRoots(settings), LibraryRoots(settings, key="fractal_library/roots"), prefer_gpu=False,
                     settings=settings)
    win.show()
    yield win
    win.gradient_library.document.modified = False  # never prompt on teardown
    win.animation.document.mark_saved()
    win.close()


def menu_titles(win) -> list[str]:
    return [a.text() for a in win.menuBar().actions()]


# --- shell --------------------------------------------------------------------
def test_application_is_named_fractalchemy(window):
    assert config.APP_NAME == "Fractalchemy"
    assert window.windowTitle() == "Fractalchemy"
    assert "Fractalchemy" in window.actionAbout.text()


def test_menu_bar_has_windows_and_help_menus(window):
    assert menu_titles(window) == ["File", "Edit", "View", "Windows", "Help"]
    assert [a.text() for a in window.menuWindows.actions()] == [
        "Transform Editor", "Gradient Library", "Animation", "Random Batch…", "Script Editor", "Formula Editor", "3D Editor", "Render Image…"]
    assert [a.text() for a in window.menuHelp.actions()] == ["Formulas…", "", "About Fractalchemy…", "About Qt…"]
    assert [a.text() for a in window.menuView.actions()][-2:] == ["Toolbar", "Status Bar"]
    assert [a.text() for a in window.menuFile.actions() if a.text()] == ["Open Fractal…", "Save Fractal", "Save Fractal As", "Exit"]
    assert not window.actionSaveFractal.isEnabled() and not window.actionSaveAs.isEnabled()   # nothing loaded


def test_toolbar_holds_the_gradient_library_button_with_popup_text(window):
    assert window.toolBar.isVisible()
    assert window.actionGradientLibrary in window.toolBar.actions() and window.actionOpenFractal in window.toolBar.actions()
    button = window.toolBar.widgetForAction(window.actionGradientLibrary)
    assert isinstance(button, QToolButton)
    assert button.toolTip() == "Gradient Library"
    assert not window.actionGradientLibrary.icon().isNull()


def test_view_menu_toggles_toolbar_and_status_bar(window):
    toolbar_action, status_action = window.menuView.actions()[-2:]
    toolbar_action.trigger()
    assert not window.toolBar.isVisible()
    toolbar_action.trigger()
    assert window.toolBar.isVisible()
    status_action.trigger()
    assert not window.statusBar().isVisible()
    status_action.trigger()
    assert window.statusBar().isVisible()


# --- Gradient Library window --------------------------------------------------
def test_gradient_library_is_a_hidden_child_window_until_requested(window):
    library = window.gradient_library
    assert isinstance(library, GradientLibraryWindow)
    assert library.parent() is window and library.isWindow()
    assert not library.isVisible()


def test_windows_menu_opens_the_gradient_library(window):
    window.menuWindows.actions()[1].trigger()
    assert window.gradient_library.isVisible()


def test_windows_menu_and_toolbar_open_the_transform_editor(window):
    window.menuWindows.actions()[0].trigger()
    assert window.editor.isVisible() and window.editor.windowTitle() == "Transform Editor"
    window.editor.close()
    assert not window.editor.isVisible()
    window.toolBar.widgetForAction(window.actionEditor).click()
    assert window.editor.isVisible()


def test_toolbar_button_opens_the_gradient_library_and_closing_only_hides_it(window):
    library = window.gradient_library
    window.toolBar.widgetForAction(window.actionGradientLibrary).click()
    assert library.isVisible()
    library.document.replace(Gradient.from_colors("kept", [(1, 2, 3), (4, 5, 6)]))
    library.close()
    assert not library.isVisible()
    assert library.document.gradient.name == "kept"  # state survives closing the window
    window.actionGradientLibrary.trigger()
    assert library.isVisible()


def test_gradient_library_has_its_own_menus_and_shortcuts(window):
    library = window.gradient_library
    assert [a.text() for a in library.menuBar().actions()] == ["File", "Edit", "View"]
    assert library.actionOpen.shortcut().toString() == "Ctrl+O"
    assert library.actionSave.shortcut().toString() == "Ctrl+S"
    assert library.actionToggleLibrary.shortcut().toString() == "Ctrl+L"
    assert library.windowTitle().startswith("Gradient Library")


def test_gradient_library_title_tracks_gradient_and_modified_state(window):
    library = window.gradient_library
    library.document.replace(Gradient.from_colors("sunset", [(1, 2, 3), (4, 5, 6)]))
    assert library.windowTitle() == "Gradient Library — sunset[*]"
    assert not library.isWindowModified()
    library.document.set_color(0, (9, 9, 9))
    assert library.isWindowModified()


def test_edit_fractal_library_from_main_menu_opens_the_fractal_library_dialog(window, monkeypatch):
    opened = []

    class FakeDialog:
        def __init__(self, controller, add_folder, parent):
            opened.append(controller)

        def exec(self):
            return 0

    monkeypatch.setattr("fractalchemy.ui.main_window.EditLibraryDialog", FakeDialog)
    window.actionEditFractalLibrary.trigger()
    assert opened == [window.fractal_library] and window.fractal_library is not window.gradient_library.library
    assert window.fractal_library.catalog.title == "Fractal Library"


def test_quitting_with_unsaved_edits_asks_first(window, monkeypatch):
    library = window.gradient_library
    library.document.replace(Gradient.from_colors("draft", [(1, 2, 3), (4, 5, 6)]))
    library.document.set_color(0, (9, 9, 9))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    assert not window.close()
    assert window.isVisible()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    window.show_gradient_library()
    assert window.close()
    spin(50)
    assert not window.isVisible() and not library.isVisible()


# --- fractal library, viewport and status bar ----------------------------------
@pytest.fixture
def fractal_window(qapp, tmp_path, samples):
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from tests.conftest import copy_samples

    library = copy_samples(samples, tmp_path / "lib")
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    fractal_roots = LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key)
    fractal_roots.add(library / "sample flames")
    win = MainWindow(LibraryRoots(settings), fractal_roots, prefer_gpu=False, settings=settings)
    win.resize(640, 420)
    win.show()
    wait_until(lambda: win.fractalLibraryPanel.model.rowCount() == 1 and not win.fractal_library._pending)
    yield win
    win.gradient_library.document.modified = False
    win.close()


def test_fractal_library_lists_flames_and_has_search_collapse_and_view_buttons(fractal_window):
    panel = fractal_window.fractalLibraryPanel
    root = panel.model.item(0)
    names = [root.child(i).text() for i in range(root.rowCount())]
    assert "candy.flame" in names and "satania_spikobius.chaos" in names and not any(n.endswith(".ugr") for n in names)
    candy = next(root.child(i) for i in range(root.rowCount()) if root.child(i).text() == "candy.flame")
    assert [candy.child(i).text() for i in range(candy.rowCount())] == ["original", "outlined", "rotated", "pearl", "obsession"]
    assert panel.search.placeholderText() and panel.collapse_button.toolTip() == "Collapse All"
    assert panel.list_button.isChecked() and not panel.thumb_button.isChecked()
    assert [a.text() for a in fractal_window.menuEdit.actions() if a.text()] == ["Undo", "Redo", "Copy Parameters", "Paste Parameters", "Edit Fractal Library…"]
    assert fractal_window.actionToggleFractalLibrary.isChecked()
    fractal_window.actionToggleFractalLibrary.setChecked(False)
    assert fractal_window.splitter.is_collapsed()


def test_opening_a_flame_renders_it_in_the_viewport_with_status(fractal_window, samples):
    win = fractal_window
    path = win.fractal_library.roots.paths()[0] / "candy.flame"
    win.open_path(path, 2)
    wait_until(lambda: win.document.flame is not None and win.document.flame.name == "rotated")
    wait_until(lambda: win.viewport.stats is not None and win.viewport.stats.finished
               and win.viewport.stats.width == win.viewport.image_rect.width(), timeout_ms=60000)
    stats = win.viewport.stats
    assert stats.passes_done == stats.passes_total == win.viewport.settings.passes
    assert win.viewport.image is not None and win.viewport.image.width() == win.viewport.image_rect.width()
    assert win.viewport.image_rect.width() <= win.viewport.width() and win.viewport.is_fit
    assert "rotated" in win.status.fractal.text() and "6 transforms + final" in win.status.fractal.text()
    assert win.status.passes.text().startswith("q ") and win.status.passes.text().endswith("✓")   # finished: quality reached
    assert win.status.progress.value() == win.status.progress.maximum() == 6
    assert "samples" in win.status.render.text() and win.status.render.text().startswith("CPU")
    assert win.windowTitle() == "Fractalchemy — rotated"


def test_choosing_a_library_row_loads_it(fractal_window):
    from fractalchemy.library.items import Kind

    win = fractal_window
    model = win.fractalLibraryPanel.model
    entry = next(i for i in model.entries() if i.kind == Kind.ENTRY and i.name == "pearl")
    win.open_item(entry)
    wait_until(lambda: win.document.flame is not None and win.document.flame.name == "pearl")
    assert win.document.source_index == 3


def test_camera_zoom_keeps_the_point_under_the_cursor_and_rerenders_at_half_size(fractal_window):
    from PySide6.QtCore import QPointF

    win = fractal_window
    win.show_flame(load_flame(win.fractal_library.roots.paths()[0] / "candy.flame", 0))
    submitted = []
    real_submit = win.render_service.submit
    win.render_service.submit = lambda key, flame, settings, priority=0: (submitted.append((key, settings)), real_submit(key, flame, settings, priority))
    before = win.viewport.generation
    view = win.viewport
    pos = QPointF(view.image_rect.center())
    anchor = view.fractal_point_at(pos)
    view.zoom_camera_at(pos, 1.0)                                       # what Ctrl+wheel does
    assert view.fractal_point_at(pos) == pytest.approx(anchor, abs=1e-9)
    assert view._document.flame.camera.zoom == pytest.approx(-0.544 + 1.0)
    assert view.generation == before + 1 and view._settle.isActive()
    assert submitted[-1][1].width == int(view.image_rect.width() * 0.5)   # interactive: half resolution
    wait_until(lambda: len(submitted) >= 2 and not view._settle.isActive())
    assert submitted[-1][1].width == view.image_rect.width() and submitted[-1][0] != submitted[-2][0]   # settled
    wait_until(lambda: view.stats is not None and view.stats.width == view.image_rect.width() and view.stats.finished,
               timeout_ms=60000)


def test_thumbnail_view_renders_icons_for_entries(fractal_window):
    from fractalchemy.library.items import Kind

    win = fractal_window
    win.actionThumbnailView.setChecked(True)
    assert win.fractalLibraryPanel.thumb_button.isChecked() and win.thumbnails.enabled
    panel = win.fractalLibraryPanel
    panel.tree.expandAll()
    entry = next(i for i in panel.model.entries() if i.kind == Kind.ENTRY and i.name == "original")
    index = panel.model.index_for(entry)
    panel.model.data(index, Qt.ItemDataRole.DecorationRole)   # what the view does when painting the row
    wait_until(lambda: win.thumbnails.cached(entry) is not None, timeout_ms=60000)
    icon = win.thumbnails.cached(entry)
    assert not icon.isNull() and icon.pixmap(120, 75).width() == 120
    win.actionThumbnailView.setChecked(False)
    assert not win.thumbnails.enabled and panel.list_button.isChecked()


# --- formula browser ------------------------------------------------------------
def test_help_menu_opens_the_formula_browser(window):
    assert any(a.text().startswith("Formulas") for a in window.menuHelp.actions())
    window.actionFormulas.trigger()
    browser = window._formula_browser
    assert browser is not None and browser.isVisible()
    groups = [browser.tree.topLevelItem(i).text(0) for i in range(browser.tree.topLevelItemCount())]
    assert "Built-in (flam3 / Apophysis)" in groups and "Apophysis 7X sources" in groups
    assert "formulas loaded" in browser.summary.text()
    browser.search.setText("collideoscope")
    visible = [browser.tree.topLevelItem(i) for i in range(browser.tree.topLevelItemCount()) if not browser.tree.topLevelItem(i).isHidden()]
    assert len(visible) == 1
    item = next(visible[0].child(i) for i in range(visible[0].childCount()) if not visible[0].child(i).isHidden())
    browser.tree.setCurrentItem(item)
    text = browser.details.toPlainText()
    assert text.startswith("collideoscope") and "collideoscope_num" in text and "int" in text and "Origin:" in text
    window.actionFormulas.trigger()   # re-opening just raises the same window
    assert window._formula_browser is browser
    browser.close()


# --- the opened file's temporary area ----------------------------------------------
def test_open_button_shows_the_file_in_a_temporary_area_above_the_library(fractal_window, tmp_path, monkeypatch):
    import shutil
    from PySide6.QtWidgets import QFileDialog, QInputDialog
    from fractalchemy.fractal.formats import load_flames
    from fractalchemy.library.items import Kind
    from fractalchemy.library.model import ITEM_ROLE

    win = fractal_window
    model = win.fractalLibraryPanel.model
    loose = tmp_path / "loose.flame"
    shutil.copy(win.fractal_library.roots.paths()[0] / "candy.flame", loose)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(loose), "")))
    win.actionOpenFractal.trigger()
    wait_until(lambda: model.open_file == loose and win.document.flame is not None and win.document.source_path == loose)
    rows = [model.item(r).data(ITEM_ROLE) for r in range(model.rowCount())]
    assert [r.kind for r in rows] == [Kind.FILE, Kind.SEPARATOR, Kind.ROOT] and rows[0].temporary and rows[0].path == loose
    first = model.item(0)
    assert [first.child(i).text() for i in range(first.rowCount())] == ["original", "outlined", "rotated", "pearl", "obsession"]
    assert all(first.child(i).data(ITEM_ROLE).temporary for i in range(first.rowCount()))
    assert win.fractalLibraryPanel.tree.item_at(win.fractalLibraryPanel.tree._proxy.index(1, 0)) is None   # the line is no item
    assert model.root_paths() == [win.fractal_library.roots.paths()[0]] and list(model.file_counts()) == model.root_paths()
    # the entries are browsable like the rest of the library
    win.open_item(first.child(3).data(ITEM_ROLE))
    wait_until(lambda: win.document.flame is not None and win.document.flame.name == "pearl")
    assert win.document.source_index == 3
    # saving a new entry into the opened file updates its area
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("sixth", True)))
    win.actionSaveAsNewEntry.trigger()
    wait_until(lambda: win.document.source_index == 5)
    wait_until(lambda: model.item(0).rowCount() == 6 and not win.fractal_library._pending)
    assert model.item(0).child(5).text() == "sixth" and len(load_flames(loose)) == 6
    # opening another file replaces the slot
    other = tmp_path / "other.flame"
    shutil.copy(win.fractal_library.roots.paths()[0] / "bel2.flame", other)
    win.open_file_path(other)
    wait_until(lambda: model.open_file == other and not win.fractal_library._pending)
    assert [model.item(r).data(ITEM_ROLE).kind for r in range(model.rowCount())] == [Kind.FILE, Kind.SEPARATOR, Kind.ROOT]
    # a file changed by another program is rescanned
    shutil.copy(loose, other)
    wait_until(lambda: model.item(0).rowCount() == 6 and not win.fractal_library._pending, timeout_ms=8000)
    win.fractal_library.show_file(None)
    assert model.open_file is None and model.rowCount() == 1
