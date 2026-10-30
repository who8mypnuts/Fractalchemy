"""Phase 4 of the 3D Editor: HDRI readers, the environment map (SH9, prefiltered levels, key lights), image-based lighting on
both engines, the Environment tab, the `mesh_…` formula and the SDF primitives."""

import numpy as np
import pytest

from fractalchemy.fractal import variations as V
from fractalchemy.fractal.scene import Flame, XForm
from fractalchemy.render.cpu_engine import CpuEngine
from fractalchemy.render.exr import write_exr
from fractalchemy.render.gpu_engine import gpu_available
from fractalchemy.render.settings import RenderSettings
from fractalchemy.scene3d import format as fa3d
from fractalchemy.scene3d.model import DistantLight, Instancer, Material, MeshAsset, Scene3D
from fractalchemy.solid import hdri as Hd
from fractalchemy.solid import holon as H
from fractalchemy.solid.capture import capture_points
from fractalchemy.solid.mesh_formula import formula_name, mesh_formula_source, register_mesh_formula, write_mesh_formula
from tests.conftest import spin, wait_until

needs_gl = pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")
SUN = np.array([1.0, 0.4, 0.5]) / np.linalg.norm([1.0, 0.4, 0.5])


def sky_image(h: int = 64, w: int = 128, sun: bool = True) -> np.ndarray:
    """A synthetic sky: blue above, warm below, a small very bright sun at `SUN`."""
    v, u = np.mgrid[0:h, 0:w]
    dirs = Hd.uv_to_direction((u + 0.5) / w, (v + 0.5) / h)
    sky = np.zeros((h, w, 3), np.float32)
    sky[..., 2] = np.clip(dirs[..., 2], 0, 1) * 0.9 + 0.1
    sky[..., 0] = 0.15 + 0.5 * np.clip(-dirs[..., 2], 0, 1)
    sky[..., 1] = 0.25
    if sun:
        sky[(dirs @ SUN) > np.cos(np.radians(4))] = (300.0, 280.0, 250.0)
    return sky


def holon_scene(hdri_path: str) -> Scene3D:
    flame = H.default_own_ifs()
    scene = Scene3D("holon", flame)
    scene.assets.append(MeshAsset("ball", "primitive", "sphere", 2, mesh=H.primitive("sphere", 2)))
    scene.instancers.append(Instancer("balls", "ball", "main", None, "tree", depth=2, tree_levels="all", size=0.7, color_mode="fixed",
                                      material=Material(color=(220, 220, 220), specular=0.6, shininess=80)))
    scene.solid.show_fractal = False
    scene.solid.ao = False
    scene.environment.hdri = hdri_path
    scene.lights = []
    return scene


# --- readers ------------------------------------------------------------------------------------------------------------
def test_hdr_and_exr_readers_round_trip_and_reject_other_files(tmp_path):
    sky = sky_image()
    Hd.write_hdr(tmp_path / "sky.hdr", sky)
    back = Hd.read_hdr(tmp_path / "sky.hdr")
    relative = np.abs(back - sky) / (sky.max(axis=2, keepdims=True) + 1e-6)     # RGBE: an 8-bit mantissa per pixel
    assert back.shape == sky.shape and relative.max() < 0.01
    for half, compress in ((False, True), (True, True), (False, False)):
        write_exr(tmp_path / "sky.exr", {"R": sky[..., 0], "G": sky[..., 1], "B": sky[..., 2]}, half=half, compress=compress)
        back = Hd.read_exr(tmp_path / "sky.exr")
        assert back.shape == sky.shape and np.abs(back - sky).max() / sky.max() < (1e-3 if half else 1e-6), (half, compress)
    write_exr(tmp_path / "grey.exr", {"Y": sky[..., 1]}, compress=True)
    assert Hd.read_exr(tmp_path / "grey.exr")[..., 0] == pytest.approx(sky[..., 1], abs=1e-6)
    from PIL import Image
    Image.fromarray((np.clip(sky, 0, 1) * 255).astype(np.uint8)).save(tmp_path / "sky.png")
    ldr = Hd.read_image_linear(tmp_path / "sky.png")
    assert ldr.shape == sky.shape and ldr.max() <= 1.0 and ldr[0, 0, 2] == pytest.approx(sky[0, 0, 2], abs=0.02)
    (tmp_path / "bad.hdr").write_bytes(b"nope")
    with pytest.raises(Hd.HdriError):
        Hd.read_hdr(tmp_path / "bad.hdr")
    with pytest.raises(Hd.HdriError):
        Hd.read_exr(tmp_path / "sky.hdr")
    with pytest.raises(Hd.HdriError):
        Hd.read_image_linear(tmp_path / "bad.hdr")


def test_environment_map_irradiance_levels_and_key_lights():
    flat = Hd.EnvironmentMap.from_image(np.full((32, 64, 3), 0.5, np.float32))
    assert flat.irradiance(np.array([[0, 0, 1.0], [1, 0, 0], [0, -1, 0]])) == pytest.approx(0.5, abs=0.01)
    assert flat.average == pytest.approx((0.5, 0.5, 0.5), abs=1e-6)
    env = Hd.EnvironmentMap.from_image(sky_image())
    assert env.image.shape == (64, 128, 3) and len(env.levels) == Hd.LEVELS and env.levels[-1].shape == (2, 4, 3)
    sunless = Hd.EnvironmentMap.from_image(sky_image(sun=False))
    up, down = sunless.irradiance(np.array([[0, 0, 1.0], [0, 0, -1.0]]))
    assert up[2] > down[2] and down[0] > up[0]                         # blue from above, warm from below
    towards, away = env.irradiance(np.array([SUN, -SUN]))
    assert towards.sum() > 3 * away.sum()
    sharp = env.sample(np.array([SUN]), 0.0)[0]
    soft = env.sample(np.array([SUN]), 4.0)[0]
    assert sharp[0] > 200 and soft[0] < 10                              # the prefiltered levels spread the sun out
    turned = env.sample(np.array([SUN]), 0.0, rotation=90.0)[0]
    assert turned[0] < 10                                                # the map turned away from the sun direction
    rotated_dir = np.asarray(SUN) @ Hd.rotation_about_z(90.0).T
    assert env.sample(np.array([rotated_dir]), 0.0, rotation=90.0)[0][0] > 200
    lights = env.key_lights(3)
    assert len(lights) == 3 and lights[0][2] == 1.0 and np.dot(lights[0][0], SUN) > np.cos(np.radians(6))
    assert lights[1][2] < 0.1 and lights[0][1][0] == 1.0                  # the fills are weak; the sun's colour peaks in red
    assert Hd.shininess_to_roughness(200) == pytest.approx(0.0) and Hd.shininess_to_roughness(1) == pytest.approx(1.0)
    assert Hd.roughness_to_level(np.array([0.0, 1.0]), 6).tolist() == [0.0, 5.0]
    uv = Hd.direction_to_uv(np.array([[1.0, 0, 0], [0, 0, 1.0]]))
    assert uv[0].tolist() == pytest.approx([0.0, 0.5]) and uv[1][1] == pytest.approx(0.0)
    assert Hd.solid_angle_weights(32, 64).sum() == pytest.approx(4 * np.pi, rel=1e-3)


def test_load_environment_caches_and_environment_for_tolerates_missing_files(tmp_path):
    Hd.write_hdr(tmp_path / "a.hdr", sky_image(16, 32))
    first = Hd.load_environment(tmp_path / "a.hdr")
    assert Hd.load_environment(tmp_path / "a.hdr") is first and first.path.endswith("a.hdr")
    from fractalchemy.scene3d.model import Environment
    assert Hd.environment_for(Environment()) is None
    assert Hd.environment_for(Environment(hdri=str(tmp_path / "missing.hdr"))) is None
    assert Hd.environment_for(Environment(hdri=str(tmp_path / "a.hdr"))) is first


# --- lighting -------------------------------------------------------------------------------------------------------------
def test_cpu_render_uses_the_hdri_for_light_and_background(tmp_path):
    Hd.write_hdr(tmp_path / "sky.hdr", sky_image())
    scene = holon_scene(str(tmp_path / "sky.hdr"))
    settings = RenderSettings(96, 72, passes=1, quality=6, points=4096, fuse=10, oversample=1).with_solid(scene)
    job = CpuEngine(threads=1).start(scene.fractal, settings)
    lit = job.run_pass().astype(int)
    job.close()
    # the background is the sky (a gradient, not the flat colour) and the spheres are lit without any distant light
    assert lit[0, 0, :3].tolist() != list(scene.environment.color) and lit[..., :3].std() > 10
    scene.environment.hdri_background = False
    job = CpuEngine(threads=1).start(scene.fractal, settings)
    colour_bg = job.run_pass().astype(int)
    job.close()
    corner = colour_bg[0, 0, :3]
    assert abs(corner - lit[0, 0, :3]).max() > 5                          # the background colour shows instead
    scene.environment.hdri = ""
    job = CpuEngine(threads=1).start(scene.fractal, settings)
    dark = job.run_pass().astype(int)
    job.close()
    assert lit[..., :3].mean() > dark[..., :3].mean()                     # without the HDRI (and no lights) it is darker


@needs_gl
def test_gpu_render_agrees_with_the_cpu_under_an_hdri(tmp_path):
    from fractalchemy.render.gpu_engine import GpuEngine
    Hd.write_hdr(tmp_path / "sky.hdr", sky_image())
    scene = holon_scene(str(tmp_path / "sky.hdr"))
    scene.environment.hdri_rotation = 45.0
    scene.environment.hdri_blur = 0.3
    settings = RenderSettings(120, 90, passes=1, quality=6, points=4096, fuse=10, oversample=1).with_solid(scene)
    engine = GpuEngine()
    gpu_job = engine.start(scene.fractal, settings)
    gpu = gpu_job.run_pass().astype(float)
    gpu_job.close()
    engine.close()
    cpu_job = CpuEngine(threads=1).start(scene.fractal, settings)
    cpu = cpu_job.run_pass().astype(float)
    cpu_job.close()
    assert np.abs(gpu[..., :3] - cpu[..., :3]).mean() < 6 and abs(gpu[..., :3].mean() - cpu[..., :3].mean()) < 4
    assert np.abs(gpu[0, 0, :3] - cpu[0, 0, :3]).max() < 6                # the background rays agree


def test_environment_settings_live_in_the_scene_file(tmp_path):
    scene = Scene3D("e", H.default_own_ifs())
    scene.environment.hdri = "x.hdr"
    scene.environment.hdri_rotation = 33.0
    scene.environment.hdri_blur = 0.4
    scene.environment.hdri_background = False
    copy = fa3d.scene_from_text(fa3d.scene_to_text(scene))
    assert copy.environment.hdri == "x.hdr" and copy.environment.hdri_rotation == 33.0 and not copy.environment.hdri_background


# --- the mesh formula and the SDF primitives ---------------------------------------------------------------------------------
def test_mesh_formula_samples_the_mesh_surface_on_both_engines(tmp_path):
    mesh = H.primitive("torus", 1)
    assert formula_name("My Ball!") == "mesh_my_ball"
    source = mesh_formula_source(mesh, "mesh_torus")
    assert "static const double mesh_torus_tri" in source and "APO_PLUGIN(\"mesh_torus\")" in source
    var = register_mesh_formula(mesh, "torus")
    assert var.name == "mesh_torus" and var.random and V.resolve("mesh_torus") is var
    flame = Flame("m", [XForm(variations={"mesh_torus": 1.0})])
    cloud = capture_points(flame, 5000)
    ring = np.hypot(cloud.xyz[:, 0], cloud.xyz[:, 1])
    assert 0.2 < ring.min() and ring.max() <= 0.5 + 1e-3 and np.abs(cloud.xyz[:, 2]).max() < 0.14
    path = write_mesh_formula(mesh, "torus", tmp_path)
    assert path == tmp_path / "mesh_torus.c" and path.read_text().startswith("/*")
    big = H.primitive("sphere", 4)                                        # 5120 faces: decimated to the table limit
    assert "mesh_ball_cdf[1024]" in mesh_formula_source(big, "mesh_ball")
    with pytest.raises(ValueError):
        mesh_formula_source(H.primitive("sphere", 0).subset(np.zeros(0, dtype=bool)), "mesh_empty")
    if gpu_available()[0]:
        from fractalchemy.formulas.verify import compare
        from fractalchemy.render.gpu_engine import _create_context
        ctx = _create_context()
        try:
            report = compare(var, ctx)
            assert report.ok, report.summary() if hasattr(report, "summary") else report
        finally:
            ctx.release()


def test_sdf_primitives_fill_their_shapes_and_stray_points_go_off_frame():
    for name, inside_check in (
        ("box3D", lambda p: (np.abs(p) <= 0.5 + 1e-6).all(axis=1)),
        ("torus3D", lambda p: np.hypot(np.hypot(p[:, 0], p[:, 2]) - 0.5, p[:, 1]) <= 0.5 + 1e-6),
        ("octahedron3D", lambda p: np.abs(p).sum(axis=1) <= 0.25 + 1e-6),
        ("cylinder3D", lambda p: (np.hypot(p[:, 0], p[:, 2]) <= 0.3 + 1e-6) & (np.abs(p[:, 1]) <= 0.25 + 1e-6)),
    ):
        assert V.resolve(name) is not None, name
        cloud = capture_points(Flame(name, [XForm(variations={name: 1.0})]), 3000)
        near = cloud.xyz[np.abs(cloud.xyz).max(axis=1) < 1.0]
        assert len(near) > 100 and inside_check(near.astype(np.float64)).mean() > 0.97, name
    # a thin capsule rejects most samples: those add nothing (the point stays where the affine put it — here the origin)
    cloud = capture_points(Flame("c", [XForm(variations={"capsule3D": 1.0})]), 3000)
    at_origin = np.abs(cloud.xyz).max(axis=1) < 1e-9
    near = cloud.xyz[~at_origin]
    assert at_origin.mean() > 0.5 and (np.abs(near).max(axis=1) < 0.2).all()
    for name in ("rbox3D", "ellipsoid3D", "cappedtorus3D", "cone3D", "pyramid3D", "hexprism3D", "rhombus3D"):
        assert V.resolve(name) is not None, name


# --- the window ---------------------------------------------------------------------------------------------------------------
@pytest.fixture
def main(main_window_factory):
    win = main_window_factory(cheap_renders=True)
    yield win
    if win._three_d is not None:
        win._three_d.wait_for_jobs()
        win._three_d.document._modified = False


def test_environment_tab_takes_an_hdri_extracts_key_lights_and_registers_mesh_formulas(main, tmp_path, monkeypatch):
    from fractalchemy.formulas import loader
    monkeypatch.setenv(loader.ENV_VAR, str(tmp_path / "formulas"))
    main.show_flame(H.default_own_ifs())
    main.actionThreeDEditor.trigger()
    editor = main.three_d_editor
    editor.resize(900, 600)
    editor.viewport.set_quality("Draft")
    wait_until(lambda: editor.isVisible())
    panel = editor.environment_panel
    editor.tabs.setCurrentWidget(panel)
    doc = editor.document
    assert not panel.rotation.isEnabled() and panel.thumbnail.text() == "No HDRI"
    Hd.write_hdr(tmp_path / "sky.hdr", sky_image())
    assert not panel.choose_hdri(tmp_path / "missing.hdr")
    assert panel.choose_hdri(tmp_path / "sky.hdr") and doc.scene.environment.hdri.endswith("sky.hdr") and doc.undo_label == "Edit environment"
    assert panel.rotation.isEnabled() and panel.thumbnail.pixmap() is not None and not panel.thumbnail.pixmap().isNull()
    panel.rotation.spin.setValue(40.0)
    panel.blur.spin.setValue(0.5)
    panel.background_check.setChecked(False)
    env = doc.scene.environment
    assert env.hdri_rotation == 40.0 and env.hdri_blur == 0.5 and not env.hdri_background
    before = len(doc.scene.lights)
    assert panel.extract_key_lights(2) == 2 and len(doc.scene.lights) == before + 2
    sun, fill = doc.scene.lights[-2:]
    assert sun.shadows and not fill.shadows and sun.intensity == 1.0 and fill.intensity < sun.intensity and sun.color[0] == 255
    doc.undo()
    assert len(doc.scene.lights) == before
    wait_until(lambda: editor.viewport.up_to_date, timeout_ms=120000)
    assert editor.viewport.image is not None
    panel.clear_button.click()
    assert doc.scene.environment.hdri == "" and not panel.rotation.isEnabled()
    # a mesh asset as a formula
    instances = editor.instances_panel
    instances._add_primitive("cube")
    refreshed = []
    editor.formulas_changed.connect(lambda: refreshed.append(True))
    name = instances.register_formula(tmp_path / "formulas")
    assert name == "mesh_cube" and refreshed and V.resolve("mesh_cube") is not None and (tmp_path / "formulas" / "mesh_cube.c").exists()
    assert any(row.name == "mesh_cube" for row in main.editor.variations_tab.rows()) if hasattr(main.editor.variations_tab, "rows") else True
    spin(50)


# --- the leftovers of the plan: point lights, tone curves, affine3D, the 3D crops, DLA assets, self-intersections -------------------
def test_point_lights_and_tone_curves_agree_on_both_engines():
    scene = holon_scene("")
    scene.fractal.coloring.curves.set_points("overall", [(0, 0), (0.5, 0.75), (1, 1)])
    scene.lights = [DistantLight(kind="point", position=(0.0, 0.0, 0.2), radius=0.4, intensity=1.5, color=(255, 200, 120), shadows=True)]
    assert scene.lights[0].is_point and not scene.lights[0].casts_shadows
    settings = RenderSettings(96, 72, passes=1, quality=6, points=4096, fuse=10, oversample=1).with_solid(scene)
    job = CpuEngine(threads=1).start(scene.fractal, settings)
    lit = job.run_pass().astype(float)
    assert job.shadow_maps == {}                                          # point lights build no shadow map
    job.close()
    scene.lights[0].intensity = 0.0
    job = CpuEngine(threads=1).start(scene.fractal, settings)
    dark = job.run_pass().astype(float)
    job.close()
    assert (lit[..., :3] - dark[..., :3]).max() > 30 and lit[..., :3].mean() > dark[..., :3].mean()   # the point light lights the spheres
    copy = fa3d.scene_from_text(fa3d.scene_to_text(scene))
    assert copy.lights[0].kind == "point" and copy.lights[0].position == (0.0, 0.0, 0.2)
    if gpu_available()[0]:
        from fractalchemy.render.gpu_engine import GpuEngine
        scene.lights[0].intensity = 1.5
        engine = GpuEngine()
        gpu_job = engine.start(scene.fractal, settings)
        gpu = gpu_job.run_pass().astype(float)
        gpu_job.close()
        engine.close()
        job = CpuEngine(threads=1).start(scene.fractal, settings)
        cpu = job.run_pass().astype(float)
        job.close()
        assert np.abs(gpu[..., :3] - cpu[..., :3]).mean() < 6


def test_affine3d_and_the_3d_crops_are_in_the_library():
    from fractalchemy.render.compiled import CompiledXForm
    xform = XForm(variations={"affine3D": 1.0}, params={"affine3D_translateX": 0.3, "affine3D_translateY": -0.2, "affine3D_translateZ": 0.5,
                  "affine3D_scaleX": 0.4, "affine3D_scaleY": 0.4, "affine3D_scaleZ": 0.4, "affine3D_rotateX": 20, "affine3D_rotateY": -35,
                  "affine3D_rotateZ": 60})
    x, y, z, _c, jac = H.apply_with_jacobian(CompiledXForm.build(xform), np.array([0.1]), np.array([0.2]), np.array([0.3]), np.array([0.5]),
                                             np.random.default_rng(0))
    ax, ay, az = np.radians([20, -35, 60])                               # JWildfire rotates about x, then y, then z: R = Rz · Ry · Rx
    rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    rotation = rz @ ry @ rx
    assert np.allclose(jac[0], rotation * 0.4, atol=1e-6)
    assert np.allclose([x[0], y[0], z[0]], rotation @ (0.4 * np.array([0.1, 0.2, 0.3])) + np.array([0.3, -0.2, 0.5]), atol=1e-9)
    assert V.resolve("pre_affine3D").kind == "pre" and V.resolve("post_affine3D").kind == "post"
    for name in ("post_mandelbulb3d_crop", "post_mandelbox3d_crop", "post_aexion_crop"):
        assert V.resolve(name) is not None and V.resolve(name).kind == "post", name
    # the bulb crop keeps points inside the Mandelbulb and zeroes the rest
    flame = Flame("bulb", [XForm(variations={"linear3D": 1.0, "post_mandelbulb3d_crop": 1.0},
                                 params={"post_mandelbulb3d_crop_power": 8, "post_mandelbulb3d_crop_filled": 1, "post_mandelbulb3d_crop_iterations": 8})])
    cloud = capture_points(flame, 4000)
    radii = np.linalg.norm(cloud.xyz, axis=1)
    kept = radii > 1e-6
    assert 0.01 < kept.mean() < 0.9 and radii[kept].max() < 1.3          # the bulb fills a few percent of the (VVAR + 1) · 2 box


def test_dla_assets_and_the_self_intersection_check():
    from fractalchemy.solid.mesh import Mesh, self_intersections
    coral = H.primitive("dla", 0)
    rep = coral.report()
    assert coral.face_count > 500 and rep.watertight and rep.components == 1 and coral.extent().max() == pytest.approx(1.0)
    grid = H.dla_grid(300, 32, seed=2)
    assert 250 <= grid.sum() <= 400 and grid[16, 16, 16]            # walkers landing on one cell in a round are counted once in the grid
    assert self_intersections(H.primitive("sphere", 2))[0] == 0
    a = H.primitive("cube", 1)
    b = a.transformed(offset=(0.3, 0.2, 0.1))
    both = Mesh(np.vstack([a.vertices, b.vertices]), np.vstack([a.faces, b.faces + a.vertex_count]))
    found, checked = self_intersections(both)
    assert found > 0 and checked > 0
    report = both.report()
    assert report.self_intersections == found and not report.printable and "self-intersecting" in report.recommendation()
    assert a.report().self_intersections == 0 and a.report(intersections=False).self_intersections is None
