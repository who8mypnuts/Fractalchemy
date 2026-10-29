"""Fractalchemy entry point."""

import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from fractalchemy.settings import configure_application


def main() -> int:
    """Create the application and show the main window.

    Returns:
        The process exit code.
    """
    from fractalchemy.ui.main_window import MainWindow   # lazy: spawned render workers re-import this module

    from fractalchemy.widgets.logo import logo_icon

    app = QApplication(sys.argv)
    configure_application(app)
    app.setWindowIcon(logo_icon())          # the flask: every window and the task bar
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    multiprocessing.freeze_support()   # the final renderer's CPU workers are spawned processes (matters when frozen)
    sys.exit(main())
