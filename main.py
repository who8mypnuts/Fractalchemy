"""Fractalchemy entry point."""

import sys

from PySide6.QtWidgets import QApplication

from fractalchemy.settings import configure_application, migrate_legacy_settings
from fractalchemy.ui.main_window import MainWindow


def main() -> int:
    """Create the application and show the main window.

    Returns:
        The process exit code.
    """
    app = QApplication(sys.argv)
    configure_application(app)
    migrate_legacy_settings()  # carry HueClid's library folders over on the first run
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
