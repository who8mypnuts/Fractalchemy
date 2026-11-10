"""The Script Editor's templates: the Templates tab's actions and the pins of the main window's Scripts menu.

A helper of `ScriptEditorWindow` (it holds the window as `w`): it keeps the list of templates (yours, then the built-in
ones), loads / runs / saves / overwrites / renames / deletes them (asking where something would be lost), and pins them
to the main window (`script_menu.ScriptPins`). *Save as Template* with parameter values changed in the Parameters tab
first asks whether those values should become the template's defaults. A pinned template run from the Scripts menu
keeps the values adjusted afterwards in the Parameters tab.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QInputDialog, QMessageBox

from ..scripting import templates as T
from .script_menu import ORIGIN_PREFIX, ScriptPins

if TYPE_CHECKING:
    from .script_editor_window import ScriptEditorWindow


class TemplateActions:
    """The Templates tab's actions and the pins (see the module docstring)."""

    def __init__(self, window: "ScriptEditorWindow"):
        self.w = window
        self.templates: list[T.Template] = []
        self.pins = ScriptPins(window.settings, window)
        tab = window.drawer.templates
        tab.is_pinned = self.pins.is_pinned
        tab.load_requested.connect(self.load)
        tab.insert_requested.connect(lambda t: window.editor.insert_snippet(T.strip_metadata(t.code)))
        tab.run_requested.connect(self.run)
        tab.save_requested.connect(self.save_as)
        tab.overwrite_requested.connect(self.overwrite)
        tab.rename_requested.connect(self.rename)
        tab.delete_requested.connect(self.delete)
        tab.refresh_requested.connect(self.refresh)
        tab.pin_toggled.connect(self.toggle_pin)
        self.pins.changed.connect(tab.refresh_pins)
        window.live.changed.connect(self._remember_pin_values)

    # --- the list -----------------------------------------------------------------------------------------------------
    def refresh(self) -> None:
        self.templates = T.all_templates(self.w.templates_folder)
        self.w.drawer.templates.set_templates(self.templates, self.w.templates_folder)

    def load(self, template: T.Template) -> bool:
        w = self.w
        if not w.confirm_discard():
            return False
        w.load_code(template.code, template.name, None, template.id)
        w.statusBar().showMessage(f"Loaded template '{template.name}'", 3000)
        return True

    def run(self, template: T.Template) -> None:
        if self.load(template):
            self.w.run()

    # --- saving -------------------------------------------------------------------------------------------------------
    def _ask_bake(self) -> bool | None:
        """With changed parameter values: save them as the defaults (True), as written (False), or cancel (None)."""
        if not self.w.live.values_for_run():
            return False
        box = QMessageBox(QMessageBox.Icon.Question, "Save as template",
                          "Save the template with the current parameter values as its defaults?", parent=self.w)
        with_values = box.addButton("Save with values", QMessageBox.ButtonRole.AcceptRole)
        as_written = box.addButton("Save as written", QMessageBox.ButtonRole.NoRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(with_values)
        box.exec()
        clicked = box.clickedButton()
        return True if clicked is with_values else False if clicked is as_written else None

    def save_as(self) -> None:
        w = self.w
        bake = self._ask_bake()
        if bake is None:
            return
        if bake:
            w.live.bake()
        meta = T.parse_metadata(w.editor.text())
        name, ok = QInputDialog.getText(w, "Save as template", "Template name:", text=meta.get("name") or w.script_name)
        if not ok or not name.strip():
            return
        existing = next((t for t in self.templates if not t.builtin and t.name == name.strip()), None)
        if existing is not None and QMessageBox.question(w, "Save as template", f"A template named '{name}' exists. Overwrite it?") \
                != QMessageBox.StandardButton.Yes:
            return
        template = T.save_user_template(name.strip(), w.editor.text(), meta.get("description", ""), w.templates_folder,
                                        existing.path if existing else None)
        w.template_id = template.id
        self.refresh()
        w.drawer.templates.select(template.id)
        w.show_tab("templates")
        w.statusBar().showMessage(f"Template '{template.name}' saved to {template.path}", 5000)

    def overwrite(self, template: T.Template) -> None:
        w = self.w
        if template.builtin or QMessageBox.question(w, "Overwrite template", f"Replace the template '{template.name}' with the script "
                                                    "in the editor?") != QMessageBox.StandardButton.Yes:
            return
        meta = T.parse_metadata(w.editor.text())
        T.save_user_template(template.name, w.editor.text(), meta.get("description", template.description), w.templates_folder,
                             template.path)
        self.refresh()
        w.statusBar().showMessage(f"Template '{template.name}' updated", 3000)

    def rename(self, template: T.Template) -> None:
        if template.builtin:
            return
        name, ok = QInputDialog.getText(self.w, "Rename template", "New name:", text=template.name)
        if ok and name.strip():
            T.rename_user_template(template, name.strip())
            self.refresh()

    def delete(self, template: T.Template) -> None:
        if template.builtin or QMessageBox.question(self.w, "Delete template", f"Delete the template '{template.name}'?") \
                != QMessageBox.StandardButton.Yes:
            return
        T.delete_user_template(template)
        self.refresh()

    # --- pins ---------------------------------------------------------------------------------------------------------
    def toggle_pin(self, template: T.Template) -> None:
        pinned = self.pins.toggle(template)
        self.w.statusBar().showMessage(f"'{template.name}' " + ("is in the main window's Scripts menu" if pinned else "was unpinned"), 4000)

    def _remember_pin_values(self) -> None:
        """A pinned template run from the main window keeps the values you adjust in the Parameters tab."""
        session = self.w.live.session
        if session is not None and session.origin.startswith(ORIGIN_PREFIX):
            self.pins.set_values(session.origin[len(ORIGIN_PREFIX):], self.w.live.values_for_run())


__all__ = ["TemplateActions"]
