"""HueClid entry point."""

import sys

from PySide6.QtWidgets import QApplication

from hueclid.config import APP_NAME
from hueclid.ui.main_window import MainWindow


def main() -> int:
    """Create the application and show the main window.

    Returns:
        The process exit code.
    """
    app = QApplication(sys.argv)
    app.setOrganizationName(APP_NAME)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
