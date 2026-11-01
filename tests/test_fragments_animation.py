"""Keyframe camera paths, easing curves, the animation clock and their window integration."""

import numpy as np
import pytest
from PySide6.QtCore import QSettings

from fractalchemy.fragments import presets
from fractalchemy.fragments.animation import AnimationSettings, camera_path, curves_past_the_end, frame_values
from fractalchemy.fragments.easing import EasingSetting, curve_name, curve_number, parse_all, with_setting, without_slider
from fractalchemy.fragments.examples import EXAMPLES_DIR
from fractalchemy.fragments.parameters import FloatParameter, VectorParameter
from fractalchemy.fragments.spline import CameraPath, Keyframe, keyframes_from_presets, parse_keyframe, spline_point
from fractalchemy.fragments.state import ParameterState
from fractalchemy.ui.fragments import FragmentsWindow
from fractalchemy.ui.fragments.animation_controls import ANIMATION, AnimationControls
from fractalchemy.ui.fragments.easing_dialog import EasingDialog
from fractalchemy.ui.fragments.timeline_window import keyframe_markers

from .conftest import spin, wait_until


def keyframes(n: int) -> list[Keyframe]:
    return [Keyframe(f"KeyFrame.{i:04d}", i, (float(i), 0.0, 0.0), (float(i), 1.0, 0.0), (0.0, 1.0, 0.0)) for i in range(1, n + 1)]


def test_keyframe_parsing_and_ordering():
    presets_text = {"Default": "FOV = 0.4", "KeyFrame.0002": "Eye = 2,0,0\nTarget = 0,0,0\nUp = 0,1,0\nFOV = 0.5",
                    "KeyFrame.0001": "Eye = 1,0,0\nTarget = 0,0,0\nUp = 0,1,0", "KeyFrame.0003": "Eye = 3,0,0"}
    found = keyframes_from_presets(presets_text)
    assert [k.name for k in found] == ["KeyFrame.0001", "KeyFrame.0002"] and found[1].fov == 0.5 and found[0].fov is None
    assert parse_keyframe("KeyFrame.0009", "Eye = 1,2,3\nTarget = 4,5,6\nUp = 0,0,1").eye == (1.0, 2.0, 3.0)


def test_catmull_rom_path_lands_on_the_control_points():
    points = np.array([k.eye for k in keyframes(4)])
    assert np.allclose(spline_point(points, 0.0, False), points[0])
    assert np.allclose(spline_point(points, 1.0, False), points[-1])
    assert np.allclose(spline_point(points, 1.0, True), points[0])           # looping wraps back
    path = CameraPath(keyframes(4), 100)
    eye0, target0, up0 = path.at(0)
    assert np.allclose(eye0, (1, 0, 0)) and np.allclose(target0, (1, 1, 0)) and np.allclose(up0, (0, 1, 0))
    xs = [path.at(f)[0][0] for f in range(0, 101, 10)]
    assert all(b >= a - 1e-9 for a, b in zip(xs, xs[1:])) and 3.9 < xs[-1] < 4.2       # monotonic, ends near the last point
    assert CameraPath(keyframes(1), 100).at(5) is None and not CameraPath([], 10).valid
    looping = CameraPath(keyframes(4), 100, loop=True)
    assert np.allclose(looping.at(99)[0], (1, 0, 0))                                 # the last frame is back at the start
    assert path.sample(5).shape == (5, 3)


def test_easing_setting_round_trip_and_evaluation():
    line = "Power1:InOutQuad:3:2:8:10:110:0.3:1:1.70158:1:0"
    setting = EasingSetting.parse(line)
    assert setting is not None and setting.parameter == "Power" and setting.component == 1 and setting.duration == 101
    assert setting.format().startswith("Power1:InOutQuad:3:2:8:10:110:")
    assert EasingSetting.parse("a:b:c") is None and parse_all([line, "junk"]) == [setting]
    assert setting.value_at(0) == 2.0 and setting.value_at(10) == 2.0                  # the start value holds before the range
    assert abs(setting.value_at(110) - 8.0) < 0.2 and abs(setting.value_at(500) - 8.0) < 0.2   # and the end after it
    linear = EasingSetting("X1", curve_number("Linear"), 0.0, 10.0, 0, 10)
    assert abs(linear.value_at(10) - 10.0) < 1e-9 and abs(linear.value_at(5) - 5.0) < 1e-9    # FragM's nudge: exact at the last frame
    pong = EasingSetting("X1", 0, 0.0, 10.0, 0, 10, loops=2, pingpong=True)
    values = [round(pong.value_at(f), 6) for f in range(0, 25, 2)]
    assert values[:6] == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0] and values[6] < values[5] and values[-1] == 0.0      # back down, then holds
    assert pong.end_frame == 21
    elastic = EasingSetting("X1", curve_number("InElastic"), 0.0, 1.0, 0, 100, period=0.2, amplitude=2.0)
    assert elastic.curve().period() == 0.2 and elastic.curve().amplitude() == 2.0
    assert curve_name(0) == "Linear"
    both = with_setting([setting], EasingSetting("Power1", 0, 0.0, 1.0, 0, 10))
    assert len(both) == 1 and both[0].start == 0.0 and without_slider(both, "Power1") == []


def test_frame_values_combine_path_and_curves():
    state = ParameterState([VectorParameter("Eye", "vec3", default=(0, 0, -10), from_=(-50,) * 3, to=(50,) * 3),
                            VectorParameter("Target", "vec3", default=(0, 0, 0), from_=(-50,) * 3, to=(50,) * 3),
                            VectorParameter("Up", "vec3", default=(0, 1, 0), from_=(-1,) * 3, to=(1,) * 3),
                            FloatParameter("FocalPlane", "float", default=1.0, from_=0, to=50),
                            FloatParameter("Power", "float", default=8.0, from_=1, to=16),
                            VectorParameter("JuliaC", "vec3", default=(0, 0, 0), from_=(-2,) * 3, to=(2,) * 3)])
    from fractalchemy.fragments.parameters import BoolParameter
    state.add(BoolParameter("AutoFocus", "bool", default=True))
    path = CameraPath(keyframes(3), 50)
    curves = [EasingSetting("Power1", 0, 1.0, 16.0, 0, 50), EasingSetting("JuliaC2", 0, 0.0, 2.0, 0, 50)]
    values = frame_values(25, state, path, curves, auto_focus=True)
    assert set(values) == {"Eye", "Target", "Up", "FocalPlane", "Power", "JuliaC"}
    assert abs(values["FocalPlane"] - 1.0) < 1e-6                                      # |Target − Eye| along this path
    assert 1.0 < values["Power"] < 16.0 and values["JuliaC"][1] > 0 and values["JuliaC"][0] == 0
    settings = AnimationSettings(fps=10, length=3)
    assert settings.frames == 30 and settings.time_of(15) == 1.5 and settings.frame_of(1.5) == 15
    assert curves_past_the_end(curves, settings) == curves and curves_past_the_end(curves, AnimationSettings(25, 10)) == []
    assert AnimationSettings.from_dict(settings.to_dict()) == settings
    built = camera_path({"KeyFrame.0001": "Eye = 1,0,0\nTarget = 0,0,0\nUp = 0,1,0", "KeyFrame.0002": "Eye = 2,0,0\nTarget = 0,0,0\nUp = 0,1,0"}, settings)
    assert built.valid and built.frames == 30
    assert [m.frame for m in keyframe_markers(keyframes(3), 101)] == [0, 50, 100] and keyframe_markers([], 10) == []


def test_keyframe_blend_interpolates_every_numeric_parameter():
    from fractalchemy.fragments.animation import keyframe_blend
    from fractalchemy.fragments.interpolate import KeyframeBlend
    from fractalchemy.fragments.parameters import BoolParameter, ColorParameter, IntParameter

    state = ParameterState([VectorParameter("Eye", "vec3", default=(0, 0, -10), from_=(-50,) * 3, to=(50,) * 3),
                            VectorParameter("Target", "vec3", default=(0, 0, 0), from_=(-50,) * 3, to=(50,) * 3),
                            VectorParameter("Up", "vec3", default=(0, 1, 0), from_=(-1,) * 3, to=(1,) * 3),
                            FloatParameter("Power", "float", default=8.0, from_=1, to=16),
                            ColorParameter("BaseColor", "vec3", default=(1, 1, 1)),
                            IntParameter("Iterations", "int", default=10, from_=1, to=100),
                            BoolParameter("Julia", "bool", default=False)])
    presets = {"KeyFrame.0001": "Eye = 1,0,0\nTarget = 0,0,0\nUp = 0,1,0\nPower = 2\nBaseColor = 0,0,0\nIterations = 10\nJulia = false",
               "KeyFrame.0002": "Eye = 2,0,0\nTarget = 0,0,0\nUp = 0,1,0\nPower = 10\nBaseColor = 1,1,1\nIterations = 20\nJulia = true",
               "Default": "Power = 8"}
    blend = KeyframeBlend(presets, state.params, 101, smooth=False)
    assert blend.valid and "Eye" not in blend.keyframes[0]
    middle = blend.at(50)
    assert abs(middle["Power"] - 6.0) < 1e-9 and all(abs(c - 0.5) < 1e-9 for c in middle["BaseColor"])
    assert middle["Iterations"] == 10 and middle["Julia"] is False                   # held until the next keyframe
    assert blend.at(100)["Iterations"] == 20 and blend.at(100)["Julia"] is True and abs(blend.at(0)["Power"] - 2.0) < 1e-9
    smooth = KeyframeBlend(presets, state.params, 101)
    assert abs(smooth.at(50)["Power"] - 6.0) < 1e-9 and smooth.at(25)["Power"] < blend.at(25)["Power"]
    settings = AnimationSettings(fps=10, length=10, interpolation="all")
    assert AnimationSettings.from_dict(settings.to_dict()).interpolation == "all"
    assert AnimationSettings.from_dict({"interpolation": "weird"}).interpolation == "camera"
    assert keyframe_blend(presets, state, AnimationSettings(fps=10, length=10)) is None
    path = camera_path(presets, settings)
    values = frame_values(50, state, path, [EasingSetting("Power1", 0, 1.0, 16.0, 0, 100)], blend=keyframe_blend(presets, state, settings))
    assert abs(values["Power"] - 8.5) < 1e-6 and values["Iterations"] == 10 and values["Eye"][0] > 1.0   # the curve wins over the blend


def test_animation_controls_clock(qapp):
    controls = AnimationControls()
    frames = []
    controls.frame_changed.connect(frames.append)
    controls.apply_settings(AnimationSettings(fps=100, length=1))
    assert controls.slider.maximum() == 100 and controls.time_label.text() == "Time: 0s:00f"
    controls.set_frame(150)
    assert controls.frame == 100 and frames == [100] and controls.time_label.text() == "Time: 1s:00f"
    controls.set_mode(ANIMATION)
    controls.set_frame(0)
    controls.play()
    assert controls.playing and not controls.play_action.isEnabled()
    spin(250)
    assert controls.frame > 5 and controls.time() == controls.frame / 100
    controls.stop()
    assert not controls.playing and controls.stop_action.isEnabled() is False
    controls.set_keyframe_ticks(3)
    assert controls.slider.tickInterval() == 50
    controls.length_spin.setValue(2)
    assert controls.settings.frames == 200 and controls.slider.maximum() == 200


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


def test_keyframes_drive_the_camera_and_ranges_keep_curves(window):
    window.open_path(EXAMPLES_DIR / "Historical 3D Fractals" / "Mandelbulb.frag")
    document = window.tabs.document
    wait_until(lambda: window.viewport.image is not None, 60000)
    text = presets.replace_preset(document.text, "KeyFrame.0001", document.state.camera_text("3D"))
    document.set_camera3d(document.camera3d().key("d", 2.0))
    text = presets.replace_preset(text, "KeyFrame.0002", document.state.camera_text("3D"))
    window.replace_text(text)
    window.build()
    path = document.camera_path()
    assert path.valid and len(path.keyframes) == 2 and window.viewport.path is not None and window.viewport.path.valid
    window.anim.set_mode(ANIMATION)
    eye_before = document.state.get("Eye")
    window.anim.set_frame(window.anim.settings.frames // 2)
    assert document.state.get("Eye") != eye_before and window.driver.time == window.anim.time()
    assert not document.can_undo or document.state.get("Eye") != eye_before        # the frame is not an undo step
    document.set_easing(EasingSetting("Power1", 0, 2.0, 12.0, 0, window.anim.settings.frames))
    window.anim.set_frame(window.anim.settings.frames)
    assert abs(document.state.get("Power") - 12.0) < 1e-6
    window.prefs.save_easing = True
    from PySide6.QtWidgets import QInputDialog
    original = QInputDialog.getText
    QInputDialog.getText = staticmethod(lambda *a, **k: ("Range-0000-0250", True))
    try:
        window.params.insert_preset()
    finally:
        QInputDialog.getText = original
    assert "Power1:Linear:0:2:12:0:" in document.text and "Range-0000-0250" in document.source.presets
    document.clear_animation()
    assert document.easing == []
    document.apply_preset("Range-0000-0250")
    assert len(document.easing) == 1 and document.easing[0].slider == "Power1"
    window.animation.show_timeline()
    assert window.animation._timeline.isVisible() and window.animation._timeline.summary.text().startswith("2 keyframes · 1 easing")
    window.anim.play()
    spin(300)
    assert window.anim.playing
    window.anim.stop()


def test_easing_dialog_builds_the_setting(qapp):
    state = ParameterState([FloatParameter("Power", "float", default=8.0, from_=1, to=16),
                            VectorParameter("JuliaC", "vec3", default=(0, 0, 0), from_=(-2,) * 3, to=(2,) * 3)])
    dialog = EasingDialog(state, AnimationSettings(), [EasingSetting("Power1", 0, 1.0, 2.0, 0, 50)], "JuliaC3")
    assert dialog.slider == "JuliaC3" and dialog.apply_button.text() == "Add curve" and not dialog.discard_button.isEnabled()
    dialog.end_spin.setValue(1.5)
    assert dialog.setting().format().startswith("JuliaC3:Linear:0:0:1.5:0:250")
    dialog.select_slider("Power1")
    assert dialog.apply_button.text() == "Apply" and dialog.discard_button.isEnabled() and dialog.setting().end == 2.0
    dialog._discard()
    assert dialog.discarded
