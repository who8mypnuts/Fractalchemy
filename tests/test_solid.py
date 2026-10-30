"""The 3D Editor's solid renderer: the scene model and `.fa3d` file, the CPU and GPU engines, and the window."""

import numpy as np
import pytest

from fractalchemy.fractal import Flame, XForm
from fractalchemy.render.cpu_engine import CpuEngine
from fractalchemy.render.gpu_engine import gpu_available
from fractalchemy.render.service import RenderService, wait_for
from fractalchemy.render.settings import RenderSettings
from fractalchemy.scene3d import format as fa3d
from fractalchemy.scene3d.model import DistantLight, Material, Scene3D, materials_for
from fractalchemy.solid.gbuffer import GBuffer, ShadowMap, light_basis
from fractalchemy.solid.shading import shade
from fractalchemy.solid.view import View, light_direction
from tests.conftest import spin

needs_gl = pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")
SETTINGS = RenderSettings(96, 64, passes=2, points=8192, fuse=10, oversample=2)


def tetrahedron() -> Flame:
    """A Sierpinski tetrahedron (four half-scale contractions, one lifted in z): a dependable little 3D surface."""
    corners = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0.5, 0.5, 0.8)]
    xforms = []
    for i, (cx, cy, cz) in enumerate(corners):
        variations = {"linear3D": 0.5}
        if cz:
            variations["ztranslate"] = cz / 2
        xforms.append(XForm(coefs=(1, 0, 0, 1, cx, cy), color=i / 3, variations=variations))
    flame = Flame("tetrahedron", xforms)
    flame.camera.scale = 60
    flame.camera.width, flame.camera.height = 96, 64
    flame.camera.center = (0.5, 0.35)
    flame.camera.pitch, flame.camera.perspective = 0.9, 0.3
    return flame


def scene() -> Scene3D:
    return Scene3D("test", tetrahedron())


# --- model / file ------------------------------------------------------------------------------------------------
def test_scene_round_trips_through_dict_and_fa3d_text(tmp_path):
    original = scene()
    original.materials = [Material(diffuse=0.5, color_mode="fixed", color=(10, 20, 30)), Material(specular=0.9)]
    original.lights.append(DistantLight(altitude=10, azimuth=200, color=(255, 0, 0), shadows=False))
    original.environment.color = (1, 2, 3)
    original.solid.display = "points"
    copy = Scene3D.from_dict(original.to_dict())
    assert copy.to_dict() == original.to_dict() and copy.fractal is not original.fractal
    assert copy.materials[0].color == (10, 20, 30) and copy.lights[2].color == (255, 0, 0)
    text = fa3d.scene_to_text(original)
    assert '"format": "fa3d"' in text and fa3d.scene_from_text(text).to_dict() == original.to_dict()
    path = tmp_path / "sub" / "scene.fa3d"
    fa3d.save_scene(original, path)
    assert fa3d.load_scene(path).to_dict() == original.to_dict()
    with pytest.raises(fa3d.Scene3DFormatError):
        fa3d.scene_from_text('{"format": "fa", "flame": {}}')
    with pytest.raises(fa3d.Scene3DFormatError):
        fa3d.scene_from_text("not json")
    # unknown keys are ignored, missing ones default
    loose = Scene3D.from_dict({"solid": {"ao": False, "bogus": 1}, "materials": [], "lights": []})
    assert loose.solid.ao is False and loose.materials and loose.lights == [] and loose.fractal is None


def test_materials_follow_the_transform_count_and_the_last_repeats():
    flame = tetrahedron()
    mats = materials_for(flame, [Material(diffuse=0.1)])
    assert len(mats) == 4 and mats[3].diffuse == 0.1 and mats[0] is not mats[1]
    flame.final = XForm()
    assert len(materials_for(flame, mats)) == 5
    s = Scene3D(materials=[Material(diffuse=0.1), Material(diffuse=0.2)])
    assert s.material_for(5).diffuse == 0.2 and s.material_for(-1).diffuse == 0.1
    assert s.copy().materials[0] is not s.materials[0]


# --- geometry helpers ---------------------------------------------------------------------------------------------
def test_view_projects_and_light_basis_is_orthonormal():
    flame = tetrahedron()
    view = View(flame.camera, 96, 64, 2)
    assert view.size == (192, 128)
    x, y, z = np.array([0.0, 0.5]), np.array([0.0, 0.0]), np.array([0.0, 0.0])
    vx, vy, vz = view.to_view(x, y, z)
    px, py = view.project(vx, vy, vz)
    assert px[1] > px[0] and np.isfinite(py).all()
    d = light_direction(55.0, -22.0)
    assert abs(np.linalg.norm(d) - 1) < 1e-9 and d[2] > 0
    b = light_basis(d)
    assert np.allclose(b @ b.T, np.eye(3), atol=1e-9) and np.allclose(b[2], -d)
    shadow = ShadowMap(55.0, -22.0, np.array([[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]]), 64)
    shadow.splat(np.array([0.0]), np.array([0.0]), np.array([0.0]))
    assert np.isfinite(shadow.depth).sum() == 1
    behind = shadow.occlusion(np.array([[-d * 0.5]]), softness=0.0)  # half a unit further from the light than the splat
    in_front = shadow.occlusion(np.array([[d * 0.5]]), softness=0.0)
    assert behind[0, 0] == pytest.approx(1 / 9) and in_front[0, 0] == 0.0   # one of the 3×3 taps is the splat


# --- CPU engine ----------------------------------------------------------------------------------------------------
def test_cpu_solid_job_renders_a_lit_object_progressively():
    job = CpuEngine(threads=2).start(tetrahedron(), SETTINGS.with_solid(scene()))
    assert job.stats.engine.startswith("CPU solid")
    first = job.run_pass()
    assert first.shape == (64, 96, 4) and job.stats.passes_done == 1 and not job.stats.finished
    second = job.run_pass()
    assert job.stats.finished and job.stats.samples > 0
    assert job.gbuffer.coverage > 0.05
    hits = job.gbuffer.hits
    # the object is lit: its pixels are not all the same shade, and the background is the environment colour
    lit = second[..., :3][_downsampled(hits, 2)]
    assert lit.std() > 8
    assert tuple(second[0, 0, :3]) == pytest.approx(_srgb(np.array(job.scene.environment.color) / 255.0), abs=2)
    job.close()


def _downsampled(mask: np.ndarray, factor: int) -> np.ndarray:
    h, w = mask.shape[0] // factor, mask.shape[1] // factor
    return mask[:h * factor, :w * factor].reshape(h, factor, w, factor).all(axis=(1, 3))


def _srgb(c: np.ndarray) -> tuple:
    lo, hi = c * 12.92, 1.055 * np.power(np.maximum(c, 1e-9), 1 / 2.4) - 0.055
    return tuple(np.where(c <= 0.0031308, lo, hi) * 255)


def test_points_display_shows_palette_colours_unlit_and_cancellation_returns_none():
    s = scene()
    s.solid.display = "points"
    s.environment.visible = False
    job = CpuEngine(threads=1).start(tetrahedron(), SETTINGS.with_solid(s))
    image = job.run_pass()
    assert job.shadow_maps == {}                       # no shadow maps are built for the unlit display
    assert image[0, 0, 3] == 0                          # transparent background
    job.close()
    job = CpuEngine(threads=1).start(tetrahedron(), SETTINGS.with_solid(scene()))
    assert job.run_pass(lambda: True) is None
    job.close()


def test_shade_reads_materials_and_fixed_colours():
    flame = tetrahedron()
    view = View(flame.camera, 8, 8, 1)
    gbuffer = GBuffer(8, 8)
    gbuffer.depth[:] = 1.0
    yy, xx = np.mgrid[0:8, 0:8]
    gbuffer.pos[..., 0], gbuffer.pos[..., 1], gbuffer.pos[..., 2] = xx * 0.1, yy * 0.1, -1.0    # a plane facing the camera
    gbuffer.color[:] = 128
    gbuffer.material[:] = 1
    gbuffer.count[:] = 10
    s = Scene3D("m", flame, materials=[Material(), Material(color_mode="fixed", color=(255, 0, 0), specular=0.0)])
    s.solid.ao = False
    s.environment.visible = False
    image = shade(view, gbuffer, s, flame, {}, (0.5, 1.5))
    assert image[4, 4, 0] > 100 and image[4, 4, 1] < 10 and image[4, 4, 2] < 10 and image[4, 4, 3] == 255


# --- GPU engine ----------------------------------------------------------------------------------------------------
@needs_gl
def test_gpu_solid_job_matches_the_cpu_shading_of_its_own_gbuffer():
    from fractalchemy.render.gpu_engine import GpuEngine
    engine = GpuEngine()
    s = scene()
    s.solid.ao_samples = 8
    job = engine.start(tetrahedron(), SETTINGS.with_solid(s))
    assert job.stats.engine.startswith("GPU solid")
    image = job.run_pass()
    assert image.shape == (64, 96, 4) and job.stats.passes_done == 1
    # rebuild the GPU's G-buffer and shadow maps on the CPU side and shade them with the numpy shader
    w, h = job.view.size
    raw = np.frombuffer(job.gbuffer_tex.read(), dtype=np.float32).reshape(h, w, 4)
    gbuffer = GBuffer(w, h)
    hit = raw[..., 3] >= 0
    assert hit.mean() > 0.05
    gbuffer.depth[hit] = -raw[..., 2][hit]
    gbuffer.pos[:] = raw[..., :3]
    code = np.rint(raw[..., 3]).astype(np.int32)
    gbuffer.color[hit] = (code & 255)[hit]
    gbuffer.material[hit] = (code >> 8)[hit]
    gbuffer.count[:] = np.rint(np.frombuffer(job.count_tex.read(), dtype=np.float32).reshape(h, w)).astype(np.int32)
    assert gbuffer.count[hit].min() >= 1 and (gbuffer.count[hit] >= s.solid.min_hits).mean() > 0.5
    assert set(np.unique(gbuffer.material[hit])) <= {0, 1, 2, 3} and len(np.unique(gbuffer.material[hit])) == 4
    maps = {}
    for index, shadow in job.shadow_maps.items():
        copy = shadow.empty_copy()
        copy.depth[:] = np.frombuffer(job.shadow_textures[index][0].read(), dtype=np.float32).reshape(shadow.size, shadow.size)
        copy.depth[copy.depth > 1e29] = np.inf
        maps[index] = copy
    assert 0 in maps and 1 not in maps               # the default scene: the key light casts shadows, the fill does not
    for display, min_hits in (("points", 3), ("solid", 3), ("solid", 1)):
        s.solid.display, s.solid.min_hits = display, min_hits
        expected = shade(job.view, gbuffer, s, job.flame, maps, job.depth_range).astype(int)
        got = job.image().astype(int)
        diff = np.abs(expected - got)
        assert diff.mean() < 0.5 and (diff.max(axis=2) > 8).mean() < 0.002, (display, min_hits)
    # the threshold empties sparse pixels: fewer surface pixels than without it
    assert gbuffer.thresholded(3).hits.sum() < gbuffer.hits.sum() and gbuffer.thresholded(1) is gbuffer
    job.run_pass()
    assert job.stats.finished
    job.close()
    job.close()                                        # idempotent
    engine.close()


@needs_gl
def test_gpu_and_cpu_solid_renders_agree_overall():
    from fractalchemy.render.gpu_engine import GpuEngine
    settings = RenderSettings(96, 64, passes=1, points=16384, fuse=10, oversample=2).with_solid(scene())
    engine = GpuEngine()
    gpu_job = engine.start(tetrahedron(), settings)
    gpu = gpu_job.run_pass().astype(float)
    cpu_job = CpuEngine(threads=2).start(tetrahedron(), settings)
    cpu = cpu_job.run_pass().astype(float)
    assert abs(gpu[..., :3].mean() - cpu[..., :3].mean()) < 6
    assert np.abs(np.array(gpu_job.depth_range) - np.array(cpu_job.depth_range)).max() < 0.3
    gpu_job.close()
    cpu_job.close()
    engine.close()


# --- service -------------------------------------------------------------------------------------------------------
def test_render_service_runs_solid_jobs(qapp):
    service = RenderService(prefer_gpu=False)
    service.start()
    try:
        done, failed = [], []
        service.pass_done.connect(lambda key, image, stats: done.append((key, image.shape, stats.engine)))
        service.job_failed.connect(lambda key, message: failed.append(message))
        service.submit("solid", tetrahedron(), SETTINGS.with_solid(scene()))
        assert wait_for(lambda: (spin(20), len(done) >= 2)[1], timeout=60), failed
        assert done[0][0] == "solid" and done[0][1] == (64, 96, 4) and "solid" in done[0][2]
    finally:
        service.stop()


# --- the window ----------------------------------------------------------------------------------------------------
from tests.conftest import wait_until  # noqa: E402


@pytest.fixture
def main(main_window_factory):
    win = main_window_factory(cheap_renders=True)
    yield win
    if win._three_d is not None:
        win._three_d.document._modified = False


def three_d(win):
    """Open the 3D Editor from the main window, small and on the draft quality so renders stay quick."""
    win.actionThreeDEditor.trigger()
    editor = win.three_d_editor
    editor.resize(760, 420)
    editor.viewport.set_quality("Draft")
    wait_until(lambda: editor.isVisible())
    return editor


def wait_rendered(editor, timeout_ms: int = 60000) -> None:
    wait_until(lambda: editor.viewport.up_to_date, timeout_ms=timeout_ms)


def test_three_d_editor_opens_from_the_windows_menu_and_pulls_the_main_fractal(main):
    assert main._three_d is None
    assert main.actionThreeDEditor in main.menuWindows.actions() and main.actionThreeDEditor in main.toolBar.actions()
    assert main.actionThreeDEditor.shortcut().toString() == "F11" and not main.actionThreeDEditor.icon().isNull()
    main.show_flame(tetrahedron())
    editor = three_d(main)
    assert editor.parent() is main and editor.isWindow() and editor.windowTitle().startswith("3D Editor — tetrahedron")
    assert editor.document.flame is not None and editor.document.flame is not main.document.flame
    assert len(editor.document.scene.materials) == 4 and editor.materials_panel.list.count() == 4
    assert [editor.tabs.tabText(i) for i in range(editor.tabs.count())] == ["Render", "Camera", "Materials", "Lights", "Environment", "Mesh", "Export"]
    wait_rendered(editor)
    stats = editor.viewport.stats
    assert stats.engine.startswith("CPU solid") and "pass" in editor.progress_label.text() and editor.engine_label.text() == stats.engine
    assert editor.viewport.image is not None and editor.viewport.image.width() == editor.viewport.width()
    editor.hide()
    main.actionThreeDEditor.trigger()
    assert editor.isVisible() and main.three_d_editor is editor


def test_orbit_pan_zoom_write_the_camera_as_merged_undo_steps_and_reset_goes_home(main):
    main.show_flame(tetrahedron())
    editor = three_d(main)
    doc, view = editor.document, editor.viewport
    home = doc.flame.camera.copy()
    view.orbit(0.2, 0.1)
    view.orbit(0.2, 0.1)
    assert doc.flame.camera.yaw == pytest.approx(0.4) and doc.flame.camera.pitch == pytest.approx(home.pitch + 0.2)
    assert doc.can_undo and len(doc._undo) == 2                  # "Use main fractal" + one merged orbit step
    assert abs(editor.camera_panel.yaw.value() - 0.4 * 57.2957795) < 0.11
    doc.end_merge()
    view.pan(50, 0)
    assert doc.flame.camera.center[0] < home.center[0] and len(doc._undo) == 3
    view.zoom_by(2)
    assert doc.flame.camera.zoom == pytest.approx(home.zoom + 0.5) and len(doc._undo) == 4
    view.change_perspective(2)
    assert doc.flame.camera.perspective == pytest.approx(home.perspective + 0.1)
    assert editor.undo_action.isEnabled() and editor.undo_action.text() == "Undo Move camera"
    editor.undo_action.trigger()
    assert doc.flame.camera.perspective == pytest.approx(home.perspective) and doc.can_redo
    editor.redo_action.trigger()
    assert doc.flame.camera.perspective == pytest.approx(home.perspective + 0.1)
    view.reset_view()
    c = doc.flame.camera
    assert (c.pitch, c.yaw, c.zoom, c.center, c.perspective) == (home.pitch, home.yaw, home.zoom, home.center, home.perspective)
    # the camera panel writes degrees back
    editor.camera_panel.pitch.spin.setValue(45.0)
    assert doc.flame.camera.pitch == pytest.approx(45 / 57.2957795, abs=1e-3) and doc.undo_label == "Move camera"
    assert view.generation > 1


def test_panels_edit_materials_lights_environment_and_renderer_through_the_document(main):
    main.show_flame(tetrahedron())
    editor = three_d(main)
    doc = editor.document
    # materials
    editor.materials_panel.select(2)
    editor.materials_panel.diffuse.spin.setValue(1.4)
    editor.materials_panel.mode_box.setCurrentIndex(1)
    assert doc.scene.materials[2].diffuse == 1.4 and doc.scene.materials[2].color_mode == "fixed" and doc.scene.materials[0].diffuse == 0.8
    assert editor.materials_panel.color.isEnabled()
    editor.materials_panel.copy_button.click()
    assert all(m.diffuse == 1.4 and m.color_mode == "fixed" for m in doc.scene.materials) and doc.undo_label == "Copy material to all"
    # lights
    assert editor.lights_panel.list.count() == 2
    editor.lights_panel.add_button.click()
    assert len(doc.scene.lights) == 3 and editor.lights_panel.current_index() == 2
    editor.lights_panel.altitude.spin.setValue(12.0)
    editor.lights_panel.shadows_check.setChecked(True)
    assert doc.scene.lights[2].altitude == 12.0 and doc.scene.lights[2].shadows and editor.lights_panel.shadow_softness.isEnabled()
    editor.lights_panel.remove_button.click()
    assert len(doc.scene.lights) == 2
    doc.undo()
    assert len(doc.scene.lights) == 3 and doc.scene.lights[2].altitude == 12.0
    # environment and renderer
    editor.environment_panel.ambient.spin.setValue(1.2)
    editor.environment_panel.visible_check.setChecked(False)
    assert doc.scene.environment.ambient == 1.2 and not doc.scene.environment.visible
    editor.render_panel.ao_check.setChecked(False)
    assert not doc.scene.solid.ao and not editor.render_panel.ao_radius.isEnabled()
    editor.render_panel.fog_check.setChecked(True)
    assert doc.scene.solid.fog and editor.render_panel.fog_start.isEnabled()
    editor.points_action.setChecked(True)
    assert doc.scene.solid.display == "points" and editor.render_panel.display_box.currentData() == "points"
    editor.render_panel.display_box.setCurrentIndex(0)
    assert doc.scene.solid.display == "solid" and not editor.points_action.isChecked()
    assert doc.modified and editor.windowTitle().endswith("•")
    editor.render_panel.quality_box.setCurrentIndex(2)
    assert editor.viewport.quality.name == "Fine"


def test_follow_re_pulls_the_main_fractal_keeping_the_orbited_camera_and_send_pushes_it_back(main):
    main.show_flame(tetrahedron())
    editor = three_d(main)
    doc = editor.document
    editor.viewport.orbit(0.5, 0.0, interactive=False)
    editor.follow_action.setChecked(True)
    assert doc.scene.follow_main
    main.document.set_xform_fields(0, color=0.77)
    assert doc.flame.xforms[0].color != 0.77                # not yet: the pull waits for the edits to pause
    wait_until(lambda: doc.flame.xforms[0].color == 0.77, timeout_ms=5000)
    assert doc.flame.camera.yaw == pytest.approx(0.5)        # the camera set here survives the re-pull
    assert doc.undo_label == "Follow main window"
    editor.follow_action.setChecked(False)
    main.document.set_xform_fields(0, color=0.11)
    spin(1300)
    assert doc.flame.xforms[0].color == 0.77
    sent = []
    editor.flame_sent.connect(sent.append)
    editor.send_action.trigger()
    assert sent and sent[0].camera.yaw == pytest.approx(0.5) and main.document.flame.camera.yaw == pytest.approx(0.5)
    assert main.document.flame.xforms[0].color == 0.77


def test_scene_files_new_open_save_and_state_persist_between_windows(main, tmp_path):
    main.show_flame(tetrahedron())
    editor = three_d(main)
    doc = editor.document
    editor.lights_panel.add_button.click()
    path = tmp_path / "scenes" / "tetra.fa3d"
    assert editor.save_scene_as(path) and path.exists() and doc.path == path and not doc.modified
    assert editor.windowTitle() == "3D Editor — tetra.fa3d" and editor.file_label.text() == str(path)
    editor.viewport.zoom_by(1)
    assert doc.modified
    assert editor.save_scene() and not doc.modified
    editor.new_scene(ask=False)
    assert doc.flame is None and doc.path is None and not editor.render_action.isEnabled() and editor.windowTitle() == "3D Editor"
    assert editor.open_scene(path, ask=False)
    assert doc.flame is not None and len(doc.scene.lights) == 3 and doc.flame.camera.zoom == pytest.approx(0.25)
    assert not editor.open_scene(tmp_path / "missing.fa3d", ask=False)
    # the scene survives a restart
    editor.viewport.orbit(0.3, 0.0, interactive=False)
    editor.save_state()
    from fractalchemy.ui.three_d import ThreeDWindow
    again = ThreeDWindow(main.render_service, None, main._settings, main_document=main.document, prefer_gpu=False)
    try:
        assert again.document.flame is not None and again.document.flame.camera.yaw == pytest.approx(0.3)
        assert again.document.path == path and again.document.modified and len(again.document.scene.lights) == 3
    finally:
        again.close()


def test_render_window_renders_the_scene_to_a_file_on_its_own_thread(main, tmp_path):
    main.show_flame(tetrahedron())
    editor = three_d(main)
    editor.render_action.trigger()
    rw = editor.render_window
    wait_until(lambda: rw.isVisible())
    assert rw.windowTitle() == "Render 3D Image — tetrahedron" and not rw.output_panel.save_details.isVisible()
    assert rw.output_panel.path.text().endswith("tetrahedron-3d.png")
    rw.size_panel.set_size(64, 48)
    rw.quality_panel.quality.setValue(8)
    rw.quality_panel.passes.setValue(2)
    rw.quality_panel.oversample.setValue(1)
    out = tmp_path / "out" / "tetra.png"
    rw.output_panel.set_path(str(out))
    rw.output_panel.save_parameters.setChecked(True)
    assert rw.start_button.isEnabled() and "64 × 48" in rw.plan_label.text() and "CPU" in rw.plan_label.text()
    rw.start(ask_overwrite=False)
    assert rw.rendering
    wait_until(lambda: rw.last_outcome is not None and not rw.rendering, timeout_ms=60000)
    outcome = rw.last_outcome
    assert outcome.complete and outcome.path == out and out.exists() and outcome.image.shape == (48, 64, 4)
    assert {p.suffix for p in outcome.extras} == {".flame", ".fa3d"} and all(p.exists() for p in outcome.extras)
    assert "Finished" in rw.progress_panel.result.text() and "tetra.png" in rw.progress_panel.result.text()
    from PIL import Image
    with Image.open(out) as image:
        assert image.size == (64, 48) and image.mode in ("RGB", "RGBA")
    assert rw.confirm_quit()
