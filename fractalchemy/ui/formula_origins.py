"""Where a formula came from, and the colour that says so in every list.

Four origins, each with a light background and a darker text colour that reads on it:

    built-in     the flam3 classics and Apophysis 7X built-ins (native Python)     blue
    apophysis    the bundled Apophysis plugin library (sources, ports, DLLs)        amber
    jwildfire    variations translated from JWildfire                               green
    user         the user's own formulas                                            violet

`origin_of(var)` classifies a registered variation; `ORIGINS` carries the labels and colours, so the Formula
Editor's list, the formula browser and the Transform Editor's Variations tab all paint the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor

from ..formulas import workbench as W
from ..fractal import variations as V

BUILTIN, APOPHYSIS, JWILDFIRE, USER = "built-in", "apophysis", "jwildfire", "user"


@dataclass(frozen=True)
class Origin:
    """One origin: its key, a label, and the two colours."""
    key: str
    label: str
    background: str
    text: str
    description: str

    @property
    def background_color(self) -> QColor:
        """The light row background."""
        return QColor(self.background)

    @property
    def text_color(self) -> QColor:
        """The darker text colour that contrasts with the background."""
        return QColor(self.text)


ORIGINS: dict[str, Origin] = {
    BUILTIN: Origin(BUILTIN, "Built-in", "#e3effb", "#123f73", "flam3 classics and Apophysis 7X built-ins (native Python)"),
    APOPHYSIS: Origin(APOPHYSIS, "Apophysis", "#fff1d6", "#6b4400", "bundled Apophysis plugin library (sources, ports, reconstructed DLLs)"),
    JWILDFIRE: Origin(JWILDFIRE, "JWildfire", "#e4f5e3", "#1e5a22", "variations translated from JWildfire"),
    USER: Origin(USER, "User", "#f1e6fb", "#4d1d7a", "your own formulas"),
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
