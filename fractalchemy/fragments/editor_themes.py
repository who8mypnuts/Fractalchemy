"""The fragment editors' colour theme: follow the application theme (the default) or pin one catalogue theme.

The themes themselves are the application's (`fractalchemy.themes`): thirty-odd themes with syntax colours checked for
contrast. This module holds the Fragments window's preference around them:

* `FOLLOW` ("Follow application theme") makes the fragment editors recolour with *View ▸ Theme*;
* any catalogue name pins that theme to every fragment editor, the preprocessed-source viewer and the diff view;
* names from before the application had themes still work (`LEGACY_NAMES`: Default → Follow, Dark → Fractalchemy
  Dark, Solarized light / dark → Solarized Light / Dark; Monokai and Paper keep their names).

Qt-free: `theme(name)` returns a theme's editor colours as a plain dictionary (the syntax keys plus background, text,
gutter, current line and selection). For `FOLLOW` that is the light fallback; the editors themselves ask the theme
manager for the live theme.
"""

from __future__ import annotations

from ..themes import catalog

FOLLOW = "Follow application theme"
DEFAULT_THEME = FOLLOW
LEGACY_NAMES = {"Default": FOLLOW, "Dark": "Fractalchemy Dark", "Solarized light": "Solarized Light",
                "Solarized dark": "Solarized Dark"}
SYNTAX_KEYS = ("keyword", "type", "function", "builtin", "string", "comment", "number", "preprocessor", "annotation", "preset", "special")
CHROME_KEYS = {"background": "editor_bg", "text": "editor_fg", "gutter": "gutter", "gutter_text": "gutter_fg",
               "current_line": "current_line", "selection": "selection"}


def canonical(name: str) -> str:
    """The preference value for `name`: a catalogue theme name, or `FOLLOW` (legacy and unknown names map)."""
    name = LEGACY_NAMES.get(name, name)
    return name if name in catalog.SEEDS else FOLLOW


def pinned(name: str) -> str | None:
    """The catalogue theme a preference value pins (None: follow the application)."""
    name = canonical(name)
    return None if name == FOLLOW else name


def theme_names() -> list[str]:
    """The choices: Follow first, then every catalogue theme."""
    return [FOLLOW, *catalog.SEEDS]


def theme(name: str) -> dict[str, str]:
    """The editor colours of `name` as a dictionary (the light fallback for Follow and unknown names)."""
    source = catalog.theme(pinned(name) or catalog.SYSTEM)
    return {**{key: source[role] for key, role in CHROME_KEYS.items()}, **{key: source[key] for key in SYNTAX_KEYS}}


__all__ = ["FOLLOW", "DEFAULT_THEME", "LEGACY_NAMES", "SYNTAX_KEYS", "canonical", "pinned", "theme_names", "theme"]
