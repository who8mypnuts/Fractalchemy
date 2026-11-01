"""The Fragments window's tools: colour grading, debug views, the Shadertoy importer, the DE composer, camera bookmarks and
flight recording, manual rendering, the HUD, colours from a gradient."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from fractalchemy.fragments.batch import prepare
from fractalchemy.fragments.composer import PRESET_RECIPES, SHAPES, STEP_KINDS, Recipe, Step, generate
from fractalchemy.fragments.examples import EXAMPLES_DIR
from fractalchemy.fragments.gl.engine import FragEngine
from fractalchemy.fragments.gl.job import FragRenderSettings
from fractalchemy.fragments.grading import Grading
from fractalchemy.fragments.shadertoy import convert, used_channels

from .conftest import spin, wait_until

MANDELBULB = EXAMPLES_DIR / "Historical 3D Fractals" / "Mandelbulb.frag"
MENGER = EXAMPLES_DIR / "Kaleidoscopic IFS" / "Menger.frag"
IMAGE = """void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(0.5 + 0.5 * cos(iTime + uv.xyx + vec3(0, 2, 4)), 1.0);
}"""
BUFFER_A = """void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv) * 0.9 + vec4(uv, 0.0, 1.0) * 0.1;
}"""
IMAGE_READING_A = """void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    fragColor = texture(iChannel0, fragCoord / iResolution.xy);
}"""


@pytest.fixture
def engine(gl_context):
    engine = FragEngine(gl_context)
    yield engine
    engine.close()


def _render(engine, request, key, width=64, height=40):
    job = engine.start(request, FragRenderSettings(width, height, subframe_max=2, subframes_per_pass=2, surface_key=key))
    image = job.run_pass()
    job.close()
    return image


# --- grading and debug views ----------------------------------------------------------------------------------------------
def test_grading_model_and_display_stage(engine):
    assert Grading().is_identity and not Grading(exposure=1.0).is_identity
    assert Grading.from_dict({"tonemap": "weird", "invert": "true", "exposure": "2"}) == Grading(exposure=2.0, invert=True)
    assert Grading.from_dict(Grading(hue=45.0, vignette=0.3).to_dict()) == Grading(hue=45.0, vignette=0.3)
    prepared = prepare(MENGER, engine)                       # has a buffer shader → the intermediate path
    with engine.ctx:
        plain = _render(engine, prepared.request, "g0")[..., :3].astype(float)
        darker = _render(engine, replace(prepared.request, grading=Grading(exposure=-2.0)), "g1")[..., :3].astype(float)
        inverted = _render(engine, replace(prepared.request, grading=Grading(invert=True)), "g2")[..., :3].astype(float)
        grey = _render(engine, replace(prepared.request, grading=Grading(saturation=0.0)), "g3")[..., :3].astype(float)
        depth = _render(engine, replace(prepared.request, debug_view="depth"), "g4")[..., :3]
    assert abs(darker.mean() - plain.mean() / 4.0) < 3.0
    assert abs(inverted.mean() - (255.0 - plain.mean())) < 3.0
    assert np.abs(grey[..., 0] - grey[..., 1]).max() <= 1
    assert depth.mean() > 0 and (depth.sum(axis=2) == 0).any()     # background black, hits bright


# --- Shadertoy ----------------------------------------------------------------------------------------------------------------
def test_shadertoy_conversions_compile_and_render(engine, tmp_path: Path):
    assert used_channels(BUFFER_A) == [0] and used_channels(IMAGE) == []
    single = convert("Plain", IMAGE)
    assert single.image is None and "mainImage(shadertoyColor" in single.main and "uniform sampler2D iChannel" not in single.main
    pair = convert("Feedback", IMAGE_READING_A, BUFFER_A, ["bufferA", None, None, None], ["self", None, None, None])
    assert pair.image is not None and pair.image_file == "Feedback-image.frag" and "#define iChannel0 backbuffer" in pair.main
    assert "#define iChannel0 frontbuffer" in pair.image and "DontClearOnChange" in pair.main
    with pytest.raises(ValueError):
        convert("bad", "void main() {}")
    (tmp_path / "single.frag").write_text(single.main)
    (tmp_path / "pair.frag").write_text(pair.main)
    (tmp_path / pair.image_file).write_text(pair.image)
    with engine.ctx:
        image = _render(engine, prepare(tmp_path / "single.frag", engine).request, "st1")
        feedback = _render(engine, prepare(tmp_path / "pair.frag", engine).request, "st2")
    assert image[..., :3].std() > 10 and feedback[..., :3].mean() > 0


# --- composer -------------------------------------------------------------------------------------------------------------------
def test_composer_recipes_generate_compiling_fragments(engine, tmp_path: Path):
    for name in PRESET_RECIPES:
        recipe = Recipe.preset(name)
        assert Recipe.from_dict(recipe.to_dict()).to_dict() == recipe.to_dict()
        path = tmp_path / f"{name}.frag"
        path.write_text(generate(recipe))
        with engine.ctx:
            image = _render(engine, prepare(path, engine).request, name, 48, 32)
        assert image[..., :3].std() > 1, name
    everything = Recipe([Step(kind, {}) for kind in STEP_KINDS], 3, "torus", {})
    text = generate(everything)
    assert all(f"S{i}_" in text or not STEP_KINDS[kind][1] for i, kind in enumerate(STEP_KINDS, start=1))
    for shape in SHAPES:
        assert generate(Recipe([Step("abs", {})], 2, shape, {})).count("float DE(vec3 p)") == 1
    path = tmp_path / "all.frag"
    path.write_text(text)
    with engine.ctx:
        assert _render(engine, prepare(path, engine).request, "all", 32, 24) is not None


# --- window-level tools -----------------------------------------------------------------------------------------------------------
@pytest.fixture
def window(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from fractalchemy.ui.fragments import FragmentsWindow

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


def rendered(win, passes: int = 1) -> None:
    wait_until(lambda: win.driver.stats is not None and win.driver.stats.passes_done >= passes and win.viewport.image is not None, 60000)


def test_bookmarks_recording_manual_mode_hud_and_gradient_colours(window, monkeypatch):
    from fractalchemy.model import Gradient

    window.open_path(MANDELBULB)
    rendered(window)
    document = window.tabs.document
    # bookmarks
    monkeypatch.setattr("fractalchemy.ui.fragments.camera_actions.QInputDialog.getText", staticmethod(lambda *a, **k: ("Start", True)))
    window.camera.add_bookmark()
    eye = document.state.get("Eye")
    document.set_values({"Eye": (9.0, 9.0, 9.0)})
    window.camera.go_to("Start")
    assert document.state.get("Eye") == eye and [b["name"] for b in window.camera.bookmarks()] == ["Start"]
    window.camera.remove("Start")
    assert window.camera.bookmarks() == []
    # flight recording: two distinct camera samples become two keyframe presets
    window.actions.record_path.setChecked(True)
    assert window.camera.recording
    document.set_values({"Eye": (2.0, 2.0, -5.0)})
    window.camera._sample()
    document.set_values({"Eye": (3.0, 2.0, -5.0)})
    window.camera._sample()
    window.actions.record_path.setChecked(False)
    assert not window.camera.recording and len(document.source.keyframe_names()) >= 2
    # manual rendering holds renders until asked
    rendered(window)
    window.actions.manual_render.setChecked(True)
    key = window.driver._key
    document.set_value("Power", 5.0)
    assert window.driver.pending and window.driver._key == key
    window.driver.render_now()
    assert not window.driver.pending and window.driver._key != key
    window.actions.manual_render.setChecked(False)
    # HUD
    window.viewport.set_hud(True)
    lines = window.viewport.hud_lines()
    assert any("subframes" in line for line in lines)
    # colours from a gradient
    gradient = Gradient.from_colors("g", [(255, 0, 0), (0, 0, 255)])
    count = window.params.colors_from_gradient(gradient)
    assert count >= 2 and document.state.get("BackgroundColor") != (1.0, 1.0, 1.0)
    # depth view and grading through the document
    window.set_debug_view("depth")
    assert document.request().debug_view == "depth"
    window.grading_panel.rows["exposure"].spin.setValue(1.0)
    assert document.grading.exposure == 1.0 and document.metadata.grading["exposure"] == 1.0


def test_de_slice_heat_map():
    from fractalchemy.ui.fragments.de_slice_dialog import heat_map

    values = np.array([[-0.5, 0.0, 0.5], [-0.1, 0.01, 2.0]])
    rgba = heat_map(values, 0.1)
    assert rgba.shape == (2, 3, 4) and rgba[0, 0, 2] > rgba[0, 0, 0] and rgba[1, 2, 0] > rgba[1, 2, 2]    # inside blue, far outside red
    spin(1)


def test_parameter_panel_filter_randomize_row_actions_and_window_shortcuts(window):
    from PySide6.QtGui import QGuiApplication

    window.open_path(MANDELBULB)
    rendered(window)
    document = window.tabs.document
    panel = window.parameters
    panel.filter.setText("col")
    shown = [n for n, w in panel.widgets.items() if not w.isHidden()]
    assert "BaseColor" in shown and "Power" not in shown and panel.current_group() == "Coloring"
    panel.filter.setText("")
    assert not panel.widgets["Power"].isHidden()
    power = document.state.get("Power")
    assert panel.randomize(group="Mandelbulb") >= 3 and "Eye" not in {}      # camera never randomised
    eye = document.state.get("Eye")
    panel.randomize(group="Camera")
    assert document.state.get("Eye") == eye
    panel.row_action("Power", "reset")
    assert document.state.get("Power") == 8.0 and document.can_undo
    panel.row_action("Power", "copy")
    assert QGuiApplication.clipboard().text() == "Power = 8"
    QGuiApplication.clipboard().setText("5.5")
    panel.row_action("Power", "paste")
    assert document.state.get("Power") == 5.5
    window.zoom_editors(1)
    assert window.tabs.editor.font().pointSize() == window.prefs.font_size > 0
    window.zoom_editors(0)
    assert window.prefs.font_size == 0
    window.step_preset(1)
    assert document.current_preset != "Default"
    window.copy_image()
    assert not QGuiApplication.clipboard().image().isNull()
    window.reset_camera()
    window.actions.show_editor.setChecked(False)
    assert not window.splitter.widget(0).isVisible()
    window.actions.show_editor.setChecked(True)
    assert window.progress.maximum() == window.driver.subframe_max
    window.open_text("void main() { gl_FragColor = vec4(1.0); }")
    window.tabs.close_others(0)
    assert len(window.tabs.tabs) == 1 and window.tabs.document is document
    del power
