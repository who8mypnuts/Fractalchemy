"""The *Info* tab of the settings panel: facts about the loaded fractal.

A two-column property tree: the file it came from, image and camera, every transform with its
variations / parameters / affine, the distinct formulas the fractal uses (with their kind,
depth behaviour and origin — double-click opens the formula browser on one), the colouring and
palette, and the facts of the last preview render.

Everything is derived from the `Flame` model, so the panel is just a view: `show_flame()` whenever
the document changes, `show_camera()` / `show_palette()` for the cheap partial updates, and
`show_render()` after every delivered pass.
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLabel, QSizePolicy, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..fractal import variations as V
from ..fractal.scene import Flame, XForm, identity_affine
from ..render.settings import RenderStats
from .formula_browser import KIND_LABELS, formula_description, origin_group

FORMULA_ROLE = Qt.ItemDataRole.UserRole
PALETTE_STRIP_HEIGHT = 14
KEY_COLUMN_MAX = 150
SWATCH_SIZE = 12
NOT_AVAILABLE = "not available — ignored when rendering"


def fmt(value: float) -> str:
    """Compact number: `0.5`, `1`, `-0.3333`."""
    if isinstance(value, bool):
        return str(value)
    if math.isfinite(value) and float(value).is_integer() and abs(value) < 1e9:
        return str(int(value))
    return f"{value:.4g}"


def affine_text(coefs) -> str:
    return "  ".join(fmt(c) for c in coefs)


def variations_text(xform: XForm) -> str:
    """`linear 1 · julian 0.5` — what the status line of a transform shows."""
    return " · ".join(f"{name} {fmt(weight)}" for name, weight in xform.variations.items()) or "none"


def formula_facts(name: str, uses: int) -> tuple[str, str]:
    """(one-line value, tooltip) for a formula row."""
    var = V.REGISTRY.get(name)
    if var is None:
        return f"×{uses}  ·  {NOT_AVAILABLE}", f"{name}: no loaded formula has this name. Help ▸ Formulas… lists what is available."
    bits = [f"×{uses}", KIND_LABELS.get(var.kind, var.kind)]
    if var.z == V.Z_FORMULA:
        bits.append("3D")
    if var.dc:
        bits.append("direct colour")
    if var.random:
        bits.append("random")
    if var.params:
        bits.append(f"{len(var.params)} parameter{'s' if len(var.params) != 1 else ''}")
    bits.append(origin_group(var))
    return "  ·  ".join(bits), formula_description(var)


def formula_uses(flame: Flame) -> dict[str, int]:
    """Distinct variation names → number of transforms using them (final included), in first-use order."""
    uses: dict[str, int] = {}
    for xform in list(flame.xforms) + ([flame.final] if flame.final else []):
        for name in xform.variations:
            uses[name] = uses.get(name, 0) + 1
    return uses


def palette_pixmap(palette, width: int, height: int = PALETTE_STRIP_HEIGHT) -> QPixmap:
    """The 256-entry palette as a horizontal strip."""
    image = QImage(max(1, len(palette)), 1, QImage.Format.Format_RGB32)
    for i, (r, g, b) in enumerate(palette):
        image.setPixelColor(i, 0, QColor(int(r), int(g), int(b)))
    return QPixmap.fromImage(image.scaled(max(1, width), height, Qt.AspectRatioMode.IgnoreAspectRatio,
                                          Qt.TransformationMode.FastTransformation))


def swatch_pixmap(rgb, size: int = SWATCH_SIZE) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(int(rgb[0]), int(rgb[1]), int(rgb[2])))
    return pixmap


class InfoPanel(QWidget):
    """Property tree describing the loaded fractal.

    Signals:
        formula_activated(str): A formula row was double-clicked (open it in the formula browser).
    """
    formula_activated = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.tree = QTreeWidget(self)
        self.palette_label: QLabel | None = None   # lives inside the tree; rebuilt with it
        self._flame: Flame | None = None
        self._stats: RenderStats | None = None
        self._groups: dict[str, QTreeWidgetItem] = {}
        self._build()
        self.show_flame(None)

    def _build(self) -> None:
        tree = self.tree
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Property", "Value"])
        tree.header().setStretchLastSection(True)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)   # long values elide; tooltips hold them
        tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(True)
        tree.setUniformRowHeights(False)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tree.setToolTip("Double-click a formula to open it in the formula browser")
        tree.itemDoubleClicked.connect(self._activated)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tree)

    # --- public slots --------------------------------------------------------------------------------------
    def show_flame(self, flame: Flame | None, source: Path | None = None, index: int = 0) -> None:
        """Rebuild the whole tree for `flame` (None = nothing loaded)."""
        self._flame = flame
        self.tree.clear()
        self._groups = {}
        if flame is None:
            QTreeWidgetItem(self.tree, ["No fractal loaded", ""]).setFirstColumnSpanned(True)
            self.tree.resizeColumnToContents(0)
            return
        self._fill_fractal(flame, source, index)
        self._fill_transforms(flame)
        self._fill_formulas(flame)
        self._fill_coloring(flame)
        self._fill_render()
        for name, group in self._groups.items():
            group.setExpanded(name != "Transforms")
        self._fit_key_column()

    def _fit_key_column(self) -> None:
        self.tree.resizeColumnToContents(0)
        self.tree.setColumnWidth(0, min(self.tree.columnWidth(0), KEY_COLUMN_MAX))

    def show_camera(self) -> None:
        """Refresh the camera rows (after pan / zoom / rotate)."""
        if self._flame is None or "Fractal" not in self._groups:
            return
        group = self._groups["Fractal"]
        for i in range(group.childCount()):
            item = group.child(i)
            if item.text(0) in CAMERA_ROWS:
                item.setText(1, CAMERA_ROWS[item.text(0)](self._flame))

    def show_palette(self) -> None:
        """Refresh the palette strip (after a gradient was applied)."""
        if self._flame is None or self.palette_label is None:
            return
        self.palette_label.setPixmap(palette_pixmap(self._flame.palette, self._strip_width()))

    def show_coloring(self) -> None:
        """Refresh the colouring rows (after brightness / gamma / background edits)."""
        if self._flame is not None and "Coloring" in self._groups:
            self._fill_coloring(self._flame)

    def show_render(self, stats: RenderStats) -> None:
        """Facts of the last delivered render pass."""
        self._stats = stats
        if self._flame is not None and "Render" in self._groups:
            self._fill_render()

    def current_formulas(self) -> list[str]:
        """Names in the 'Formulas' group, in display order (tests and the browser link use this)."""
        group = self._groups.get("Formulas")
        return [group.child(i).text(0) for i in range(group.childCount())] if group else []

    # --- sections ------------------------------------------------------------------------------------------
    def _group(self, title: str, value: str = "") -> QTreeWidgetItem:
        item = self._groups.get(title)
        if item is None:
            item = QTreeWidgetItem(self.tree, [title, value])
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            self._groups[title] = item
        else:
            item.setText(1, value)
            item.takeChildren()
        return item

    def _fill_fractal(self, flame: Flame, source: Path | None, index: int) -> None:
        group = self._group("Fractal", flame.name)
        _row(group, "Name", flame.name)
        if source is not None:
            fmt_name = {".flame": "Apophysis / flam3 .flame", ".chaos": "Chaotica world", ".fa": "Fractalchemy .fa"}.get(
                source.suffix.lower(), source.suffix.lower() or "file")
            _row(group, "File", source.name, tooltip=str(source))
            _row(group, "Entry", f"#{index + 1}")
            _row(group, "Format", fmt_name + (f"  ·  version {flame.source_version}" if flame.source_version else ""))
        else:
            _row(group, "File", "not saved")
        cam = flame.camera
        _row(group, "Size", f"{cam.width} × {cam.height}")
        for label, text in CAMERA_ROWS.items():
            _row(group, label, text(flame))
        _row(group, "Transforms", f"{len(flame.xforms)}" + (" + final" if flame.final else ""))
        _row(group, "Render hints", f"oversample {flame.oversample}  ·  filter {fmt(flame.filter_radius)}",
             tooltip="The file's own supersampling / filter radius for final renders (the preview has its own, on the Image tab)")
        if flame.unsupported:
            _row(group, "Ignored", ", ".join(flame.unsupported), tooltip="Variations the file uses that no loaded formula provides")

    def _fill_transforms(self, flame: Flame) -> None:
        count = len(flame.xforms) + (1 if flame.final else 0)
        group = self._group("Transforms", f"{count}" + (" (xaos)" if any(x.chaos for x in flame.xforms) else ""))
        total = sum(max(0.0, x.weight) for x in flame.xforms) or 1.0
        for i, xform in enumerate(flame.xforms):
            title = f"{i + 1}" + (f"  {xform.name}" if xform.name else "")
            item = _row(group, title, f"{xform.weight / total * 100:.0f}%  ·  {variations_text(xform)}")
            self._fill_xform(item, xform, final=False)
        if flame.final:
            title = "Final" + (f"  {flame.final.name}" if flame.final.name else "")
            item = _row(group, title, variations_text(flame.final))
            self._fill_xform(item, flame.final, final=True)

    def _fill_xform(self, item: QTreeWidgetItem, xform: XForm, final: bool) -> None:
        if not final:
            _row(item, "Weight", fmt(xform.weight))
        _row(item, "Colour", f"{fmt(xform.color)}  ·  speed {fmt(xform.color_speed)}", tooltip="Palette position and colour speed (flam3 semantics)")
        _row(item, "Opacity", fmt(xform.opacity))
        if xform.var_color != 1.0:
            _row(item, "Var colour", fmt(xform.var_color))
        variations = _row(item, "Variations", str(len(xform.variations)))
        for name, weight in xform.variations.items():
            child = _row(variations, name, fmt(weight))
            child.setData(0, FORMULA_ROLE, name)
            params = [(k, v) for k, v in xform.params.items() if V.parameter_owner(k) == name or k.startswith(name + "_")]
            for key, value in params:
                _row(child, key, fmt(value))
            if V.REGISTRY.get(name) is None:
                child.setText(1, f"{fmt(weight)}  ·  {NOT_AVAILABLE}")
                child.setForeground(1, QColor(200, 60, 60))
        variations.setExpanded(True)
        if xform.has_pre():
            _row(item, "Pre affine", affine_text(xform.pre), tooltip="Applied to the point before the affine (Fractalchemy's pre affine)")
        _row(item, "Affine", affine_text(xform.coefs), tooltip="a b c d e f  —  (x, y) → (a·x + c·y + e, b·x + d·y + f)")
        if tuple(xform.post) != identity_affine():
            _row(item, "Post affine", affine_text(xform.post))
        if xform.chaos:
            _row(item, "Xaos", "  ".join(fmt(w) for w in xform.chaos), tooltip="Relative weights of the transform chosen next")

    def _fill_formulas(self, flame: Flame) -> None:
        uses = formula_uses(flame)
        missing = [n for n in uses if V.REGISTRY.get(n) is None]
        summary = f"{len(uses)}" + (f"  ·  {len(missing)} not available" if missing else "")
        group = self._group("Formulas", summary)
        for name in sorted(uses, key=str.lower):
            value, tooltip = formula_facts(name, uses[name])
            item = _row(group, name, value, tooltip=tooltip)
            item.setData(0, FORMULA_ROLE, name)
            if name in missing:
                item.setForeground(1, QColor(200, 60, 60))

    def _fill_coloring(self, flame: Flame) -> None:
        col = flame.coloring
        group = self._group("Coloring", "")
        _row(group, "Brightness", fmt(col.brightness))
        _row(group, "Gamma", fmt(col.gamma))
        _row(group, "Gamma threshold", fmt(col.gamma_threshold))
        _row(group, "Vibrancy", fmt(col.vibrancy))
        _row(group, "Contrast", fmt(col.contrast))
        background = _row(group, "Background", "#%02x%02x%02x" % tuple(int(c) for c in col.background))
        background.setIcon(1, swatch_pixmap(col.background))
        palette = _row(group, "Palette", "")
        self.palette_label = QLabel(self.tree)
        self.palette_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.palette_label.setToolTip(f"{len(flame.palette)} colours; the point colour 0..1 indexes this strip")
        self.tree.setItemWidget(palette, 1, self.palette_label)
        self.show_palette()

    def _fill_render(self) -> None:
        stats = self._stats
        group = self._group("Render", "" if stats is None else stats.engine.split(" (")[0])
        if stats is None:
            _row(group, "Status", "not rendered yet")
            return
        _row(group, "Engine", stats.engine)
        _row(group, "Image", f"{stats.width} × {stats.height}")
        _row(group, "Passes", f"{stats.passes_done} of {stats.passes_total}" + ("  ·  refining" if stats.refining else ""))
        _row(group, "Quality", f"{stats.quality:.1f} samples per pixel", tooltip="Samples per pixel accumulated so far")
        _row(group, "Samples", _millions(stats.samples) + (f"  ·  {_millions(stats.samples / stats.seconds)}/s" if stats.seconds > 0 else ""))
        _row(group, "Time", f"{stats.seconds:.1f} s")
        for note in stats.notes:
            _row(group, "Note", note, tooltip=note)

    # --- helpers -------------------------------------------------------------------------------------------
    def _strip_width(self) -> int:
        width = self.tree.columnWidth(1) - 8
        if width <= 0:
            width = max(60, self.tree.viewport().width() - self.tree.columnWidth(0) - 8)
        return max(60, width)

    def _activated(self, item: QTreeWidgetItem, _column: int) -> None:
        name = item.data(0, FORMULA_ROLE)
        if name:
            self.formula_activated.emit(name)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._flame is not None:
            self.show_palette()


CAMERA_ROWS = {
    "Centre": lambda f: f"{fmt(f.camera.center[0])}, {fmt(f.camera.center[1])}",
    "Zoom": lambda f: f"{fmt(f.camera.zoom)}  ·  scale {fmt(f.camera.scale)}",
    "Rotate": lambda f: f"{fmt(f.camera.rotate)}°",
    "3D camera": lambda f: (f"pitch {fmt(math.degrees(f.camera.pitch))}°"
                            + (f" / y {fmt(math.degrees(f.camera.pitch_y))}°" if f.camera.pitch_y else "")
                            + f"  ·  yaw {fmt(math.degrees(f.camera.yaw))}°  ·  "
                            f"perspective {fmt(f.camera.perspective)}  ·  z {fmt(f.camera.zpos)}  ·  dof {fmt(f.camera.dof)}")
                  if f.camera.is_3d() else "flat (2D)",
}


def _row(parent: QTreeWidgetItem, key: str, value: str, tooltip: str = "") -> QTreeWidgetItem:
    item = QTreeWidgetItem(parent, [key, value])
    item.setToolTip(1, tooltip or value)
    item.setToolTip(0, tooltip or key)
    return item


def _millions(n: float) -> str:
    if n >= 1e9:
        return f"{n / 1e9:.2f} G"
    if n >= 1e6:
        return f"{n / 1e6:.1f} M"
    if n >= 1e3:
        return f"{n / 1e3:.0f} k"
    return f"{n:.0f}"
