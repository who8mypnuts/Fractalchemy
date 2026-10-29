"""The Transform Editor's list tabs — Variations, Variables and Xaos — one `ValueTable` each.

* **Variations** — every loaded formula (built-ins, bundled plugins, user formulas) with the selected
  transform's weight for it; used ones in bold; rows tinted by origin (`formula_origins`); search box,
  *Hide unused*, *Clear*. The third column tags `pre` / `post` formulas, 3D ones (they set the depth),
  direct-colour and random ones.
* **Variables** — the parameters of the transform's active variations (z / 3D parameters included), with
  *Show all variables* listing every parameter of every formula. Double-click a name to reset its default.
* **Xaos** — the transform's outgoing (*to*) or incoming (*from*) xaos weights.

Every tab edits the document through the context (undoable) and refreshes from `refresh()`.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QVBoxLayout, QWidget

from ..fractal import variations as V
from ..fractal.scene import XForm
from ..fractal.xform_ops import chaos_row
from ..widgets.silent import updating
from ..widgets.value_table import ValueRow, ValueTable
from .editor_context import EditorContext
from .formula_origins import ORIGINS, origin_of

KIND_TAGS = {V.PRE: "pre", V.POST: "post"}
MISSING_COLOR = QColor(200, 60, 60)
UNDECLARED_COLOR = QColor(150, 150, 150)


def variation_tags(var: V.Variation | None) -> str:
    """Short tags for the Variations list: `pre`, `post`, `3D`, `DC`, `random`, or `missing`."""
    if var is None:
        return "missing"
    tags = [KIND_TAGS[var.kind]] if var.kind in KIND_TAGS else []
    tags += [tag for flag, tag in ((var.z == V.Z_FORMULA, "3D"), (var.dc, "DC"), (var.random, "random")) if flag]
    return " ".join(tags)


def _param_tooltip(key: str, owner: str, default: float, info: V.ParamInfo | None) -> str:
    tip = f"{key} — parameter of {owner}; default {default:g}"
    if info is None:
        return tip
    if info.min is not None or info.max is not None:
        tip += f"; range {'' if info.min is None else f'{info.min:g}'} … {'' if info.max is None else f'{info.max:g}'}"
    if info.nonzero:
        tip += "; must not be 0"
    if info.cyclic:
        tip += "; cyclic"
    return tip


def param_rows(xform: XForm, show_all: bool) -> list[ValueRow]:
    """The Variables tab's rows: parameters of the transform's variations (or of every formula), used ones first."""
    names = list(xform.variations)
    if show_all:
        names += [n for n in V.catalogue() if n not in xform.variations]
    rows: list[ValueRow] = []
    seen: set[str] = set()
    for name in names:
        var = V.REGISTRY.get(name)
        used = name in xform.variations
        if var is None:   # a missing formula: show what the file had
            for key, value in xform.params.items():
                if key.startswith(name + "_") and key not in seen:
                    seen.add(key)
                    rows.append(ValueRow(key, value, name, f"{key}: parameter of {name} (formula not available)", bold=used,
                                         color=MISSING_COLOR))
            continue
        for key, default in var.params.items():
            if key in seen:
                continue
            seen.add(key)
            info = var.param_info.get(key)
            rows.append(ValueRow(key, xform.params.get(key, default), name, _param_tooltip(key, name, default, info), bold=used,
                                 integer=info is not None and info.type == "int"))
    for key, value in xform.params.items():   # parameters no formula declares (kept for round-tripping)
        if key not in seen:
            seen.add(key)
            rows.append(ValueRow(key, value, "", f"{key}: not declared by any loaded formula", color=UNDECLARED_COLOR))
    return rows


class TableTab(QWidget):
    """Base of the list tabs: a `ValueTable` with an optional search box and a "shown of total" count.

    Subclasses fill `rows()` for the selected transform and handle `_edited` / `_double_clicked`.
    """

    def __init__(self, context: EditorContext, headers: tuple[str, ...], parent: QWidget | None = None, searchable: bool = True):
        super().__init__(parent)
        self.context = context
        self._updating = False
        self.search = QLineEdit(self) if searchable else None
        self.table = ValueTable(self, headers)
        self.count_label = QLabel(self)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(2, 2, 2, 2)
        if self.search is not None:
            self.search.setPlaceholderText(f"Search {headers[0].lower()}s…")
            self.search.setClearButtonEnabled(True)
            self.search.textChanged.connect(lambda _t: self.apply_filter())
            self.layout_.addWidget(self.search)
        self.layout_.addWidget(self.table, 1)
        self.bottom = QHBoxLayout()
        self.layout_.addLayout(self.bottom)
        self.table.value_edited.connect(self._edited)
        self.table.name_double_clicked.connect(self._double_clicked)

    @property
    def document(self):
        """The document the tab edits."""
        return self.context.document

    def rows(self) -> list[ValueRow]:
        """The rows for the selected transform (empty when there is none)."""
        raise NotImplementedError

    def hide_row(self) -> Callable[[ValueRow], bool] | None:
        """A predicate hiding rows besides the search (None = none)."""
        return None

    def refresh(self) -> None:
        """Show the selected transform's values."""
        with updating(self):
            self.table.set_rows(self.rows())
        self.setEnabled(self.context.xform() is not None)
        self.apply_filter()

    def apply_filter(self) -> None:
        """Hide the rows the search box (and `hide_row`) exclude; show the count."""
        shown = self.table.filter(self.search.text() if self.search is not None else "", self.hide_row())
        self.count_label.setText(f"{shown} of {len(self.table.names())}")

    def _edited(self, name: str, value: float) -> None:
        raise NotImplementedError

    def _double_clicked(self, name: str) -> None:
        raise NotImplementedError


class VariationsTab(TableTab):
    """Weights of every variation for the selected transform."""

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, ("Variation", "Weight", "Kind"), parent)
        self.hide_unused = QCheckBox("Hide unused", self)
        self.clear_button = QPushButton("Clear", self)
        self.clear_button.setToolTip("Set every variation of this transform to zero")
        self.table.setToolTip("Type a weight, or press on a name and drag sideways (Shift: coarse, Ctrl / Alt: fine).\n"
                              "Double-click a name to switch it between 0 and 1.")
        self.bottom.addWidget(self.hide_unused)
        self.bottom.addWidget(self.count_label, 1)
        self.bottom.addWidget(self.clear_button)
        self.hide_unused.toggled.connect(lambda _c: self.apply_filter())
        self.clear_button.clicked.connect(lambda: self.document.clear_variations(self.context.selected))
        self._names: list[str] = []
        self.populate()

    def populate(self) -> None:
        """(Re)build the list from the registry — call after formulas were (re)loaded."""
        self._names = V.catalogue()
        self.refresh()

    def rows(self) -> list[ValueRow]:
        """Every registered variation (plus the file's unknown ones) with the transform's weight."""
        xform = self.context.xform()
        weights = dict(xform.variations) if xform is not None else {}
        names = self._names + [n for n in weights if n not in V.REGISTRY and n not in self._names]   # a file's unknown ones too
        rows = []
        for name in names:
            var = V.REGISTRY.get(name)
            tip = f"{name}" + (f" — {var.summary()}" if var is not None else " — not available: no loaded formula has this name")
            origin = ORIGINS[origin_of(var)] if var is not None else None
            rows.append(ValueRow(name, weights.get(name, 0.0), variation_tags(var), tip, bold=name in weights,
                                 color=MISSING_COLOR if var is None else origin.text_color,
                                 background=origin.background_color if origin is not None else None))
        return rows

    def hide_row(self) -> Callable[[ValueRow], bool] | None:
        """With *Hide unused* on, rows at weight 0 are hidden."""
        return (lambda row: row.value == 0) if self.hide_unused.isChecked() else None

    def _edited(self, name: str, value: float) -> None:
        if not self._updating:
            self.document.set_variation(self.context.selected, name, value)

    def _double_clicked(self, name: str) -> None:
        current = self.table.value_of(name) or 0.0
        self.document.set_variation(self.context.selected, name, 1.0 if current == 0 else 0.0)


class VariablesTab(TableTab):
    """Parameters of the active variations (or all of them)."""

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, ("Variable", "Value", "Variation"), parent)
        self.show_all = QCheckBox("Show all variables", self)
        self.show_all.setToolTip("List every parameter of every loaded formula, not only those of the active variations")
        self.table.setToolTip("Type a value, or press on a name and drag sideways. Double-click a name to reset its default.")
        self.bottom.addWidget(self.show_all)
        self.bottom.addWidget(self.count_label, 1)
        self.show_all.toggled.connect(lambda _c: self.refresh())

    def rows(self) -> list[ValueRow]:
        """The parameters of the active variations (or of every formula with *Show all*)."""
        xform = self.context.xform()
        return param_rows(xform, self.show_all.isChecked()) if xform is not None else []

    def _edited(self, key: str, value: float) -> None:
        if not self._updating:
            self.document.set_param(self.context.selected, key, value)

    def _double_clicked(self, key: str) -> None:
        """Reset the parameter to the formula's default."""
        owner = V.parameter_owner(key)
        var = V.REGISTRY.get(owner) if owner else None
        if var is not None and key in var.params:
            self.document.set_param(self.context.selected, key, var.params[key])


class XaosTab(TableTab):
    """Outgoing (`to`) or incoming (`from`) xaos weights of the selected transform."""

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, ("Transform", "Weight"), parent, searchable=False)
        self.to_button = QRadioButton("View links as \"to\"", self)
        self.from_button = QRadioButton("View links as \"from\"", self)
        self.to_button.setChecked(True)
        self.to_button.setToolTip("Each row: the relative weight of choosing that transform after this one")
        self.from_button.setToolTip("Each row: the relative weight of choosing this transform after that one")
        self.table.setToolTip("Relative weight of the link (1 = default, 0 = never). Double-click a name to switch 0 ↔ 1.")
        self.clear_all = QPushButton("Clear all", self)
        self.set_all = QPushButton("Set all", self)
        self.clear_all.setToolTip("Set every outgoing link of this transform to 0")
        self.set_all.setToolTip("Set every outgoing link of this transform to 1 (the default: no xaos)")
        self.note = QLabel(self)
        self.note.setWordWrap(True)
        self.count_label.hide()
        self.layout_.addWidget(self.to_button)
        self.layout_.addWidget(self.from_button)
        self.bottom.addWidget(self.clear_all)
        self.bottom.addWidget(self.set_all)
        self.bottom.addStretch(1)
        self.layout_.addWidget(self.note)
        self.to_button.toggled.connect(lambda _c: self.refresh())
        self.clear_all.clicked.connect(lambda: self._set_all(0.0))
        self.set_all.clicked.connect(lambda: self._set_all(1.0))

    def _row_name(self, index: int) -> str:
        xform = self.context.xform(index)
        return f"{index + 1}" + (f" - {xform.name}" if xform is not None and xform.name else "")

    def rows(self) -> list[ValueRow]:
        """One row per transform with the link weight in the chosen direction (none for the final transform)."""
        flame, selected = self.context.flame, self.context.selected
        if flame is None or selected is None:
            return []
        n = len(flame.xforms)
        rows = []
        for j in range(n):
            if self.to_button.isChecked():
                value = chaos_row(flame.xforms[selected], n)[j]
                tip = f"Weight of transform {j + 1} being chosen after transform {selected + 1}"
            else:
                value = chaos_row(flame.xforms[j], n)[selected]
                tip = f"Weight of transform {selected + 1} being chosen after transform {j + 1}"
            rows.append(ValueRow(self._row_name(j), value, "", tip, bold=value != 1.0, decimals=4))
        return rows

    def refresh(self) -> None:
        """Show the links, and say why there are none for the final transform."""
        super().refresh()
        flame = self.context.flame
        self.setEnabled(flame is not None and self.context.selected is not None)
        self.note.setText("The final transform has no xaos links." if flame is not None and self.context.selected is None else "")

    def _indices(self, name: str) -> tuple[int, int] | None:
        """(from, to) transform indices of the row called `name`, in the current view direction."""
        names = self.table.names()
        if name not in names or self.context.selected is None:
            return None
        j, selected = names.index(name), self.context.selected
        return (selected, j) if self.to_button.isChecked() else (j, selected)

    def _edited(self, name: str, value: float) -> None:
        pair = self._indices(name)
        if pair is not None and not self._updating:
            self.document.set_chaos(pair[0], pair[1], value)

    def _double_clicked(self, name: str) -> None:
        pair = self._indices(name)
        if pair is not None:
            current = self.table.value_of(name) or 0.0
            self.document.set_chaos(pair[0], pair[1], 0.0 if current == 1.0 else 1.0)

    def _set_all(self, value: float) -> None:
        if self.context.selected is not None:
            self.document.set_all_chaos(self.context.selected, value)


__all__ = ["TableTab", "VariationsTab", "VariablesTab", "XaosTab", "param_rows", "variation_tags"]
