"""Viewer controls: view zoom/pan, composition (Ctrl) pan/zoom, output resolution, render settings, status bar."""

import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF, QSettings, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest

from fractalchemy.fractal import Camera
from fractalchemy.fractal.formats import load_flame
from fractalchemy.ui.fractal_viewport import MAX_ZOOM
from fractalchemy.ui.settings_panel import PASSES_KEY, QUALITY_KEY
from fractalchemy.ui.viewer_bar import RESOLUTIONS
from tests.conftest import spin


@pytest.fixture
def window(main_window_factory, samples):
    win = main_window_factory(size=(1000, 640))
    spin(50)
    win.show_flame(load_flame(samples / "sample flames" / "candy.flame", 0))   # 3840×2160
    spin(50)
    return win


def wheel(widget, pos: QPointF, notches: float, modifiers=Qt.KeyboardModifier.NoModifier) -> None:
    event = QWheelEvent(pos, widget.mapToGlobal(pos.toPoint()).toPointF(), QPoint(), QPoint(0, int(notches * 120)),
                        Qt.MouseButton.NoButton, modifiers, Qt.ScrollPhase.NoScrollPhase, False)
    widget.wheelEvent(event)


# --- camera model -----------------------------------------------------------------
def test_camera_at_size_keeps_the_framing_across_the_width():
    camera = Camera(center=(0.1, 0.2), scale=100, zoom=1, rotate=15, width=400, height=300)
    square = camera.at_size(800, 800)
    assert square.pixels_per_unit(800, 800) == pytest.approx(400)   # 2^zoom · 800/400 · 100
    assert square.zoom == 0 and square.rotate == 15 and square.center == camera.center
    same = camera.at_size(400, 300)
    assert same.pixels_per_unit(400, 300) == pytest.approx(camera.pixels_per_unit(400, 300))


# --- view zoom / pan (the fractal is untouched) ----------------------------------------
def test_fit_is_the_default_and_zoom_is_clamped_between_fit_and_300_percent(window):
    view = window.viewport
    camera_before = window.document.flame.camera.copy()
    assert view.is_fit and view.image_rect.width() <= view.width()
    fit = view.fit_zoom()
    assert fit < 1.0 and window.viewerBar.zoom_box.currentText() == f"{fit * 100:.0f} %"
    view.set_zoom(10.0)
    assert view.zoom() == MAX_ZOOM and window.viewerBar.zoom_box.currentText() == "300 %"
    view.set_zoom(0.01)
    assert view.zoom() == pytest.approx(fit)                    # zooming out stops once the whole image is visible
    assert window.document.flame.camera == camera_before        # view zoom never changes the fractal


def test_wheel_zooms_the_view_about_the_cursor_and_drag_pans(window):
    view = window.viewport
    view.set_zoom(1.0)
    pos = QPointF(view.width() * 0.3, view.height() * 0.4)
    image_point = view.screen_to_image(pos)
    wheel(view, pos, 2)
    assert view.zoom() == pytest.approx(1.25 ** 2)
    assert view.screen_to_image(pos).x() == pytest.approx(image_point.x(), abs=1e-6)
    before = view.screen_to_image(QPointF(0, 0))
    QTest.mousePress(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(300, 200))
    QTest.mouseMove(view, QPoint(340, 230))
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(340, 230))
    after = view.screen_to_image(QPointF(0, 0))
    assert after.x() == pytest.approx(before.x() - 40 / view.zoom(), abs=1e-6)
    assert after.y() == pytest.approx(before.y() - 30 / view.zoom(), abs=1e-6)
    assert window.document.flame.camera.zoom == -0.544          # composition untouched


def test_panning_cannot_push_the_image_off_screen(window):
    view = window.viewport
    view.set_zoom(1.0)
    view.pan_view(QPoint(100000, -100000))
    rect = view.image_rect
    assert rect.x() == 0 and rect.width() == view.width()        # image still covers the widget
    assert rect.y() == 0 and rect.height() == view.height()
    view.zoom_to_fit()
    assert view.is_fit and view.image_rect.center().x() == pytest.approx(view.width() / 2, abs=1)


def test_zoom_box_accepts_typed_values_and_presets(window):
    bar, view = window.viewerBar, window.viewport
    bar.zoom_box.setEditText("150")
    bar.zoom_box.lineEdit().editingFinished.emit()
    assert view.zoom() == pytest.approx(1.5)
    bar.zoom_box.setEditText("999 %")
    bar.zoom_box.lineEdit().editingFinished.emit()
    assert view.zoom() == MAX_ZOOM
    bar.zoom_box.setCurrentIndex(0)
    bar.zoom_box.activated.emit(0)                               # "Fit"
    assert view.is_fit
    window.actionZoomActual.trigger()
    assert view.zoom() == 1.0
    window.actionZoomFit.trigger()
    assert view.is_fit


# --- composition (Ctrl) ---------------------------------------------------------------
def test_ctrl_wheel_and_ctrl_drag_change_the_composition(window):
    view = window.viewport
    camera = window.document.flame.camera
    pos = QPointF(view.image_rect.center())
    anchor = view.fractal_point_at(pos)
    wheel(view, pos, 1, Qt.KeyboardModifier.ControlModifier)
    assert camera.zoom == pytest.approx(-0.544 + 0.25)
    assert view.fractal_point_at(pos) == pytest.approx(anchor, abs=1e-9)
    assert view.is_fit                                           # the view itself did not zoom
    start, end = QPoint(400, 300), QPoint(460, 300)
    expected = view.fractal_point_at(QPointF(start))
    QTest.mousePress(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, start)
    QTest.mouseMove(view, end)
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, end)
    assert view.fractal_point_at(QPointF(end)) == pytest.approx(expected, abs=1e-9)   # the point followed the mouse
    assert camera.center != (0.0, 0.0)


# --- resolution ---------------------------------------------------------------------------
def test_resolution_dropdown_changes_the_image_aspect_not_the_window(window):
    view, bar = window.viewport, window.viewerBar
    size_before = window.size()
    assert window.document.image_size == (3840, 2160) and "3840 × 2160" in bar.resolution_box.itemText(0)
    bar.select_resolution((1080, 1080))
    assert bar.resolution_box.currentText().startswith("1:1") and window.document.image_size == (1080, 1080)
    assert abs(view.image_rect.width() - view.image_rect.height()) <= 1
    assert window.size() == size_before and view.is_fit
    assert view.image_camera().pixels_per_unit(1080, 1080) == pytest.approx(960 * 2 ** -0.544 * 1080 / 3840)
    bar.select_resolution((700, 500))                            # not a preset → Custom
    assert bar.resolution_box.currentData() == "custom" and bar.width_box.isVisible() and bar.width_box.value() == 700
    bar.height_box.setValue(350)
    assert window.document.image_size == (700, 350)
    bar.select_resolution(None)
    assert window.document.image_size == (3840, 2160) and not bar.width_box.isVisible()
    assert len(RESOLUTIONS) >= 12 and any("Print" in r[0] for r in RESOLUTIONS)


def test_zooming_in_renders_only_the_visible_region(window):
    view = window.viewport
    view.set_zoom(2.0, QPointF(view.width() / 2, view.height() / 2))
    camera, width, height = view.render_camera()
    assert (width, height) == (view.width(), view.height())
    image = view.image_camera()
    assert camera.pixels_per_unit(width, height) == pytest.approx(image.pixels_per_unit(image.width, image.height) * 2.0)
    centre = view.fractal_point_at(QPointF(view.width() / 2, view.height() / 2))
    assert camera.center == pytest.approx(centre)


# --- settings panel ---------------------------------------------------------------------------
def test_settings_panel_controls_passes_and_quality_and_persists(window, tmp_path):
    panel, view = window.settingsPanel, window.viewport
    assert panel.passes == view.settings.passes == 6 and panel.quality == view.settings.quality == 8.0
    generation = view.generation
    panel.set_values(3, 20.0)
    assert view.settings.passes == 3 and view.settings.quality == 20.0 and view.generation == generation + 1
    stored = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    assert int(stored.value(PASSES_KEY)) == 3 and float(stored.value(QUALITY_KEY)) == 20.0
    assert [a.text() for a in window.menuView.actions()][:4] == [
        "Show/Hide Fractal Library", "Refresh Fractal Library", "Thumbnails in Fractal Library", "Show/Hide Settings Panel"]


def test_settings_panel_collapses_like_the_library(window):
    assert window.splitter.has_last_pane() and not window.splitter.is_last_collapsed()
    window.actionToggleSettings.setChecked(False)
    assert window.splitter.is_last_collapsed() and window.splitter.sizes()[-1] == 0
    assert not window.splitter.is_collapsed()
    window.splitter.toggle_last()
    assert not window.splitter.is_last_collapsed() and window.actionToggleSettings.isChecked()


# --- status bar -------------------------------------------------------------------------------
def test_status_bar_widgets_never_overlap(window):
    status = window.status
    from fractalchemy.render.settings import RenderStats
    status.set_engine("GPU (NVIDIA GeForce RTX 4090/PCIe/SSE2)")
    status.show_progress(RenderStats("GPU (NVIDIA GeForce RTX 4090/PCIe/SSE2)", 3, 6, 123_456_789, 0, 2.5, 1920, 1080))
    spin(50)
    widgets = [status.fractal, status.render, status.passes, status.progress]
    rects = [w.geometry() for w in widgets]
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert not a.intersects(b), (a, b)
    assert rects[0].right() < rects[1].left() < rects[2].left() < rects[3].left()
    assert status.render.text().startswith("GPU  ·  1920×1080") and "Pass 3 of 6" in status.passes.text()
    assert status.render.width() >= status.render.fontMetrics().horizontalAdvance(status.render.text())
    assert status.progress.geometry().right() <= window.statusBar().width()


# --- ViewGeometry (no window needed) ---------------------------------------------------------------
def test_view_geometry_fits_centres_and_clamps():
    from fractalchemy.ui.view_geometry import ViewGeometry

    view = ViewGeometry(image_size=(400, 300), widget_size=(200, 200))
    assert view.is_fit and view.fit_zoom() == 0.5 and view.image_rect.width() == 200 and view.image_rect.y() == 25  # 150 tall, centred
    view.set_zoom(1.0, QPointF(0, 0))                    # image pixel (0, 0) was at the top-left corner of the rect
    assert view.zoom() == 1.0 and view.image_rect.width() == 200 and not view.is_fit
    view.pan(QPointF(10_000, 10_000))                    # cannot drag the image away from the widget
    assert view.offset == QPointF(0, 0)
    view.pan(QPointF(-10_000, -10_000))
    assert view.offset == QPointF(-200, -100)            # right/bottom edges of the image stay at the widget's edges
    view.set_zoom(0.01)
    assert view.zoom() == view.fit_zoom()
    view.set_zoom(99)
    assert view.zoom() == MAX_ZOOM
    view.set_image_size((50, 50))
    assert view.is_fit and view.fit_zoom() == MAX_ZOOM and view.image_rect.width() == 150   # tiny images: never past 300 %
    view.set_widget_size(0, 0)
    assert view.widget_size == (1, 1) and view.fit_zoom() > 0


def test_view_geometry_maps_screen_image_and_regions_consistently():
    from fractalchemy.ui.view_geometry import ViewGeometry

    view = ViewGeometry(image_size=(1000, 500), widget_size=(300, 200))
    view.set_zoom(2.0, QPointF(150, 100))
    for pos in (QPointF(0, 0), QPointF(150, 100), QPointF(299, 199)):
        image = view.screen_to_image(pos)
        back = view.image_to_screen(QRectF(image.x(), image.y(), 1, 1))
        assert back.x() == pytest.approx(pos.x()) and back.y() == pytest.approx(pos.y())
    region = view.visible_region()
    assert region.width() == pytest.approx(150) and region.height() == pytest.approx(100)
    assert view.image_to_screen(region).toAlignedRect() == view.image_rect


def test_zoom_box_ignores_garbage_and_keeps_the_current_value(window):
    bar, view = window.viewerBar, window.viewport
    view.set_zoom(1.5)
    for text in ("abc", "", "%", "fit "):
        bar.zoom_box.setEditText(text)
        bar.zoom_box.lineEdit().editingFinished.emit()
        if text.strip() == "fit":
            assert view.is_fit
        else:
            assert view.zoom() == pytest.approx(1.5) and bar.zoom_box.currentText() == "150 %"
        view.set_zoom(1.5)
    bar.zoom_box.setEditText("-50")
    bar.zoom_box.lineEdit().editingFinished.emit()
    assert view.zoom() == pytest.approx(view.fit_zoom())            # negative → clamped to the minimum
