"""Where a formula came from, and the colour that says so in every list.

Four origins, each with a row tint and a text colour that reads on it:

    built-in     the flam3 classics and Apophysis 7X built-ins (native Python)     blue
    apophysis    the bundled Apophysis plugin library (sources, ports, DLLs)        amber
    jwildfire    variations translated from JWildfire                               green
    user         the user's own formulas                                            violet

The colours belong to the theme (`origin_<kind>` / `origin_<kind>_text`, made from the theme's own blue / yellow /
green / purple): pale tints with dark text on light themes, dark tints with light text on dark ones, always at least
4.5:1. The lists that use them repaint when the theme changes.

`origin_of(var)` classifies a registered variation; `ORIGINS` carries the labels and colours, so the Formula
Editor's list, the formula browser and the Transform Editor's Variations tab all paint the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor

from ..widgets.theming import theme_color

from ..formulas import workbench as W
from ..fractal import variations as V

BUILTIN, APOPHYSIS, JWILDFIRE, USER = "built-in", "apophysis", "jwildfire", "user"


@dataclass(frozen=True)
class Origin:
    """One origin: its key, a label, the theme roles of its colours, and a description."""
    key: str
    label: str
    role: str                # the theme role of the row tint; the text colour is `<role>_text`
    description: str

    @property
    def background_color(self) -> QColor:
        """The row tint in the current theme."""
        return theme_color(self.role)

    @property
    def text_color(self) -> QColor:
        """The text colour that reads on the tint (current theme)."""
        return theme_color(f"{self.role}_text")


ORIGINS: dict[str, Origin] = {
    BUILTIN: Origin(BUILTIN, "Built-in", "origin_builtin", "flam3 classics and Apophysis 7X built-ins (native Python)"),
    APOPHYSIS: Origin(APOPHYSIS, "Apophysis", "origin_apophysis", "bundled Apophysis plugin library (sources, ports, reconstructed DLLs)"),
    JWILDFIRE: Origin(JWILDFIRE, "JWildfire", "origin_jwildfire", "variations translated from JWildfire"),
    USER: Origin(USER, "User", "origin_user", "your own formulas"),
}
ORDER = (BUILTIN, APOPHYSIS, JWILDFIRE, USER)


def origin_of(var: V.Variation, user_dir: Path | None = None) -> str:
    """The origin key of a registered variation (`user_dir`: a folder whose formulas count as the user's)."""
    if var.style == V.LEGACY:
        return BUILTIN
    path = W.origin_path(var)
    if path is None:
        return APOPHYSIS
    if (user_dir is not None and path.parent == user_dir) or W.is_user_file(path) or not W.is_bundled_path(path):
        return USER
    return JWILDFIRE if "jwildfire" in path.parts else APOPHYSIS


def origin_for_name(name: str, user_dir: Path | None = None) -> Origin | None:
    """The `Origin` of a registered formula name (None for an unknown name)."""
    var = V.REGISTRY.get(name)
    return ORIGINS[origin_of(var, user_dir)] if var is not None else None


__all__ = ["Origin", "ORIGINS", "ORDER", "BUILTIN", "APOPHYSIS", "JWILDFIRE", "USER", "origin_of", "origin_for_name"]
