"""Animations: the model, interpolation, the .faanim file, the frame renderer, and the Animation windows."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF

from fractalchemy.animation import Animation, animation_from_text, animation_to_text, load_animation, save_animation
from fractalchemy.animation.format import AnimationParseError
from fractalchemy.animation.interpolate import align_flames, blend_plan, catmull_rom_weights, ease, flame_at
from fractalchemy.animation.render import AnimationRenderSettings, ffmpeg_command, ffmpeg_path, video_problems
from fractalchemy.fractal.scene import Flame, XForm
from fractalchemy.render.final_settings import FinalRenderSettings
from tests.conftest import mouse_move, mouse_press, mouse_release, open_flame_and_wait, spin, wait_until

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "sample flames"


def two_flames() -> tuple[Flame, Flame]:
    a = Flame("a", [XForm(coefs=(0.5, 0, 0, 0.5, 0, 0), color=0.0, variations={"linear": 1.0}),
                    XForm(coefs=(0.5, 0, 0, 0.5, 0.5, 0), color=1.0, variations={"spherical": 1.0})])
    b = Flame("b", [XForm(coefs=(1.0, 0, 0, 1.0, 1.0, 0), color=0.4, variations={"linear": 0.5, "julian": 0.5}, params={"julian_power": 4}),
                    XForm(coefs=(0.5, 0, 0, 0.5, 0.5, 1.0), color=0.0, variations={"spherical": 1.0}),
                    XForm(coefs=(0.3, 0, 0, 0.3, 0, 0), color=0.5, variations={"bubble": 1.0})])
    b.final = XForm(variations={"julia3D": 1.0}, params={"julia3D_power": 3}, color_speed=0.0)
    a.camera.center, b.camera.center = (0.0, 0.0), (1.0, 2.0)
    a.camera.zoom, b.camera.zoom = 0.0, 1.0
    a.coloring.brightness, b.coloring.brightness = 4.0, 8.0
    a.palette = [(0, 0, 0)] * 256
    b.palette = [(200, 100, 0)] * 256
    return a, b


# --- model ------------------------------------------------------------------------------------------------------
def test_animation_keyframes_are_sorted_unique_movable_and_extend_the_length():
    a, b = two_flames()
    anim = Animation(fps=24, total_frames=10)
    k1 = anim.set_keyframe(30, a, "one")
    k0 = anim.set_keyframe(0, b)
    assert [k.frame for k in anim.keyframes] == [0, 30] and anim.total_frames == 31 and k0.label == "b" and k1.name == "one"
    replaced = anim.set_keyframe(30, b, "")
    assert replaced is k1 and k1.flame.name == "b" and k1.name == "one" and len(anim.keyframes) == 2
    assert anim.keyframe_at(30) is k1 and anim.index_at(30) == 1 and anim.segment(15) == (k0, k1) and anim.segment(40) == (k1, None)
    assert anim.next_keyframe(0) is k1 and anim.previous_keyframe(30) is k0 and anim.previous_keyframe(0) is None
    assert anim.move_keyframe(k1, -5) == 1 and anim.move_keyframe(k0, 20) == 0          # kept between neighbours
    assert anim.move_keyframe(k1, 100) == 100 and anim.total_frames == 101
    anim.set_total_frames(50)
    assert anim.total_frames == 101                                                     # never shorter than the last keyframe
    anim.remove_keyframe(k1)
    anim.set_total_frames(50)
    assert anim.total_frames == 50 and anim.duration == pytest.approx(50 / 24) and anim.last_frame == 49
    assert anim.frame_to_seconds(24) == 1.0 and anim.is_valid()


def test_animation_round_trips_through_dict_and_faanim_text_and_file(tmp_path):
    a, b = two_flames()
    anim = Animation("walk", 25, 100, "smooth", "ease-in-out", True, render={"folder": "/x"})
    anim.set_keyframe(0, a)
    anim.set_keyframe(99, b, "end")
    again = Animation.from_dict(json.loads(json.dumps(anim.to_dict())))
    assert again.to_dict() == anim.to_dict() and again.keyframes[1].flame.final is not None and again.render == {"folder": "/x"}
    text = animation_to_text(anim)
    assert '"format": "fractalchemy-animation"' in text and animation_from_text(text).to_dict() == anim.to_dict()
    path = save_animation(anim, tmp_path / "walk")
    assert path.suffix == ".faanim" and load_animation(path).to_dict() == anim.to_dict()
    with pytest.raises(AnimationParseError):
        animation_from_text("{}")
    with pytest.raises(AnimationParseError):
        animation_from_text("not json")
    with pytest.raises(AnimationParseError):
        load_animation(tmp_path / "missing.faanim")
    assert Animation.from_dict({"interpolation": "bogus", "easing": "?", "fps": 0, "keyframes": []}).interpolation == "linear"
    assert Animation.from_dict({"fps": 0}).fps == 1


# --- interpolation ----------------------------------------------------------------------------------------------
def test_alignment_gives_every_keyframe_the_same_structure():
    a, b = two_flames()
    aa, bb = align_flames([a, b])
    assert len(aa.xforms) == len(bb.xforms) == 3 and aa.final is not None and bb.final is not None
    assert aa.xforms[2].weight == 0.0 and aa.xforms[2].opacity == 0.0 and aa.xforms[2].variations == {"bubble": 1.0}   # padded from b
    assert list(aa.xforms[0].variations) == list(bb.xforms[0].variations) == ["linear", "julian"]
    assert aa.xforms[0].variations["julian"] == 0.0 and aa.xforms[0].params["julian_power"] == 4.0   # the other keyframe's value
    assert aa.final.variations == {"linear": 1.0, "julia3D": 0.0} and aa.final.params["julia3D_power"] == 3.0
    assert a.xforms[0].variations == {"linear": 1.0} and len(a.xforms) == 2                         # the originals are untouched


def test_linear_interpolation_blends_every_number_and_holds_outside_the_keyframes():
    a, b = two_flames()
    anim = Animation(fps=10, total_frames=30)
    anim.set_keyframe(10, a)
    anim.set_keyframe(20, b)
    assert flame_at(anim, 0).to_dict()["xforms"] == a.to_dict()["xforms"] and flame_at(anim, 29).camera.center == (1.0, 2.0)
    mid = flame_at(anim, 15)
    assert mid.camera.center == (0.5, 1.0) and mid.camera.zoom == 0.5 and mid.coloring.brightness == 6.0
    assert mid.xforms[0].coefs == pytest.approx((0.75, 0, 0, 0.75, 0.5, 0)) and mid.xforms[0].color == pytest.approx(0.2)
    assert mid.xforms[0].variations == pytest.approx({"linear": 0.75, "julian": 0.25}) and mid.xforms[0].params["julian_power"] == 4.0
    assert mid.xforms[2].weight == pytest.approx(0.25) and mid.xforms[2].variations == {"bubble": 1.0}
    assert mid.final.variations == pytest.approx({"linear": 0.5, "julia3D": 0.5})
    assert mid.palette[0] == (100, 50, 0) and mid.name == "animation — frame 15"
    plan = blend_plan(anim, 15)
    assert [k.frame for k, _w in plan] == [10, 20] and sum(w for _k, w in plan) == pytest.approx(1.0)
    anim.interpolation = "hold"
    assert flame_at(anim, 19).camera.center == (0.0, 0.0) and flame_at(anim, 20).camera.center == (1.0, 2.0)
    assert Animation().flame_at(0) is None


def test_smooth_easing_and_loop():
    a, b = two_flames()
    c = a.copy()
    c.camera.center = (3.0, 0.0)
    anim = Animation(fps=10, total_frames=40, interpolation="smooth")
    anim.set_keyframe(0, a)
    anim.set_keyframe(10, b)
    anim.set_keyframe(20, c)
    assert sum(catmull_rom_weights(0.3)) == pytest.approx(1.0) and catmull_rom_weights(0.0) == pytest.approx((0, 1, 0, 0))
    assert flame_at(anim, 10).camera.center == (1.0, 2.0)                     # the spline passes through the keyframes
    plan = blend_plan(anim, 5)
    assert len(plan) == 3 and sum(w for _k, w in plan) == pytest.approx(1.0)     # the clamped start merges p0 into p1
    between = flame_at(anim, 5).camera.center
    assert 0.0 < between[0] < 1.0
    assert ease(0.5, "none") == 0.5 and ease(0.5, "ease-in") == 0.25 and ease(0.5, "ease-out") == 0.75 and ease(0.5, "ease-in-out") == 0.5
    anim.easing, anim.interpolation = "ease-in", "linear"
    assert flame_at(anim, 5).camera.center == (0.25, 0.5)
    anim.easing = "none"
    assert flame_at(anim, 30).camera.center == (3.0, 0.0)                     # after the last keyframe: held
    anim.loop = True
    assert flame_at(anim, 30).camera.center == (1.5, 0.0)                     # looping: halfway back to the first keyframe
    anim.interpolation = "smooth"
    plan = blend_plan(anim, 25)
    assert [k.frame for k, _w in plan] == [10, 20, 0] and sum(w for _k, w in plan) == pytest.approx(1.0)


# --- render settings ------------------------------------------------------------------------------------------
def test_render_settings_frames_paths_problems_and_ffmpeg_command(tmp_path):
    s = AnimationRenderSettings(FinalRenderSettings(width=64, height=48, quality=10), str(tmp_path), "my clip", video=True)
    assert s.frames(10) == list(range(10)) and s.frames(10)[0] == 0
    assert AnimationRenderSettings(start_frame=3, end_frame=7, step=2).frames(100) == [3, 5, 7]
    assert AnimationRenderSettings(start_frame=50, end_frame=-1).frames(10) == [9]
    assert s.frame_path(7, 10).name == "my clip_0007.png" and s.digits(100000) == 5 and s.frame_pattern(10).endswith("my clip_%04d.png")
    assert s.video_path().name == "my clip.mp4" and s.extension == ".png"
    assert s.image.quality == 10 and AnimationRenderSettings().image.quality == 500.0
    command = ffmpeg_command(s, 24, 10, 0, executable="ffmpeg")
    assert command[:1] == ["ffmpeg"] and "-framerate" in command and command[command.index("-framerate") + 1] == "24"
    assert "libx264" in command and "-crf" in command and command[-1].endswith("my clip.mp4")
    gif = ffmpeg_command(AnimationRenderSettings(folder=str(tmp_path), video_format="gif"), 10, 10, 0, executable="ffmpeg")
    assert gif[-1].endswith("frame.gif") and "palettegen" in " ".join(gif)
    bad = AnimationRenderSettings(FinalRenderSettings(output_format="exr"), "", "", step=2, video=True)
    problems = bad.problems(10)
    assert any("folder" in p for p in problems) and any("base name" in p for p in problems) and any("step 1" in p for p in problems)
    assert any("cannot read" in p for p in video_problems(bad))
    assert not AnimationRenderSettings(folder=str(tmp_path), video=False).problems(10)
    back = AnimationRenderSettings.from_dict(json.loads(json.dumps(s.to_dict())))
    assert back == s and AnimationRenderSettings.from_dict({"video_format": "nope", "step": 0}).video_format == "mp4"
    assert AnimationRenderSettings.from_dict({"step": 0}).step == 1


# --- the frame renderer -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("engine", ["auto", "cpu"])
def test_render_job_writes_every_frame_skips_existing_and_can_be_stopped(qapp, tmp_path, engine):
    from fractalchemy.animation.render_job import AnimationRenderJob

    a, b = two_flames()
    a.camera.width = a.camera.height = 64
    anim = Animation(fps=5, total_frames=4)
    anim.set_keyframe(0, a)
    anim.set_keyframe(3, b)
    folder = tmp_path / "out"
    settings = AnimationRenderSettings(FinalRenderSettings(width=32, height=24, quality=8, engine=engine, oversample=1, fuse=5),
                                       str(folder), "clip", video=False)
    outcomes, progress = [], []
    job = AnimationRenderJob(anim, settings)
    job.progressed.connect(progress.append)
    job.succeeded.connect(outcomes.append)
    job.failed.connect(lambda m: outcomes.append(m))
    job.start()
    wait_until(lambda: outcomes, 240000)
    job.wait(5000)
    outcome = outcomes[0]
    assert not isinstance(outcome, str), outcome
    assert outcome.complete and [p.name for p in outcome.frames] == ["clip_0000.png", "clip_0001.png", "clip_0002.png", "clip_0003.png"]
    assert all(p.exists() and p.stat().st_size > 0 for p in outcome.frames) and outcome.samples > 0
    assert progress[-1].phase == "Finished" and progress[-1].fraction == 1.0 and any(p.preview is not None for p in progress)
    assert any(p.index == 2 and p.count == 4 for p in progress)
    # a second run skips what exists and renders only the missing frame
    outcome.frames[1].unlink()
    outcomes.clear()
    job = AnimationRenderJob(anim, AnimationRenderSettings(settings.image, str(folder), "clip", skip_existing=True))
    job.succeeded.connect(outcomes.append)
    job.failed.connect(lambda m: outcomes.append(m))
    job.start()
    wait_until(lambda: outcomes, 240000)
    job.wait(5000)
    assert [p.name for p in outcomes[0].frames] == ["clip_0001.png"] and outcomes[0].skipped == [0, 2, 3]
    # cancelling stops the batch early
    outcomes.clear()
    job = AnimationRenderJob(anim, AnimationRenderSettings(settings.image, str(tmp_path / "stopped"), "clip"))
    job.succeeded.connect(outcomes.append)
    job.failed.connect(lambda m: outcomes.append(m))
    job.cancel()
    job.start()
    wait_until(lambda: outcomes, 240000)
    job.wait(5000)
    assert not isinstance(outcomes[0], str) and not outcomes[0].complete and len(outcomes[0].frames) <= 1


@pytest.mark.skipif(ffmpeg_path() is None, reason="ffmpeg is not installed")
def test_render_job_encodes_a_video_with_ffmpeg(qapp, tmp_path):
    from fractalchemy.animation.render_job import AnimationRenderJob

    a, b = two_flames()
    anim = Animation(fps=5, total_frames=3)
    anim.set_keyframe(0, a)
    anim.set_keyframe(2, b)
    settings = AnimationRenderSettings(FinalRenderSettings(width=32, height=24, quality=8, oversample=1, fuse=5), str(tmp_path), "vid",
                                       video=True, keep_frames=False)
    outcomes = []
    job = AnimationRenderJob(anim, settings)
    job.succeeded.connect(outcomes.append)
    job.failed.connect(lambda m: outcomes.append(m))
    job.start()
    wait_until(lambda: outcomes, 240000)
    job.wait(5000)
    outcome = outcomes[0]
    assert not isinstance(outcome, str) and outcome.video == tmp_path / "vid.mp4" and outcome.video.stat().st_size > 0
    assert outcome.frames == [] and not (tmp_path / "vid_0000.png").exists() and any("removed" in n for n in outcome.notes)


def test_render_job_reports_a_failure_when_nothing_can_be_written(qapp, tmp_path):
    from fractalchemy.animation.render_job import AnimationRenderJob

    a, b = two_flames()
    anim = Animation(fps=5, total_frames=2)
    anim.set_keyframe(0, a)
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("in the way")
    settings = AnimationRenderSettings(FinalRenderSettings(width=8, height=8, quality=1, oversample=1, fuse=1), str(blocker / "frames"), "f")
    results = []
    job = AnimationRenderJob(anim, settings)
    job.succeeded.connect(lambda o: results.append(("ok", o)))
    job.failed.connect(lambda m: results.append(("failed", m)))
    job.start()
    wait_until(lambda: results, 60000)
    job.wait(5000)
    assert results[0][0] == "failed" and results[0][1]


def test_timeline_hit_testing_zoom_and_ticks(qapp):
    from fractalchemy.widgets.timeline import RULER_HEIGHT, TRACK_HEIGHT, Timeline
    a, b = two_flames()
    anim = Animation(fps=10, total_frames=100)
    anim.set_keyframe(0, a)
    anim.set_keyframe(50, b)
    timeline = Timeline()
    timeline.resize(620, RULER_HEIGHT + TRACK_HEIGHT + 8)
    timeline.show()
    timeline.set_data(anim.total_frames, anim.fps, anim.keyframes, anim.keyframes[1], 25)
    y = RULER_HEIGHT + TRACK_HEIGHT / 2
    assert timeline.keyframe_at(QPointF(timeline.x_of(50), y)) is anim.keyframes[1]
    assert timeline.keyframe_at(QPointF(timeline.x_of(50), 5)) is None            # the ruler is not the track
    assert timeline.keyframe_at(QPointF(timeline.x_of(25), y)) is None
    assert timeline.frame_near(timeline.x_of(42.4)) == 42 and timeline.frame_near(-1000) == 0 and timeline.frame_near(10 ** 6) == 99
    fit = timeline.pixels_per_frame
    timeline.zoom_by(4.0, timeline.x_of(50))
    assert timeline.pixels_per_frame == pytest.approx(fit * 4) and 0 < timeline.frame_at(timeline.width() / 2) < 100
    timeline.zoom_by(1e-9)
    assert timeline.pixels_per_frame == pytest.approx(fit)                        # never smaller than the fit
    timeline.fit()
    assert timeline.pixels_per_frame == pytest.approx(fit)
    timeline.set_data(1, 1, [], None, 0)                                           # a one-frame, keyframe-less animation paints
    timeline.grab()
    timeline.set_data(10 ** 6, 240, [], None, 0)
    assert timeline._tick_step() >= 1000
    timeline.grab()


def test_live_preview_survives_a_failing_flame_provider(qapp):
    from fractalchemy.render.service import RenderService
    from fractalchemy.ui.live_preview import LivePreview

    def broken():
        raise RuntimeError("no keyframes")

    service = RenderService(prefer_gpu=False)
    service.start()
    try:
        preview = LivePreview(flame_provider=broken, name="test")
        preview.bind(None, service)
        preview.show()
        preview.request()
        spin(50)
        assert preview.image is None and not preview.busy
        preview.grab()
    finally:
        service.stop()
        preview.deleteLater()
        spin(20)


# --- the windows ------------------------------------------------------------------------------------------------
@pytest.fixture
def animation(main_window_factory):
    win = main_window_factory(cheap_renders=True)
    open_flame_and_wait(win, SAMPLES / "candy.flame", 0)
    win.actionAnimation.trigger()
    wait_until(lambda: win.animation.isVisible())
    spin(50)
    yield win
    win.animation.document.mark_saved()


def test_animation_window_opens_from_the_main_window_and_captures_keyframes(animation):
    win = animation
    aw, doc = win.animation, win.animation.document
    assert win.actionAnimation in win.toolBar.actions() and win.actionAnimation in win.menuWindows.actions()
    assert win.actionAnimation.shortcut().toString() == "F9" and not win.actionAnimation.icon().isNull()
    assert aw.windowTitle() == "Animation — animation" and not doc.animation.keyframes and aw.act_capture.isEnabled()
    key = aw.capture_keyframe()
    assert key is not None and key.frame == 0 and key.flame.name == win.document.flame.name and doc.modified and doc.selected is key
    assert aw.keyframe_panel.list.count() == 1 and "*" in aw.windowTitle() and aw.act_render.isEnabled()
    doc.set_frame(60)
    open_flame_and_wait(win, SAMPLES / "candy.flame", 2)
    key2 = aw.capture_keyframe()
    assert key2.frame == 60 and [k.frame for k in doc.animation.keyframes] == [0, 60] and doc.animation.total_frames == 150
    assert aw.keyframe_panel.list.count() == 2 and aw.keyframe_panel.list.currentRow() == 1 and aw.keyframe_panel.frame_box.value() == 60
    doc.set_frame(30)
    assert "50 %" in aw.blend_label.text() and aw.frame_box.value() == 30
    wait_until(lambda: aw.preview.stats is not None, 60000)
    assert aw.preview.stats.width > 0
    # capturing on a keyed frame replaces it; update replaces the selected one from the main window
    doc.set_frame(60)
    open_flame_and_wait(win, SAMPLES / "candy.flame", 1)
    aw.capture_keyframe()
    assert len(doc.animation.keyframes) == 2 and doc.animation.keyframe_at(60).flame.name == win.document.flame.name
    aw.keyframe_panel.update_button.click()
    assert doc.animation.keyframe_at(60).flame.name == win.document.flame.name


def test_clicking_a_keyframe_shows_it_in_the_main_window_like_choosing_a_fractal(animation):
    win = animation
    aw, doc = win.animation, win.animation.document
    first = win.document.flame
    aw.capture_keyframe()
    doc.set_frame(40)
    open_flame_and_wait(win, SAMPLES / "candy.flame", 2)
    second = win.document.flame
    aw.capture_keyframe()
    assert win.document.flame.name == second.name
    aw.keyframe_panel.list.itemClicked.emit(aw.keyframe_panel.list.item(0))
    assert win.document.flame.name == first.name and win.document.source_path is None and doc.frame == 0 and doc.selected.frame == 0
    aw.timeline.keyframe_clicked.emit(doc.animation.keyframes[1])
    assert win.document.flame.name == second.name and doc.frame == 40
    aw.keyframe_panel.list.setCurrentRow(0)
    aw.keyframe_panel.show_button.click()
    assert win.document.flame.name == first.name
    aw.act_delete.trigger()
    assert len(doc.animation.keyframes) == 1 and doc.selected.frame == 40


def test_animation_files_save_and_open_showing_the_first_keyframe(animation, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda parent, title, text, *a: warnings.append(text)))
    win = animation
    aw, doc = win.animation, win.animation.document
    aw.capture_keyframe()
    doc.set_frame(20)
    open_flame_and_wait(win, SAMPLES / "candy.flame", 2)
    aw.capture_keyframe()
    aw.settings_panel.name_edit.setText("my anim")
    aw.settings_panel.name_edit.editingFinished.emit()
    aw.settings_panel.fps_box.setValue(24)
    aw.settings_panel.interpolation_box.setCurrentIndex(aw.settings_panel.interpolation_box.findData("smooth"))
    aw.settings_panel.loop_check.setChecked(True)
    assert doc.animation.name == "my anim" and doc.animation.fps == 24 and doc.animation.interpolation == "smooth" and doc.animation.loop
    path = tmp_path / "my anim.faanim"
    assert aw._write(path) and path.exists() and not doc.modified and aw.windowTitle() == "Animation — my anim"
    assert aw.save_animation()                                  # in place, no dialog
    aw.new_animation()
    assert not doc.animation.keyframes and doc.path is None
    assert aw.open_animation(path)
    assert [k.frame for k in doc.animation.keyframes] == [0, 20] and doc.animation.fps == 24 and doc.path == path
    assert win.document.flame.name == doc.animation.keyframes[0].flame.name and doc.selected.frame == 0 and doc.frame == 0
    assert aw.keyframe_panel.list.count() == 2 and aw.settings_panel.fps_box.value() == 24 and aw.settings_panel.loop_check.isChecked()
    assert not aw.open_animation(tmp_path / "missing.faanim") and warnings and "cannot read" in warnings[0]


def test_timeline_scrubs_drags_keyframes_and_playback_runs(animation):
    win = animation
    aw, doc = win.animation, win.animation.document
    aw.capture_keyframe()
    doc.set_frame(100)
    aw.capture_keyframe()
    timeline = aw.timeline
    timeline.fit()
    spin(20)
    # scrub
    x = timeline.x_of(50)
    mouse_press(timeline, QPointF(x, 10))
    assert doc.frame == 50
    mouse_move(timeline, QPointF(timeline.x_of(75), 10))
    mouse_release(timeline, QPointF(timeline.x_of(75), 10))
    assert doc.frame == 75
    # drag the second keyframe to frame 120
    key = doc.animation.keyframes[1]
    y = timeline.height() - 22
    mouse_press(timeline, QPointF(timeline.x_of(100), y))
    assert doc.selected is key
    mouse_move(timeline, QPointF(timeline.x_of(120), y))
    mouse_release(timeline, QPointF(timeline.x_of(120), y))
    assert key.frame == 120 and doc.frame == 120
    assert timeline.keyframe_at(QPointF(timeline.x_of(120), y)) is key and timeline.keyframe_at(QPointF(timeline.x_of(60), y)) is None
    timeline.zoom_by(2.0)
    assert timeline.pixels_per_frame > 0
    timeline.fit()
    # playback advances the playhead at the frame rate
    doc.set_frame(0)
    aw.playback.play()
    assert aw.playback.playing and aw.play_button.text() == "Pause"
    wait_until(lambda: doc.frame >= 5, 5000)
    aw.playback.pause()
    frame = doc.frame
    spin(100)
    assert doc.frame == frame and not aw.playback.playing
    aw.playback.stop()
    assert doc.frame == 0
    aw.playback.play()
    wait_until(lambda: not aw.playback.playing, 15000)                 # 150 frames at 30 fps: ends after 5 s
    assert doc.frame == doc.animation.last_frame


def test_render_animation_window_renders_a_small_batch(animation, tmp_path):
    win = animation
    aw, doc = win.animation, win.animation.document
    aw.capture_keyframe()
    doc.set_frame(2)
    aw.capture_keyframe()
    doc.set_settings(total_frames=3)
    aw.show_render_window()
    rw = aw.render_window
    assert rw.isVisible() and rw.windowTitle().startswith("Render Animation")
    rw.size_panel.set_size(32, 24)
    rw.quality_panel.density.setCurrentText("8")
    rw.quality_panel.oversample.setValue(1)
    rw.output_panel.folder.setText(str(tmp_path / "frames"))
    rw.output_panel.set_base_name("test")
    rw.output_panel._emit()
    s = rw.current_settings()
    assert s.folder.endswith("frames") and s.base_name == "test" and s.image.width == 32 and s.frames(3) == [0, 1, 2]
    assert rw.start_button.isEnabled() and "3 frames" in rw.plan_label.text()
    assert doc.animation.render["base_name"] == "test"         # the settings travel with the animation
    rw.start(ask_overwrite=False)
    assert rw.rendering
    wait_until(lambda: not rw.rendering, 240000)
    assert rw.last_outcome is not None and len(rw.last_outcome.frames) == 3 and (tmp_path / "frames" / "test_0002.png").exists()
    assert "3 frames written" in rw.progress_panel.result.text()
    rw.video_panel.enable.setChecked(ffmpeg_path() is not None)
    assert rw.video_panel.command.text().startswith("ffmpeg") or ffmpeg_path() is None
