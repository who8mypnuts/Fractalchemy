"""The 3D Editor's property panels: Render, Camera, Materials, Lights and Environment.

Each panel binds to the `Scene3DDocument`: it fills its controls from the scene on the document's signals
and writes edits back through the document's methods, with a merge key per control so a slider drag is one
undo step (the key is released when the slider is let go). A `_updating` guard keeps model → control
updates from echoing back as edits.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget, QPushButton,
                               QSpinBox, QVBoxLayout, QWidget)

from ...scene3d.model import DistantLight
from ...widgets.float_row import FloatRow
from ...widgets.images import rgba_to_qimage
from ...widgets.silent import blocked, updating
from ..image_panel import ColorButton
from .document import MAX_LIGHTS, Scene3DDocument
from .viewport import QUALITIES

DEGREES = 57.29577951308232


class _Panel(QWidget):
    """Shared plumbing: the document, the re-entrancy guard, FloatRow helpers."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._document: Scene3DDocument | None = None
        self._updating = False

    def _row(self, label: str, lo: float, hi: float, decimals: int, tooltip: str, on_change, merge_key: str,
             suffix: str = "", spin_range: tuple[float, float] | None = None) -> FloatRow:
        row = FloatRow(label, lo, hi, decimals, suffix=suffix, spin_range=spin_range, parent=self).set_tooltip(tooltip)
        row.value_changed.connect(lambda value: None if self._updating else on_change(value, merge_key))
        row.slider.sliderReleased.connect(lambda: self._document.end_merge() if self._document else None)
        return row

    def _color(self, title: str, on_change) -> ColorButton:
        button = ColorButton(self)
        button.picker.setWindowTitle(title)
        button.color_changed.connect(lambda color: None if self._updating else on_change(tuple(color)))
        button.picker.finished_with.connect(lambda _ok: self._document.end_merge() if self._document else None)
        return button


# --- render ---------------------------------------------------------------------------------------------------------
class RenderPanel(_Panel):
    """Display mode, preview quality, ambient occlusion, normal smoothing and fog.

    Signals:
        quality_changed(str): The viewport quality preset chosen.
    """
    quality_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.display_box = QComboBox(self)
        self.display_box.addItem("Solid (lit surface)", "solid")
        self.display_box.addItem("Points (palette colours, unlit)", "points")
        self.display_box.addItem("Mesh (generated on the Mesh tab)", "mesh")
        self.display_box.setToolTip("How the viewport and renders draw the fractal")
        self.quality_box = QComboBox(self)
        for level in QUALITIES:
            self.quality_box.addItem(level.name, level.name)
        self.quality_box.setToolTip("Viewport preview quality: samples and supersampling (renders to file have their own)")
        self.ao_check = QCheckBox("Ambient occlusion", self)
        self.ao_check.setToolTip("Darken corners and crevices that see less of the surroundings")
        self.ao_radius = self._row("Radius", 0.005, 0.2, 3, "Sampling radius as a fraction of the depth range", self._solid("ao_radius"), "ao_radius")
        self.ao_intensity = self._row("Intensity", 0.0, 1.0, 2, "How dark occluded places get", self._solid("ao_intensity"), "ao_intensity")
        self.ao_samples = QSpinBox(self)
        self.ao_samples.setRange(4, 64)
        self.ao_samples.setToolTip("Samples per pixel: more is smoother and slower")
        self.ao_falloff = self._row("Falloff", 0.2, 4.0, 2, "How quickly occluders lose weight with distance (1 = linear)", self._solid("ao_falloff"), "ao_falloff")
        self.smoothing = self._row("Smoothing", 0.0, 4.0, 0, "Blur of the surface normals in pixels (0 = none): hides the grain of the point cloud",
                                   self._solid("normal_smoothing"), "normal_smoothing")
        self.min_hits = QSpinBox(self)
        self.min_hits.setRange(1, 50)
        self.min_hits.setToolTip("Density threshold: a pixel needs this many samples to count as surface. Removes the stray dust "
                                 "a flame's blur variations scatter about (1 = every sample counts)")
        self.fog_check = QCheckBox("Fog", self)
        self.fog_check.setToolTip("Fade the surface towards a colour with depth")
        self.fog_start = self._row("Start", 0.0, 1.0, 2, "Where the fog begins, as a fraction of the depth range", self._solid("fog_start"), "fog_start")
        self.fog_end = self._row("End", 0.0, 1.0, 2, "Where the fog is complete", self._solid("fog_end"), "fog_end")
        self.fog_color = self._color("Fog colour", lambda c: self._document.update_solid("fog_color", fog_color=c))
        self._build()
        self.display_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._document.update_solid(None, display=self.display_box.currentData()))
        self.quality_box.currentIndexChanged.connect(lambda _i: self.quality_changed.emit(self.quality_box.currentData()))
        self.ao_check.toggled.connect(lambda on: None if self._updating else self._document.update_solid(None, ao=on))
        self.ao_samples.valueChanged.connect(lambda v: None if self._updating else self._document.update_solid("ao_samples", ao_samples=int(v)))
        self.min_hits.valueChanged.connect(lambda v: None if self._updating else self._document.update_solid("min_hits", min_hits=int(v)))
        self.fog_check.toggled.connect(lambda on: None if self._updating else self._document.update_solid(None, fog=on))

    def _solid(self, field: str):
        return lambda value, key: self._document.update_solid(key, **{field: value})

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        top = QFormLayout()
        top.addRow("Display", self.display_box)
        top.addRow("Preview quality", self.quality_box)
        layout.addLayout(top)
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Density threshold", self))
        threshold_row.addWidget(self.min_hits)
        threshold_row.addStretch(1)
        layout.addLayout(threshold_row)
        ao = QGroupBox("Shading", self)
        ao_layout = QVBoxLayout(ao)
        ao_layout.addWidget(self.smoothing)
        ao_layout.addWidget(self.ao_check)
        ao_layout.addWidget(self.ao_radius)
        ao_layout.addWidget(self.ao_intensity)
        ao_layout.addWidget(self.ao_falloff)
        samples_row = QHBoxLayout()
        samples_row.addWidget(QLabel("Samples", ao))
        samples_row.addWidget(self.ao_samples)
        samples_row.addStretch(1)
        ao_layout.addLayout(samples_row)
        layout.addWidget(ao)
        fog = QGroupBox("Fog", self)
        fog_layout = QVBoxLayout(fog)
        fog_layout.addWidget(self.fog_check)
        fog_layout.addWidget(self.fog_start)
        fog_layout.addWidget(self.fog_end)
        colour_row = QHBoxLayout()
        colour_row.addWidget(QLabel("Colour", fog))
        colour_row.addWidget(self.fog_color)
        colour_row.addStretch(1)
        fog_layout.addLayout(colour_row)
        layout.addWidget(fog)
        layout.addStretch(1)

    def bind(self, document: Scene3DDocument) -> None:
        self._document = document
        for signal in (document.scene_replaced, document.scene_restored, document.solid_changed):
            signal.connect(self.refresh)
        self.refresh()

    def set_quality_name(self, name: str) -> None:
        with blocked(self.quality_box):
            index = self.quality_box.findData(name)
            self.quality_box.setCurrentIndex(max(0, index))

    def refresh(self) -> None:
        if self._document is None:
            return
        s = self._document.scene.solid
        with updating(self), blocked(self.display_box, self.ao_check, self.ao_samples, self.fog_check, self.min_hits):
            self.display_box.setCurrentIndex(max(0, self.display_box.findData(s.display)))
            self.min_hits.setValue(int(s.min_hits))
            self.ao_check.setChecked(s.ao)
            self.ao_radius.set_value(s.ao_radius)
            self.ao_intensity.set_value(s.ao_intensity)
            self.ao_samples.setValue(int(s.ao_samples))
            self.ao_falloff.set_value(s.ao_falloff)
            self.smoothing.set_value(s.normal_smoothing)
            self.fog_check.setChecked(s.fog)
            self.fog_start.set_value(s.fog_start)
            self.fog_end.set_value(s.fog_end)
            self.fog_color.set_color(s.fog_color)
        lit = s.display != "points"
        for w in (self.ao_check, self.ao_radius, self.ao_intensity, self.ao_samples, self.ao_falloff, self.smoothing, self.fog_check,
                  self.fog_start, self.fog_end, self.fog_color):
            w.setEnabled(lit)
        for w in (self.ao_radius, self.ao_intensity, self.ao_samples, self.ao_falloff):
            w.setEnabled(lit and s.ao)
        for w in (self.fog_start, self.fog_end, self.fog_color):
            w.setEnabled(lit and s.fog)


# --- camera ---------------------------------------------------------------------------------------------------------
class CameraPanel(_Panel):
    """The flame's 3D camera as numbers: pitch / yaw / tilt in degrees, perspective, depth offset, zoom.

    Signals:
        reset_requested(): The *Reset view* button.
    """
    reset_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.pitch = self._row("Pitch", -180.0, 180.0, 1, "Tilt of the camera about the screen's horizontal axis (Apophysis pitch)", self._angle("pitch"), "pitch", "°")
        self.yaw = self._row("Yaw", -180.0, 180.0, 1, "Turn of the camera about the vertical axis (Apophysis yaw)", self._angle("yaw"), "yaw", "°")
        self.tilt = self._row("Tilt", -180.0, 180.0, 1, "Tilt about the screen's vertical axis, after the pitch", self._angle("pitch_y"), "pitch_y", "°")
        self.perspective = self._row("Perspective", 0.0, 2.0, 2, "Perspective strength (0 = orthographic)", self._field("perspective"), "perspective")
        self.zpos = self._row("Distance", -5.0, 5.0, 2, "Depth offset of the fractal (Apophysis cam_zpos)", self._field("zpos"), "zpos")
        self.zoom = self._row("Zoom", -4.0, 6.0, 2, "Magnification in powers of two (the wheel in the viewport)", self._field("zoom"), "zoom")
        self.reset_button = QPushButton("Reset view", self)
        self.reset_button.setToolTip("Back to the camera the fractal arrived with (double-click in the viewport)")
        self.reset_button.clicked.connect(self.reset_requested)
        layout = QVBoxLayout(self)
        for row in (self.pitch, self.yaw, self.tilt, self.perspective, self.zpos, self.zoom):
            layout.addWidget(row)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.reset_button)
        layout.addLayout(buttons)
        hint = QLabel("In the viewport: left-drag orbits, right-drag pans, the wheel zooms, Ctrl+wheel changes the perspective.", self)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #808080;")
        layout.addWidget(hint)
        layout.addStretch(1)

    def _angle(self, field: str):
        return lambda degrees, key: self._document.set_camera(key, **{field: degrees / DEGREES})

    def _field(self, field: str):
        return lambda value, key: self._document.set_camera(key, **{field: value})

    def bind(self, document: Scene3DDocument) -> None:
        self._document = document
        for signal in (document.scene_replaced, document.scene_restored, document.fractal_changed, document.camera_changed):
            signal.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        flame = self._document.flame if self._document else None
        self.setEnabled(flame is not None)
        if flame is None:
            return
        c = flame.camera
        with updating(self):
            self.pitch.set_value(c.pitch * DEGREES)
            self.yaw.set_value(c.yaw * DEGREES)
            self.tilt.set_value(c.pitch_y * DEGREES)
            self.perspective.set_value(c.perspective)
            self.zpos.set_value(c.zpos)
            self.zoom.set_value(c.zoom)


# --- materials ------------------------------------------------------------------------------------------------------
class MaterialsPanel(_Panel):
    """One material per transform: pick the transform in the list, edit its surface on the right."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.list = QListWidget(self)
        self.list.setToolTip("The transforms; each has its own material (the final transform has the last one)")
        self.list.setMaximumHeight(140)
        self.mode_box = QComboBox(self)
        self.mode_box.addItem("Palette colour", "palette")
        self.mode_box.addItem("Fixed colour", "fixed")
        self.mode_box.setToolTip("Colour the surface from the point's palette colour, or with one fixed colour")
        self.color = self._color("Surface colour", lambda c: self._material("color", color=c))
        self.diffuse = self._row("Diffuse", 0.0, 2.0, 2, "Strength of the diffuse (matte) reflection", self._mat_field("diffuse"), "diffuse")
        self.ambient = self._row("Ambient", 0.0, 2.0, 2, "How much of the environment's ambient light the surface reflects", self._mat_field("ambient"), "ambient")
        self.specular = self._row("Specular", 0.0, 2.0, 2, "Strength of the highlight", self._mat_field("specular"), "specular")
        self.shininess = self._row("Shininess", 1.0, 200.0, 0, "Tightness of the highlight (Phong exponent)", self._mat_field("shininess"), "shininess")
        self.specular_color = self._color("Highlight colour", lambda c: self._material("specular_color", specular_color=c))
        self.wrap = self._row("Light wrap", 0.0, 1.0, 2, "Let light reach round the terminator (softer shading)", self._mat_field("wrap"), "wrap")
        self.copy_button = QPushButton("Copy to all transforms", self)
        self.copy_button.setToolTip("Give every transform this material")
        self._build()
        self.list.currentRowChanged.connect(lambda _row: self._show_current())
        self.mode_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._material(None, color_mode=self.mode_box.currentData()))
        self.copy_button.clicked.connect(lambda: self._document.copy_material_to_all(self.current_index()) if self._document else None)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        form = QFormLayout()
        form.addRow("Colour from", self.mode_box)
        form.addRow("Colour", self.color)
        layout.addLayout(form)
        for row in (self.diffuse, self.ambient, self.specular, self.shininess, self.wrap):
            layout.addWidget(row)
        spec = QHBoxLayout()
        spec.addWidget(QLabel("Highlight colour", self))
        spec.addWidget(self.specular_color)
        spec.addStretch(1)
        layout.addLayout(spec)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.copy_button)
        layout.addLayout(buttons)
        layout.addStretch(1)

    def _mat_field(self, field: str):
        return lambda value, key: self._material(key, **{field: value})

    def _material(self, merge_key, **fields) -> None:
        if self._document is not None and self.current_index() >= 0:
            self._document.update_material(self.current_index(), merge_key, **fields)

    def current_index(self) -> int:
        return self.list.currentRow()

    def select(self, index: int) -> None:
        if 0 <= index < self.list.count():
            self.list.setCurrentRow(index)

    def bind(self, document: Scene3DDocument) -> None:
        self._document = document
        for signal in (document.scene_replaced, document.scene_restored, document.fractal_changed):
            signal.connect(self.refresh)
        document.materials_changed.connect(self._show_current)
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the transform list (keeping the selection where possible) and show the selected material."""
        if self._document is None:
            return
        flame = self._document.flame
        current = max(0, self.list.currentRow())
        with blocked(self.list):
            self.list.clear()
            if flame is not None:
                for i, xform in enumerate(flame.xforms):
                    name = xform.name or ", ".join(sorted(xform.variations)) or "transform"
                    self.list.addItem(f"{i + 1}  {name}")
                if flame.final is not None:
                    self.list.addItem("Final transform")
            if self.list.count():
                self.list.setCurrentRow(min(current, self.list.count() - 1))
        self.setEnabled(self.list.count() > 0)
        self._show_current()

    def _show_current(self) -> None:
        if self._document is None or self.current_index() < 0:
            return
        m = self._document.scene.material_for_transform(self.current_index())
        with updating(self), blocked(self.mode_box):
            self.mode_box.setCurrentIndex(max(0, self.mode_box.findData(m.color_mode)))
            self.color.set_color(m.color)
            self.diffuse.set_value(m.diffuse)
            self.ambient.set_value(m.ambient)
            self.specular.set_value(m.specular)
            self.shininess.set_value(m.shininess)
            self.specular_color.set_color(m.specular_color)
            self.wrap.set_value(m.wrap)
        self.color.setEnabled(m.color_mode == "fixed")


# --- lights ---------------------------------------------------------------------------------------------------------
class LightsPanel(_Panel):
    """The distant lights: a list with add / remove, and the selected light's placement, colour and shadow."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.list = QListWidget(self)
        self.list.setMaximumHeight(110)
        self.add_button = QPushButton("Add light", self)
        self.add_point_button = QPushButton("Add point light", self)
        self.remove_button = QPushButton("Remove", self)
        self.kind_box = QComboBox(self)
        self.kind_box.addItem("Distant (sun-like, placed relative to the camera)", "distant")
        self.kind_box.addItem("Point (in the fractal's space, with falloff)", "point")
        self.pos_x = self._row("X", -5.0, 5.0, 2, "Position of the point light in fractal coordinates", self._light_position(0), "pos_x")
        self.pos_y = self._row("Y", -5.0, 5.0, 2, "Position of the point light in fractal coordinates", self._light_position(1), "pos_y")
        self.pos_z = self._row("Z", -5.0, 5.0, 2, "Position of the point light in fractal coordinates", self._light_position(2), "pos_z")
        self.radius = self._row("Radius", 0.01, 5.0, 2, "Distance at which the light has fallen to half (inverse-square falloff)", self._light_field("radius"), "radius")
        self.altitude = self._row("Altitude", -90.0, 90.0, 1, "Height above the view plane (90° = from the camera)", self._light_field("altitude"), "altitude", "°")
        self.azimuth = self._row("Azimuth", -180.0, 180.0, 1, "Direction around the view axis (0° = from the right, 90° = from above)", self._light_field("azimuth"), "azimuth", "°")
        self.intensity = self._row("Intensity", 0.0, 3.0, 2, "Strength of the light", self._light_field("intensity"), "intensity")
        self.color = self._color("Light colour", lambda c: self._light("color", color=c))
        self.shadows_check = QCheckBox("Casts shadows", self)
        self.shadows_check.setToolTip("Render a shadow map from this light (the surface shades itself)")
        self.shadow_intensity = self._row("Darkness", 0.0, 1.0, 2, "How dark the shadows are", self._light_field("shadow_intensity"), "shadow_intensity")
        self.shadow_softness = self._row("Softness", 0.0, 6.0, 1, "Blur of the shadow edge", self._light_field("shadow_softness"), "shadow_softness")
        self._build()
        self.list.currentRowChanged.connect(lambda _row: self._show_current())
        self.add_button.clicked.connect(self._add)
        self.add_point_button.clicked.connect(self._add_point)
        self.remove_button.clicked.connect(lambda: self._document.remove_light(self.current_index()) if self._document else None)
        self.shadows_check.toggled.connect(lambda on: None if self._updating else self._light(None, shadows=on))
        self.kind_box.currentIndexChanged.connect(lambda _i: None if self._updating else self._light(None, kind=self.kind_box.currentData()))

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.add_point_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(self.kind_box)
        for row in (self.altitude, self.azimuth, self.pos_x, self.pos_y, self.pos_z, self.radius, self.intensity):
            layout.addWidget(row)
        colour = QHBoxLayout()
        colour.addWidget(QLabel("Colour", self))
        colour.addWidget(self.color)
        colour.addStretch(1)
        layout.addLayout(colour)
        shadow = QGroupBox("Shadow", self)
        shadow_layout = QVBoxLayout(shadow)
        shadow_layout.addWidget(self.shadows_check)
        shadow_layout.addWidget(self.shadow_intensity)
        shadow_layout.addWidget(self.shadow_softness)
        layout.addWidget(shadow)
        layout.addStretch(1)

    def _light_field(self, field: str):
        return lambda value, key: self._light(key, **{field: value})

    def _light_position(self, axis: int):
        def setter(value, key):
            light = self._current_light()
            if light is not None:
                position = list(light.position)
                position[axis] = float(value)
                self._light(key, position=tuple(position))
        return setter

    def _current_light(self):
        index = self.current_index()
        lights = self._document.scene.lights if self._document is not None else []
        return lights[index] if 0 <= index < len(lights) else None

    def _add_point(self) -> None:
        if self._document is None:
            return
        index = self._document.add_light(DistantLight(kind="point", position=(0.0, 0.0, 1.0), radius=1.0, intensity=1.0, shadows=False,
                                                      color=(255, 240, 220)))
        if index >= 0:
            self.list.setCurrentRow(index)

    def _light(self, merge_key, **fields) -> None:
        if self._document is not None and self.current_index() >= 0:
            self._document.update_light(self.current_index(), merge_key, **fields)

    def _add(self) -> None:
        if self._document is None:
            return
        index = self._document.add_light(DistantLight(altitude=30.0, azimuth=90.0, intensity=0.5, shadows=False))
        if index >= 0:
            self.list.setCurrentRow(index)

    def current_index(self) -> int:
        return self.list.currentRow()

    def bind(self, document: Scene3DDocument) -> None:
        self._document = document
        for signal in (document.scene_replaced, document.scene_restored, document.lights_changed):
            signal.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        if self._document is None:
            return
        lights = self._document.scene.lights
        current = self.list.currentRow()
        with blocked(self.list):
            self.list.clear()
            for i, light in enumerate(lights):
                where = (f"point at {light.position[0]:g}, {light.position[1]:g}, {light.position[2]:g}" if light.is_point
                         else f"{light.altitude:g}°, {light.azimuth:g}°")
                self.list.addItem(f"Light {i + 1}  ({where})" + ("  · shadows" if light.casts_shadows else ""))
            if lights:
                self.list.setCurrentRow(min(max(0, current), len(lights) - 1))
        self.add_button.setEnabled(len(lights) < MAX_LIGHTS)
        self.remove_button.setEnabled(bool(lights))
        self._show_current()

    def _show_current(self) -> None:
        if self._document is None:
            return
        index = self.current_index()
        lights = self._document.scene.lights
        has = 0 <= index < len(lights)
        for w in (self.kind_box, self.altitude, self.azimuth, self.pos_x, self.pos_y, self.pos_z, self.radius, self.intensity, self.color,
                  self.shadows_check, self.shadow_intensity, self.shadow_softness):
            w.setEnabled(has)
        if not has:
            return
        light = lights[index]
        with updating(self), blocked(self.shadows_check, self.kind_box):
            self.kind_box.setCurrentIndex(max(0, self.kind_box.findData(light.kind)))
            self.altitude.set_value(light.altitude)
            self.azimuth.set_value(light.azimuth)
            self.pos_x.set_value(light.position[0])
            self.pos_y.set_value(light.position[1])
            self.pos_z.set_value(light.position[2])
            self.radius.set_value(light.radius)
            self.intensity.set_value(light.intensity)
            self.color.set_color(light.color)
            self.shadows_check.setChecked(light.shadows)
            self.shadow_intensity.set_value(light.shadow_intensity)
            self.shadow_softness.set_value(light.shadow_softness)
        point = light.is_point
        for w in (self.altitude, self.azimuth):
            w.setVisible(not point)
        for w in (self.pos_x, self.pos_y, self.pos_z, self.radius):
            w.setVisible(point)
        self.shadows_check.setEnabled(not point)
        self.shadows_check.setToolTip("Point lights cast no shadows (shadow maps are directional)" if point
                                      else "Render a shadow map from this light (the surface shades itself)")
        self.shadow_intensity.setEnabled(light.casts_shadows)
        self.shadow_softness.setEnabled(light.casts_shadows)


# --- environment ----------------------------------------------------------------------------------------------------
class EnvironmentPanel(_Panel):
    """Background colour and visibility, ambient light, exposure, and the HDRI: file, rotation, strength, blur,
    whether it is the background, a thumbnail, and *Extract key lights* (the brightest regions become distant lights).

    Signals:
        status(str): A message for the status bar.
    """
    status = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.color = self._color("Background colour", lambda c: self._document.update_environment("color", color=c))
        self.visible_check = QCheckBox("Show the background", self)
        self.visible_check.setToolTip("Off: the background is transparent (renders keep the alpha channel)")
        self.ambient = self._row("Ambient", 0.0, 2.0, 2, "Strength of the ambient light (the background colour's, or the HDRI's irradiance)",
                                 self._env_field("ambient"), "ambient")
        self.exposure = self._row("Exposure", 0.1, 4.0, 2, "Brightness multiplier on the shaded image", self._env_field("exposure"), "exposure")
        self.hdri_path = QLabel("none", self)
        self.hdri_path.setStyleSheet("color: #808080;")
        self.hdri_path.setWordWrap(True)
        self.browse_button = QPushButton("Choose HDRI…", self)
        self.clear_button = QPushButton("Clear", self)
        self.thumbnail = QLabel(self)
        self.thumbnail.setFixedSize(240, 120)
        self.thumbnail.setStyleSheet("background: #181818; color: #666;")
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setText("No HDRI")
        self.rotation = self._row("Rotation", -180.0, 180.0, 1, "Turn the map about the vertical axis", self._env_field("hdri_rotation"), "hdri_rotation", "°")
        self.strength = self._row("Light", 0.0, 4.0, 2, "How strongly the HDRI lights the surface (diffuse and reflections)",
                                  self._env_field("hdri_strength"), "hdri_strength")
        self.blur = self._row("Blur", 0.0, 1.0, 2, "Blur of the HDRI as the background", self._env_field("hdri_blur"), "hdri_blur")
        self.background_check = QCheckBox("HDRI as the background", self)
        self.background_check.setToolTip("Off: the background colour shows while the HDRI still lights the scene")
        self.key_count = QSpinBox(self)
        self.key_count.setRange(1, 6)
        self.key_count.setValue(2)
        self.extract_button = QPushButton("Extract key lights", self)
        self.extract_button.setToolTip("Add the HDRI's brightest regions as distant lights (the first casts shadows) — HDRI lighting with shadows")
        self._build()
        self.visible_check.toggled.connect(lambda on: None if self._updating else self._document.update_environment(None, visible=on))
        self.background_check.toggled.connect(lambda on: None if self._updating else self._document.update_environment(None, hdri_background=on))
        self.browse_button.clicked.connect(self.choose_hdri)
        self.clear_button.clicked.connect(lambda: self._document.update_environment(None, hdri="") if self._document else None)
        self.extract_button.clicked.connect(lambda: self.extract_key_lights(self.key_count.value()))

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        colour = QHBoxLayout()
        colour.addWidget(QLabel("Background", self))
        colour.addWidget(self.color)
        colour.addStretch(1)
        layout.addLayout(colour)
        layout.addWidget(self.visible_check)
        layout.addWidget(self.ambient)
        layout.addWidget(self.exposure)
        group = QGroupBox("HDRI environment", self)
        g = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(self.browse_button)
        row.addWidget(self.clear_button)
        row.addStretch(1)
        g.addLayout(row)
        g.addWidget(self.hdri_path)
        g.addWidget(self.thumbnail, 0, Qt.AlignmentFlag.AlignHCenter)
        g.addWidget(self.rotation)
        g.addWidget(self.strength)
        g.addWidget(self.blur)
        g.addWidget(self.background_check)
        keys = QHBoxLayout()
        keys.addWidget(self.extract_button)
        keys.addWidget(self.key_count)
        keys.addWidget(QLabel("lights", group))
        keys.addStretch(1)
        g.addLayout(keys)
        layout.addWidget(group)
        layout.addStretch(1)

    def _env_field(self, field: str):
        return lambda value, key: self._document.update_environment(key, **{field: value})

    def choose_hdri(self, path=None) -> bool:
        """Pick an HDRI (`.hdr`, `.exr` or an LDR image); a dialog when no path is given."""
        if self._document is None:
            return False
        if path is None:
            chosen, _filter = QFileDialog.getOpenFileName(self, "Choose an HDRI", "",
                                                          "Environment images (*.hdr *.exr *.png *.jpg *.jpeg *.tif *.tiff);;All files (*)")
            if not chosen:
                return False
            path = chosen
        from ...solid import hdri
        try:
            hdri.load_environment(path)
        except (OSError, hdri.HdriError) as exc:
            self.status.emit(f"Could not read the HDRI: {exc}")
            return False
        self._document.update_environment(None, hdri=str(path))
        return True

    def extract_key_lights(self, count: int = 2) -> int:
        """Add the HDRI's brightest regions as distant lights; returns how many were added."""
        if self._document is None:
            return 0
        added = self._document.add_key_lights(count)
        self.status.emit(f"Added {added} light{'s' if added != 1 else ''} from the HDRI" if added else "No HDRI to take lights from")
        return added

    def bind(self, document: Scene3DDocument) -> None:
        self._document = document
        for signal in (document.scene_replaced, document.scene_restored, document.environment_changed):
            signal.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        if self._document is None:
            return
        env = self._document.scene.environment
        with updating(self), blocked(self.visible_check, self.background_check):
            self.color.set_color(env.color)
            self.visible_check.setChecked(env.visible)
            self.ambient.set_value(env.ambient)
            self.exposure.set_value(env.exposure)
            self.rotation.set_value(env.hdri_rotation)
            self.strength.set_value(env.hdri_strength)
            self.blur.set_value(env.hdri_blur)
            self.background_check.setChecked(env.hdri_background)
        has = bool(env.hdri)
        for w in (self.rotation, self.strength, self.blur, self.background_check, self.extract_button, self.key_count, self.clear_button):
            w.setEnabled(has)
        self.hdri_path.setText(env.hdri if has else "none")
        self._show_thumbnail(env.hdri if has else "")

    def _show_thumbnail(self, path: str) -> None:
        if not path:
            self.thumbnail.setPixmap(QPixmap())
            self.thumbnail.setText("No HDRI")
            return
        from ...solid import hdri
        env_map = hdri.environment_for(self._document.scene.environment)
        if env_map is None:
            self.thumbnail.setPixmap(QPixmap())
            self.thumbnail.setText("Cannot read the HDRI")
            return
        image = env_map.levels[min(1, len(env_map.levels) - 1)]
        tone = image / (1.0 + image)                               # Reinhard, then sRGB: a glance at the map
        srgb = np.where(tone <= 0.0031308, tone * 12.92, 1.055 * np.power(np.maximum(tone, 1e-9), 1 / 2.4) - 0.055)
        rgba = np.empty(image.shape[:2] + (4,), dtype=np.uint8)
        rgba[..., :3] = np.clip(srgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
        rgba[..., 3] = 255
        pixmap = QPixmap.fromImage(rgba_to_qimage(np.ascontiguousarray(rgba)))
        self.thumbnail.setPixmap(pixmap.scaled(self.thumbnail.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


__all__ = ["RenderPanel", "CameraPanel", "MaterialsPanel", "LightsPanel", "EnvironmentPanel", "DEGREES"]
