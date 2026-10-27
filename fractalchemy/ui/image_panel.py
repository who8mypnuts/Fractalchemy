"""The *Image* tab of the settings panel: preview effort, camera, 3D camera and colouring of the fractal.

Every control edits the `FractalDocument`'s flame (which re-renders the viewport) and follows the
document when the flame changes, so the tab always shows the current values. Each group has a
*Revert* button that restores the values the file was loaded with.

Camera conventions are Apophysis's: `zoom` is log2 (each +1 halves the visible span around the
centre), `rotate` is degrees, the 3D camera has pitch / yaw (shown in degrees, stored in radians),
perspective, z position and depth blur (`cam_dof`).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from .. import config
from ..widgets.color_dialog import ColorPickerDialog
from ..widgets.float_row import FloatRow
from ..widgets.silent import set_value_silently
from .fractal_document import FractalDocument

PASSES_RANGE = (1, 50)
QUALITY_RANGE = (0.5, 500.0)
ZOOM_RANGE = (-4.0, 8.0)
PAN_STEP = 0.1          # fraction of the image moved per arrow click
PITCH_RANGE = (-180.0, 180.0)
YAW_RANGE = (-180.0, 180.0)
PERSPECTIVE_RANGE = (0.0, 1.0)
ZPOS_RANGE = (-5.0, 5.0)
DOF_RANGE = (0.0, 2.0)
BRIGHTNESS_RANGE = (0.0, 50.0)
GAMMA_RANGE = (0.1, 10.0)
THRESHOLD_RANGE = (0.0, 1.0)
VIBRANCY_RANGE = (0.0, 1.0)
SWATCH_SIZE = 14
SPIN_WIDTH = 68


class ColorButton(QPushButton):
    """A button showing a colour swatch and its hex value; emits `color_changed` live from a picker.

    Signals:
        color_changed(tuple): The chosen RGB (0..255) on every adjustment in the picker.
    """
    color_changed = Signal(tuple)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = (0, 0, 0)
        self.picker = ColorPickerDialog(self)
        self.picker.setWindowTitle("Background colour")
        self.picker.color_changed.connect(self._picked)
        self.clicked.connect(self.open_picker)
        self.set_color(self._color)

    def color(self) -> tuple[int, int, int]:
        return self._color

    def set_color(self, color) -> None:
        """Show `color` without emitting."""
        self._color = tuple(int(c) for c in color)
        pixmap = QPixmap(SWATCH_SIZE, SWATCH_SIZE)
        pixmap.fill(QColor(*self._color))
        self.setIcon(pixmap)
        self.setText("#%02x%02x%02x" % self._color)
        if self.picker.isVisible() and self.picker.color() != self._color:
            self.picker.set_color(self._color, as_original=True)

    def open_picker(self) -> None:
        self.picker.set_color(self._color, as_original=True)
        self.picker.show_beside(self)

    def _picked(self, color: tuple) -> None:
        if tuple(color) != self._color:
            self.set_color(color)
            self.color_changed.emit(self._color)


class ImagePanel(QWidget):
    """Preview effort + camera + 3D camera + colouring controls, bound to a `FractalDocument`.

    Signals:
        render_settings_changed(int, float): (passes, quality) whenever either preview box changes.
        render_options_changed(): Oversample, filter radius or the refinement cap changed.
    """
    render_settings_changed = Signal(int, float)
    render_options_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._document: FractalDocument | None = None
        self._updating = False
        # preview effort
        self.passes_box = QSpinBox(self)
        self.quality_box = QDoubleSpinBox(self)
        self.oversample_box = QSpinBox(self)
        self.filter_box = QDoubleSpinBox(self)
        self.refine_check = QCheckBox("Keep refining to", self)
        self.refine_box = QDoubleSpinBox(self)
        # camera
        self.zoom = FloatRow("Zoom", *ZOOM_RANGE, decimals=2, step=0.1, spin_range=(-20.0, 40.0), parent=self)
        self.center_x = QDoubleSpinBox(self)
        self.center_y = QDoubleSpinBox(self)
        self.rotate = QDoubleSpinBox(self)
        self.pan_up = QToolButton(self)
        self.pan_down = QToolButton(self)
        self.pan_left = QToolButton(self)
        self.pan_right = QToolButton(self)
        self.revert_view = QToolButton(self)
        # 3D camera
        self.pitch = FloatRow("Pitch", *PITCH_RANGE, decimals=1, step=1.0, suffix="°", spin_range=(-3600.0, 3600.0), parent=self)
        self.yaw = FloatRow("Yaw", *YAW_RANGE, decimals=1, step=1.0, suffix="°", spin_range=(-3600.0, 3600.0), parent=self)
        self.perspective = FloatRow("Perspective", *PERSPECTIVE_RANGE, decimals=3, step=0.01, spin_range=(-10.0, 10.0), parent=self)
        self.zpos = FloatRow("Z position", *ZPOS_RANGE, decimals=2, step=0.1, spin_range=(-1000.0, 1000.0), parent=self)
        self.dof = FloatRow("Depth blur", *DOF_RANGE, decimals=2, step=0.05, spin_range=(0.0, 100.0), parent=self)
        self.flat_note = QLabel(self)
        self.revert_3d = QToolButton(self)
        # colouring
        self.brightness = FloatRow("Brightness", *BRIGHTNESS_RANGE, decimals=2, step=0.5, spin_range=(0.0, 1000.0), parent=self)
        self.gamma = FloatRow("Gamma", *GAMMA_RANGE, decimals=2, step=0.1, spin_range=(0.01, 100.0), parent=self)
        self.threshold = FloatRow("Threshold", *THRESHOLD_RANGE, decimals=3, step=0.01, parent=self)
        self.vibrancy = FloatRow("Vibrancy", *VIBRANCY_RANGE, decimals=2, step=0.05, parent=self)
        self.background = ColorButton(self)
        self.revert_coloring = QToolButton(self)
        self._build()
        self._connect()
        self.set_enabled_for_flame(False)

    # --- layout --------------------------------------------------------------------------------------------
    def _build(self) -> None:
        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._preview_group())
        layout.addWidget(self._camera_group())
        layout.addWidget(self._camera_3d_group())
        layout.addWidget(self._coloring_group())
        layout.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _revert_icon(self, button: QToolButton, tip: str) -> None:
        button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_BrowserReload))
        button.setToolTip(tip)

    def _preview_group(self) -> QGroupBox:
        self.passes_box.setRange(*PASSES_RANGE)
        self.passes_box.setToolTip("Progressive passes per preview render; the image is refreshed after each")
        self.quality_box.setRange(*QUALITY_RANGE)
        self.quality_box.setDecimals(1)
        self.quality_box.setSingleStep(1.0)
        self.quality_box.setToolTip("Samples per pixel over the whole preview (Apophysis 'quality')")
        self.oversample_box.setRange(1, config.MAX_OVERSAMPLE)
        self.oversample_box.setToolTip("Supersampling: buckets per pixel side before the spatial filter (Apophysis 'oversample')")
        self.filter_box.setRange(0.0, config.MAX_FILTER_RADIUS)
        self.filter_box.setDecimals(2)
        self.filter_box.setSingleStep(0.1)
        self.filter_box.setToolTip("Radius of the Gaussian filter summing buckets into pixels (Apophysis 'filter radius'); "
                                   "oversample 2 with 0.5 is plain 2×2 anti-aliasing, larger radii soften the picture")
        self.refine_check.setToolTip("After the passes, keep adding samples while nothing changes (each extra pass doubles them)")
        self.refine_box.setRange(1.0, config.MAX_REFINE_QUALITY)
        self.refine_box.setDecimals(0)
        self.refine_box.setSingleStep(100.0)
        self.refine_box.setPrefix("q ")
        self.refine_box.setToolTip("Quality (samples per pixel) at which refining stops")
        for box in (self.passes_box, self.quality_box, self.oversample_box, self.filter_box, self.refine_box):
            box.setKeyboardTracking(False)
            box.setFixedWidth(SPIN_WIDTH + 8)
        group = QGroupBox("Preview", self)
        form = QFormLayout(group)
        form.setHorizontalSpacing(4)
        form.addRow("Passes", self.passes_box)
        form.addRow("Quality", self.quality_box)
        form.addRow("Oversample", self.oversample_box)
        form.addRow("Filter", self.filter_box)
        form.addRow(self.refine_check, self.refine_box)
        return group

    def _camera_group(self) -> QGroupBox:
        group = QGroupBox("Camera", self)
        layout = QVBoxLayout(group)
        self.zoom.set_tooltip("Magnification around the image centre: +1 halves the visible span (Apophysis zoom, 2^zoom)")
        layout.addWidget(self.zoom)
        row = QHBoxLayout()
        arrows = QGridLayout()
        arrows.setSpacing(1)
        for button, arrow, tip, pos in ((self.pan_up, Qt.ArrowType.UpArrow, "Pan up", (0, 1)),
                                        (self.pan_left, Qt.ArrowType.LeftArrow, "Pan left", (1, 0)),
                                        (self.pan_right, Qt.ArrowType.RightArrow, "Pan right", (1, 2)),
                                        (self.pan_down, Qt.ArrowType.DownArrow, "Pan down", (2, 1))):
            button.setArrowType(arrow)
            button.setToolTip(f"{tip} by {PAN_STEP:.0%} of the image")
            button.setAutoRepeat(True)
            arrows.addWidget(button, *pos)
        self._revert_icon(self.revert_view, "Revert: centre, zoom and rotation as loaded from the file")
        arrows.addWidget(self.revert_view, 1, 1)
        row.addLayout(arrows)
        form = QFormLayout()
        form.setContentsMargins(8, 0, 0, 0)
        form.setHorizontalSpacing(4)
        for box, lo, hi, decimals, step, suffix in ((self.center_x, -1e6, 1e6, 4, 0.05, ""), (self.center_y, -1e6, 1e6, 4, 0.05, ""),
                                                    (self.rotate, -360.0, 360.0, 1, 5.0, "°")):
            box.setRange(lo, hi)
            box.setDecimals(decimals)
            box.setSingleStep(step)
            box.setSuffix(suffix)
            box.setKeyboardTracking(False)
            box.setFixedWidth(SPIN_WIDTH + 8)
        self.rotate.setWrapping(True)
        self.center_x.setToolTip("Fractal-space x at the image centre")
        self.center_y.setToolTip("Fractal-space y at the image centre (y points down, as in flam3)")
        self.rotate.setToolTip("Rotation of the camera in degrees")
        form.addRow("Centre x", self.center_x)
        form.addRow("Centre y", self.center_y)
        form.addRow("Rotation", self.rotate)
        row.addLayout(form, 1)
        layout.addLayout(row)
        return group

    def _camera_3d_group(self) -> QGroupBox:
        group = QGroupBox("3D camera", self)
        layout = QVBoxLayout(group)
        self.pitch.set_tooltip("Tilt of the plane towards the viewer (Apophysis cam_pitch)")
        self.yaw.set_tooltip("Turn around the vertical axis (Apophysis cam_yaw)")
        self.perspective.set_tooltip("Strength of the perspective: points further away shrink (cam_perspective)")
        self.zpos.set_tooltip("Depth of the plane the camera looks at (cam_zpos); points in front / behind it get perspective")
        self.dof.set_tooltip("Depth of field: blur growing with the distance from the z position (cam_dof)")
        for row in (self.pitch, self.yaw, self.perspective, self.zpos, self.dof):
            layout.addWidget(row)
        self.flat_note.setWordWrap(True)
        self.flat_note.setEnabled(False)
        bottom = QHBoxLayout()
        bottom.addWidget(self.flat_note, 1)
        self._revert_icon(self.revert_3d, "Revert: 3D camera as loaded from the file")
        bottom.addWidget(self.revert_3d)
        layout.addLayout(bottom)
        return group

    def _coloring_group(self) -> QGroupBox:
        group = QGroupBox("Colouring", self)
        layout = QVBoxLayout(group)
        self.brightness.set_tooltip("Overall brightness of the log-density image")
        self.gamma.set_tooltip("Display gamma: higher lifts the faint parts")
        self.threshold.set_tooltip("Gamma threshold: densities below it are blended linearly (kills speckle)")
        self.vibrancy.set_tooltip("1 = colour from the palette, 0 = per-channel gamma (washes out)")
        for row in (self.brightness, self.gamma, self.threshold, self.vibrancy):
            layout.addWidget(row)
        bottom = QHBoxLayout()
        label = QLabel("Background", self)
        label.setMinimumWidth(64)
        bottom.addWidget(label)
        self.background.setToolTip("Background colour of the image")
        bottom.addWidget(self.background, 1)
        self._revert_icon(self.revert_coloring, "Revert: colouring as loaded from the file")
        bottom.addWidget(self.revert_coloring)
        layout.addLayout(bottom)
        return group

    # --- wiring --------------------------------------------------------------------------------------------
    def _connect(self) -> None:
        self.passes_box.valueChanged.connect(self._preview_changed)
        self.quality_box.valueChanged.connect(self._preview_changed)
        self.oversample_box.valueChanged.connect(self._options_changed)
        self.filter_box.valueChanged.connect(self._options_changed)
        self.refine_box.valueChanged.connect(self._options_changed)
        self.refine_check.toggled.connect(self._options_changed)
        self.zoom.value_changed.connect(lambda v: self._edit(lambda d: d.set_view(zoom=v)))
        self.center_x.valueChanged.connect(lambda v: self._edit(lambda d: d.set_view(center=(v, d.flame.camera.center[1]))))
        self.center_y.valueChanged.connect(lambda v: self._edit(lambda d: d.set_view(center=(d.flame.camera.center[0], v))))
        self.rotate.valueChanged.connect(lambda v: self._edit(lambda d: d.set_view(rotate=v)))
        self.pan_up.clicked.connect(lambda: self._edit(lambda d: d.pan(0.0, -PAN_STEP)))
        self.pan_down.clicked.connect(lambda: self._edit(lambda d: d.pan(0.0, PAN_STEP)))
        self.pan_left.clicked.connect(lambda: self._edit(lambda d: d.pan(-PAN_STEP, 0.0)))
        self.pan_right.clicked.connect(lambda: self._edit(lambda d: d.pan(PAN_STEP, 0.0)))
        self.revert_view.clicked.connect(lambda: self._edit(lambda d: d.revert_view()))
        self.pitch.value_changed.connect(lambda v: self._edit(lambda d: d.set_camera_3d(pitch=math.radians(v))))
        self.yaw.value_changed.connect(lambda v: self._edit(lambda d: d.set_camera_3d(yaw=math.radians(v))))
        self.perspective.value_changed.connect(lambda v: self._edit(lambda d: d.set_camera_3d(perspective=v)))
        self.zpos.value_changed.connect(lambda v: self._edit(lambda d: d.set_camera_3d(zpos=v)))
        self.dof.value_changed.connect(lambda v: self._edit(lambda d: d.set_camera_3d(dof=v)))
        self.revert_3d.clicked.connect(lambda: self._edit(lambda d: d.revert_camera_3d()))
        self.brightness.value_changed.connect(lambda v: self._edit(lambda d: d.set_coloring(brightness=v)))
        self.gamma.value_changed.connect(lambda v: self._edit(lambda d: d.set_coloring(gamma=v)))
        self.threshold.value_changed.connect(lambda v: self._edit(lambda d: d.set_coloring(gamma_threshold=v)))
        self.vibrancy.value_changed.connect(lambda v: self._edit(lambda d: d.set_coloring(vibrancy=v)))
        self.background.color_changed.connect(lambda c: self._edit(lambda d: d.set_coloring(background=c)))
        self.revert_coloring.clicked.connect(lambda: self._edit(lambda d: d.revert_coloring()))

    def bind(self, document: FractalDocument) -> None:
        """Follow `document`: refresh on every change, edit it from the controls."""
        self._document = document
        document.flame_replaced.connect(self.refresh)
        document.camera_changed.connect(self.refresh_camera)
        document.coloring_changed.connect(self.refresh_coloring)
        self.refresh()

    def _edit(self, action) -> None:
        if self._document is None or self._document.flame is None or self._updating:
            return
        action(self._document)

    # --- model → controls ----------------------------------------------------------------------------------
    def refresh(self) -> None:
        flame = self._document.flame if self._document is not None else None
        self.set_enabled_for_flame(flame is not None)
        if flame is None:
            return
        self.refresh_camera()
        self.refresh_coloring()

    def refresh_camera(self) -> None:
        flame = self._document.flame if self._document is not None else None
        if flame is None:
            return
        cam = flame.camera
        self._updating = True
        try:
            self.zoom.set_value(cam.zoom)
            set_value_silently(self.center_x, cam.center[0])
            set_value_silently(self.center_y, cam.center[1])
            set_value_silently(self.rotate, cam.rotate)
            self.pitch.set_value(math.degrees(cam.pitch))
            self.yaw.set_value(math.degrees(cam.yaw))
            self.perspective.set_value(cam.perspective)
            self.zpos.set_value(cam.zpos)
            self.dof.set_value(cam.dof)
            self.flat_note.setText("Flat: all zero — tilt the plane with pitch / yaw, or give depth with perspective."
                                   if not cam.is_3d() else "3D camera active.")
        finally:
            self._updating = False

    def refresh_coloring(self) -> None:
        flame = self._document.flame if self._document is not None else None
        if flame is None:
            return
        col = flame.coloring
        self._updating = True
        try:
            self.brightness.set_value(col.brightness)
            self.gamma.set_value(col.gamma)
            self.threshold.set_value(col.gamma_threshold)
            self.vibrancy.set_value(col.vibrancy)
            self.background.set_color(col.background)
        finally:
            self._updating = False

    def set_enabled_for_flame(self, enabled: bool) -> None:
        for w in (self.zoom, self.center_x, self.center_y, self.rotate, self.pan_up, self.pan_down, self.pan_left, self.pan_right,
                  self.revert_view, self.pitch, self.yaw, self.perspective, self.zpos, self.dof, self.revert_3d,
                  self.brightness, self.gamma, self.threshold, self.vibrancy, self.background, self.revert_coloring):
            w.setEnabled(enabled)

    # --- preview effort ------------------------------------------------------------------------------------
    @property
    def passes(self) -> int:
        return self.passes_box.value()

    @property
    def quality(self) -> float:
        return self.quality_box.value()

    def set_preview(self, passes: int, quality: float) -> bool:
        """Set both boxes silently; True if anything changed."""
        before = (self.passes, self.quality)
        set_value_silently(self.passes_box, int(passes))
        set_value_silently(self.quality_box, float(quality))
        return (self.passes, self.quality) != before

    def _preview_changed(self, *_args) -> None:
        self.render_settings_changed.emit(self.passes, self.quality)

    # --- render options ------------------------------------------------------------------------------------
    @property
    def oversample(self) -> int:
        return self.oversample_box.value()

    @property
    def filter_radius(self) -> float:
        return self.filter_box.value()

    @property
    def refine_to(self) -> float:
        """Refinement cap as a quality; 0 when refining is off."""
        return self.refine_box.value() if self.refine_check.isChecked() else 0.0

    def set_options(self, oversample: int, filter_radius: float, refine_to: float) -> bool:
        """Set the option controls silently; True if anything changed."""
        before = (self.oversample, self.filter_radius, self.refine_to)
        set_value_silently(self.oversample_box, int(oversample))
        set_value_silently(self.filter_box, float(filter_radius))
        with QSignalBlocker(self.refine_check):
            self.refine_check.setChecked(refine_to > 0)
        if refine_to > 0:
            set_value_silently(self.refine_box, float(refine_to))
        self.refine_box.setEnabled(refine_to > 0)
        return (self.oversample, self.filter_radius, self.refine_to) != before

    def _options_changed(self, *_args) -> None:
        self.refine_box.setEnabled(self.refine_check.isChecked())
        self.render_options_changed.emit()

