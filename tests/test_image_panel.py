"""The Image tab: camera / 3D camera / colouring controls editing the document, and saving the result."""

import math
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from fractalchemy.fractal import Flame, XForm
from fractalchemy.fractal.formats import load_flames
from fractalchemy.ui.fractal_document import FractalDocument
from fractalchemy.ui.image_panel import PAN_STEP, ImagePanel
from fractalchemy.widgets.float_row import FloatRow
from tests.conftest import copy_samples, spin, wait_until


def sierpinski() -> Flame:
    flame = Flame("s", [XForm(coefs=(0.5, 0, 0, 0.5, 0, 0)), XForm(coefs=(0.5, 0, 0, 0.5, 0.5, 0))])
    flame.camera.center = (0.5, 0.25)
    flame.camera.width, flame.camera.height = 400, 200
    return flame


# --- document ------------------------------------------------------------------------------------------
def test_document_setters_announce_changes_and_track_modification(qapp):
    doc = FractalDocument()
    seen = []
    for name in ("camera_changed", "coloring_changed", "modified_changed"):
        getattr(doc, name).connect(lambda *a, n=name: seen.append((n,) + a))
    doc.set_camera_3d(pitch=1.0)          # no flame: nothing happens
    doc.set_coloring(gamma=2.0)
    assert seen == [] and not doc.modified
    doc.replace(sierpinski())
    assert not doc.modified and doc.original is not None and doc.original is not doc.flame
    doc.set_camera_3d(pitch=0.5, perspective=0.3)
    assert doc.flame.camera.pitch == 0.5 and doc.flame.camera.perspective == 0.3 and doc.flame.camera.yaw == 0.0
    assert doc.modified and ("modified_changed", True) in seen and ("camera_changed",) in seen
    doc.set_coloring(brightness=7.0, background=(1, 2, 3))
    assert doc.flame.coloring.brightness == 7.0 and doc.flame.coloring.background == (1, 2, 3)
    assert ("coloring_changed",) in seen
    assert doc.original.camera.pitch == 0.0 and doc.original.coloring.brightness == 4.0   # the loaded state is kept
    doc.revert_camera_3d()
    doc.revert_coloring()
    assert doc.flame.camera.pitch == 0.0 and doc.flame.coloring.brightness == 4.0 and doc.flame.coloring.background == (0, 0, 0)
    doc.set_view(zoom=1.0, center=(2.0, 2.0))
    doc.revert_view()
    assert doc.flame.camera.zoom == 0.0 and doc.flame.camera.center == (0.5, 0.25)
    doc.mark_saved()
    assert not doc.modified and ("modified_changed", False) in seen


def test_document_pan_moves_in_screen_directions_respecting_rotation(qapp):
    doc = FractalDocument()
    doc.replace(sierpinski())
    cam = doc.flame.camera
    span = cam.width / cam.pixels_per_unit(cam.width, cam.height)   # fractal units across the image
    doc.pan(PAN_STEP, 0.0)
    assert cam.center == pytest.approx((0.5 + PAN_STEP * span, 0.25))
    doc.pan(0.0, PAN_STEP)   # y points down on screen, so "down" increases y
    assert cam.center == pytest.approx((0.5 + PAN_STEP * span, 0.25 + PAN_STEP * span * cam.height / cam.width))
    doc.set_view(center=(0.0, 0.0), rotate=90.0)
    doc.pan(PAN_STEP, 0.0)   # a rotated camera pans along the rotated axis
    assert abs(cam.center[0]) < 1e-9 and abs(abs(cam.center[1]) - PAN_STEP * span) < 1e-9


# --- widgets -------------------------------------------------------------------------------------------
def test_float_row_keeps_slider_and_spin_in_step(qapp):
    row = FloatRow("Gamma", 0.1, 10.0, decimals=2, step=0.1, spin_range=(0.01, 100.0))
    seen = []
    row.value_changed.connect(seen.append)
    row.set_value(2.5)
    assert row.value() == 2.5 and row.slider.value() == 250 and seen == []   # programmatic: silent
    row.slider.setValue(400)
    assert row.spin.value() == 4.0 and seen == [4.0]
    row.spin.setValue(50.0)                     # beyond the slider: it parks at its end
    assert row.slider.value() == row.slider.maximum() and seen == [4.0, 50.0]
    wide = FloatRow("Pitch", -180.0, 180.0, decimals=1)
    wide.set_value(-90.0)
    assert wide.slider.value() == -900 and wide.spin.value() == -90.0


# --- the panel ----------------------------------------------------------------------------------------
@pytest.fixture
def bound(qapp):
    doc = FractalDocument()
    panel = ImagePanel()
    panel.show()
    panel.bind(doc)
    yield doc, panel
    panel.close()


def test_panel_is_disabled_until_a_flame_is_loaded_and_then_shows_its_values(bound):
    doc, panel = bound
    assert not panel.zoom.isEnabled() and not panel.background.isEnabled() and not panel.pan_up.isEnabled()
    flame = sierpinski()
    flame.camera.zoom, flame.camera.rotate = 1.5, 30.0
    flame.camera.pitch, flame.camera.yaw, flame.camera.perspective, flame.camera.zpos, flame.camera.dof = math.radians(45), math.radians(-20), 0.4, 0.5, 0.2
    flame.coloring.brightness, flame.coloring.gamma, flame.coloring.gamma_threshold, flame.coloring.vibrancy = 12.0, 3.5, 0.05, 0.8
    flame.coloring.background = (10, 20, 30)
    doc.replace(flame)
    assert panel.zoom.isEnabled() and panel.zoom.value() == 1.5 and panel.rotate.value() == 30.0
    assert panel.center_x.value() == 0.5 and panel.center_y.value() == 0.25
    assert panel.pitch.value() == 45.0 and panel.yaw.value() == -20.0 and panel.perspective.value() == 0.4
    assert panel.zpos.value() == 0.5 and panel.dof.value() == 0.2 and panel.flat_note.text() == "3D camera active."
    assert panel.brightness.value() == 12.0 and panel.gamma.value() == 3.5 and panel.threshold.value() == 0.05
    assert panel.vibrancy.value() == 0.8 and panel.background.color() == (10, 20, 30) and panel.background.text() == "#0a141e"
    assert not doc.modified   # reflecting the model is not an edit


def test_panel_controls_edit_the_document(bound):
    doc, panel = bound
    doc.replace(sierpinski())
    cam, col = doc.flame.camera, doc.flame.coloring
    assert "Flat" in panel.flat_note.text()
    panel.zoom.spin.setValue(2.0)
    assert cam.zoom == 2.0 and cam.center == (0.5, 0.25)   # zoom is around the centre: the centre stays
    panel.zoom.slider.setValue(-100)
    assert cam.zoom == -1.0
    panel.rotate.setValue(90.0)
    assert cam.rotate == 90.0
    panel.center_x.setValue(1.25)
    panel.center_y.setValue(-0.5)
    assert cam.center == (1.25, -0.5)
    panel.pan_left.click()
    assert cam.center != (1.25, -0.5) and panel.center_x.value() == pytest.approx(cam.center[0], abs=1e-4)
    panel.revert_view.click()
    assert (cam.center, cam.zoom, cam.rotate) == ((0.5, 0.25), 0.0, 0.0) and panel.zoom.value() == 0.0
    panel.pitch.spin.setValue(30.0)
    panel.yaw.spin.setValue(-15.0)
    panel.perspective.spin.setValue(0.25)
    panel.zpos.spin.setValue(-0.75)
    panel.dof.spin.setValue(0.1)
    assert cam.pitch == pytest.approx(math.radians(30)) and cam.yaw == pytest.approx(math.radians(-15))
    assert (cam.perspective, cam.zpos, cam.dof) == (0.25, -0.75, 0.1) and panel.flat_note.text() == "3D camera active."
    panel.revert_3d.click()
    assert not cam.is_3d() and panel.pitch.value() == 0.0
    panel.brightness.spin.setValue(9.0)
    panel.gamma.spin.setValue(2.2)
    panel.threshold.spin.setValue(0.1)
    panel.vibrancy.spin.setValue(0.5)
    assert (col.brightness, col.gamma, col.gamma_threshold, col.vibrancy) == (9.0, 2.2, 0.1, 0.5)
    panel.background.picker.set_color((200, 100, 50), as_original=True)   # the live picker
    panel.background.picker.red.setValue(201)
    assert col.background == (201, 100, 50) and panel.background.text() == "#c96432"
    panel.revert_coloring.click()
    assert col.brightness == 4.0 and col.background == (0, 0, 0) and panel.brightness.value() == 4.0
    assert doc.modified


def test_preview_boxes_live_on_the_image_tab(bound):
    _doc, panel = bound
    seen = []
    panel.render_settings_changed.connect(lambda p, q: seen.append((p, q)))
    assert panel.set_preview(3, 20.0) and not panel.set_preview(3, 20.0) and seen == []
    panel.passes_box.setValue(4)
    assert seen == [(4, 20.0)]


# --- saving ---------------------------------------------------------------------------------------------
def test_viewport_render_camera_keeps_the_3d_settings(qapp):
    from fractalchemy.ui.fractal_viewport import FractalViewport
    from fractalchemy.render.service import RenderService

    doc = FractalDocument()
    view = FractalViewport()
    service = RenderService(prefer_gpu=False)
    view.bind(doc, service)
    view.resize(300, 200)
    flame = sierpinski()
    flame.camera.pitch, flame.camera.perspective, flame.camera.dof = 0.7, 0.3, 0.1
    doc.replace(flame)
    camera, _w, _h = view.render_camera()
    assert (camera.pitch, camera.perspective, camera.dof) == (0.7, 0.3, 0.1)
    view.close()


def test_save_fractal_writes_the_adjusted_flame_back_into_its_entry(qapp, tmp_path, samples):
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.ui.main_window import MainWindow

    library = copy_samples(samples, tmp_path / "lib")
    path = library / "sample flames" / "flamepack1.flame"
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    win = MainWindow(LibraryRoots(settings), LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key), prefer_gpu=False, settings=settings)
    win.show()
    try:
        win.open_path(path, 7)
        wait_until(lambda: win.document.flame is not None and win.document.flame.name == "3d musk sphere")
        assert not win.actionSaveFractal.isEnabled() and win.windowTitle() == "Fractalchemy — 3d musk sphere"
        assert win.document.flame.camera.is_3d() and win.settingsPanel.image.pitch.value() == pytest.approx(60.9, abs=0.05)
        panel = win.settingsPanel.image
        panel.pitch.spin.setValue(30.0)
        panel.brightness.spin.setValue(12.0)
        panel.background.picker.set_color((5, 6, 7), as_original=True)
        panel.background.picker.blue.setValue(8)
        assert win.actionSaveFractal.isEnabled() and win.windowTitle() == "Fractalchemy — 3d musk sphere*"
        win.actionSaveFractal.trigger()
        spin(50)
        assert not win.document.modified and not win.actionSaveFractal.isEnabled() and win.windowTitle().endswith("sphere")
        saved = load_flames(path)[7]
        assert saved.name == "3d musk sphere" and saved.camera.pitch == pytest.approx(math.radians(30))
        assert saved.coloring.brightness == 12.0 and saved.coloring.background == (5, 6, 8)
        assert saved.camera.yaw == pytest.approx(win.document.original.camera.yaw) and len(load_flames(path)) == 27
        assert Path(path).read_text().count("<flame ") == 27
        win.document.set_view(zoom=0.5)
        assert win.actionSaveFractal.isEnabled()
    finally:
        win.gradient_library.document.modified = False
        win.close()
