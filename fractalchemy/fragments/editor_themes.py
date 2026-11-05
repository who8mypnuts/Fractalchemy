"""Colour themes for the fragment editor: the syntax colours plus the editor's background, text, gutter and selection.

Plain dictionaries (Qt-free) — the editor turns them into formats and a palette. *Default* is the host's light
scheme (every other editor in the application uses it); the rest are the classics a GLSL author may be used to:
Solarized light / dark, Monokai, a plain Dark and the high-contrast *Paper*. The theme is a Fragments preference
(`editor_theme`) applied to every tab, the preprocessed-source viewer and the diff view.
"""

from __future__ import annotations

DEFAULT_THEME = "Default"
SYNTAX_KEYS = ("keyword", "type", "function", "builtin", "string", "comment", "number", "preprocessor", "annotation", "preset", "special")

THEMES: dict[str, dict[str, str]] = {
    "Default": {
        "background": "", "text": "", "gutter": "", "gutter_text": "#8a8a8a", "current_line": "", "selection": "",
        "keyword": "#7b2fa0", "type": "#1565c0", "function": "#3b5f9e", "builtin": "#8d5a00", "string": "#2e7d32",
        "comment": "#8a8a8a", "number": "#c45200", "preprocessor": "#4a7a48", "annotation": "#b5541c", "preset": "#9a9a9a",
        "special": "#0d47a1",
    },
    "Dark": {
        "background": "#1e1f22", "text": "#d6d6d6", "gutter": "#232428", "gutter_text": "#6f7075", "current_line": "#2a2b30", "selection": "#264f78",
        "keyword": "#c586c0", "type": "#4fc1ff", "function": "#dcdcaa", "builtin": "#d7ba7d", "string": "#ce9178",
        "comment": "#6a9955", "number": "#b5cea8", "preprocessor": "#9cdcfe", "annotation": "#f0a060", "preset": "#7a7a7a",
        "special": "#4ec9b0",
    },
    "Solarized light": {
        "background": "#fdf6e3", "text": "#657b83", "gutter": "#eee8d5", "gutter_text": "#93a1a1", "current_line": "#eee8d5", "selection": "#d3cbb7",
        "keyword": "#859900", "type": "#b58900", "function": "#268bd2", "builtin": "#2aa198", "string": "#2aa198",
        "comment": "#93a1a1", "number": "#d33682", "preprocessor": "#cb4b16", "annotation": "#6c71c4", "preset": "#93a1a1",
        "special": "#dc322f",
    },
    "Solarized dark": {
        "background": "#002b36", "text": "#839496", "gutter": "#073642", "gutter_text": "#586e75", "current_line": "#073642", "selection": "#274c5a",
        "keyword": "#859900", "type": "#b58900", "function": "#268bd2", "builtin": "#2aa198", "string": "#2aa198",
        "comment": "#586e75", "number": "#d33682", "preprocessor": "#cb4b16", "annotation": "#6c71c4", "preset": "#586e75",
        "special": "#dc322f",
    },
    "Monokai": {
        "background": "#272822", "text": "#f8f8f2", "gutter": "#2d2e27", "gutter_text": "#75715e", "current_line": "#3e3d32", "selection": "#49483e",
        "keyword": "#f92672", "type": "#66d9ef", "function": "#a6e22e", "builtin": "#fd971f", "string": "#e6db74",
        "comment": "#75715e", "number": "#ae81ff", "preprocessor": "#f92672", "annotation": "#fd971f", "preset": "#75715e",
        "special": "#66d9ef",
    },
    "Paper": {
        "background": "#ffffff", "text": "#000000", "gutter": "#f4f4f4", "gutter_text": "#777777", "current_line": "#f2f6ff", "selection": "#bcd5ff",
        "keyword": "#000080", "type": "#005a9c", "function": "#1a1a7a", "builtin": "#7a4100", "string": "#006400",
        "comment": "#707070", "number": "#a33000", "preprocessor": "#2e5e2e", "annotation": "#9a3f10", "preset": "#888888",
        "special": "#00337a",
    },
}


def theme(name: str) -> dict[str, str]:
    """The theme called `name` (the default when unknown)."""
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def theme_names() -> list[str]:
    return list(THEMES)


__all__ = ["THEMES", "DEFAULT_THEME", "SYNTAX_KEYS", "theme", "theme_names"]
