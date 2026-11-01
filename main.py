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
    fragment = _fragment_argument(sys.argv[1:])
    if fragment is not None:
        window.show_fragments(fragment)    # `--fragment FILE`: open the Fragments window on a .frag / .fafrag
    return app.exec()


def _fragment_argument(args: list[str]) -> str | None:
    """The file named by `--fragment FILE` / `--fragment=FILE`, or a bare `.frag` / `.fafrag` argument."""
    for i, arg in enumerate(args):
        if arg == "--fragment" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--fragment="):
            return arg.split("=", 1)[1]
        if arg.lower().endswith((".frag", ".fafrag")):
            return arg
    return None


if __name__ == "__main__":
    multiprocessing.freeze_support()   # the final renderer's CPU workers are spawned processes (matters when frozen)
    sys.exit(main())
