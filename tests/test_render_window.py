"""The Render Image window: size linking, format syncing, validation, rendering off the GUI thread, persistence."""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from fractalchemy.render.output import read_embedded_parameters
from fractalchemy.ui.fractal_document import FractalDocument
from fractalchemy.ui.render_output_panel import OutputPanel
from fractalchemy.ui.render_size_panel import SizePanel
from fractalchemy.ui.render_progress import format_rate, format_seconds
from fractalchemy.ui.render_window import RenderWindow
from tests.conftest import open_flame_and_wait, spin, wait_until
from tests.test_render import sierpinski

FLAMES = Path(__file__).resolve().parents[1] / "samples" / "sample flames"


def _quick(window: RenderWindow, path: Path, quality: str = "20", width: int = 48, height: int = 32) -> None:
    """Configure a window for a fast CPU render into `path`."""
    window.size_panel.set_size(width, height)
    q = window.quality_panel
    q.density.setEditText(quality)
    q.oversample.setValue(1)
    q.engine.setCurrentIndex(q.engine.findData("cpu"))
    q.threads.setValue(1)
    window.output_panel.set_path(str(path))


# --- panels ---------------------------------------------------------------------------------------
def test_size_panel_links_aspect_swaps_and_matches_presets(qapp):
    panel = SizePanel()
    panel.set_size(1920, 1080)
    changes = []
    panel.size_changed.connect(lambda w, h: changes.append((w, h)))
    panel.width_box.setValue(960)
    assert panel.size() == (960, 540) and changes[-1] == (960, 540)        # linked: height follows
    panel.link.setChecked(False)
    panel.width_box.setValue(1000)
    assert panel.size() == (1000, 540)                                      # unlinked: independent
    panel.height_box.setValue(500)
    assert panel.size() == (1000, 500)
    panel.link.setChecked(True)                                             # re-linking captures the new ratio
    panel.height_box.setValue(250)
    assert panel.size() == (500, 250)
    panel.swap.click()
    assert panel.size() == (250, 500) and "1 : 2" in panel.aspect.text()
    panel.choose_preset(panel.preset_index((3840, 2160)))
    assert panel.size() == (3840, 2160) and tuple(panel.presets.currentData()) == (3840, 2160)
    panel.set_preview_size(3840, 2160)
    assert panel.presets.currentData() == "preview" and "3840 × 2160" in panel.presets.currentText()
    panel.set_preview_size(800, 600)
    assert panel.size() == (800, 600)                                        # the preview preset follows the viewer


def test_output_panel_keeps_format_and_extension_in_step(qapp, tmp_path):
    panel = OutputPanel()
    panel.set_path(str(tmp_path / "pic.jpg"))
    assert panel.format_box.currentData() == "jpeg" and not panel.transparent.isEnabled() and panel.quality.isEnabled()
    panel.format_box.setCurrentIndex(panel.format_box.findData("tiff"))
    assert panel.path.text().endswith("pic.tif") and panel.depth.isEnabled() and panel.transparent.isEnabled()
    panel.set_path(str(tmp_path / "noext"))
    assert panel.path.text().endswith("noext.tif")
    panel.format_box.setCurrentIndex(panel.format_box.findData("webp"))
    assert panel.lossless.isEnabled()
    panel.lossless.setChecked(True)
    assert not panel.quality.isEnabled()
    assert not panel.save_details.isChecked() and not panel.details_format.isEnabled()     # off by default
    panel.save_details.setChecked(True)
    assert panel.details_format.isEnabled() and panel.details_format.currentData() == "md"


def test_time_and_rate_formatting():
    assert format_seconds(None) == "—" and format_seconds(42) == "42 s" and format_seconds(187) == "3 min 07 s"
    assert format_seconds(8100) == "2 h 15 min" and format_seconds(3 * 86400) == "3 d 0 h"
    assert format_rate(2.5e6) == "2.5 M samples/s" and format_rate(1.2e9) == "1.20 G samples/s"


# --- window -----------------------------------------------------------------------------------------
@pytest.fixture
def render_window(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "render.ini"), QSettings.Format.IniFormat)
    document = FractalDocument()
    window = RenderWindow(document, settings=settings)
    yield window, document, settings
    if window.job is not None:
        window.job.cancel()
        window.wait_for_job()
    window.close()


def test_start_is_blocked_until_the_settings_are_valid(render_window, tmp_path):
    window, document, _ = render_window
    window.output_panel.path.clear()
    window.output_panel.path.editingFinished.emit()
    assert not window.start_button.isEnabled() and "No fractal" in window.start_button.toolTip()
    document.replace(sierpinski())
    assert window.windowTitle().endswith("sierpinski") and window.output_panel.path.text().endswith("sierpinski.png")
    assert window.start_button.isEnabled()
    window.output_panel.format_box.setCurrentIndex(window.output_panel.format_box.findData("webp"))
    window.size_panel.set_size(20000, 100)
    assert not window.start_button.isEnabled() and "WebP" in window.plan_label.text()
    window.size_panel.set_size(200, 100)
    assert window.start_button.isEnabled() and "One tile" in window.plan_label.text()


def test_window_renders_in_the_background_and_keeps_its_snapshot(render_window, tmp_path):
    window, document, _ = render_window
    document.replace(sierpinski())
    out = tmp_path / "gasket.png"
    _quick(window, out)
    window.output_panel.save_details.setChecked(True)
    window.start(ask_overwrite=False)
    assert window.rendering and not window.start_button.isEnabled() and window.stop_button.isEnabled()
    assert not window.size_panel.isEnabled()
    other = sierpinski()
    other.name = "changed-later"
    document.replace(other)                                   # editing / loading meanwhile must not leak in
    wait_until(lambda: not window.rendering, timeout_ms=60000)
    spin(50)
    assert window.last_outcome is not None and window.last_outcome.path == out and out.exists()
    assert window.last_outcome.report == out.with_suffix(".md") and "## Transforms" in out.with_suffix(".md").read_text()
    assert "gasket.md" in window.progress_panel.result.text()
    assert 'name="sierpinski"' in read_embedded_parameters(out)
    assert window.windowTitle().endswith("changed-later") and window.output_panel.path.text().endswith("changed-later.png")
    assert "Finished" in window.progress_panel.result.text() and window.start_button.isEnabled()
    assert window.progress_panel.phase.text() == "Finished" and window.progress_panel.bar.value() == window.progress_panel.bar.maximum()
    assert "≈" in window.progress_panel.remaining.text() or "measured" in window.estimate_label.text()


def test_pause_resume_and_stop_keep_a_partial_render(render_window, tmp_path):
    window, document, _ = render_window
    document.replace(sierpinski())
    out = tmp_path / "partial.png"
    _quick(window, out, quality="80", width=320, height=240)
    window.quality_panel.memory.setValue(1)                    # four tiles, so stopping leaves some finished
    window.start(ask_overwrite=False)
    wait_until(lambda: window.progress_panel.elapsed.text() != "—", timeout_ms=20000)
    window.toggle_pause()
    assert window.job.paused and window.pause_button.text() == "Resume" and "(paused)" in window.progress_panel.phase.text()
    spin(200)
    window.toggle_pause()
    assert not window.job.paused and window.pause_button.text() == "Pause"
    wait_until(lambda: window.progress_panel.tiles.text().startswith("2 of"), timeout_ms=60000)
    window.stop()
    wait_until(lambda: not window.rendering, timeout_ms=60000)
    spin(50)
    assert window.last_outcome is not None and not window.last_outcome.result.complete
    assert out.exists() and "Stopped early" in window.progress_panel.result.text()


def test_settings_persist_between_windows(render_window, tmp_path):
    window, document, settings = render_window
    window.quality_panel.density.setEditText("777")
    window.quality_panel.filter_box.setCurrentIndex(window.quality_panel.filter_box.findData("mitchell"))
    window.output_panel.depth.setCurrentIndex(1)
    window.output_panel.save_details.setChecked(True)
    window.output_panel.details_format.setCurrentIndex(window.output_panel.details_format.findData("html"))
    again = RenderWindow(FractalDocument(), settings=settings)
    assert again.current_settings().save_details and again.current_settings().details_format == "html"
    assert again.current_settings().quality == 777 and again.current_settings().filter_kind == "mitchell"
    assert again.current_settings().depth == 16 and again.quality_panel.radius.value() == 1.0   # Mitchell's own radius
    again.close()


# --- main window integration --------------------------------------------------------------------------
def test_main_window_action_opens_the_render_window_following_the_viewer(main_window_factory):
    win = main_window_factory(cheap_renders=True)
    open_flame_and_wait(win, FLAMES / "candy.flame")
    assert not win.render_window.isVisible()
    win.actionRenderImage.trigger()
    assert win.render_window.isVisible() and win.render_window.windowTitle().endswith(win.document.flame.name)
    assert win.render_window.size_panel.presets.itemText(0).endswith(f"{win.document.image_size[0]} × {win.document.image_size[1]}")
    win.document.set_image_size((640, 400))
    assert "640 × 400" in win.render_window.size_panel.presets.itemText(0)
    win.render_window.close()
    assert not win.render_window.isVisible()                    # hidden, not destroyed
    assert win.render_window.confirm_quit()
    assert win.toolBar.actions()[-1] is win.actionRenderImage
