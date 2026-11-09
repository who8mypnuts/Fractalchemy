"""The syntax highlighters' shared half: text formats made from a theme's syntax roles.

The Script Editor's Python highlighter, the Formula Editor's C-dialect one and the Fragments window's GLSL one each
decide *what* a piece of text is (a keyword, a string, a comment…); the colour of each kind is the theme role of the
same name (`themes.model.SYNTAX_ROLES`). `set_theme(theme)` rebuilds the formats and re-colours the document, so an
editor follows a theme change without reopening anything.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from ..themes.model import Theme
from .theming import current_theme

ITALIC_ROLES = ("comment", "preset")


class ThemedHighlighter(QSyntaxHighlighter):
    """A highlighter whose formats (`self._formats[role]`) come from a theme.

    Subclasses set `ROLES` (the syntax roles they use) and `BOLD` (the ones drawn bold).
    """
    ROLES: tuple[str, ...] = ()
    BOLD: tuple[str, ...] = ("keyword",)

    def __init__(self, document: QTextDocument, theme: Theme | None = None):
        super().__init__(document)                   # (Qt highlights the document itself once the event loop runs)
        self._formats: dict[str, QTextCharFormat] = {}
        self._build(theme or current_theme())

    def set_theme(self, theme: Theme) -> None:
        """Use `theme`'s syntax colours and re-colour the document."""
        self._build(theme)
        if self.document() is not None and not self.document().isEmpty():
            self.rehighlight()

    def _build(self, theme: Theme) -> None:
        self._formats = {role: self._format(theme[role], role in self.BOLD, role in ITALIC_ROLES) for role in self.ROLES}

    def color_of(self, role: str) -> QColor:
        """The colour text of kind `role` is drawn in (tests and previews)."""
        return self._formats[role].foreground().color()

    @staticmethod
    def _format(colour: str, bold: bool, italic: bool) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(colour))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        fmt.setFontItalic(italic)
        return fmt


__all__ = ["ThemedHighlighter"]
