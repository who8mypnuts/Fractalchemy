"""The Script Editor's actions, menus and toolbar (built onto the window, which keeps them as `actionRun`, `menuScript`, …).

Kept apart from `script_editor_window.py` so the window module only coordinates (the `editor_actions.py` pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QToolBar, QToolButton

from ..widgets.icons import action_icon

if TYPE_CHECKING:
    from .script_editor_window import ScriptEditorWindow


def build_actions(w: "ScriptEditorWindow") -> None:
    """Create every action of the Script Editor, its menu bar and its toolbar."""
    def action(text: str, slot, shortcut: str = "", icon: str = "", tip: str = "", checkable: bool = False) -> QAction:
        a = QAction(text, w)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        if icon:
            a.setIcon(action_icon(icon))
        a.setToolTip(tip + (f" ({shortcut})" if shortcut else "") if tip else text)
        a.setStatusTip(tip or text)
        a.setCheckable(checkable)
        a.triggered.connect(slot)
        return a

    w.actionNew = action("New Script", w.new_script, "Ctrl+N", "new", "New script")
    w.actionOpen = action("Open Script…", w.open_script, "Ctrl+O", "open", "Open a script file")
    w.actionSave = action("Save Script", lambda: w.save_script(False), "Ctrl+S", "save", "Save the script")
    w.actionSaveAs = action("Save Script As…", lambda: w.save_script(True), "Ctrl+Shift+S", "save-as", "Save the script under a new name")
    w.actionRun = action("Run", w.run, "Ctrl+Return", "run", "Run the script on the fractal")
    w.actionStop = action("Stop", w.stop, "Shift+Esc", "stop", "Stop the running script")
    w.actionStop.setEnabled(False)
    w.actionRecord = action("Record", w.set_recording, "Ctrl+Shift+R", "record",
                            "Record: write the code for every edit you make in Fractalchemy at the cursor", checkable=True)
    w.actionRecordValues = action("Record Values", lambda: w.set_record_style("absolute"), "", "",
                                  "Record what the values become (camera.zoom = 1.25)", checkable=True)
    w.actionRecordChanges = action("Record Changes", lambda: w.set_record_style("relative"), "", "",
                                   "Record how the values change (camera.zoom += 0.25): the recording works on any fractal", checkable=True)
    w.actionRecordValues.setChecked(True)
    w.actionRunMany = action("Run on Many Fractals…", w.batch_requested.emit, "", "", "Apply this script to many fractals and keep the results in a file")
    w.actionUndo = action("Undo", w.editor.undo, "", "undo", "Undo the last edit in the script")
    w.actionRedo = action("Redo", w.editor.redo, "", "redo", "Redo")
    w.actionCut = action("Cut", w.editor.cut, "Ctrl+X")
    w.actionCopy = action("Copy", w.editor.copy, "Ctrl+C")
    w.actionPaste = action("Paste", w.editor.paste, "Ctrl+V")
    w.actionFind = action("Find…", lambda: w.find_bar.open(False), "", "find", "Find (Ctrl+F) / replace (Ctrl+H)")
    w.actionReplace = action("Replace…", lambda: w.find_bar.open(True))
    w.actionGoto = action("Go to Line…", w.goto_line)
    w.actionComment = action("Toggle Comment", w.editor.toggle_comment, "", "comment", "Comment / uncomment the selected lines (Ctrl+/)")
    w.actionIndent = action("Indent", w.editor.indent, "", "indent", "Indent the selected lines (Tab)")
    w.actionOutdent = action("Outdent", w.editor.outdent, "", "outdent", "Outdent the selected lines (Shift+Tab)")
    w.actionCheck = action("Check Syntax", w.check_syntax, "Ctrl+Shift+C", "check", "Check the script for syntax errors without running it")
    w.actionFlameToScript = action("Flame → Script", w.flame_to_script, "", "flame-script", "Generate a script that rebuilds the fractal shown in the main window")
    w.actionRevert = action("Revert Flame", w.revert_flame, "", "revert", "Put the fractal back as it was before the last run")
    w.actionRevert.setEnabled(False)
    w.actionSaveTemplate = action("Save as Template…", w.save_as_template, "", "template", "Keep the script as a template of your own")
    w.actionClearOutput = action("Clear Output", w.output.clear_output, "", "clear", "Clear the output panel")
    w.actionToggleDrawer = action("Show/Hide Drawer", w._toggle_drawer, "Ctrl+L", "drawer", "Show or hide the documentation drawer", checkable=True)
    w.actionToggleDrawer.setChecked(True)
    w.actionClose = action("Close Window", w.close, "Ctrl+W")
    w.actionGuide = action("Scripting Guide", lambda: w.show_reference("guide"), "F1")
    w.actionApi = action("API Reference", lambda: w.show_reference("api"))
    w.actionVariations = action("Variations", lambda: w.show_reference("variations"))
    w.actionTemplates = action("Templates", lambda: w.show_tab("templates"))
    w.actionInfo = action("Script Info", lambda: w.show_tab("info"))
    w.actionContext = action("Context Help", lambda: w.show_tab("context"))
    for a in (w.actionUndo, w.actionRedo):
        a.setEnabled(False)
    w.editor.undoAvailable.connect(w.actionUndo.setEnabled)
    w.editor.redoAvailable.connect(w.actionRedo.setEnabled)

    bar = w.menuBar()
    w.menuFile = bar.addMenu("File")
    for a in (w.actionNew, w.actionOpen, w.actionSave, w.actionSaveAs):
        w.menuFile.addAction(a)
    w.menuFile.addSeparator()
    w.menuFile.addAction(w.actionClose)
    w.menuEdit = bar.addMenu("Edit")
    for a in (w.actionUndo, w.actionRedo, None, w.actionCut, w.actionCopy, w.actionPaste, None, w.actionFind, w.actionReplace,
              w.actionGoto, None, w.actionComment, w.actionIndent, w.actionOutdent):
        w.menuEdit.addAction(a) if a is not None else w.menuEdit.addSeparator()
    w.menuScript = bar.addMenu("Script")
    for a in (w.actionRun, w.actionStop, w.actionRecord, w.actionCheck, None, w.actionRunMany, None, w.actionFlameToScript,
              w.actionRevert, None, w.actionSaveTemplate, w.actionClearOutput):
        w.menuScript.addAction(a) if a is not None else w.menuScript.addSeparator()
    w.menuRecordStyle = w.menuScript.addMenu("Record Style")
    w.menuRecordStyle.addAction(w.actionRecordValues)
    w.menuRecordStyle.addAction(w.actionRecordChanges)
    w.actionRecord.setMenu(w.menuRecordStyle)
    w.menuView = bar.addMenu("View")
    for a in (w.actionToggleDrawer, None, w.actionContext, w.actionGuide, w.actionApi, w.actionVariations, w.actionInfo, w.actionTemplates):
        w.menuView.addAction(a) if a is not None else w.menuView.addSeparator()

    w.toolBar = QToolBar("Script toolbar", w)
    w.toolBar.setMovable(False)
    w.toolBar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    w.addToolBar(w.toolBar)
    for a in (w.actionNew, w.actionOpen, w.actionSave, w.actionSaveAs, None, w.actionRun, w.actionStop, w.actionRecord, None, w.actionUndo,
              w.actionRedo, None, w.actionFind, w.actionComment, w.actionOutdent, w.actionIndent, w.actionCheck, None,
              w.actionFlameToScript, w.actionRevert, None, w.actionSaveTemplate, w.actionClearOutput, w.actionToggleDrawer):
        w.toolBar.addAction(a) if a is not None else w.toolBar.addSeparator()
    for a in (w.actionNew, w.actionOpen, w.actionSave, w.actionSaveAs, w.actionUndo, w.actionRedo, w.actionFind, w.actionComment,
              w.actionOutdent, w.actionIndent, w.actionCheck, w.actionClearOutput, w.actionToggleDrawer):
        button = w.toolBar.widgetForAction(a)
        if button is not None:
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    record = w.toolBar.widgetForAction(w.actionRecord)
    if isinstance(record, QToolButton):
        record.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)   # ▾ chooses Values / Changes


__all__ = ["build_actions"]
