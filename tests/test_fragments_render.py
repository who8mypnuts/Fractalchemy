"""Hi-res / animation rendering: settings, tiles, the renderer, files, the job thread, the window, the batch API and the CLI."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QSettings

from fractalchemy.fragments import batch
from fractalchemy.fragments.animation import AnimationSettings
from fractalchemy.fragments.examples import EXAMPLES_DIR
from fractalchemy.fragments.files import FileManager
from fractalchemy.fragments.gl.engine import FragEngine
from fractalchemy.fragments.gl.final import FragFinalRenderer, FrameImage, to_display_rgba8, write_frame
from fractalchemy.fragments.gl.job import FragRequest
from fractalchemy.fragments.glsl_compat import CompatOptions, modernise
from fractalchemy.fragments.preprocessor import Preprocessor
from fractalchemy.fragments.render_settings import FragFinalSettings
from fractalchemy.fragments.state import ParameterState
from fractalchemy.fragments.templates import NEW_3D
from fractalchemy.render.exr import read_exr_attributes
from fractalchemy.render.final_engine import PHASE_CANCELLED
from fractalchemy.render.output import read_embedded_parameters
from fractalchemy.solid.hdri import read_exr
from fractalchemy.ui.fragments import FragmentsWindow

from .conftest import wait_until

MANDELBULB = EXAMPLES_DIR / "Historical 3D Fractals" / "Mandelbulb.frag"


@pytest.fixture(scope="module")
def engine(_shared_gl_context):
    with _shared_gl_context:
        engine = FragEngine(_shared_gl_context)
        yield engine
        engine.close()


def prepared(engine: FragEngine, text: str = NEW_3D):
    source = Preprocessor(FileManager()).parse(text, None)
    options = CompatOptions("modernise", engine.capabilities.glsl_version, engine.capabilities.has_fp64)
    state = ParameterState(source.all_params)
    state.apply_settings(source.presets["Default"])
    request = FragRequest(modernise(source, options), modernise(source.buffer_shader, options) if source.buffer_shader else None,
                          dict(state.values), source.buffer, source.clear_on_change, source.subframes_between_redraws, source.depth_to_alpha)
    return source, request, state


def test_settings_geometry_names_and_problems(tmp_path):
    s = FragFinalSettings(tile_width=100, tile_height=50, tiles=2, padding=0.25, subframes=10, output_path=str(tmp_path / "a.png"))
    assert s.inner_tile == (80, 40) and s.image_size == (160, 80) and s.tile_count == 4 and s.total_steps(250) == 40
    assert s.frames(250) == [0] and s.with_(animation=True, start_frame=5, end_frame=300).frames(250) == list(range(5, 251))
    assert s.frame_path(12, 250).name == "a.png" and s.with_(animation=True).frame_path(12, 250).name == "a.00012.png"
    assert s.with_(animation=True).frame_pattern(250).endswith("a.%05d.png") and s.files_folder().name == "a Files"
    assert s.unique(Path("x.png")).name.startswith("x-") and s.problems() == []
    assert "too large" in s.with_(tile_width=4096, tiles=32).problems()[0]
    assert s.with_(tile_width=4096, tiles=32, output_format="exr").problems() == []              # EXR is exempt from the size limit
    assert "choose an output file" in s.with_(output_path="").problems()[0]
    assert FragFinalSettings.from_dict(s.to_dict()) == s and "2 × 2 tiles" in s.describe_plan(250)
    command = s.with_(animation=True, video=True).ffmpeg_command(25, 250, 0, executable="ffmpeg")
    assert command[0] == "ffmpeg" and "-framerate" in command and command[-1].endswith("a.mp4") and "libx264" in command
    assert "unique file names" in " ".join(s.with_(video=True, unique_name=True, output_format="png").video_problems())


def test_renderer_assembles_tiles_like_a_single_render(engine):
    with engine.ctx:
        _source, request, state = prepared(engine)
        single = FragFinalSettings(tile_width=64, tile_height=64, tiles=1, subframes=1, output_path="x.png")
        padded = FragFinalSettings(tile_width=64, tile_height=64, tiles=2, padding=1.0, subframes=1, output_path="x.png")   # inner 32 × 2 = 64
        frames = []
        for settings in (single, padded):
            renderer = FragFinalRenderer(engine, request, state, settings, AnimationSettings(), None, [], False)
            result = renderer.run(frame_done=frames.append)
            assert result.complete and result.frames_rendered == 1
        assert frames[0].rgba.shape == frames[1].rgba.shape == (64, 64, 4)
        assert np.abs(frames[0].rgba - frames[1].rgba).mean() < 0.02          # the dither differs per pixel, the picture does not
        depth_settings = single.with_(depth_to_alpha=True, tiles=2, tile_width=32, tile_height=32)
        frames.clear()
        FragFinalRenderer(engine, request, state, depth_settings, AnimationSettings(), None, [], False).run(frame_done=frames.append)
        assert frames[0].depth is not None and frames[0].depth.shape == (64, 64) and frames[0].depth.min() < 1.0
        reports = []
        cancelled = FragFinalRenderer(engine, request, state, single.with_(subframes=5), AnimationSettings(), None, [], False)
        cancelled.control.cancel()
        assert not cancelled.run(progress=reports.append).complete and reports[-1].phase == PHASE_CANCELLED


def test_write_frame_formats(tmp_path, engine):
    image = FrameImage(0, np.random.default_rng(1).random((8, 12, 4)).astype(np.float32), np.full((8, 12), 0.25, dtype=np.float32))
    png = write_frame(image, tmp_path / "f.png", FragFinalSettings(output_format="png", depth=16), "FOV = 0.4")
    assert png.is_file() and read_embedded_parameters(png, "frAg") == "FOV = 0.4"
    exr = write_frame(image, tmp_path / "f.exr", FragFinalSettings(output_format="exr", depth=32, depth_to_alpha=True), "FOV = 0.4")
    data = read_exr(exr)
    assert data.shape == (8, 12, 3) and np.allclose(data, image.rgba[..., :3], atol=1e-6)
    assert read_exr_attributes(exr).get("frAg") == "FOV = 0.4"
    plain = write_frame(FrameImage(0, image.rgba, None), tmp_path / "g.exr", FragFinalSettings(output_format="exr", depth=16), "")
    assert plain.is_file()
    small = to_display_rgba8(FrameImage(0, np.zeros((2000, 3000, 4), dtype=np.float32)), max_side=1000)
    assert small.shape == (667, 1000, 4) and small.dtype == np.uint8


def test_batch_api_prepare_check_render(engine, tmp_path):
    with engine.ctx:
        ready = batch.prepare(MANDELBULB, engine, "Octobulb")
        assert ready.state.get("Power") == 8.18304 and ready.request.buffer_modern is not None
        with pytest.raises(batch.BatchError):
            batch.prepare(MANDELBULB, engine, "Nope")
        assert batch.check(MANDELBULB, engine) == []
        settings = FragFinalSettings(tile_width=32, tile_height=24, tiles=1, subframes=1, output_path=str(tmp_path / "b.png"))
        result = batch.render(MANDELBULB, settings, engine)
        assert result.complete and result.paths == [tmp_path / "b.png"] and (tmp_path / "b.png").is_file()
        written = batch.render_presets(MANDELBULB, settings, engine, tmp_path / "presets")
        assert sorted(p.name for p in written) == ["Mandelbulb-Default.png", "Mandelbulb-Octobulb.png"]
        animated = batch.render(MANDELBULB, settings.with_(animation=True, start_frame=3, end_frame=4, output_path=str(tmp_path / "anim.png")),
                                engine, animation=AnimationSettings(fps=10, length=1))
        assert [p.name for p in animated.paths] == ["anim.00003.png", "anim.00004.png"]


def test_cli_renders_and_checks(tmp_path):
    root = Path(__file__).resolve().parents[1]
    run = subprocess.run([sys.executable, str(root / "tools" / "render_frag.py"), str(MANDELBULB), "--out", str(tmp_path / "cli.png"),
                          "--size", "48x32", "--subframes", "1", "--quiet"], capture_output=True, text=True, timeout=240)
    assert run.returncode == 0, run.stderr
    assert (tmp_path / "cli.png").is_file()
    broken = tmp_path / "broken.frag"
    broken.write_text("void main() { gl_FragColor = vec4(1.0) +; }\n")
    run = subprocess.run([sys.executable, str(root / "tools" / "render_frag.py"), "--check", str(MANDELBULB), str(broken)],
                         capture_output=True, text=True, timeout=240)
    assert run.returncode == 1 and "FAIL" in run.stdout and "ok" in run.stdout


@pytest.fixture
def window(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "fragments.ini"), QSettings.Format.IniFormat)
    win = FragmentsWindow(None, settings)
    win.resize(1000, 640)
    win.show()
    wait_until(lambda: win._capabilities is not None, 30000)
    yield win
    for tab in win.tabs.tabs:
        tab.document._modified = False
    win.shutdown()
    win.close()


def test_render_window_renders_a_tiled_image_with_extras(window, tmp_path):
    window.open_path(MANDELBULB)
    document = window.tabs.document
    wait_until(lambda: window.viewport.image is not None, 60000)
    window.show_render_window()
    rw = window.render_window
    assert rw.isVisible() and rw.windowTitle().endswith("Mandelbulb")
    rw.tiles_panel.set_tile_size(48, 32)
    rw.tiles_panel.tiles_slider.setValue(2)
    rw.quality_panel.subframes_spin.setValue(2)
    rw.output_panel.set_path(str(tmp_path / "hires.png"))
    rw.output_panel._on_path_edited()
    rw.output_panel.params_check.setChecked(True)
    rw.output_panel.fragment_check.setChecked(True)
    rw.output_panel.includes_check.setChecked(True)
    rw.output_panel.report_check.setChecked(True)
    rw.output_panel.report_combo.setCurrentIndex(rw.output_panel.report_combo.findData("html"))
    assert rw.start_button.isEnabled() and "2 × 2 tiles" in rw.plan_label.text() and rw.estimate_label.text().startswith("Estimated")
    rw.start(ask_overwrite=False)
    assert rw.rendering
    wait_until(lambda: not rw.rendering, 180000)
    outcome = rw.last_outcome
    assert outcome is not None and outcome.path == tmp_path / "hires.png" and outcome.sidecar.is_file() and outcome.report.is_file()
    assert (tmp_path / "hires Files" / "DE-Raytracer.frag").is_file()
    from PIL import Image
    with Image.open(outcome.path) as image:
        assert image.size == (96, 64) and "frAg" in image.info
    assert "#preset Default" in outcome.report.read_text() and document.metadata.render["tiles"] == 2
    assert outcome.details == tmp_path / "hires.html" and "Per tile" in outcome.details.read_text() and "Power" in outcome.details.read_text()
    assert "Saved" in rw.progress_panel.result.text()
    # the settings persisted
    assert "hires.png" in window._settings.value("fragments/render_settings")


def test_render_window_animation_frames(window, tmp_path):
    window.open_text(NEW_3D)
    wait_until(lambda: window.viewport.image is not None, 60000)
    window.anim.apply_settings(AnimationSettings(fps=5, length=1))
    window.show_render_window()
    rw = window.render_window
    rw.tiles_panel.set_tile_size(32, 24)
    rw.tiles_panel.tiles_slider.setValue(1)
    rw.quality_panel.subframes_spin.setValue(1)
    rw.animation_panel.setChecked(True)
    rw.animation_panel.start_spin.setValue(1)
    rw.animation_panel.end_spin.setValue(2)
    rw.output_panel.set_path(str(tmp_path / "anim.png"))
    rw.output_panel._on_path_edited()
    rw.output_panel.fragment_check.setChecked(False)
    rw.output_panel.params_check.setChecked(False)
    rw.start(ask_overwrite=False)
    wait_until(lambda: not rw.rendering, 180000)
    assert sorted(p.name for p in rw.last_outcome.frames) == ["anim.00001.png", "anim.00002.png"]
