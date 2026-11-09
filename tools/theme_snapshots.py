"""Screenshots of the main windows in chosen themes, for reviewing readability by eye (a development aid).

    python tools/theme_snapshots.py OUT_DIR [THEME ...]          # default: Nord, Nord Snow Storm, Dracula, Solarized Light

For every theme it writes `<theme>-<window>.png` for the main window, the Transform Editor, the Gradient Library, the
Script Editor, the Formula Editor, the Fragments window and (when present) the Mutate & Breed window. Runs offscreen on
the CPU engine; the sample flames are the library.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_THEMES = ("Nord", "Nord Snow Storm", "Dracula", "Solarized Light")


def spin(ms: int) -> None:
    from PySide6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main(argv: list[str]) -> int:
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from fractalchemy import config
    config.PREVIEW_REFINE_TO = 0.0
    out = Path(argv[0]) if argv else Path("theme-snapshots")
    names = argv[1:] or list(DEFAULT_THEMES)
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    from fractalchemy.fractal.formats import load_flame
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.scripting.generate import flame_to_script
    from fractalchemy.ui.main_window import MainWindow
    from fractalchemy.widgets.theming import theme_manager

    settings = QSettings(str(out / "snapshots.ini"), QSettings.Format.IniFormat)
    roots = LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key)
    roots.add(ROOT / "samples" / "sample flames")
    theme_manager().install(app, None)
    win = MainWindow(LibraryRoots(settings), roots, prefer_gpu=False, settings=settings)
    win.resize(1200, 760)
    win.show()
    win.inspectorPanel.set_values(1, 1.0)
    win.show_flame(load_flame(ROOT / "samples" / "sample flames" / "candy.flame", 0))
    script = win.script_editor
    script.editor.set_text(flame_to_script(win.document.flame)[:2500])
    formula = win.formula_editor
    formula.load_formula("julian")
    windows = {"main": win, "transform-editor": win.editor, "gradient-library": win.gradient_library, "script-editor": script,
               "formula-editor": formula, "fragments": win.fragments_window}
    mutation = getattr(win, "mutation_window", None)
    if mutation is not None:
        windows["mutate-breed"] = mutation
    for window in windows.values():
        window.show()
        window.resize(max(window.width(), 1100), max(window.height(), 700))
    for name in names:
        theme_manager().apply(name, persist=False)
        spin(2500)
        for key, window in windows.items():
            window.grab().save(str(out / f"{name.replace(' ', '_')}-{key}.png"))
        print(f"{name}: {len(windows)} screenshots")
    win.gradient_library.document.modified = False
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
