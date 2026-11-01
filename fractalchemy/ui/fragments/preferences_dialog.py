"""*Edit ▸ Preferences…* for the Fragments window: FragM's preferences as tabs (GUI, Editor, GLSL, Paths, Application).

The dialog edits a copy of `FragPreferences` and hands it back through `preferences()`; the window applies and
stores it. *Restore defaults* resets the tabs to a fresh record. The include-path list is an editable list with
Add / Remove buttons (the bundled folder is always searched last and is not listed).
"""

from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from ...fragments.glsl_compat import MODES
from ...fragments.preferences import FragPreferences

MODE_LABELS = {"modernise": "Modernise (translate legacy GLSL to 330+ core)", "patch": "FragM compatibility patch",
               "off": "Off (sources as written)"}


class PreferencesDialog(QDialog):
    """Edit the preferences (see the module docstring)."""

    def __init__(self, parent: QWidget | None, preferences: FragPreferences):
        super().__init__(parent)
        self.setWindowTitle("Fragments preferences")
        self._build()
        self.show_preferences(preferences)

    # --- layout --------------------------------------------------------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._gui_tab(), "GUI")
        self.tabs.addTab(self._editor_tab(), "Editor")
        self.tabs.addTab(self._glsl_tab(), "GLSL")
        self.tabs.addTab(self._paths_tab(), "Paths")
        self.tabs.addTab(self._application_tab(), "Application")
        layout.addWidget(self.tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
                                   | QDialogButtonBox.StandardButton.RestoreDefaults)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(lambda: self.show_preferences(FragPreferences()))
        layout.addWidget(buttons)

    def _gui_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.max_recent = _spin(1, 50)
        form.addRow("Recent files", self.max_recent)
        self.loop_play = QCheckBox("Loop play by default")
        form.addRow(self.loop_play)
        self.draw_paths = QCheckBox("Draw the camera paths over the viewport")
        form.addRow(self.draw_paths)
        self.traveling_wheel = QCheckBox("2D wheel zooms towards the pointer (traveling) instead of the centre")
        form.addRow(self.traveling_wheel)
        self.log_max_rows = _spin(50, 100000, 100)
        form.addRow("Log rows kept", self.log_max_rows)
        return page

    def _editor_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.font_size = _spin(0, 48)
        self.font_size.setSpecialValueText("system")
        form.addRow("Font size (pt)", self.font_size)
        self.jump_to_error = QCheckBox("Jump to the first error line after a failed build")
        form.addRow(self.jump_to_error)
        self.autoload = QCheckBox("Reload a tab when its file changes on disk (unsaved edits are kept)")
        form.addRow(self.autoload)
        return page

    def _glsl_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.autorun = QCheckBox("Build a fragment when it is opened")
        form.addRow(self.autorun)
        self.auto_build = QCheckBox("Rebuild after every edit (auto-build)")
        form.addRow(self.auto_build)
        self.move_main = QCheckBox("Move main() to the end of the program")
        self.move_main.setToolTip("FragM's moveMain: the fragment's main is renamed and called from a trailing one, so code after it still links")
        form.addRow(self.move_main)
        self.use_defines = QCheckBox("Locked parameters become #defines (else const)")
        form.addRow(self.use_defines)
        self.compat_mode = QComboBox()
        for mode in MODES:
            self.compat_mode.addItem(MODE_LABELS[mode], mode)
        form.addRow("Compatibility layer", self.compat_mode)
        self.save_easing = QCheckBox("Inserted presets carry the easing-curve settings")
        form.addRow(self.save_easing)
        self.default_fps = _spin(1, 240)
        form.addRow("Animation frame rate", self.default_fps)
        self.refresh_ms = _spin(5, 2000, 5)
        self.refresh_ms.setSuffix(" ms")
        self.refresh_ms.setToolTip("The viewport aims for one delivered image per this interval (subframes per pass adapt)")
        form.addRow("Refresh interval", self.refresh_ms)
        self.interactive_scale = QDoubleSpinBox()
        self.interactive_scale.setRange(0.1, 1.0)
        self.interactive_scale.setSingleStep(0.05)
        self.interactive_scale.setToolTip("Render scale while the camera moves (1 = full size)")
        form.addRow("Interactive scale", self.interactive_scale)
        return page

    def _paths_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Extra folders searched for #include files (the fragment's own folder first, the bundled Include folder last):"))
        self.include_list = QListWidget()
        layout.addWidget(self.include_list, 1)
        buttons = QHBoxLayout()
        add = QPushButton("Add folder…")
        add.clicked.connect(self._add_include)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_include)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return page

    def _application_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.log_to_file = QCheckBox("Mirror the log to a file")
        form.addRow(self.log_to_file)
        self.log_file = QLineEdit()
        self.log_file.setPlaceholderText("fragments.log in the cache folder")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_log)
        row = QHBoxLayout()
        row.addWidget(self.log_file, 1)
        row.addWidget(browse)
        form.addRow("Log file", row)
        self.log_file_max_kb = _spin(16, 1_000_000, 256)
        self.log_file_max_kb.setSuffix(" KB")
        form.addRow("Rotate after", self.log_file_max_kb)
        self.verbose = QCheckBox("Verbose: log the parameter values after every build")
        form.addRow(self.verbose)
        return page

    # --- values --------------------------------------------------------------------------------------------------------------
    def show_preferences(self, p: FragPreferences) -> None:
        """Put `p` into the widgets."""
        self.max_recent.setValue(p.max_recent)
        self.loop_play.setChecked(p.loop_play)
        self.draw_paths.setChecked(p.draw_paths)
        self.traveling_wheel.setChecked(p.traveling_wheel)
        self.log_max_rows.setValue(p.log_max_rows)
        self.font_size.setValue(p.font_size)
        self.jump_to_error.setChecked(p.jump_to_error)
        self.autoload.setChecked(p.autoload)
        self.autorun.setChecked(p.autorun)
        self.auto_build.setChecked(p.auto_build)
        self.move_main.setChecked(p.move_main)
        self.use_defines.setChecked(p.use_defines)
        self.compat_mode.setCurrentIndex(max(0, self.compat_mode.findData(p.compat_mode)))
        self.save_easing.setChecked(p.save_easing)
        self.default_fps.setValue(p.default_fps)
        self.refresh_ms.setValue(p.refresh_ms)
        self.interactive_scale.setValue(p.interactive_scale)
        self.include_list.clear()
        self.include_list.addItems(p.include_paths)
        self.log_to_file.setChecked(p.log_to_file)
        self.log_file.setText(p.log_file)
        self.log_file_max_kb.setValue(p.log_file_max_kb)
        self.verbose.setChecked(p.verbose)

    def preferences(self) -> FragPreferences:
        """The preferences as edited."""
        return FragPreferences(
            max_recent=self.max_recent.value(), loop_play=self.loop_play.isChecked(), draw_paths=self.draw_paths.isChecked(),
            traveling_wheel=self.traveling_wheel.isChecked(), log_max_rows=self.log_max_rows.value(), font_size=self.font_size.value(),
            jump_to_error=self.jump_to_error.isChecked(), autoload=self.autoload.isChecked(), autorun=self.autorun.isChecked(),
            auto_build=self.auto_build.isChecked(), move_main=self.move_main.isChecked(), use_defines=self.use_defines.isChecked(),
            compat_mode=self.compat_mode.currentData(), save_easing=self.save_easing.isChecked(), default_fps=self.default_fps.value(),
            refresh_ms=self.refresh_ms.value(), interactive_scale=self.interactive_scale.value(),
            include_paths=[self.include_list.item(i).text() for i in range(self.include_list.count())],
            log_to_file=self.log_to_file.isChecked(), log_file=self.log_file.text().strip(), log_file_max_kb=self.log_file_max_kb.value(),
            verbose=self.verbose.isChecked()).normalised()

    # --- paths ---------------------------------------------------------------------------------------------------------------
    def _add_include(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Include folder")
        if chosen:
            self.include_list.addItem(chosen)

    def _remove_include(self) -> None:
        for item in self.include_list.selectedItems():
            self.include_list.takeItem(self.include_list.row(item))

    def _browse_log(self) -> None:
        chosen, _filter = QFileDialog.getSaveFileName(self, "Log file", self.log_file.text(), "Log (*.log);;All files (*)")
        if chosen:
            self.log_file.setText(chosen)


def _spin(low: int, high: int, step: int = 1) -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(low, high)
    spin.setSingleStep(step)
    return spin


__all__ = ["PreferencesDialog"]
