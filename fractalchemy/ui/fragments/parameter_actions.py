"""The Fragments window's parameter and preset commands: reset, copy / paste settings, select source, slider bounds,
insert / group-to / select preset (FragM's F1 – F4, F8, F9).

A helper of `FragmentsWindow` (it holds the window as `w`); the text edits go through the window's `_replace_text`
(undoable in the editor) and rebuild the document.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PySide6.QtGui import QGuiApplication, QTextCursor
from PySide6.QtWidgets import QInputDialog, QMessageBox

from ...fragments import presets
from ...fragments.annotations import rewrite_bound

if TYPE_CHECKING:
    from .window import FragmentsWindow


class ParameterActions:
    """The parameter / preset commands (see the module docstring).

    Args:
        window: The Fragments window.
    """

    def __init__(self, window: "FragmentsWindow"):
        self.w = window

    def reset_all(self) -> None:
        if self.w.tabs.document is not None:
            self.w.tabs.document.reset()
            self.w.message("All parameters reset")

    def copy_settings(self) -> None:
        document = self.w.tabs.document
        if document is not None:
            QGuiApplication.clipboard().setText(document.state.to_text(provenance=document.path.name if document.path else "Unnamed"))
            self.w.message("Settings copied to the clipboard")

    def paste_settings(self) -> None:
        document = self.w.tabs.document
        if document is not None:
            document.apply_settings(QGuiApplication.clipboard().text())
            self.w.message("Pasted settings from the clipboard")

    def paste_selected(self) -> None:
        document, editor = self.w.tabs.document, self.w.tabs.editor
        if document is not None and editor is not None and editor.selected_text():
            document.apply_settings(editor.selected_text().replace("\u2029", "\n"))
            self.w.message("Pasted the selected settings")

    def select_source(self, name: str) -> None:
        """*Select source*: select the line declaring parameter `name` in the editor."""
        editor, document = self.w.tabs.editor, self.w.tabs.document
        if editor is None or document is None:
            return
        pattern = re.compile(rf"^\s*uniform\s+\S+\s+{re.escape(name)}\s*;", re.MULTILINE)
        match = pattern.search(document.text)
        if match:
            line = document.text.count("\n", 0, match.start()) + 1
            editor.select_line_range(line, line)
            editor.setFocus()
        else:
            self.w.message(f"'{name}' is declared in an include, not in this file")

    def edit_bound(self, name: str, component: int, which: int, value: float) -> None:
        """A slider bound typed in a context menu: rewrite the annotation in the source (FragM's `comboSliderBoundsChanged`)."""
        document = self.w.tabs.document
        if document is None:
            return
        new_text = rewrite_bound(document.text, name, component, which, value)
        if new_text is None:
            self.w.message(f"The declaration of '{name}' is not in this file")
            return
        self.w.replace_text(new_text)
        self.w.build_document(document)

    def insert_preset(self) -> None:
        """F8: write the current settings into the source as a preset (FragM's `insertPreset`)."""
        document, editor = self.w.tabs.document, self.w.tabs.editor
        if document is None or editor is None or document.source is None:
            return
        selected = presets.selected_preset_name(editor.selected_text().replace("\u2029", "\n"))
        suggested = selected or (presets.next_keyframe_name(list(document.source.presets)) if document.camera_kind == "3D" else "Default")
        name, ok = QInputDialog.getText(self.w, "Add preset", "Name for the preset (KeyFrame.nnnn for a camera keyframe):", text=suggested)
        if not ok or not name.strip():
            return
        name = name.strip()
        if presets.is_keyframe(name):
            body = document.state.camera_text(document.camera_kind)
        elif presets.is_range(name):
            if not document.easing:
                QMessageBox.warning(self.w, "Fragments", "Set up some parameter easing curves first (F7)!")
                return
            body = "\n".join(document.easing_lines())
        else:
            body = document.state.to_text(extra_lines=document.easing_lines() if self.w.prefs.save_easing else [])
        self.w.replace_text(presets.replace_preset(document.text, name, body))
        self.w.build_document(document)
        document.apply_preset(name)
        self.w.parameters.rebuild()
        self.w.message(f"Added preset {name}")

    def group_to_preset(self, group: str | None) -> None:
        """F4: a preset holding one group's settings."""
        document = self.w.tabs.document
        if document is None or document.source is None:
            return
        group = group or self.w.parameters.current_group()
        name, ok = QInputDialog.getText(self.w, "Group to preset", f"Name for the preset of group '{group}':", text=group)
        if ok and name.strip():
            self.w.replace_text(presets.replace_preset(document.text, name.strip(), self.w.parameters.group_settings_text(group)))
            self.w.build_document(document)
            self.w.message(f"Added preset {name.strip()}")

    def select_preset(self) -> None:
        """F9: select the current preset's block in the editor."""
        document, editor = self.w.tabs.document, self.w.tabs.editor
        if document is None or editor is None or not document.current_preset:
            return
        span = presets.find_preset(document.text, document.current_preset)
        if span is None:
            return
        cursor = editor.textCursor()
        cursor.setPosition(span[0])
        cursor.setPosition(span[1], QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        editor.centerCursor()
        editor.setFocus()



__all__ = ["ParameterActions"]
