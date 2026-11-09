"""*View ▸ Theme*: System, then the Nord family, the dark themes and the light themes as submenus, one checkable entry
each. Choosing one applies it to the whole application at once (and it is remembered)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QWidget

from ..themes import catalog
from .theming import on_theme_changed, theme_manager


class ThemeMenu(QMenu):
    """The theme chooser (see the module docstring); `actions_by_name` maps every theme name to its entry."""

    def __init__(self, parent: QWidget | None = None, title: str = "Theme"):
        super().__init__(title, parent)
        self.setToolTipsVisible(True)
        self.group = QActionGroup(self)
        self.group.setExclusive(True)
        self.actions_by_name: dict[str, QAction] = {}
        self._add(self, catalog.SYSTEM, "The platform's own look; editor colours adapt to its light or dark palette")
        self.addSeparator()
        add_theme_groups(self, lambda submenu, name: self._add(submenu, name, f"{name} — {'dark' if catalog.is_dark(name) else 'light'}"))
        self.check(theme_manager().name)
        on_theme_changed(self, lambda _theme: self.check(theme_manager().name), lazy=False)   # cheap: keep the tick right

    def _add(self, menu: QMenu, name: str, tip: str) -> None:
        action = menu.addAction(name)
        action.setCheckable(True)
        action.setToolTip(tip)
        action.setStatusTip(f"Theme: {tip}")
        action.triggered.connect(lambda _checked=False, n=name: theme_manager().apply(n))
        self.group.addAction(action)
        self.actions_by_name[name] = action

    def check(self, name: str) -> None:
        """Tick the entry of theme `name`."""
        action = self.actions_by_name.get(name)
        if action is not None and not action.isChecked():
            action.setChecked(True)


def add_theme_groups(menu: QMenu, add: Callable[[QMenu, str], None]) -> None:
    """One submenu per catalogue group (Nord, Dark, Light) under `menu`, calling `add(submenu, name)` for every theme in it —
    the structure *View ▸ Theme* and the Fragments window's *Editor theme* menu share."""
    for title, names in catalog.groups():
        submenu = menu.addMenu(title)
        for name in names:
            add(submenu, name)


__all__ = ["ThemeMenu", "add_theme_groups"]
