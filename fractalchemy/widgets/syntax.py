"""Syntax highlighting that takes its colours from the theme.

Each language's highlighter lists the theme roles it paints with, and how (`STYLES`: role → bold, italic). The colours
come from a `themes.Theme` through `set_theme`, which `BaseCodeEditor` calls whenever its theme changes, so every
editor (Script, Formula and Fragments) is readable in every theme and recolours live.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from ..themes import Theme


class ThemedHighlighter(QSyntaxHighlighter):
    """Base class: `self._formats[role]` holds the `QTextCharFormat` of each role in `STYLES` for the current theme."""
    STYLES: dict[str, tuple[bool, bool]] = {}

    def __init__(self, document: QTextDocument, theme: Theme | None = None):
        super().__init__(document)
        self._formats: dict[str, QTextCharFormat] = {}
        if theme is None:
            from .theming import current_theme
            theme = current_theme()
        self.set_theme(theme, rehighlight=False)

    def set_theme(self, theme: Theme, rehighlight: bool = True) -> None:
        """Use `theme`'s syntax colours (and recolour the document)."""
        self._formats = {role: text_format(theme[role], bold, italic) for role, (bold, italic) in self.STYLES.items()}
        if rehighlight and self.document() is not None:
            self.rehighlight()

    def format_color(self, role: str) -> QColor:
        """The colour `role` is painted in (tests, and the legend in the docs)."""
        return self._formats[role].foreground().color()


def text_format(colour: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    """A character format in `colour`."""
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(colour))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    fmt.setFontItalic(italic)
    return fmt


__all__ = ["ThemedHighlighter", "text_format"]
