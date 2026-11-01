"""The Fragments window's Help menu: the guide (`docs/fragments.md`), the welcome note, the batch / CLI help, links.

The guide is rendered from the repository's markdown by `QTextBrowser.setMarkdown` (tables included) in a plain
window with a search box; the welcome note is FragM's first-run advice, brought up to date for this host; the
scripting page is the command-line renderer's `--help` text. Links open the system browser.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QDesktopServices, QTextDocument
from PySide6.QtWidgets import QDialog, QLineEdit, QMessageBox, QTextBrowser, QVBoxLayout, QWidget

GUIDE_PATH = Path(__file__).resolve().parents[3] / "docs" / "fragments.md"
CLI_PATH = Path(__file__).resolve().parents[3] / "tools" / "render_frag.py"

WELCOME = """<p><b>Welcome to Fragments</b> — Fragmentarium inside Fractalchemy.</p>
<p>(1) Fragments render on the GPU through OpenGL. A discrete graphics card with recent drivers is best; software
rasterisers work but slowly.</p>
<p>(2) Windows and some Linux drivers have a GPU watchdog that resets a driver when one draw takes about two seconds.
The viewport renders at half size while the camera moves, adapts the subframes per image to the refresh interval, and
splits a subframe into tiles when one takes longer than the budget (the status bar then shows <i>tiled n×n</i>), so
heavy fragments should stay clear of it. Hi-res renders are tiled by construction.</p>
<p>(3) Most examples accumulate <i>subframes</i> (progressive rendering) and keep the GPU busy while they do. The
<i>Subframe max</i> box on the toolbar limits how many are drawn; 0 means keep going.</p>
<p>(4) Fragmentarium and FragM <code>.frag</code> files open unchanged; the bundled library (<i>Library ▸ Examples</i>)
is FragM's. Files saved as <code>.fafrag</code> carry Fractalchemy's render and animation settings in a comment
FragM ignores.</p>
<p>(5) New to distance estimators? <i>Library ▸ Examples ▸ Fractalchemy Tutorials</i> holds four fragments that explain
themselves step by step; open the <i>Walkthrough</i> dock (<i>Windows</i> menu) to jump between the steps.</p>
<p>See <i>Help ▸ Fragment language and guide</i> for the directives, the annotations and every control.</p>"""

LINKS = (("FragM on GitHub (3Dickulus)", "https://github.com/3Dickulus/FragM"),
         ("Fragmentarium (Syntopia)", "https://syntopia.github.io/Fragmentarium/"),
         ("Fragmentarium wiki", "https://github.com/3Dickulus/FragM/wiki"),
         ("FractalForums", "https://fractalforums.org/"),
         ("The GLSL specification", "https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.4.60.pdf"))


class MarkdownWindow(QDialog):
    """A markdown page with a search box (Ctrl+F-like filtering by scrolling to the first match)."""

    def __init__(self, parent: QWidget | None, title: str, markdown: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(False)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find…")
        self.search.returnPressed.connect(self._find)
        layout.addWidget(self.search)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(lambda url: QDesktopServices.openUrl(url) if url.scheme() in ("http", "https") else None)
        self.browser.document().setMarkdown(markdown, QTextDocument.MarkdownFeature.MarkdownDialectGitHub)
        layout.addWidget(self.browser, 1)
        self.resize(900, 700)

    def _find(self) -> None:
        text = self.search.text()
        if text and not self.browser.find(text):
            cursor = self.browser.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.browser.setTextCursor(cursor)
            self.browser.find(text)


def show_guide(parent: QWidget | None) -> MarkdownWindow:
    """*Help ▸ Fragment language and guide*: `docs/fragments.md`."""
    try:
        text = GUIDE_PATH.read_text(encoding="utf-8")
    except OSError:
        text = "# Fragments\n\n`docs/fragments.md` is not available in this installation."
    window = MarkdownWindow(parent, "Fragments — guide and language reference", text)
    window.show()
    return window


def show_cli_help(parent: QWidget | None) -> MarkdownWindow:
    """*Help ▸ Batch rendering from the command line*: the CLI's help text."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("render_frag", CLI_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        import argparse
        parser = argparse.ArgumentParser(prog="python tools/render_frag.py", description=module.__doc__.split("\n\n")[0])
        module.add_arguments(parser)
        usage = parser.format_help()
        body = f"# Batch rendering from the command line\n\n{module.__doc__}\n\n```\n{usage}\n```"
    except Exception as exc:  # noqa: BLE001 - the tool is optional in an installation
        body = f"# Batch rendering\n\n`tools/render_frag.py` could not be loaded: {exc}"
    window = MarkdownWindow(parent, "Fragments — batch rendering", body)
    window.show()
    return window


def show_welcome(parent: QWidget | None) -> None:
    """*Help ▸ Welcome note*."""
    QMessageBox.information(parent, "Welcome to Fragments", WELCOME)


__all__ = ["MarkdownWindow", "show_guide", "show_cli_help", "show_welcome", "LINKS", "GUIDE_PATH"]
