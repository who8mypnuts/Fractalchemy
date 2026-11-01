"""*Build ▸ DE Composer…*: build a distance estimator from folds, transforms and a primitive without writing GLSL.

Left: the loop's steps (add from the kinds of `fragments.composer.STEP_KINDS`, remove, move), with the selected
step's parameters below; right: the loop count, the end shape and its parameters, a preset recipe to start from, and
the generated GLSL. *Create tab* opens the fragment in a new tab (the recipe is kept in its metadata); *Update tab*
rewrites that tab from the current recipe and rebuilds it, so the viewport follows each change. Every parameter is
also a slider in the Parameters dock afterwards.
"""

from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QMenu, QPlainTextEdit, QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from ...fragments.composer import PRESET_RECIPES, SHAPES, STEP_KINDS, Recipe, Step, generate
from ...widgets.layouts import row

RECIPE_KEY = "composer"


class ParamForm(QWidget):
    """Spin boxes for one parameter list (`[(name, default, (lo, hi))]`); `values()` returns name → value."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.form = QFormLayout(self)
        self.form.setContentsMargins(0, 0, 0, 0)
        self._spins: dict[str, list[QDoubleSpinBox]] = {}
        self.on_change = lambda: None

    def show_params(self, params, values: dict) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._spins = {}
        for name, default, (lo, hi) in params:
            current = values.get(name, default)
            components = list(current) if isinstance(current, (tuple, list)) else [current]
            spins = []
            for component in components:
                spin = QDoubleSpinBox()
                spin.setRange(lo, hi)
                spin.setDecimals(3)
                spin.setSingleStep(0.05)
                spin.setValue(float(component))
                spin.valueChanged.connect(lambda _v: self.on_change())
                spins.append(spin)
            self._spins[name] = spins
            self.form.addRow(name, row(*spins, stretch_all=True) if len(spins) > 1 else spins[0])

    def values(self) -> dict:
        return {name: (spins[0].value() if len(spins) == 1 else tuple(s.value() for s in spins)) for name, spins in self._spins.items()}


class ComposerDialog(QDialog):
    """The composer (see the module docstring). `window` supplies `open_text`, `replace_text`, `build_document` and `tabs`."""

    def __init__(self, window, recipe: Recipe | None = None, document=None):
        super().__init__(window if isinstance(window, QWidget) else None)
        self.setWindowTitle("DE Composer")
        self.w = window
        self.recipe = recipe or Recipe.preset("Menger sponge")
        self.document = document
        self._build()
        self._show_recipe()
        self.resize(980, 640)

    # --- layout --------------------------------------------------------------------------------------------------------------
    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.addWidget(self._steps_group(), 1)
        right = QVBoxLayout()
        right.addWidget(self._loop_group())
        self.code = QPlainTextEdit()
        self.code.setReadOnly(True)
        right.addWidget(self.code, 1)
        buttons = QHBoxLayout()
        self.create_button = QPushButton("Create tab")
        self.create_button.clicked.connect(self._create)
        self.update_button = QPushButton("Update tab")
        self.update_button.clicked.connect(self._update)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        buttons.addWidget(self.create_button)
        buttons.addWidget(self.update_button)
        buttons.addStretch(1)
        buttons.addWidget(close)
        right.addLayout(buttons)
        layout.addLayout(right, 1)

    def _steps_group(self) -> QGroupBox:
        group = QGroupBox("Loop steps")
        layout = QVBoxLayout(group)
        self.steps = QListWidget()
        self.steps.currentRowChanged.connect(self._select_step)
        layout.addWidget(self.steps, 1)
        bar = QHBoxLayout()
        add = QToolButton()
        add.setText("Add step")
        add.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(add)
        for kind, (label, _params, _template) in STEP_KINDS.items():
            menu.addAction(label, lambda k=kind: self._add_step(k))
        add.setMenu(menu)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_step)
        up = QPushButton("Up")
        up.clicked.connect(lambda: self._move(-1))
        down = QPushButton("Down")
        down.clicked.connect(lambda: self._move(1))
        for widget in (add, remove, up, down):
            bar.addWidget(widget)
        bar.addStretch(1)
        layout.addLayout(bar)
        self.step_params = ParamForm()
        self.step_params.on_change = self._step_params_changed
        layout.addWidget(QLabel("Step parameters"))
        layout.addWidget(self.step_params)
        return group

    def _loop_group(self) -> QGroupBox:
        group = QGroupBox("Loop and shape")
        form = QFormLayout(group)
        self.name = QLineEdit()
        self.name.textChanged.connect(lambda _t: self._recipe_changed())
        form.addRow("Name", self.name)
        self.preset = QComboBox()
        self.preset.addItem("— start from a preset —", "")
        for key in PRESET_RECIPES:
            self.preset.addItem(key, key)
        self.preset.currentIndexChanged.connect(self._load_preset)
        form.addRow("Preset", self.preset)
        self.iterations = QSpinBox()
        self.iterations.setRange(1, 40)
        self.iterations.valueChanged.connect(lambda _v: self._recipe_changed())
        form.addRow("Iterations", self.iterations)
        self.shape = QComboBox()
        for key, (label, _params, _template) in SHAPES.items():
            self.shape.addItem(label, key)
        self.shape.currentIndexChanged.connect(self._shape_changed)
        form.addRow("End shape", self.shape)
        self.shape_params = ParamForm()
        self.shape_params.on_change = self._recipe_changed
        form.addRow(self.shape_params)
        return group

    # --- recipe ↔ widgets --------------------------------------------------------------------------------------------------------
    def _show_recipe(self) -> None:
        self._loading = True
        self.name.setText(self.recipe.name)
        self.iterations.setValue(self.recipe.iterations)
        self.shape.setCurrentIndex(max(0, self.shape.findData(self.recipe.shape)))
        self.shape_params.show_params(SHAPES[self.recipe.shape][1], self.recipe.shape_values)
        self.steps.clear()
        for index, step in enumerate(self.recipe.steps, start=1):
            self.steps.addItem(f"{index}. {STEP_KINDS[step.kind][0]}")
        self._loading = False
        if self.recipe.steps:
            self.steps.setCurrentRow(0)
        else:
            self.step_params.show_params([], {})
        self._refresh_code()

    def _select_step(self, index: int) -> None:
        if 0 <= index < len(self.recipe.steps):
            step = self.recipe.steps[index]
            self.step_params.show_params(STEP_KINDS[step.kind][1], step.values)

    def _step_params_changed(self) -> None:
        index = self.steps.currentRow()
        if 0 <= index < len(self.recipe.steps):
            self.recipe.steps[index].values = self.step_params.values()
            self._refresh_code()

    def _shape_changed(self) -> None:
        if getattr(self, "_loading", False):
            return
        self.recipe.shape = self.shape.currentData()
        self.recipe.shape_values = {}
        self.shape_params.show_params(SHAPES[self.recipe.shape][1], {})
        self._refresh_code()

    def _recipe_changed(self) -> None:
        if getattr(self, "_loading", False):
            return
        self.recipe.name = self.name.text() or "Composed fractal"
        self.recipe.iterations = self.iterations.value()
        self.recipe.shape_values = self.shape_params.values()
        self._refresh_code()

    def _load_preset(self) -> None:
        key = self.preset.currentData()
        if key:
            self.recipe = Recipe.preset(key)
            self._show_recipe()

    def _add_step(self, kind: str) -> None:
        self.recipe.steps.append(Step(kind, {}))
        self._show_recipe()
        self.steps.setCurrentRow(len(self.recipe.steps) - 1)

    def _remove_step(self) -> None:
        index = self.steps.currentRow()
        if 0 <= index < len(self.recipe.steps):
            del self.recipe.steps[index]
            self._show_recipe()

    def _move(self, delta: int) -> None:
        index = self.steps.currentRow()
        target = index + delta
        if 0 <= index < len(self.recipe.steps) and 0 <= target < len(self.recipe.steps):
            steps = self.recipe.steps
            steps[index], steps[target] = steps[target], steps[index]
            self._show_recipe()
            self.steps.setCurrentRow(target)

    def _refresh_code(self) -> None:
        self.code.setPlainText(generate(self.recipe))
        self.update_button.setEnabled(self.document is not None and self.document in [t.document for t in self.w.tabs.tabs])

    # --- tabs ------------------------------------------------------------------------------------------------------------------
    def _create(self) -> None:
        self.document = self.w.open_text(generate(self.recipe))
        self.document.set_tab_metadata(RECIPE_KEY, self.recipe.to_dict())
        self._refresh_code()

    def _update(self) -> None:
        if self.document is None:
            return
        tab = self.w.tabs.tab_for(self.document)
        if tab is None:
            return
        self.w.tabs.set_current(self.document)
        self.w.replace_text(generate(self.recipe))
        self.document.set_tab_metadata(RECIPE_KEY, self.recipe.to_dict())
        self.w.build_document(self.document)


__all__ = ["ComposerDialog", "ParamForm", "RECIPE_KEY"]
