"""The fragment engine on a GL context: surfaces, the job protocol, uniform upload, diagnostics, the corpus (GL, llvmpipe)."""

import json
from pathlib import Path

import numpy as np
import pytest

from fractalchemy.fragments.examples import EXAMPLES_DIR, all_examples
from fractalchemy.fragments.files import FileManager
from fractalchemy.fragments.gl.engine import FragBuildError, FragEngine
from fractalchemy.fragments.gl.job import FragRenderSettings, FragRequest, TileSpec
from fractalchemy.fragments.gl.surfaces import buffer_dtype
from fractalchemy.fragments.gl.uniforms import tile_projection
from fractalchemy.fragments.glsl_compat import CompatOptions, modernise
from fractalchemy.fragments.preprocessor import Preprocessor
from fractalchemy.fragments.state import ParameterState
from fractalchemy.fragments.templates import NEW_2D, NEW_3D

ACCUMULATE = """#buffer RGBA32F
#vertex
varying vec2 coord;
void main() { gl_Position = gl_Vertex; coord = (gl_ProjectionMatrix * gl_Vertex).xy; }
#endvertex
varying vec2 coord;
uniform sampler2D backbuffer;
uniform int subframe;
uniform vec2 pixelSize;
uniform float Gain; slider[0,1,4]
uniform vec3 Tint; color[1,0.5,0.25]
uniform bool Flag; checkbox[true]
uniform int Count; slider[0,3,10]
uniform float Unused; slider[0,1,2]
void main() {
    vec4 prev = texture2D(backbuffer, coord * 0.5 + 0.5);
    gl_FragColor = prev + vec4(Tint * Gain, 1.0) * (Flag ? 1.0 : 0.0) * float(Count > 0) + vec4(0.0) * float(subframe) * pixelSize.x;
}
"""
# the known failures: broken in FragM as well (checked by reading the sources; see the plan, §5.6)
KNOWN_FAILURES = {
    "eiffieGI2/MontecarloByEffie-KnightyMod.frag", "eiffieGI2/MontecarloByEffie.frag", "eiffieGI2/pseudoknightyan.frag",
    "Experimental/DoubleTest.frag",                         # ComplexBase's double atan returns a float
    "Knighty Collection/PseudoKnightyan.frag",              # uses `time` without declaring it (KN_VOLUMETRIC)
    "Knighty Collection/SimpleIFS/SimpleIFS-OT-RT-final.frag", "Knighty Collection/SimpleIFS/SimpleIFS-RT-final.frag",   # rand2 before MathUtils
}


@pytest.fixture(scope="module")
def engine(_shared_gl_context):
    with _shared_gl_context:
        engine = FragEngine(_shared_gl_context)
        yield engine
        engine.close()


def build(engine: FragEngine, text: str, path: Path | None = None, settings_text: str = "") -> tuple[FragRequest, ParameterState]:
    source = Preprocessor(FileManager(original=path)).parse(text, path)
    options = CompatOptions("modernise", engine.capabilities.glsl_version, engine.capabilities.has_fp64)
    state = ParameterState(source.all_params)
    if "Default" in source.presets:
        state.apply_settings(source.presets["Default"])
    if settings_text:
        state.apply_settings(settings_text)
    request = FragRequest(modernise(source, options), modernise(source.buffer_shader, options) if source.buffer_shader else None,
                          dict(state.values), source.buffer, source.clear_on_change, source.subframes_between_redraws, source.depth_to_alpha)
    return request, state


def test_capabilities_and_buffer_formats(engine):
    caps = engine.capabilities
    assert caps.gl_version >= 330 and caps.glsl_version >= 330 and caps.renderer and len(caps.describe()) == 5
    assert buffer_dtype("") == ("f4", "RGBA32F") and buffer_dtype("rgba8") == ("f1", "RGBA8") and buffer_dtype("RGBA16") == ("f2", "RGBA16")
    assert buffer_dtype("nonsense") == ("f1", "RGBA8")


def test_job_accumulates_subframes_and_reports_facts(engine):
    with engine.ctx:
        request, _state = build(engine, ACCUMULATE)
        job = engine.start(request, FragRenderSettings(32, 16, subframe_max=6, subframes_per_pass=2, surface_key="t1"))
        image = job.run_pass()
        assert image.shape == (16, 32, 4) and image.dtype == np.uint8
        assert job.stats.passes_done == 2 and job.stats.passes_total == 6 and not job.stats.finished
        facts = job.stats.facts
        assert facts.compile_ms > 0 and "Unused" in facts.unused and set(facts.active) >= {"Gain", "Tint", "Flag", "Count"}
        accumulated = job.surface.read_float()
        assert np.allclose(accumulated[..., 3], 2.0) and np.allclose(accumulated[..., 0], 2.0)        # two subframes of (1, .5, .25, 1)
        while not job.stats.finished:
            assert job.run_pass() is not None
        assert job.surface.subframe == 6 and np.allclose(job.surface.read_float()[..., 1], 3.0)
        assert job.image()[0, 0, 0] == 255                                                               # the plain copy clamps
        job.close()
        # a second job for the same key continues the accumulation unless it asks for a clear
        again = engine.start(request, FragRenderSettings(32, 16, subframe_max=8, surface_key="t1", clear=False))
        again.run_pass()
        assert again.surface.subframe == 7 and again.stats.facts.compile_ms == job.stats.facts.compile_ms   # the cached program, its build time
        fresh = engine.start(request, FragRenderSettings(32, 16, subframe_max=8, surface_key="t1", clear=True))
        fresh.run_pass()
        assert fresh.surface.subframe == 1
        redisplay = engine.start(request, FragRenderSettings(32, 16, surface_key="t1", clear=False, redisplay_only=True))
        assert redisplay.run_pass() is not None and redisplay.surface.subframe == 1 and redisplay.stats.finished
        for j in (again, fresh, redisplay):
            j.close()


def test_values_upload_by_program_type_and_cancel(engine):
    with engine.ctx:
        request, state = build(engine, ACCUMULATE, settings_text="Flag = false")
        job = engine.start(request, FragRenderSettings(8, 8, subframe_max=1, surface_key="t2"))
        job.run_pass()
        assert np.allclose(job.surface.read_float()[..., :3], 0.0)                  # the bool switched the colour off
        job.close()
        request2 = FragRequest(request.modern, None, {**request.values, "Flag": True, "Gain": 2, "Count": 0.0}, request.buffer)
        job = engine.start(request2, FragRenderSettings(8, 8, subframe_max=1, surface_key="t2"))
        job.run_pass()
        assert np.allclose(job.surface.read_float()[..., :3], 0.0)                  # Count uploaded as int 0 → factor 0
        job.close()
        job = engine.start(request, FragRenderSettings(8, 8, subframe_max=3, subframes_per_pass=3, surface_key="t3"))
        assert job.run_pass(cancelled=lambda: True) is None                            # cancelled before the first subframe
        job.close()


def test_depth_probe_and_tiles(engine):
    with engine.ctx:
        request, _state = build(engine, NEW_3D)
        job = engine.start(request, FragRenderSettings(48, 32, subframe_max=1, surface_key="t4", depth_probe=(24, 16)))
        image = job.run_pass()
        assert image is not None and job.stats.facts.probe_depth is not None and 0.0 <= job.stats.facts.probe_depth <= 1.0
        job.close()
        whole_job = engine.start(request, FragRenderSettings(64, 64, subframe_max=1, surface_key="whole"))
        whole = whole_job.run_pass()
        whole_job.close()
        tiles = []
        for index in range(4):
            tile_job = engine.start(request, FragRenderSettings(32, 32, subframe_max=1, surface_key=("tile", index), tile=TileSpec(index, 2, 0.0)))
            tiles.append(tile_job.run_pass())
            tile_job.close()
        assembled = np.zeros_like(whole)
        for index, tile in enumerate(tiles):
            dx, dy = index // 2, 1 - index % 2
            assembled[dy * 32:(dy + 1) * 32, dx * 32:(dx + 1) * 32] = tile
        # the raytracer dithers per pixel, so compare the structure, not the exact bytes
        assert np.mean(np.abs(assembled.astype(int) - whole.astype(int))) < 12
        assert tile_projection(0, 1, 0.0)[0] == 1.0 and tile_projection(3, 2, 0.0)[12:14] == (0.5, 0.5)


def test_build_error_carries_mapped_diagnostics(engine):
    with engine.ctx:
        request, _state = build(engine, "void main() { gl_FragColor = vec4(1.0) +; }\n")
        with pytest.raises(FragBuildError) as info:
            engine.build(request.modern)
        error = info.value
        assert error.diagnostics and error.diagnostics[0].severity == "error" and error.diagnostics[0].line == 1
        assert error.report is not None and error.report.is_file()
        assert engine.check(request.modern)                       # and `check` reports the same without raising
        ok_request, _ = build(engine, NEW_2D)
        assert engine.check(ok_request.modern) == []


@pytest.mark.slow
def test_every_example_compiles_except_the_known_fragm_failures(engine):
    failures = {}
    with engine.ctx:
        for path in all_examples():
            key = str(path.relative_to(EXAMPLES_DIR))
            try:
                request, _state = build(engine, path.read_text(encoding="utf-8", errors="replace"), path)
                assert engine.check(request.modern) == []
                if request.buffer_modern is not None:
                    assert engine.check(request.buffer_modern) == []
            except Exception as exc:  # noqa: BLE001 - collected and reported together
                failures[key] = str(exc).splitlines()[0][:120]
    unexpected = {k: v for k, v in failures.items() if k not in KNOWN_FAILURES}
    fixed = KNOWN_FAILURES - set(failures)
    assert not unexpected, f"examples that stopped compiling: {unexpected}"
    assert not fixed, f"known failures that now compile — update KNOWN_FAILURES: {fixed}"


@pytest.mark.slow
def test_example_sample_renders_finite_non_constant_images(engine):
    samples = ["2D Systems/Mandelbrot.frag", "Historical 3D Fractals/Mandelbulb.frag", "Kaleidoscopic IFS/Menger.frag",
               "2D Systems/Game of Life.frag", "Knighty Collection/Pseudo-MandalayBox.frag", "Tutorials/20 - Progressive 2D.frag"]
    with engine.ctx:
        for name in samples:
            path = EXAMPLES_DIR / name
            request, _state = build(engine, path.read_text(encoding="utf-8", errors="replace"), path)
            job = engine.start(request, FragRenderSettings(64, 40, subframe_max=2, subframes_per_pass=2, surface_key=name))
            image = job.run_pass()
            job.close()
            assert image is not None and image.shape == (40, 64, 4), name
            assert image[..., :3].std() > 1.0, f"{name} rendered a flat image"


def test_parameter_inventory_matches_the_snapshot():
    """Every parameter FragM would show for the bundled examples, as recorded by tools/fragments_snapshot.py."""
    from tools.fragments_snapshot import SNAPSHOT, inventory
    recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    current = json.loads(json.dumps(inventory(), default=list))
    assert current.keys() == recorded.keys()
    different = [name for name in recorded if recorded[name] != current[name]]
    assert not different, f"the parameter inventory changed for {different[:5]}… — review and rerun tools/fragments_snapshot.py"


SLOW = """uniform int Work; slider[1,4000,100000]
void main() {
    float acc = 0.0;
    for (int i = 0; i < Work; i++) acc += sin(float(i) * gl_FragCoord.x * 1e-3);
    gl_FragColor = vec4(fract(acc), 0.0, 0.0, 1.0);
}
"""


def test_watchdog_splits_slow_subframes_into_tiles(engine):
    from fractalchemy.fragments.gl.passes import split_rects

    assert split_rects(10, 7, 2) == [(0, 0, 5, 4), (5, 0, 5, 4), (0, 4, 5, 3), (5, 4, 5, 3)]
    request, _state = build(engine, SLOW)
    with engine.ctx:
        job = engine.start(request, FragRenderSettings(96, 96, subframe_max=6, subframes_per_pass=6, surface_key="slow", subframe_budget_ms=0.001))
        image = job.run_pass()
        whole = engine.start(request, FragRenderSettings(96, 96, subframe_max=6, subframes_per_pass=6, surface_key="slow2", subframe_budget_ms=0))
        reference = whole.run_pass()
        job.close()
        whole.close()
    assert job.stats.facts.tiled > 1 and any("tiles" in note for note in job.stats.notes)
    assert whole.stats.facts.tiled == 1
    assert np.array_equal(image, reference)       # tiling changes the draws, not the picture


def test_gpu_load_limit_idles_between_passes(engine):
    import time

    request, _state = build(engine, SLOW)
    with engine.ctx:
        job = engine.start(request, FragRenderSettings(16, 16, subframe_max=4, surface_key="throttle", gpu_load=0.5))
        job.run_pass()                                  # builds and draws the first subframe
        started = time.perf_counter()
        job._throttle(0.05, lambda: False)              # half duty cycle: idle as long as the pass took
        idled = time.perf_counter() - started
        cancelled_at = time.perf_counter()
        job._throttle(1.0, lambda: True)                # a cancelled job does not idle
        job.close()
    assert 0.04 <= idled < 0.5 and time.perf_counter() - cancelled_at < 0.1
