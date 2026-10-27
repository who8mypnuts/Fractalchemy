"""Final renderer: filters, density estimation, settings / tiling, samplers, the engine, output formats, the Qt job."""

import struct
import time
import zlib
from pathlib import Path

import numpy as np
import pytest

from fractalchemy.fractal import Flame, XForm
from fractalchemy.fractal.scene import Coloring
from fractalchemy.render import filters
from fractalchemy.render.cpu_engine import CpuEngine
from fractalchemy.render.denoise import DENOISERS, denoise
from fractalchemy.render.final_engine import PHASE_CANCELLED, PHASE_DONE, FinalRenderer
from fractalchemy.render.final_service import FinalRenderJob
from fractalchemy.render.final_settings import FinalRenderSettings, plan_tiles
from fractalchemy.render.gpu_engine import gpu_available
from fractalchemy.render.output import (FORMATS, SaveOptions, format_for_path, output_format, read_embedded_parameters,
                                        save_image, size_problem, with_extension)
from fractalchemy.render.report import Report, Section, Table, build_report, machine_text, render_report, report_extension, to_text
from fractalchemy.render.control import RenderControl
from fractalchemy.render.settings import RenderSettings
from fractalchemy.render.tonemap import ToneParams, finish, log_scale, tonemap
from tests.conftest import spin, wait_until
from tests.test_render import sierpinski, synthetic_histogram

needs_gl = pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")
QUICK = dict(quality=30, oversample=2, engine="cpu", cpu_threads=2, fuse=10)


# --- reconstruction filters ------------------------------------------------------------------------
@pytest.mark.parametrize("kind", filters.FILTERS, ids=[f.key for f in filters.FILTERS])
@pytest.mark.parametrize("oversample", [1, 2, 3])
def test_filter_taps_are_normalised_symmetric_and_cover_the_block(kind, oversample):
    taps = filters.make_taps(kind, kind.default_radius, oversample)
    assert taps.weights.sum() == pytest.approx(1.0)
    assert taps.offsets.size >= oversample and taps.reach >= 0
    centre = (oversample - 1) / 2
    mirrored = {(-(o - centre) + centre): w for o, w in zip(taps.offsets.tolist(), taps.weights.tolist())}
    for o, w in zip(taps.offsets.tolist(), taps.weights.tolist()):
        assert mirrored[o] == pytest.approx(w)       # symmetric about the pixel centre


def test_box_filter_is_the_block_mean_and_tiny_radii_degrade_to_it():
    rng = np.random.default_rng(0)
    os_, g = 3, 4
    buckets = rng.random((g + 5 * os_ + g, g + 7 * os_ + g, 4)).astype(np.float32)
    reduced = filters.downsample(buckets, filters.make_taps(filters.filter_kind("box"), 1.0, os_), g, 7, 5)
    expected = buckets[g:g + 15, g:g + 21].reshape(5, os_, 7, os_, 4).mean(axis=(1, 3))
    assert np.abs(reduced - expected).max() < 1e-5
    tiny = filters.make_taps(filters.filter_kind("gaussian"), 0.0, os_)
    assert tiny.offsets.tolist() == [0, 1, 2] and tiny.weights.tolist() == pytest.approx([1 / 3] * 3)
    with pytest.raises(ValueError):
        filters.downsample(buckets, filters.make_taps(filters.filter_kind("lanczos3"), 1.0, os_), 1, 7, 5)


def test_density_estimation_spreads_sparse_hits_and_keeps_dense_ones_sharp():
    counts = np.zeros((60, 60))
    counts[15, 15] = 1.0          # one lonely hit
    counts[45, 45] = 400.0        # a dense spot
    scaled = np.stack([counts] * 4, axis=-1).astype(np.float32)
    out = filters.density_estimate(scaled, counts, 2, filters.DensityEstimation(9.0, 0.0, 0.4))
    assert out.sum() == pytest.approx(scaled.sum(), rel=0.02)            # energy is conserved
    assert out[15, 15, 3] < 0.2 * scaled[15, 15, 3]                      # the lonely hit was spread out
    assert out[45, 45, 3] > 0.5 * scaled[45, 45, 3]                      # the dense spot stayed put
    assert out[15, 25, 3] > 0 and out[45, 55, 3] == pytest.approx(0.0, abs=1e-6)


def test_blur_fallback_matches_scipy_roughly():
    rng = np.random.default_rng(1)
    array = rng.random((40, 50, 2)).astype(np.float32)
    reference = filters.gaussian_blur(array, 2.0, 8.0)
    fallback = filters._box_gaussian(array, 2.0)
    assert np.abs(reference[5:-5, 5:-5] - fallback[5:-5, 5:-5]).max() < 0.08
    assert fallback.sum() == pytest.approx(array.sum(), rel=0.02)
    assert filters.box_blur(np.arange(12, dtype=np.float32).reshape(3, 4, 1), 3)[1, 1, 0] == pytest.approx(5.0)


# --- tone map halves and denoisers ---------------------------------------------------------------
def test_tonemap_halves_compose_and_transparent_mode_unpremultiplies():
    params = ToneParams.derive(Coloring(brightness=5, gamma=3, background=(40, 50, 60)), 50.0, 1_000_000)
    hist = synthetic_histogram()
    assert np.array_equal(tonemap(hist, params)[..., :3], (np.clip(finish(log_scale(hist, params), params)[..., :3] * 255 + 0.5, 0, 255)).astype(np.uint8))
    rgba = finish(log_scale(hist, params), params, transparent=True)
    assert rgba[0, 0].tolist() == [0, 0, 0, 0]                       # empty pixel: fully transparent, no background
    assert 0 < rgba[1, 1, 3] < 1 and rgba[..., 3].max() <= 1.0
    opaque = finish(log_scale(hist, params), params)
    assert (opaque[..., 3] == 1).all() and opaque[0, 0, :3].tolist() == pytest.approx([40 / 255, 50 / 255, 60 / 255])


def test_denoisers_reduce_noise_and_unavailable_ones_are_no_ops():
    rng = np.random.default_rng(2)
    clean = np.zeros((64, 80, 3), np.float32)
    clean[:, 40:] = 0.7
    noisy = np.clip(clean + rng.normal(0, 0.1, clean.shape), 0, 1).astype(np.float32)
    before = np.abs(noisy - clean).mean()
    for kind in DENOISERS:
        out = denoise(noisy, kind.key, 60)
        assert out.shape == noisy.shape and out.dtype == np.float32
        if kind.key in ("guided", "bilateral") or (kind.available and kind.key == "nlmeans"):
            assert np.abs(out - clean).mean() < before
        elif not kind.available or kind.key in ("none", "density"):
            assert out is noisy


# --- settings and tiling --------------------------------------------------------------------------
def test_settings_round_trip_and_validation():
    s = FinalRenderSettings(3000, 2000, denoiser="density", output_path="x.png")
    again = FinalRenderSettings.from_dict({**s.to_dict(), "width": "640", "junk": 1, "depth": "sixteen"})
    assert again.width == 640 and again.depth == 8 and again.denoiser == "density"
    assert FinalRenderSettings().problems() == ["Choose an output file"]
    assert any("Oversample" in p for p in FinalRenderSettings(oversample=99, output_path="x").problems())
    assert FinalRenderSettings(3840, 2160, oversample=2).gutter() == 1
    assert FinalRenderSettings(oversample=2, denoiser="density", de_max_radius=9).gutter() == 19


def test_memory_budgets_follow_the_machine_and_the_settings():
    from fractalchemy.render.final_settings import describe_plan
    from fractalchemy.render.memory import gpu_budget_bytes, memory_budget_bytes, physical_memory_bytes
    ram = physical_memory_bytes()
    assert ram >= 1 << 30                                              # a real figure, not a failed probe
    assert memory_budget_bytes(FinalRenderSettings()) == int(ram * 0.5)   # no fixed ceiling: half of installed RAM
    assert memory_budget_bytes(FinalRenderSettings(memory_limit_mb=70000)) == 70000 << 20
    assert gpu_budget_bytes(FinalRenderSettings()) == 1 << 30 and gpu_budget_bytes(FinalRenderSettings(gpu_memory_mb=12288)) == 12 << 30
    s = FinalRenderSettings(4000, 3000, oversample=2)
    assert "One tile" in describe_plan(s, plan_tiles(s, budget_bytes=8 << 30))
    text = describe_plan(s, plan_tiles(s, budget_bytes=1 << 30))
    assert "tiles" in text and "memory limit" in text and "GB" not in text.split("(")[0]
    gpu_text = describe_plan(s.with_size(8000, 6000), plan_tiles(s.with_size(8000, 6000), gpu=True, budget_bytes=64 << 30))
    assert "GPU memory" in gpu_text


def test_tiles_cover_the_image_exactly_within_the_budget():
    s = FinalRenderSettings(1000, 700, oversample=2, filter_kind="lanczos3")
    plan = plan_tiles(s, budget_bytes=20 << 20)
    assert plan.count > 1
    covered = np.zeros((1400, 2000), dtype=int)
    for t in plan.tiles:
        assert t.x0 % 2 == 0 and t.y0 % 2 == 0 and t.width % 2 == 0 and t.height % 2 == 0
        assert t.gutter == s.gutter() and t.buckets * plan.bytes_per_bucket <= (20 << 20) * 1.01
        covered[t.y0:t.y1, t.x0:t.x1] += 1
    assert (covered == 1).all()
    assert plan_tiles(s, budget_bytes=1 << 30).count == 1
    gpu = plan_tiles(s, gpu=True, max_texture=1024, budget_bytes=1 << 30)
    assert all(max(t.padded_size) <= 1024 for t in gpu.tiles) and gpu.count >= 4


# --- output formats --------------------------------------------------------------------------------
def _read_png16(path: Path) -> np.ndarray:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, header = 8, b"", None
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    width, height, depth, colour = header[:4]
    channels = 4 if colour == 6 else 3
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(height, 1 + width * channels * 2)
    assert (raw[:, 0] == 0).all() and depth == 16
    return raw[:, 1:].copy().view(">u2").reshape(height, width, channels)


def test_every_available_format_writes_and_png16_is_exact(tmp_path):
    rng = np.random.default_rng(0)
    image = rng.integers(0, 65536, (9, 13, 4), dtype=np.uint16)
    for fmt in FORMATS:
        if not fmt.available:
            continue
        path = tmp_path / f"out{fmt.extension}"
        save_image(image, path, fmt, SaveOptions(depth=16, transparent=True, parameters="<flame name='x'/>"))
        assert path.stat().st_size > 0, fmt.key
    exact = _read_png16(tmp_path / "out.png")
    assert np.array_equal(exact, image)
    assert "<flame" in read_embedded_parameters(tmp_path / "out.png")
    assert "<flame" in read_embedded_parameters(tmp_path / "out.jpg")
    assert "<flame" in read_embedded_parameters(tmp_path / "out.svg")
    from PIL import Image
    with Image.open(tmp_path / "out.jpg") as im:
        assert im.size == (13, 9) and im.mode == "RGB"


def test_exr_is_linear_premultiplied_and_carries_metadata(tmp_path):
    from fractalchemy.render.exr import read_exr_attributes, srgb_to_linear, write_exr
    image = np.zeros((6, 8, 4), dtype=np.uint16)
    image[..., 0] = 65535                # pure red …
    image[..., 1] = 32768                # … half green (display value)
    image[..., 3] = 32768                # 50 % alpha
    path = tmp_path / "x.exr"
    fmt = output_format("exr")
    assert fmt.float_channels and fmt.depth16 and fmt.alpha
    save_image(image, path, fmt, SaveOptions(depth=32, transparent=True, parameters="<flame name='e'/>",
                                             attributes={"fractalchemy:samples": "123", "comments": "hi"}))
    attrs = read_exr_attributes(path)
    assert attrs["comments"] == "hi" and attrs["fractalchemy:samples"] == "123" and "premultiplied" in attrs["fractalchemy:alpha"]
    assert read_embedded_parameters(path) == "<flame name='e'/>" and attrs["writer"].startswith("Fractalchemy")
    pytest.importorskip("OpenEXR")
    import OpenEXR
    channels = OpenEXR.File(str(path), separate_channels=True).channels()
    alpha = 32768 / 65535
    assert channels["A"].pixels.dtype == np.float32 and channels["A"].pixels[0, 0] == pytest.approx(alpha)
    assert channels["R"].pixels[0, 0] == pytest.approx(1.0 * alpha, abs=1e-6)                       # premultiplied
    assert channels["G"].pixels[0, 0] == pytest.approx(float(srgb_to_linear(np.float32(alpha))) * alpha, abs=1e-6)  # linearised
    for bad in (b"PNG?", b"\x76\x2f\x31\x01\x02\x00\x00\x00name\0string\0\xff", path.read_bytes()[:40]):
        (tmp_path / "not.exr").write_bytes(bad)
        with pytest.raises(ValueError):                        # truncated or foreign files never escape as struct errors
            read_exr_attributes(tmp_path / "not.exr")
    with pytest.raises(ValueError):
        write_exr(tmp_path / "e.exr", {})
    with pytest.raises(ValueError):
        write_exr(tmp_path / "e.exr", {"R": np.zeros((2, 2)), "G": np.zeros((3, 2))})
    half = tmp_path / "h.exr"
    write_exr(half, {"R": np.full((3, 3), 0.25, np.float32)}, half=True)
    assert OpenEXR.File(str(half), separate_channels=True).channels()["R"].pixels.dtype == np.float16


def test_format_helpers_and_limits(tmp_path):
    assert format_for_path("a/b.JPG").key == "jpeg" and format_for_path("x.txt") is None
    assert with_extension("/p/name.jpg", output_format("png")) == "/p/name.png"
    assert with_extension("/p/name", output_format("tiff")) == "/p/name.tif"
    assert size_problem(output_format("webp"), 20000, 10) and size_problem(output_format("png"), 20000, 10) is None
    with pytest.raises(ValueError):
        save_image(np.zeros((2, 70000, 4), np.uint16), tmp_path / "x.jpg", output_format("jpeg"), SaveOptions())


# --- the shared-memory histogram ---------------------------------------------------------------------
@pytest.mark.parametrize("partitioned", [False, True])
def test_shared_histogram_accumulates_exactly(monkeypatch, partitioned):
    import threading

    from fractalchemy.render import cpu_workers
    monkeypatch.setattr(cpu_workers, "PARTITION_ABOVE", 0 if partitioned else 1 << 40)
    rng = np.random.default_rng(5)
    width, height = 300, 200
    idx = rng.integers(0, width * height, 50_000)
    op = rng.random(50_000)
    ci = rng.integers(0, 256, 50_000)
    palette = rng.random((256, 3)).astype(np.float32)
    locks = [threading.Lock() for _ in range(cpu_workers.BAND_LOCKS)]
    hist = cpu_workers.SharedHistogram(width, height, create=True)
    try:
        hist.add(idx, op, ci, palette, locks)
        hist.add(idx[:0], op[:0], ci[:0], palette, locks)          # an empty batch is a no-op
        expected = np.zeros((4, width * height))
        for ch in range(3):
            np.add.at(expected[ch], idx, palette[ci, ch] * op)
        np.add.at(expected[3], idx, op)
        assert np.allclose(hist.array().reshape(4, -1), expected, atol=1e-9)
        assert hist.array().shape == (4, height, width)
    finally:
        hist.close(unlink=True)


def test_cpu_sampler_surfaces_worker_errors():
    from fractalchemy.render.samplers import CpuSampler
    sampler = CpuSampler(sierpinski(), threads=1, fuse=2)
    try:
        sampler.begin_tile((1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 8, 8)
        sampler._results.put(("error", 0, "ZeroDivisionError: boom"))     # what a worker sends when it raises
        with pytest.raises(RuntimeError, match="worker 1 failed: ZeroDivisionError: boom"):
            sampler.accumulate(1000, RenderControl())
    finally:
        sampler.close()


def test_render_estimate_prefers_measured_rates():
    from fractalchemy.render.estimate import RenderEstimate, engine_kind
    s = FinalRenderSettings(100, 100, quality=10)
    est = RenderEstimate()
    assert est.rate_for("gpu", None) is None and "Time unknown" in est.describe(s, 2, "gpu", None) and est.short(s, 2, "gpu", None) == ""
    assert est.rate_for("cpu", ("CPU (numpy, 4 threads)", 2e6))[0].startswith("the preview") and est.rate_for("gpu", ("CPU", 2e6)) is None
    est.record("cpu", 0)                                          # a zero rate is not a measurement
    assert "cpu" not in est.measured
    est.record("cpu", 5e5)
    text = est.describe(s, 2, "cpu", ("CPU", 2e6))
    assert "last CPU render" in text and "0.00 G samples" in text and est.short(s, 2, "cpu", None) == "≈ 0.4 s"
    assert engine_kind(FinalRenderSettings(engine="cpu"), True) == "cpu" and engine_kind(FinalRenderSettings(engine="auto"), False) == "cpu"
    assert engine_kind(FinalRenderSettings(engine="gpu"), True) == "gpu"


# --- the engine -------------------------------------------------------------------------------------
def _render(flame: Flame, settings: FinalRenderSettings, control: RenderControl | None = None, progress=None):
    reports = []

    def record(p):
        reports.append(p)
        if progress is not None:
            progress(p)
    result = FinalRenderer(flame, settings, control).run(record)
    return result, reports


def test_final_render_matches_the_preview_engine_and_tiles_are_seamless():
    flame = sierpinski()
    settings = FinalRenderSettings(96, 64, memory_limit_mb=1, denoiser="density", de_max_radius=2, **QUICK)
    result, reports = _render(flame, settings)
    assert result.complete and result.image.shape == (64, 96, 4) and result.image.dtype == np.uint16
    assert result.samples >= settings.samples_per_tile and result.engine.startswith("CPU")
    phases = [r.phase for r in reports]
    assert phases[-1] == PHASE_DONE and reports[-1].fraction == 1.0 and reports[-1].remaining == 0.0
    assert reports[-1].tiles >= 2 and any(r.preview is not None for r in reports)
    preview = CpuEngine(threads=1).start(flame, RenderSettings(96, 64, passes=1, quality=30, points=4096, fuse=10)).run_pass()
    final8 = (result.image[..., :3] >> 8).astype(float)
    assert abs(final8.mean() - preview[..., :3].astype(float).mean()) < 6       # same exposure
    assert final8[42, 58].max() < 30 and final8[3, 48].max() > 30               # same picture (hole / edge)
    seam = reports[-1].tiles and [t for t in plan_tiles(settings, budget_bytes=1 << 20).tiles][0].y1 // 2
    rows = final8.mean(axis=(1, 2))
    assert abs(rows[seam] - rows[seam - 1]) < 0.4 * max(rows.max(), 1)           # no visible step at the tile seam


def test_final_render_can_be_cancelled_and_keeps_the_finished_part():
    flame = sierpinski()
    control = RenderControl()
    settings = FinalRenderSettings(96, 64, memory_limit_mb=1, save_incomplete=True, **{**QUICK, "quality": 400})

    def stop_after_first_tile(p):
        if p.tile == 2:
            control.cancel()

    result, reports = _render(flame, settings, control, stop_after_first_tile)
    assert not result.complete and reports[-1].phase == PHASE_CANCELLED
    assert result.image[:20, :, :3].max() > 0            # the first tile was finished and kept
    control2 = RenderControl()
    control2.cancel()
    result2, _ = _render(flame, FinalRenderSettings(32, 24, save_incomplete=False, **QUICK), control2)
    assert not result2.complete and result2.image[..., :3].max() == 0


def test_render_control_tracks_pauses():
    control = RenderControl()
    control.pause()
    assert control.paused
    time.sleep(0.12)
    control.resume()
    assert not control.paused and 0.1 <= control.paused_seconds < 1.0
    control.cancel()
    assert control.cancelled() and not control.wait_if_paused()


@needs_gl
def test_gpu_sampler_agrees_with_cpu_sampler():
    flame = sierpinski()
    cpu, _ = _render(flame, FinalRenderSettings(96, 64, **QUICK))
    gpu, _ = _render(flame, FinalRenderSettings(96, 64, **{**QUICK, "engine": "gpu"}))
    assert gpu.engine.startswith("GPU")
    a, b = (cpu.image[..., :3] >> 8).astype(float), (gpu.image[..., :3] >> 8).astype(float)
    assert abs(a.mean() - b.mean()) < 8 and b[42, 58].max() < 30 and b[3, 48].max() > 30


def test_gpu_request_falls_back_to_cpu_with_a_note(monkeypatch):
    import fractalchemy.render.samplers as samplers

    def broken(*args, **kwargs):
        raise RuntimeError("no display")
    monkeypatch.setattr("fractalchemy.render.gpu_engine.GpuEngine", broken)
    sampler, note = samplers.create_sampler(sierpinski(), __import__("fractalchemy.render.compiled", fromlist=["CompiledFlame"]).CompiledFlame.build(sierpinski()), "gpu", 1, 1, 5)
    try:
        assert "no display" in note and not sampler.is_gpu
    finally:
        sampler.close()


# --- the details report -----------------------------------------------------------------------------
def _xaos_flame() -> Flame:
    flame = sierpinski()
    flame.xforms[0].chaos = [1.0, 0.0, 2.0]
    flame.xforms[1].variations = {"julian": 0.7, "linear": 0.3}
    flame.xforms[1].params = {"julian_power": 3.0, "julian_dist": 1.0}
    flame.xforms[1].name = "pipe|name"
    flame.final = XForm(variations={"spherical": 1.0}, color_speed=0.0)
    return flame


def test_report_is_complete_in_all_three_formats(tmp_path):
    flame = _xaos_flame()
    settings = FinalRenderSettings(64, 48, memory_limit_mb=1, denoiser="density", output_path=str(tmp_path / "a.png"), **QUICK)
    result, _ = _render(flame, settings)
    (tmp_path / "a.png").write_bytes(b"x" * 1234)
    report = build_report(flame, settings, result, tmp_path / "a.png", tmp_path / "a.flame", "lib/a.flame (entry 1)", tmp_path / "a.md")
    keys = [sec.key for sec in report.sections]
    assert keys[:10] == ["output", "render", "timing", "system", "fractal", "camera", "coloring", "palette", "transforms", "variations"]
    assert "xaos" in keys
    text = render_report(report, "txt")
    records = [line.split("\t") for line in text.splitlines() if not line.startswith("#")]
    assert all(len(r) == 2 and " " not in r[0] and r[0] == r[0].lower() for r in records)     # key<TAB>value, grep-able keys
    values = dict(records)
    assert values["output.file_bytes"] == "1234" and values["output.complete"] == "true" and values["render.tiles"] == str(result.plan.count)
    assert values["timing.tiles.count"] == str(len(result.tiles)) and float(values["timing.samples"]) == result.samples
    assert values["fractal.transforms"] == "3" and values["fractal.final_transform"] == "true" and values["fractal.xaos"] == "true"
    assert values["transforms.2.variations"] == "julian=0.7 linear=0.3" and values["transforms.2.params"] == "julian_dist=1 julian_power=3"
    assert values["transforms.final.variations"] == "spherical=1" and values["xaos.1.to_2"] == "0"
    assert values["variations.julian.parameters"] == "dist power" and values["variations.linear.transforms"] == "3"
    assert values["palette.entries"] == "256" and values["camera.pixels_per_unit"] and values["system.cpu_count"]
    assert len(set(r[0] for r in records)) == len(records)                                   # every key unique
    spaced = Table("", "t", [("id", "id"), ("v", "v")], id_key="id")
    spaced.add_row({"id": "pre blur.x", "v": 1})
    assert "s.pre_blur_x.v\t1" in to_text(Report("r", report.generated, [Section("s", "S", tables=[spaced])]))
    md = render_report(report, "md")
    assert md.startswith("# Fractalchemy render report") and "| Field | Value |" in md and "pipe\\|name" in md
    assert "| Render completed | yes |" in md and "### Xaos matrix" in md
    html_text = render_report(report, "html")
    assert html_text.startswith("<!DOCTYPE html>") and "<h2 id=\"variations\">" in html_text and "pipe|name" in html_text
    assert "<script" not in html_text and "&lt;" not in html_text.split("<body>")[0]
    assert machine_text(True) == "true" and machine_text(-0.0) == "0" and machine_text([1, 2.5]) == "1, 2.5"
    assert report_extension("html") == ".html" and report_extension("bogus") == ".md"


# --- the Qt job ---------------------------------------------------------------------------------------
def test_render_job_renders_saves_and_reports(qapp, tmp_path):
    flame = sierpinski()
    path = tmp_path / "out" / "gasket.png"
    settings = FinalRenderSettings(64, 48, output_path=str(path), save_parameters=True, embed_parameters=True,
                                   save_details=True, details_format="txt", **QUICK)
    job = FinalRenderJob(flame, settings, source="memory")
    reports, outcomes, failures = [], [], []
    job.progressed.connect(reports.append)
    job.succeeded.connect(outcomes.append)
    job.failed.connect(failures.append)
    job.start()
    wait_until(lambda: job.isFinished(), timeout_ms=60000)
    spin(50)
    assert not failures and len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.path == path and path.exists() and outcome.sidecar == path.with_suffix(".flame")
    assert "sierpinski" in read_embedded_parameters(path) and "<flame" in outcome.sidecar.read_text()
    assert reports[-1].phase == PHASE_DONE and outcome.result.complete
    assert outcome.report == path.with_suffix(".txt") and "fractal.source\tmemory" in outcome.report.read_text()
    assert f"output.parameters_file\t{outcome.sidecar}" in outcome.report.read_text()


def test_render_job_reports_save_failures(qapp, tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x")
    settings = FinalRenderSettings(32, 24, output_path=str(blocker / "x.png"), **QUICK)
    job = FinalRenderJob(sierpinski(), settings)
    failures, outcomes = [], []
    job.failed.connect(failures.append)
    job.succeeded.connect(outcomes.append)
    job.start()
    wait_until(lambda: job.isFinished(), timeout_ms=60000)
    spin(50)
    assert not outcomes and failures and failures[0].startswith("The render finished but could not be saved")


def test_render_job_reports_setup_failures(qapp, tmp_path):
    job = FinalRenderJob(Flame("none", [XForm(weight=0)]), FinalRenderSettings(32, 24, output_path=str(tmp_path / "x.png"), **QUICK))
    failures = []
    job.failed.connect(failures.append)
    job.start()
    wait_until(lambda: job.isFinished(), timeout_ms=20000)
    spin(50)
    assert failures and "positive weight" in failures[0]
