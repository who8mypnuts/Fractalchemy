"""Main window shell: menus, toolbar, the Gradient Library tool window, and settings migration."""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox, QToolButton

from fractalchemy import config
from fractalchemy.library.roots import KEY as ROOTS_KEY, LibraryRoots
from fractalchemy.model import Gradient
from fractalchemy.settings import migrate_legacy_settings
from fractalchemy.ui.gradient_library_window import GradientLibraryWindow
from fractalchemy.ui.main_window import MainWindow
from tests.conftest import spin


@pytest.fixture
def window(qapp, tmp_path):
    win = MainWindow(LibraryRoots(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)))
    win.show()
    yield win
    win.gradient_library.document.modified = False  # never prompt on teardown
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
    assert [a.text() for a in window.menuWindows.actions()] == ["Gradient Library"]
    assert [a.text() for a in window.menuHelp.actions()] == ["About Fractalchemy…", "About Qt…"]
    assert [a.text() for a in window.menuView.actions()] == ["Toolbar", "Status Bar"]


def test_toolbar_holds_the_gradient_library_button_with_popup_text(window):
    assert window.toolBar.isVisible()
    assert window.toolBar.actions() == [window.actionGradientLibrary]
    button = window.toolBar.widgetForAction(window.actionGradientLibrary)
    assert isinstance(button, QToolButton)
    assert button.toolTip() == "Gradient Library"
    assert not window.actionGradientLibrary.icon().isNull()


def test_view_menu_toggles_toolbar_and_status_bar(window):
    toolbar_action, status_action = window.menuView.actions()
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
    window.menuWindows.actions()[0].trigger()
    assert window.gradient_library.isVisible()


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


def test_edit_library_from_main_menu_opens_the_library_dialog(window, monkeypatch):
    opened = []

    class FakeDialog:
        def __init__(self, controller, add_folder, parent):
            opened.append(controller)

        def exec(self):
            return 0

    monkeypatch.setattr("fractalchemy.ui.gradient_library_window.EditLibraryDialog", FakeDialog)
    window.actionEditLibrary.trigger()
    assert opened == [window.gradient_library.library]


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


# --- settings migration -------------------------------------------------------
def test_legacy_hueclid_settings_are_migrated_once(tmp_path):
    old = QSettings(str(tmp_path / "hueclid.ini"), QSettings.Format.IniFormat)
    new = QSettings(str(tmp_path / "fractalchemy.ini"), QSettings.Format.IniFormat)
    old.setValue(ROOTS_KEY, [str(tmp_path)])
    assert migrate_legacy_settings(old, new) == [ROOTS_KEY]
    assert LibraryRoots(new).paths() == [tmp_path.resolve()]
    new.setValue(ROOTS_KEY, [])
    assert migrate_legacy_settings(old, new) == []  # the user's newer value wins
    assert LibraryRoots(new).paths() == []


def test_migration_is_a_no_op_without_legacy_settings(tmp_path):
    old = QSettings(str(tmp_path / "hueclid.ini"), QSettings.Format.IniFormat)
    new = QSettings(str(tmp_path / "fractalchemy.ini"), QSettings.Format.IniFormat)
    assert migrate_legacy_settings(old, new) == []
    assert not new.contains(ROOTS_KEY)
