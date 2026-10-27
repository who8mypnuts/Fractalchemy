"""Fractalchemy entry point."""

import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from fractalchemy.settings import configure_application, migrate_legacy_settings


def main() -> int:
    """Create the application and show the main window.

    Returns:
        The process exit code.
    """
    from fractalchemy.ui.main_window import MainWindow   # lazy: spawned render workers re-import this module

    app = QApplication(sys.argv)
    configure_application(app)
    migrate_legacy_settings()  # carry HueClid's library folders over on the first run
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    multiprocessing.freeze_support()   # the final renderer's CPU workers are spawned processes (matters when frozen)
    sys.exit(main())
