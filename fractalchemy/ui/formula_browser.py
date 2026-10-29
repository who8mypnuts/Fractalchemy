"""A window listing every loaded formula (variation / plugin) with its parameters and origin.

The editor that will *use* the formulas comes later; this is the catalogue view: what is
available, where it came from, which parameters it takes, and which formula files failed
to load and why.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import config
from ..formulas import last_report, user_formula_dir
from ..fractal import variations as V

KIND_LABELS = {V.PRE: "pre", V.NORMAL: "normal", V.POST: "post"}


def formula_description(var: V.Variation) -> str:
    """Multi-line summary shown when a formula is selected."""
    lines = [var.name, ""]
    lines.append(f"Kind: {KIND_LABELS.get(var.kind, var.kind)}" + ("; uses random numbers" if var.random else ""))
    depth = {V.Z_NONE: "leaves the depth alone", V.Z_PASS: "passes the depth through (Apophysis built-in rule)",
             V.Z_FORMULA: "3D: sets the depth itself"}[var.z]
    lines.append(f"Depth: {depth}")
    if var.dc:
        lines.append("Direct colour: writes the point colour (blended by the transform's var_color)")
    if var.uses_affine:
        lines.append("Reads the transform's affine coefficients")
    lines.append(f"Implementation: {'formula file (compiled for numpy + GLSL)' if var.style == V.FORMULA else 'native Python (numpy + GLSL)'}")
    if var.origin:
        lines.append(f"Origin: {var.origin}")
    if var.note:
        lines.append(f"Note: {var.note}")
    if var.params:
        lines += ["", "Parameters:"]
        for key, default in var.params.items():
            info = var.param_info.get(key)
            extra = ""
            if info is not None:
                bounds = []
                if info.min is not None:
                    bounds.append(f"min {info.min:g}")
                if info.max is not None:
                    bounds.append(f"max {info.max:g}")
                if info.cyclic:
                    bounds.append("cyclic")
                if info.nonzero:
                    bounds.append("non-zero")
                extra = f" ({info.type}{', ' + ', '.join(bounds) if bounds else ''})"
            lines.append(f"    {key} = {default:g}{extra}")
    else:
        lines += ["", "No parameters (weight only)."]
    return "\n".join(lines)


def origin_group(var: V.Variation) -> str:
    """Folder-ish label used to group the tree."""
    if var.style == V.LEGACY:
        return "Built-in (flam3 / Apophysis)"
    parts = Path(var.origin).parts
    if "library" in parts:
        return {"apophysis7x": "Apophysis 7X sources", "plugins": "Community plugin sources", "ports": "Hand-ported sources",
                "reconstructed": "Reconstructed from DLLs"}.get(parts[parts.index("library") + 1], "Library")
    return "User formulas"


class FormulaBrowser(QWidget):
    """Tool window: searchable tree of formulas grouped by origin, details on the right."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle(f"Formulas — {config.APP_NAME}")
        self.resize(860, 560)
        self.search = QLineEdit(placeholderText="Search formulas and parameters…")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Formula", "Kind", "Parameters"])
        self.tree.setColumnWidth(0, 220)
        self.tree.setColumnWidth(1, 70)
        self.details = QPlainTextEdit(readOnly=True)
        self.summary = QLabel()
        splitter = QSplitter()
        splitter.addWidget(self.tree)
        splitter.addWidget(self.details)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        top = QHBoxLayout()
        top.addWidget(self.search)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(splitter)
        layout.addWidget(self.summary)
        self.search.textChanged.connect(self.filter)
        self.tree.currentItemChanged.connect(self._show_details)
        self.populate()

    def populate(self) -> None:
        """(Re)build the tree from the registry."""
        self.tree.clear()
        groups: dict[str, QTreeWidgetItem] = {}
        for name in V.catalogue():
            var = V.REGISTRY[name]
            group = origin_group(var)
            if group not in groups:
                groups[group] = QTreeWidgetItem(self.tree, [group])
                groups[group].setExpanded(True)
            item = QTreeWidgetItem(groups[group], [name, KIND_LABELS.get(var.kind, var.kind), ", ".join(var.params)])
            item.setData(0, Qt.ItemDataRole.UserRole, name)
        report = last_report()
        if report is not None and report.errors:
            failed = QTreeWidgetItem(self.tree, [f"Not loaded ({len(report.errors)})"])
            for source, message in report.errors:
                QTreeWidgetItem(failed, [Path(source).name, "", message]).setToolTip(2, f"{source}\n{message}")
        for group in groups.values():
            group.setText(1, str(group.childCount()))
        text = f"{len(V.catalogue())} formulas loaded"
        if report is not None:
            text += f" in {report.seconds:.2f} s" + (f", {len(report.errors)} failed" if report.errors else "")
        self.summary.setText(text + f".  User formulas folder: {user_formula_dir()}")

    def filter(self, text: str) -> None:
        """Hide formulas (and empty groups) that do not match `text`."""
        needle = text.strip().lower()
        for g in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(g)
            visible = 0
            for i in range(group.childCount()):
                item = group.child(i)
                hit = not needle or needle in item.text(0).lower() or needle in item.text(2).lower()
                item.setHidden(not hit)
                visible += hit
            group.setHidden(visible == 0)

    def select(self, name: str) -> None:
        """Show formula `name` (clearing any filter that hides it); unknown names just clear the selection."""
        for g in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(g)
            for i in range(group.childCount()):
                item = group.child(i)
                if item.data(0, Qt.ItemDataRole.UserRole) == name:
                    if item.isHidden():
                        self.search.clear()
                    group.setExpanded(True)
                    self.tree.setCurrentItem(item)
                    self.tree.scrollToItem(item)
                    return
        self.tree.setCurrentItem(None)
        self.details.setPlainText(f"{name}: not available (no loaded formula has this name).")

    def _show_details(self, item: QTreeWidgetItem | None, _previous=None) -> None:
        name = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        var = V.REGISTRY.get(name) if name else None
        self.details.setPlainText(formula_description(var) if var is not None else (item.toolTip(2) if item else ""))
