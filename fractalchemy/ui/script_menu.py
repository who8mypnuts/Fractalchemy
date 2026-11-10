"""Scripts in the main window: templates pinned from the Script Editor, run in one click with their saved values.

* `ScriptPins` — the pinned templates in QSettings (`scripts/pinned`, JSON): a key per template (`builtin:<name>` for
  the shipped ones, whose files move with the installation; `user:<path>` for your own), its name, and the parameter
  values it runs with (updated whenever you adjust them in the Parameters tab after running it from the menu).
* `ScriptsMenu` — the main window's **Scripts ▾** toolbar menu and *Windows ▸ Scripts*: the pinned templates, then
  *Adjust Parameters…* (the Script Editor's Parameters tab for the last one run from here), *Manage Pinned Scripts…*
  (its Templates tab) and *Run a Script on Many Fractals…*. Running a pin does not open the editor or touch its text
  (`ScriptEditorWindow.run_code`); the run is one undo step like any other.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Callable

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QMenu, QWidget

from ..scripting import templates as T

PINS_KEY = "scripts/pinned"
ORIGIN_PREFIX = "pinned:"


def pin_key(template: T.Template) -> str:
    """A stable key for a template: built-in ones by name, yours by file."""
    return f"builtin:{template.name}" if template.builtin else f"user:{template.path or template.name}"


@dataclass
class Pin:
    key: str
    name: str
    values: dict = field(default_factory=dict)


class ScriptPins(QObject):
    """The pinned templates (see the module docstring).

    Signals:
        changed(): A pin was added, removed or its values changed.
    """
    changed = Signal()

    def __init__(self, settings: QSettings, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings
        self._pins: list[Pin] = self._load()

    def _load(self) -> list[Pin]:
        try:
            data = json.loads(self._settings.value(PINS_KEY, "[]") or "[]")
            return [Pin(str(d["key"]), str(d.get("name", "")), dict(d.get("values", {}))) for d in data]
        except (TypeError, ValueError, KeyError):
            return []

    def _save(self) -> None:
        self._settings.setValue(PINS_KEY, json.dumps([asdict(p) for p in self._pins]))
        self.changed.emit()

    @property
    def pins(self) -> list[Pin]:
        return list(self._pins)

    def is_pinned(self, template: T.Template) -> bool:
        return any(p.key == pin_key(template) for p in self._pins)

    def toggle(self, template: T.Template) -> bool:
        """Pin `template` (or unpin it); True when it is pinned afterwards."""
        key = pin_key(template)
        if any(p.key == key for p in self._pins):
            self._pins = [p for p in self._pins if p.key != key]
            self._save()
            return False
        self._pins.append(Pin(key, template.name))
        self._save()
        return True

    def set_values(self, key: str, values: dict) -> None:
        for pin in self._pins:
            if pin.key == key and pin.values != values:
                pin.values = dict(values)
                self._save()

    def template(self, pin: Pin, templates: list[T.Template]) -> T.Template | None:
        """The template a pin refers to, among `templates` (None: it was deleted or renamed)."""
        return next((t for t in templates if pin_key(t) == pin.key), None)


class ScriptsMenu(QMenu):
    """The main window's Scripts menu (see the module docstring)."""

    def __init__(self, editor: Callable[[], object], batch: Callable[[], None], parent: QWidget | None = None):
        """Args:
            editor: Returns the Script Editor window (created on first use, not shown); it holds the pins.
            batch: Opens the *Run a Script on Many Fractals* window.
        """
        super().__init__("Scripts", parent)
        self._editor = editor
        self._batch = batch
        self.setToolTipsVisible(True)
        self.aboutToShow.connect(self.rebuild)

    def rebuild(self) -> None:
        self.clear()
        editor = self._editor()
        pins = editor.pins
        templates = editor.all_templates()
        for pin in pins.pins:
            template = pins.template(pin, templates)
            action = self.addAction(pin.name, lambda _c=False, p=pin: self.run_pin(p))
            action.setEnabled(template is not None)
            action.setToolTip(template.description if template is not None else "This template no longer exists")
        if not pins.pins:
            self.addAction("No pinned scripts — pin templates in the Script Editor").setEnabled(False)
        self.addSeparator()
        adjust = self.addAction("Adjust Parameters…", lambda: editor.show_tab("parameters"))
        adjust.setEnabled(editor.live.session is not None and editor.live.session.origin.startswith(ORIGIN_PREFIX) and bool(editor.live.specs))
        self.addAction("Manage Pinned Scripts…", lambda: editor.show_tab("templates"))
        self.addAction("Run a Script on Many Fractals…", self._batch)

    def run_pin(self, pin: Pin) -> bool:
        """Run a pinned template on the fractal with its saved values."""
        editor = self._editor()
        template = editor.pins.template(pin, editor.all_templates())
        if template is None:
            return False
        return editor.run_code(template.code, template.name, parameters=dict(pin.values), origin=ORIGIN_PREFIX + pin.key)


__all__ = ["ScriptPins", "ScriptsMenu", "Pin", "pin_key", "ORIGIN_PREFIX"]
