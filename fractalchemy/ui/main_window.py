"""Top-level application window: menu bar, toolbar, status bar, and the tool windows it opens.

The main window is the shell that the fractal editor will grow into. Today its
central area is a placeholder; the real work happens in the Gradient Library
window, which the *Windows* menu and the toolbar button show.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QMessageBox

from .. import config
from ..library.roots import LibraryRoots
from ..widgets.icons import gradient_icon
from .gradient_library_window import GradientLibraryWindow
from .loader import load_ui

UI_FILE = Path(__file__).resolve().parents[2] / "ui" / "main_window.ui"
ABOUT_TEXT = (
    f"<h3>{config.APP_NAME} {config.APP_VERSION}</h3>"
    "<p>A fractal gradient editor and library, with aspirations of becoming a full fractal editor.</p>"
    "<p>Reads and writes gradients for Apophysis / flam3 (<code>.flame</code>), Ultra Fractal "
    "(<code>.ugr</code>, <code>.gradient</code>, <code>.ufr</code>), Fractint (<code>.map</code>) and "
    "Chaotica (<code>.chaos</code>), and extracts palettes from images.</p>"
)


class MainWindow(QMainWindow):
    """Application shell: File / Edit / View / Windows / Help menus, a toolbar, and the Gradient Library window."""
    def __init__(self, roots: LibraryRoots | None = None):
        """Args:
            roots: Library folders for the Gradient Library; defaults to the persisted list.
        """
        super().__init__()
        load_ui(self, UI_FILE)
        self.setWindowIcon(gradient_icon())
        self.gradient_library = GradientLibraryWindow(roots, self)
        self._connect_actions()

    # --- wiring -------------------------------------------------------------
    def _connect_actions(self) -> None:
        self.actionGradientLibrary.setIcon(gradient_icon())
        self.actionGradientLibrary.triggered.connect(self.show_gradient_library)
        self.actionEditLibrary.triggered.connect(self.gradient_library.edit_library)
        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.about)
        self.actionAboutQt.triggered.connect(lambda: QMessageBox.aboutQt(self, f"About Qt — {config.APP_NAME}"))
        self.menuView.insertAction(self.actionShowStatusBar, self.toolBar.toggleViewAction())
        self.actionShowStatusBar.toggled.connect(self.statusBar().setVisible)

    # --- slots --------------------------------------------------------------
    def show_gradient_library(self) -> None:
        """Open the Gradient Library window, or bring it to the front if it is already open."""
        self.gradient_library.bring_to_front()

    def about(self) -> None:
        """Show the About box."""
        QMessageBox.about(self, f"About {config.APP_NAME}", ABOUT_TEXT)

    # --- Qt overrides -------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        """Quitting closes the tool windows too, so check for unsaved gradient edits first."""
        if not self.gradient_library.files.confirm_discard():
            event.ignore()
            return
        self.gradient_library.close()
        super().closeEvent(event)
