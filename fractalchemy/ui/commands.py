"""What the command palette (`Ctrl+K`) offers, in every window of the application.

`window_commands(window)` walks a window's menu bar — submenus included, dynamic ones (*Open Recent*, *Recover*,
*Scripts*, *Theme*) filled first — into `Command`s titled by the action and placed by their menu path ("Edit ▸ Copy
Parameters As"). `PaletteShortcut` hangs off one shared application-wide event filter: `Ctrl+K` in the main
window or any of its tool windows opens a `CommandPalette` listing that window's commands, then the main window's
(when it is another window), then the script templates ("Run template: …"). The commands used last are remembered
(`palette/recent`) and come first.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QSettings, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QWidget

from ..widgets.command_palette import Command, CommandPalette

if TYPE_CHECKING:
    from .main_window import MainWindow

RECENT_KEY = "palette/recent"
RECENT_SIZE = 10
SHORTCUT = QKeySequence("Ctrl+K")


def _title(action: QAction) -> str:
    return action.text().replace("&&", "\0").replace("&", "").replace("\0", "&").split("\t")[0]


def menu_commands(menu: QMenu, path: str, seen: set[int] | None = None) -> list[Command]:
    """Every action of `menu` and its submenus (dynamic menus are filled first, as when they are opened)."""
    seen = set() if seen is None else seen
    if id(menu) in seen:
        return []
    seen.add(id(menu))
    menu.aboutToShow.emit()
    commands = []
    for action in menu.actions():
        if action.isSeparator() or not action.isVisible():
            continue
        sub = action.menu()
        if sub is not None:
            commands += menu_commands(sub, f"{path} ▸ {_title(action)}" if path else _title(action), seen)
            continue
        title = _title(action)
        if not title:
            continue
        if action.isCheckable():
            title += " ✓" if action.isChecked() else ""
        commands.append(Command(title, path, action.shortcut().toString(QKeySequence.SequenceFormat.NativeText),
                                action.trigger, action.isEnabled(), action.icon() if not action.icon().isNull() else None))
    return commands


def window_commands(window: QMainWindow) -> list[Command]:
    """The commands of a window's menu bar."""
    commands: list[Command] = []
    bar = window.menuBar() if isinstance(window, QMainWindow) else None
    if bar is None:
        return commands
    seen: set[int] = set()
    for action in bar.actions():
        if action.menu() is not None:
            commands += menu_commands(action.menu(), _title(action), seen)
    return commands


def template_commands(main: "MainWindow") -> list[Command]:
    """"Run template: …" for every script template (the Script Editor is created on first use)."""
    editor = main.script_editor
    return [Command(f"Run template: {t.name}", "Scripts", "", lambda _t=t: editor.run_code(_t.code, _t.name, origin="palette"), True)
            for t in editor.all_templates()]


class _CtrlKFilter(QObject):
    """The one application-wide event filter: `Ctrl+K` goes to the `PaletteShortcut` whose main window owns the active
    window. Shared, so that every main window made (tests make hundreds) doesn't add another filter every event of the
    application has to pass through; shortcuts register and unregister themselves."""

    _instance: "_CtrlKFilter | None" = None

    def __init__(self):
        super().__init__(QApplication.instance())
        self.shortcuts: list[PaletteShortcut] = []
        QApplication.instance().installEventFilter(self)

    @classmethod
    def shared(cls) -> "_CtrlKFilter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt override
        if event.type() != QEvent.Type.ShortcutOverride or event.key() != Qt.Key.Key_K \
                or event.modifiers() != Qt.KeyboardModifier.ControlModifier:
            return False
        window = QApplication.activeWindow()
        if isinstance(window, CommandPalette):
            return False
        for shortcut in self.shortcuts:
            if shortcut.belongs(window):
                event.accept()
                shortcut.open(window)
                return True
        return False


class PaletteShortcut(QObject):
    """`Ctrl+K` anywhere in the main window's family of windows (see the module docstring)."""

    def __init__(self, main: "MainWindow", settings: QSettings):
        super().__init__(main)
        self.main = main
        self._settings = settings
        self.palette: CommandPalette | None = None
        shortcuts = _CtrlKFilter.shared().shortcuts
        shortcuts.append(self)
        self.destroyed.connect(lambda *_: self in shortcuts and shortcuts.remove(self))

    def release(self) -> None:
        """Stop listening (the main window is closing)."""
        shortcuts = _CtrlKFilter.shared().shortcuts
        if self in shortcuts:
            shortcuts.remove(self)

    def belongs(self, window: QWidget | None) -> bool:
        while window is not None:
            if window is self.main:
                return True
            window = window.parentWidget()
        return False

    def commands(self, window: QWidget) -> list[Command]:
        """The commands for `window`: its own, the main window's, the templates."""
        own = window_commands(window) if isinstance(window, QMainWindow) else []
        shared = window_commands(self.main) if window is not self.main else []
        name = window.windowTitle().split(" — ")[0] if window is not self.main else ""
        for command in own:
            command.path = f"{name}: {command.path}" if name else command.path
        return own + shared + template_commands(self.main)

    def recent(self) -> list[str]:
        try:
            return [str(key) for key in json.loads(self._settings.value(RECENT_KEY, "[]") or "[]")]
        except (TypeError, ValueError):
            return []

    def _remember(self, key: str) -> None:
        recent = [key] + [k for k in self.recent() if k != key]
        self._settings.setValue(RECENT_KEY, json.dumps(recent[:RECENT_SIZE]))

    def open(self, window: QWidget | None = None) -> CommandPalette:
        """Show the palette for `window` (the main window by default)."""
        window = window or self.main
        self.palette = CommandPalette(self.commands(window), self.recent(), window)
        self.palette.ran.connect(self._remember)
        self.palette.show()
        self.palette.query.setFocus()
        return self.palette


__all__ = ["PaletteShortcut", "window_commands", "menu_commands", "template_commands", "SHORTCUT"]
