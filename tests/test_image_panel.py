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
from tests.conftest import copy_samples, wait_until


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
        assert win.actionSaveFractal.isEnabled() and win.windowTitle() == "Fractalchemy — 3d musk sphere"
        assert win.document.flame.camera.is_3d() and win.settingsPanel.image.pitch.value() == pytest.approx(60.9, abs=0.05)
        panel = win.settingsPanel.image
        panel.pitch.spin.setValue(30.0)
        panel.brightness.spin.setValue(12.0)
        panel.background.picker.set_color((5, 6, 7), as_original=True)
        panel.background.picker.blue.setValue(8)
        assert win.actionSaveFractal.isEnabled() and win.windowTitle() == "Fractalchemy — 3d musk sphere*"
        win.actionSaveFractal.trigger()   # written on the thread pool
        wait_until(lambda: not win.document.modified)
        assert win.windowTitle().endswith("sphere")
        saved = load_flames(path)[7]
        assert saved.name == "3d musk sphere" and saved.camera.pitch == pytest.approx(math.radians(30))
        assert saved.coloring.brightness == 12.0 and saved.coloring.background == (5, 6, 8)
        assert saved.camera.yaw == pytest.approx(win.document.original.camera.yaw) and len(load_flames(path)) == 27
        assert Path(path).read_text().count("<flame ") == 27
        win.document.set_view(zoom=0.5)
        assert win.document.modified and win.windowTitle().endswith("*")
    finally:
        win.gradient_library.document.modified = False
        win.close()


def test_preview_options_persist_and_reach_the_viewport(qapp, tmp_path):
    from fractalchemy.ui.settings_panel import FILTER_KEY, OVERSAMPLE_KEY, REFINE_KEY, SettingsPanel

    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    panel = SettingsPanel(settings=settings)
    seen = []
    panel.render_options_changed.connect(lambda o, f, r: seen.append((o, f, r)))
    assert (panel.oversample, panel.filter_radius) == (2, 0.5) and panel.refine_to == 0.0   # tests run with refining off
    panel.image.refine_check.setChecked(True)
    panel.image.refine_box.setValue(300.0)
    panel.image.oversample_box.setValue(3)
    panel.image.filter_box.setValue(1.0)
    assert seen[-1] == (3, 1.0, 300.0) and int(settings.value(OVERSAMPLE_KEY)) == 3
    assert float(settings.value(FILTER_KEY)) == 1.0 and float(settings.value(REFINE_KEY)) == 300.0
    panel.image.refine_check.setChecked(False)
    assert panel.refine_to == 0.0 and not panel.image.refine_box.isEnabled() and float(settings.value(REFINE_KEY)) == 0.0
    again = SettingsPanel(settings=settings)
    assert (again.oversample, again.filter_radius, again.refine_to) == (3, 1.0, 0.0)
    again.set_options(2, 0.5, 200.0)
    assert again.image.refine_check.isChecked() and again.refine_to == 200.0


def test_main_window_applies_preview_options_to_the_viewport(qapp, tmp_path):
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.ui.main_window import MainWindow

    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    win = MainWindow(LibraryRoots(settings), LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key), prefer_gpu=False, settings=settings)
    try:
        assert (win.viewport.settings.oversample, win.viewport.settings.filter_radius, win.viewport.settings.refine_to) == (2, 0.5, 0.0)
        win.settingsPanel.set_options(1, 0.2, 150.0)
        assert (win.viewport.settings.oversample, win.viewport.settings.filter_radius, win.viewport.settings.refine_to) == (1, 0.2, 150.0)
    finally:
        win.gradient_library.document.modified = False
        win.close()


# --- undo / redo / paste ----------------------------------------------------------------------------------
def test_document_undo_redo_coalesces_drags_and_paste_is_undoable(qapp):
    from fractalchemy.ui import fractal_document as FD

    doc = FractalDocument()
    states = []
    doc.undo_changed.connect(lambda u, r: states.append((u, r)))
    restored = []
    doc.flame_restored.connect(lambda: restored.append(1))
    doc.replace(sierpinski())
    assert not doc.can_undo and not doc.undo() and not doc.redo()
    doc.set_coloring(brightness=5.0)
    doc.set_coloring(brightness=6.0)      # same kind, right away: one undo step (a slider drag)
    doc.set_coloring(gamma=3.0)           # different kind: a new step
    assert doc.can_undo and states[-1] == (True, False) and len(doc._undo) == 2
    assert doc.undo() and doc.flame.coloring.gamma == 4.0 and doc.flame.coloring.brightness == 6.0 and restored == [1]
    assert doc.undo() and doc.flame.coloring.brightness == 4.0 and not doc.can_undo and doc.can_redo
    assert doc.redo() and doc.flame.coloring.brightness == 6.0 and doc.redo() and doc.flame.coloring.gamma == 3.0 and not doc.can_redo
    FD.UNDO_COALESCE_SECONDS, saved = 0.0, FD.UNDO_COALESCE_SECONDS
    try:
        doc.set_view(zoom=1.0)
        doc.set_view(zoom=2.0)
        assert len(doc._undo) == 4      # no coalescing when the window is zero
    finally:
        FD.UNDO_COALESCE_SECONDS = saved
    doc.set_curve("red", [(0, 0), (0.5, 0.7), (1, 1)])
    assert not doc.flame.coloring.curves.is_default("red")
    doc.reset_curves("red")
    assert doc.flame.coloring.curves.is_default() and doc.undo() and not doc.flame.coloring.curves.is_default("red")
    other = sierpinski()
    other.name = "pasted"
    other.coloring.brightness = 9.0
    doc.paste(other)
    assert doc.flame.name == "pasted" and doc.modified and doc.can_undo and doc.undo() and doc.flame.name == "s"
    doc.replace(sierpinski())
    assert not doc.can_undo and not doc.can_redo and states[-1] == (False, False)


def test_pan_units_and_modifier_steps(qapp):
    from PySide6.QtCore import Qt
    from fractalchemy.ui.image_panel import PAN_STEP, PAN_STEP_COARSE, PAN_STEP_FINE

    doc = FractalDocument()
    doc.replace(sierpinski())
    doc.pan_units(0.1, 0.0)
    assert doc.flame.camera.center == pytest.approx((0.6, 0.25))
    doc.pan_units(0.0, -1.0)
    assert doc.flame.camera.center == pytest.approx((0.6, -0.75))          # screen "up" is −y
    doc.set_view(center=(0.0, 0.0), rotate=90.0)
    doc.pan_units(1.0, 0.0)
    assert abs(doc.flame.camera.center[0]) < 1e-9 and abs(abs(doc.flame.camera.center[1]) - 1.0) < 1e-9
    assert ImagePanel.pan_step(Qt.KeyboardModifier.NoModifier) == PAN_STEP == 0.1
    assert ImagePanel.pan_step(Qt.KeyboardModifier.ShiftModifier) == PAN_STEP_COARSE == 1.0
    assert ImagePanel.pan_step(Qt.KeyboardModifier.ControlModifier) == PAN_STEP_FINE == 0.01


def test_panel_contrast_pitch_and_curves_edit_the_document(bound):
    from fractalchemy.fractal.curves import DEFAULT_POINTS
    doc, panel = bound
    doc.replace(sierpinski())
    panel.contrast.spin.setValue(1.5)
    assert doc.flame.coloring.contrast == 1.5
    panel.pitch.spin.setValue(-25.0)
    assert doc.flame.camera.pitch == pytest.approx(math.radians(-25)) and panel.flat_note.text() == "3D camera active."
    assert not hasattr(panel, "pitch_y")                   # Fractalchemy's extra Y pitch is not offered in the panel
    assert panel.pitch.label.text() == "Pitch" and panel.yaw.label.text() == "Yaw"
    editor = panel.curves
    editor.select("green")
    editor.canvas._commit([(0, 0), (0.5, 0.9), (1, 1)])
    assert doc.flame.coloring.curves.points["green"] == [(0.0, 0.0), (0.5, 0.9), (1.0, 1.0)]
    assert editor.buttons["green"].text().endswith("•") and editor.buttons["red"].text() == "R"
    editor.reset_button.click()
    assert doc.flame.coloring.curves.is_default("green") and editor.buttons["green"].text() == "G"
    editor.canvas._commit([(0, 0), (0.5, 0.9), (1, 1)])
    editor.select("overall")
    editor.canvas._commit([(0, 0.2), (1, 1)])
    editor.reset_all_button.click()
    assert doc.flame.coloring.curves.is_default()
    doc.undo()
    assert doc.flame.coloring.curves.points["overall"] == [(0.0, 0.2), (1.0, 1.0)] and editor.curves().points["overall"] == [(0.0, 0.2), (1.0, 1.0)]
    panel.revert_coloring.click()
    assert doc.flame.coloring.curves.is_default() and doc.flame.coloring.contrast == 1.0 and editor.curves().points["green"] == DEFAULT_POINTS


def test_curve_canvas_mouse_adds_moves_and_removes_points(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QMouseEvent
    from fractalchemy.widgets.curve_editor import CurveCanvas

    canvas = CurveCanvas()
    canvas.resize(200, 200)
    canvas.show()
    seen = []
    canvas.points_changed.connect(lambda ch, pts: seen.append((ch, pts)))
    centre = canvas._to_screen(0.5, 0.5)

    def press(pos, button=Qt.MouseButton.LeftButton):
        canvas.mousePressEvent(QMouseEvent(QMouseEvent.Type.MouseButtonPress, pos, pos, button, button, Qt.KeyboardModifier.NoModifier))

    press(centre)                                  # click on empty canvas: a new point
    assert len(canvas.points()) == 3 and seen[-1][0] == "overall" and seen[-1][1][1] == pytest.approx((0.5, 0.5), abs=0.02)
    target = canvas._to_screen(0.5, 0.8)
    canvas.mouseMoveEvent(QMouseEvent(QMouseEvent.Type.MouseMove, target, target, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    canvas.mouseReleaseEvent(QMouseEvent(QMouseEvent.Type.MouseButtonRelease, target, target, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
    assert canvas.points()[1] == pytest.approx((0.5, 0.8), abs=0.02)
    press(canvas._to_screen(0.5, 0.8), Qt.MouseButton.RightButton)   # right-click removes it
    assert len(canvas.points()) == 2
    press(canvas._to_screen(0.0, 0.0), Qt.MouseButton.RightButton)   # end points stay
    assert len(canvas.points()) == 2
    canvas.close()


# --- files and clipboard ----------------------------------------------------------------------------------
def test_clipboard_round_trip_and_paste_formats(qapp, samples):
    from fractalchemy.fractal.formats import flame_from_text, flame_to_text
    from fractalchemy.fractal.formats.flame_xml import flame_to_xml

    flame = load_flames(samples / "sample flames" / "candy.flame")[2]
    again = flame_from_text(flame_to_text(flame))
    assert again.name == "rotated" and again.xforms[2].variations == flame.xforms[2].variations and again.palette == flame.palette
    assert flame_from_text(flame_to_xml(flame)).name == "rotated"
    chaos = next(p for p in (samples / "sample flames").iterdir() if p.suffix == ".chaos")
    assert flame_from_text(chaos.read_text()).xforms
    with pytest.raises(ValueError):
        flame_from_text("not parameters at all")


def test_main_window_toolbar_undo_copy_paste_and_save_flows(qapp, tmp_path, samples, monkeypatch):
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.ui.main_window import MainWindow

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda parent, title, text, *a: warnings.append((title, text))))
    library = copy_samples(samples, tmp_path / "lib")
    path = library / "sample flames" / "candy.flame"
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    win = MainWindow(LibraryRoots(settings), LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key), prefer_gpu=False, settings=settings)
    win.show()
    try:
        names = [a.text() for a in win.toolBar.actions() if a.text()]
        assert names == ["Open Fractal…", "Save Fractal", "Save Fractal As", "Undo", "Redo", "Copy Parameters", "Paste Parameters",
                         "Transform Editor", "Gradient Library", "Animation", "Random Batch…", "Script Editor",
                         "Formula Editor", "Render Image…"]
        assert [a.text() for a in win.menuSaveAs.actions()] == ["As New Entry in This File…", "As New File…", "Into Existing File…"]
        assert [a.text() for a in win.menuEdit.actions() if a.text()] == ["Undo", "Redo", "Copy Parameters", "Paste Parameters", "Edit Fractal Library…"]
        assert not win.actionUndo.isEnabled() and not win.actionCopyParameters.isEnabled() and not win.actionSaveFractal.isEnabled()
        win.open_path(path, 2)
        wait_until(lambda: win.document.flame is not None and win.document.flame.name == "rotated")
        assert win.actionSaveFractal.isEnabled() and win.actionSaveAs.isEnabled() and win.actionCopyParameters.isEnabled()
        # an edit: undo / redo through the actions, nothing written by itself
        before = path.read_bytes()
        win.settingsPanel.image.brightness.spin.setValue(12.0)
        assert win.actionUndo.isEnabled() and win.windowTitle().endswith("*")
        win.actionUndo.trigger()
        assert win.document.flame.coloring.brightness == 4.0 and win.actionRedo.isEnabled()
        win.actionRedo.trigger()
        assert win.document.flame.coloring.brightness == 12.0 and path.read_bytes() == before
        # copy → clipboard holds .fa text; paste replaces the parameters (undoable)
        win.actionCopyParameters.trigger()
        text = QGuiApplication.clipboard().text()
        assert text.startswith("{") and '"rotated"' in text
        QGuiApplication.clipboard().setText(text.replace('"rotated"', '"pasted copy"'))
        win.actionPasteParameters.trigger()
        assert win.document.flame.name == "pasted copy" and win.document.flame.coloring.brightness == 12.0
        win.actionUndo.trigger()
        assert win.document.flame.name == "rotated"
        QGuiApplication.clipboard().setText("garbage")
        win.actionPasteParameters.trigger()          # reports, keeps the flame
        assert win.document.flame.name == "rotated" and warnings and warnings[-1][0] == "Cannot paste parameters"
        # Save: overwrite the entry
        win.actionSaveFractal.trigger()
        wait_until(lambda: not win.document.modified)
        assert load_flames(path)[2].coloring.brightness == 12.0 and len(load_flames(path)) == 5
        # Save As ▸ new entry in this file (name prompt)
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("rotated copy", True)))
        win.settingsPanel.image.gamma.spin.setValue(2.0)
        win.actionSaveAsNewEntry.trigger()
        wait_until(lambda: win.document.source_index == 5)
        entries = load_flames(path)
        assert len(entries) == 6 and entries[5].name == "rotated copy" and entries[5].coloring.gamma == 2.0
        assert entries[2].coloring.gamma != 2.0 and win.document.flame.name == "rotated copy" and not win.document.modified
        # Save As ▸ new file (.fa)
        target = tmp_path / "mine.fa"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
        win.actionSaveAsNewFile.trigger()
        wait_until(lambda: win.document.source_path == target)
        assert load_flames(target)[0].name == "rotated copy" and win.document.source_index == 0
        wait_until(lambda: win.fractalLibraryPanel.model.open_file == target)   # a file outside the library: browsable on top
        win.actionSaveAsNewFile.trigger()           # an existing file is appended to, never wiped
        wait_until(lambda: win.document.source_index == 1)
        assert len(load_flames(target)) == 2
        # Save As ▸ into an existing file
        monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(path), "")))
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("into candy", True)))
        win.actionSaveAsIntoFile.trigger()
        wait_until(lambda: win.document.source_path == path and win.document.source_index == 6)
        assert load_flames(path)[6].name == "into candy"
    finally:
        win.gradient_library.document.modified = False
        win.close()


def test_viewer_bar_guides_overlay_rule_of_thirds_golden_ratio_and_centre(qapp, tmp_path):
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.ui.main_window import MainWindow

    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    win = MainWindow(LibraryRoots(settings), LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key), prefer_gpu=False, settings=settings)
    win.show()
    try:
        bar, view = win.viewerBar, win.viewport
        assert not hasattr(bar, "detail_box")                     # the Detail dropdown is gone
        assert not bar.guides_shown and bar.guide_kinds() == ("thirds",) and view.guide_lines() == []
        win.document.replace(sierpinski())
        win.document.set_image_size((600, 300))
        bar.guides_button.setChecked(True)                          # the button toggles the overlay
        assert view.guides_shown and win.actionShowGuides.isChecked()
        lines = view.guide_lines()
        assert len(lines) == 4 and {k for k, *_ in lines} == {"thirds"}
        rect = view.image_rect
        xs = sorted(x1 for _k, x1, _y1, x2, _y2 in lines if x1 == x2)
        assert xs == pytest.approx([rect.left() + rect.width() / 3, rect.left() + 2 * rect.width() / 3], abs=1.5)
        bar.guide_actions["golden"].setChecked(True)
        bar.guide_actions["center"].setChecked(True)
        assert bar.guide_kinds() == ("thirds", "golden", "center") and len(view.guide_lines()) == 10
        golden = sorted(x1 for k, x1, _y1, x2, _y2 in view.guide_lines() if k == "golden" and x1 == x2)
        assert golden[0] == pytest.approx(rect.left() + rect.width() * 0.381966, abs=1.5)
        win.actionShowGuides.trigger()                               # View ▸ Show Guides toggles it too
        assert not bar.guides_shown and not view.guides_shown and view.guide_lines() == []
        bar.guides_button.setChecked(False)
        bar.guide_actions["golden"].setChecked(False)               # ticking a kind while hidden shows the overlay
        bar.guide_actions["golden"].setChecked(True)
        assert bar.guides_shown and view.guides_shown
        assert settings.value("viewer/guides") in (True, "true") and settings.value("viewer/guide_kinds") == "thirds,golden,center"
        again = MainWindow(LibraryRoots(settings), LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key), prefer_gpu=False, settings=settings)
        try:
            assert again.viewerBar.guides_shown and again.viewerBar.guide_kinds() == ("thirds", "golden", "center")
            assert again.viewport.guides_shown and again.actionShowGuides.isChecked()
        finally:
            again.gradient_library.document.modified = False
            again.close()
    finally:
        win.gradient_library.document.modified = False
        win.close()
