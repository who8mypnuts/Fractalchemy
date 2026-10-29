"""The *Random Batch* window: pick the variations to draw from, how many flames, and generate.

The list holds every loaded formula (built-ins, bundled plugins and the user's own), each with a
check box; the search box filters it (debounced), *Check all* / *Uncheck all* act on what is listed.
*Generate* builds the flames on the thread pool (see `fractal/random_flame.py`) and emits
`batch_ready(list[Flame])`; the main window shows them in the library's temporary area.

The unchecked set, the count and the transform range persist in QSettings, so a formula the user
adds later starts out checked.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from .. import config
from ..fractal import variations as V
from ..fractal.random_flame import RandomOptions, random_batch
from .background import run_in_background
from .formula_browser import KIND_LABELS

EXCLUDED_KEY = "random/excluded"
COUNT_KEY = "random/count"
MIN_KEY = "random/min_transforms"
MAX_KEY = "random/max_transforms"
SEARCH_DEBOUNCE_MS = 250
DEFAULT_COUNT = 10
MAX_COUNT = 500
BATCH_NAME = "Randomly Generated"


class RandomBatchWindow(QWidget):
    """Tool window generating random flames from a chosen set of variations.

    Signals:
        batch_ready(list): The generated flames.
        status(str): Progress / outcome text.
    """
    batch_ready = Signal(list)
    status = Signal(str)

    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle(f"Random Batch — {config.APP_NAME}")
        self.resize(420, 560)
        self._settings = settings
        self._busy = False
        self._loading = False
        self.search = QLineEdit(placeholderText="Filter variations…", parent=self)
        self.list = QListWidget(self)
        self.check_all_button = QPushButton("Check all", self)
        self.uncheck_all_button = QPushButton("Uncheck all", self)
        self.count_box = QSpinBox(self)
        self.min_box = QSpinBox(self)
        self.max_box = QSpinBox(self)
        self.generate_button = QPushButton("Generate", self)
        self.summary = QLabel(self)
        self._search_timer = QTimer(self, singleShot=True, interval=SEARCH_DEBOUNCE_MS)
        self._build()
        self._connect()
        self.populate()
        self._load()

    # --- layout ---------------------------------------------------------------------------------------------
    def _build(self) -> None:
        self.search.setClearButtonEnabled(True)
        self.list.setAlternatingRowColors(True)
        self.list.setToolTip("Variations the random flames may use; every loaded formula is listed, your own plugins included")
        self.check_all_button.setToolTip("Check every listed variation (only the matches while a filter is typed)")
        self.uncheck_all_button.setToolTip("Uncheck every listed variation (only the matches while a filter is typed)")
        self.count_box.setRange(1, MAX_COUNT)
        self.count_box.setValue(DEFAULT_COUNT)
        self.count_box.setToolTip("How many random fractals to generate")
        for box, value in ((self.min_box, 2), (self.max_box, 5)):
            box.setRange(1, 20)
            box.setValue(value)
        self.min_box.setToolTip("Fewest transforms per fractal")
        self.max_box.setToolTip("Most transforms per fractal")
        self.generate_button.setToolTip("Generate the batch: the fractals appear in the library's temporary area (not saved)")
        self.generate_button.setDefault(True)
        self.summary.setWordWrap(True)
        self.summary.setEnabled(False)
        buttons = QHBoxLayout()
        buttons.addWidget(self.check_all_button)
        buttons.addWidget(self.uncheck_all_button)
        buttons.addStretch(1)
        form = QFormLayout()
        form.addRow("Fractals", self.count_box)
        transforms = QHBoxLayout()
        transforms.addWidget(self.min_box)
        transforms.addWidget(QLabel("to", self))
        transforms.addWidget(self.max_box)
        transforms.addStretch(1)
        form.addRow("Transforms", transforms)
        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.list, 1)
        layout.addLayout(buttons)
        layout.addLayout(form)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.summary)

    def _connect(self) -> None:
        self.search.textChanged.connect(lambda _t: self._search_timer.start())
        self._search_timer.timeout.connect(self.filter)
        self.check_all_button.clicked.connect(lambda: self._set_listed(True))
        self.uncheck_all_button.clicked.connect(lambda: self._set_listed(False))
        self.list.itemChanged.connect(lambda _i: self._on_checks_changed())
        self.generate_button.clicked.connect(self.generate)
        for box in (self.count_box, self.min_box, self.max_box):
            box.valueChanged.connect(lambda _v: self._save())

    # --- the variation list ---------------------------------------------------------------------------------
    def populate(self) -> None:
        """(Re)list every registered formula, keeping the current check states."""
        checked = set(self.checked_names())
        known = {self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())}
        self.list.blockSignals(True)
        self.list.clear()
        for name in V.catalogue():
            var = V.REGISTRY[name]
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setToolTip(f"{KIND_LABELS.get(var.kind, var.kind)} · {var.origin or 'built-in'}")
            item.setCheckState(Qt.CheckState.Checked if (name in checked or name not in known) else Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False)
        self.filter()
        self._on_checks_changed(save=False)

    def filter(self) -> None:
        needle = self.search.text().strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def checked_names(self) -> list[str]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]

    def set_checked(self, names, checked: bool = True) -> None:
        wanted = set(names)
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) in wanted:
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.list.blockSignals(False)
        self._on_checks_changed()

    def _set_listed(self, checked: bool) -> None:
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            item = self.list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.list.blockSignals(False)
        self._on_checks_changed()

    def _on_checks_changed(self, save: bool = True) -> None:
        n = len(self.checked_names())
        self.summary.setText(f"{n} of {self.list.count()} variations checked"
                             + ("" if n else " — with none checked, flames use linear only"))
        if save:
            self._save()

    # --- persistence ------------------------------------------------------------------------------------------
    def _load(self) -> None:
        if self._settings is None:
            return
        self._loading = True
        try:
            try:
                self.count_box.setValue(int(self._settings.value(COUNT_KEY, DEFAULT_COUNT)))
                self.min_box.setValue(int(self._settings.value(MIN_KEY, 2)))
                self.max_box.setValue(int(self._settings.value(MAX_KEY, 5)))
            except (TypeError, ValueError):
                pass
            excluded = self._settings.value(EXCLUDED_KEY, [])
            if isinstance(excluded, str):
                excluded = [excluded] if excluded else []
            if excluded:
                self.set_checked(list(excluded), False)
        finally:
            self._loading = False

    def _save(self) -> None:
        if self._settings is None or self._loading:
            return
        checked = set(self.checked_names())
        excluded = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())
                    if self.list.item(i).data(Qt.ItemDataRole.UserRole) not in checked]
        self._settings.setValue(EXCLUDED_KEY, excluded)
        self._settings.setValue(COUNT_KEY, self.count_box.value())
        self._settings.setValue(MIN_KEY, self.min_box.value())
        self._settings.setValue(MAX_KEY, self.max_box.value())

    # --- generating -------------------------------------------------------------------------------------------
    def options(self, width: int = 1024, height: int = 768) -> RandomOptions:
        lo, hi = sorted((self.min_box.value(), self.max_box.value()))
        return RandomOptions(self.checked_names(), lo, hi, width, height)

    def generate(self) -> None:
        """Build the batch on the thread pool and announce it."""
        if self._busy:
            return
        count = self.count_box.value()
        options = self.options()
        self._busy = True
        self.generate_button.setEnabled(False)
        self.generate_button.setText(f"Generating {count}…")
        self.status.emit(f"Generating {count} random fractals…")
        QApplication.processEvents()
        run_in_background(random_batch, count, options, on_done=self._done, on_error=self._failed)

    def _done(self, flames: list) -> None:
        self._busy = False
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate")
        self.status.emit(f"Generated {len(flames)} random fractals")
        self.batch_ready.emit(flames)

    def _failed(self, exc: Exception) -> None:
        self._busy = False
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate")
        self.status.emit(f"Random batch failed: {exc}")
