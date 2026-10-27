"""Rendering: tone map (numpy vs GLSL), CPU and GPU engines, and the render service."""

import numpy as np
import pytest

from fractalchemy.fractal import Flame, XForm
from fractalchemy.fractal.formats import load_flame
from fractalchemy.fractal.scene import Coloring
from fractalchemy.render.compiled import CompiledFlame, selection_table
from fractalchemy.render.cpu_engine import CpuEngine
from fractalchemy.render.gpu_engine import gpu_available
from fractalchemy.render.service import PRIORITY_THUMBNAIL, RenderService, wait_for
from fractalchemy.render.settings import RenderSettings
from fractalchemy.render.tonemap import FULLSCREEN_VERTEX_GLSL, TONEMAP_GLSL, ToneParams, tonemap
from tests.conftest import spin

needs_gl = pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")
SMALL = RenderSettings(96, 64, passes=2, quality=20, points=4096, fuse=10)


def sierpinski() -> Flame:
    """Three half-scale translations: a dependable, fast-converging test flame."""
    flame = Flame("sierpinski", [
        XForm(coefs=(0.5, 0, 0, 0.5, 0, 0), color=0.0),
        XForm(coefs=(0.5, 0, 0, 0.5, 0.5, 0), color=0.5),
        XForm(coefs=(0.5, 0, 0, 0.5, 0, 0.5), color=1.0),
    ])
    flame.camera.center = (0.5, 0.5)
    flame.camera.scale = 60
    flame.camera.width, flame.camera.height = 96, 64
    flame.coloring.brightness = 8
    return flame


# --- settings / compilation ---------------------------------------------------
def test_settings_scale_and_split_into_passes():
    s = RenderSettings(200, 100, passes=4, quality=2)
    assert s.samples_total == 40000 and s.samples_per_pass == 10000
    assert s.scaled(0.5).width == 100 and s.scaled(0.5).height == 50 and s.with_size(3, 0).height == 1


def test_selection_table_applies_xaos_and_recovers_from_dead_rows():
    table = selection_table([XForm(weight=1, chaos=[0, 1]), XForm(weight=3, chaos=[0, 0])])
    assert table[0].tolist() == [0.0, 1.0]            # after xform 0 only xform 1 may follow
    assert table[1].tolist() == pytest.approx([0.25, 1.0])   # dead row falls back to plain weights


def test_compiled_flame_drops_zero_weight_xforms_and_identity_final():
    flame = sierpinski()
    flame.xforms.append(XForm(weight=0))
    flame.final = XForm(color_speed=0.0)
    compiled = CompiledFlame.build(flame)
    assert compiled.count == 3 and compiled.final is None and compiled.palette.shape == (256, 3)
    with pytest.raises(ValueError):
        CompiledFlame.build(Flame("empty", [XForm(weight=0)]))


# --- tone map -----------------------------------------------------------------
def synthetic_histogram() -> np.ndarray:
    rng = np.random.default_rng(3)
    hist = np.zeros((8, 16, 4), dtype=np.float32)
    count = rng.integers(0, 400, (8, 16)).astype(np.float32)
    count[0, 0] = 0
    count[1, 1] = 1
    colour = rng.random((8, 16, 3)).astype(np.float32)
    hist[..., :3] = colour * count[..., None]
    hist[..., 3] = count
    return hist


def test_tonemap_numpy_behaves_like_apophysis():
    params = ToneParams.derive(Coloring(brightness=4, gamma=4, gamma_threshold=0.01, background=(10, 20, 30)), 50.0, 2_000_000)
    image = tonemap(synthetic_histogram(), params)
    assert image.shape == (8, 16, 4) and image.dtype == np.uint8 and (image[..., 3] == 255).all()
    assert image[0, 0, :3].tolist() == [10, 20, 30]          # empty pixel shows the background
    brighter = tonemap(synthetic_histogram(), ToneParams.derive(Coloring(brightness=40, gamma=4), 50.0, 2_000_000))
    assert brighter[..., :3].mean() > image[..., :3].mean()


@needs_gl
def test_tonemap_glsl_matches_numpy(gl_context):
    import moderngl
    ctx = gl_context
    hist = synthetic_histogram()
    params = ToneParams.derive(Coloring(brightness=6, gamma=2.2, gamma_threshold=0.05, vibrancy=0.6, background=(0, 30, 60)), 40.0, 600_000)
    expected = tonemap(hist, params)
    prog = ctx.program(vertex_shader=FULLSCREEN_VERTEX_GLSL, fragment_shader=TONEMAP_GLSL)
    tex = ctx.texture((16, 8), 4, hist.tobytes(), dtype="f4")
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    out = ctx.texture((16, 8), 4)
    fbo = ctx.framebuffer([out])
    fbo.use()
    tex.use(0)
    prog["u_histogram"].value = 0
    for name, value in params.as_uniforms().items():
        prog[name].value = value
    ctx.vertex_array(prog, []).render(mode=moderngl.TRIANGLES, vertices=3)
    actual = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(8, 16, 4)
    assert np.abs(actual[..., :3].astype(int) - expected[..., :3].astype(int)).max() <= 2


# --- engines ------------------------------------------------------------------
def test_cpu_engine_renders_progressively_with_stats():
    job = CpuEngine(threads=2).start(sierpinski(), SMALL)
    first = job.run_pass()
    assert first.shape == (64, 96, 4) and not job.stats.finished and job.stats.passes_done == 1
    second = job.run_pass()
    assert job.stats.finished and job.stats.samples >= SMALL.samples_total * 0.9
    assert job.stats.hits > 0 and job.stats.engine.startswith("CPU")
    assert first[..., :3].max() > 40 and second[..., :3].mean() > 0
    # the gasket spans pixels x 18..78, y 2..62 (y down): its big central hole is empty, its edges are lit
    assert second[42, 58, :3].max() < 30 and second[3, 48, :3].max() > 30 and second[32, 19, :3].max() > 30
    job.close()


def test_cpu_engine_honours_cancellation():
    job = CpuEngine(threads=1).start(sierpinski(), SMALL)
    assert job.run_pass(lambda: True) is None and job.stats.passes_done == 0
    job.close()


@needs_gl
def test_gpu_engine_agrees_with_cpu_engine():
    from fractalchemy.render.gpu_engine import GpuEngine
    engine = GpuEngine()
    settings = RenderSettings(96, 64, passes=1, quality=60, points=4096, fuse=10)
    gpu_job = engine.start(sierpinski(), settings)
    gpu = gpu_job.run_pass().astype(int)
    assert gpu_job.stats.finished and gpu_job.stats.engine.startswith("GPU")
    cpu_job = CpuEngine(threads=2).start(sierpinski(), settings)
    cpu = cpu_job.run_pass().astype(int)
    # same structure: the empty centre, the filled corners, and similar overall brightness
    assert gpu[42, 58, :3].max() < 30 and gpu[3, 48, :3].max() > 30 and gpu[32, 19, :3].max() > 30
    assert abs(gpu[..., :3].mean() - cpu[..., :3].mean()) < 12
    gpu_job.close()
    cpu_job.close()
    engine.close()


@needs_gl
def test_gpu_engine_renders_real_flames_with_final_xforms_and_xaos(samples):
    from fractalchemy.render.gpu_engine import GpuEngine
    engine = GpuEngine()
    for name, index in (("candy.flame", 0), ("candy.flame", 2), ("stuff.flame", 1)):
        job = engine.start(load_flame(samples / "sample flames" / name, index), SMALL)
        image = job.run_pass()
        assert image is not None and image[..., :3].max() > 0, name
        job.close()
    engine.close()


# --- service ------------------------------------------------------------------
@pytest.fixture
def service(qapp):
    svc = RenderService(prefer_gpu=False)
    svc.start()
    yield svc
    svc.stop()


def test_service_delivers_passes_then_finishes(service):
    passes, finished = [], []
    service.pass_done.connect(lambda key, image, stats: passes.append((key, image.shape, stats.passes_done)))
    service.job_finished.connect(lambda key, stats: finished.append(key))
    service.submit("view", sierpinski(), SMALL)
    assert wait_for(lambda: (spin(20), bool(finished))[1], timeout=20)
    assert [p[2] for p in passes] == [1, 2] and passes[0][0] == "view" and passes[0][1] == (64, 96, 4)
    assert service.engine_name.startswith("CPU")


def test_service_supersedes_same_key_and_reports_failures(service):
    keys = []
    service.pass_done.connect(lambda key, image, stats: keys.append(key))
    failures = []
    service.job_failed.connect(lambda key, message: failures.append((key, message)))
    slow = RenderSettings(160, 120, passes=6, quality=200, points=4096)
    service.submit(("view", 1), sierpinski(), slow)
    service.submit(("view", 1), sierpinski(), SMALL)      # replaces the queued/running slow one
    service.submit("broken", Flame("none", [XForm(weight=0)]), SMALL)
    assert wait_for(lambda: (spin(20), bool(failures))[1], timeout=20)
    assert failures[0][0] == "broken" and "positive weight" in failures[0][1]
    assert wait_for(lambda: (spin(20), keys.count(("view", 1)) >= 2)[1], timeout=20)
    spin(300)
    assert keys.count(("view", 1)) == 2   # only the small render's two passes arrived


def test_service_runs_viewport_before_thumbnails(service):
    order = []
    service.job_finished.connect(lambda key, stats: order.append(key))
    for i in range(3):
        service.submit(("thumb", i), sierpinski(), RenderSettings(32, 24, passes=1, quality=20, points=1024), PRIORITY_THUMBNAIL)
    service.submit("view", sierpinski(), SMALL)
    assert wait_for(lambda: (spin(20), len(order) == 4)[1], timeout=30)
    assert order[0] == "view" or order[1] == "view"   # the viewport pre-empts queued thumbnails
