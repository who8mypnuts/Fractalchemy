"""Colour themes for the whole application (Qt-free): the model and contrast rules (`model`), the catalogue
(`catalog`, with the Nord family in `nord`). `widgets/theming.py` applies them to Qt."""

from .catalog import DEFAULT_THEME, SYSTEM, groups, is_dark, theme, theme_names
from .model import ROLES, Seed, Theme, contrast_ratio, derive

__all__ = ["DEFAULT_THEME", "SYSTEM", "groups", "is_dark", "theme", "theme_names", "ROLES", "Seed", "Theme", "contrast_ratio",
           "derive"]
