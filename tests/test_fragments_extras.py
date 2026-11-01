"""The Fragments window's later additions, Qt-free side: definitions, stereo / regions / tile ranges, LUTs and the post
stack, the DE exporter, sessions, library metadata, mutation, snippets, gradient normals and the Blender script."""

from __future__ import annotations


import numpy as np
import pytest

from fractalchemy.fragments.batch import prepare
from fractalchemy.fragments.blender_script import blender_script
from fractalchemy.fragments.definitions import all_definitions, find_definition, find_in_files
from fractalchemy.fragments.examples import EXAMPLES_DIR, INCLUDE_DIR
from fractalchemy.fragments.export_de import export_de, extract_de, glsl_literal, to_hlsl
from fractalchemy.fragments.gl.engine import FragEngine
from fractalchemy.fragments.gl.final import FragFinalRenderer
from fractalchemy.fragments.gl.mesh import Bounds, ProbeResult
from fractalchemy.fragments.gl.uniforms import IDENTITY, tile_projection
from fractalchemy.fragments.grading import Grading
from fractalchemy.fragments.library_meta import LibraryMeta, scan_fragment
from fractalchemy.fragments.lut import LutError, identity_lut, parse_cube, read_cube
from fractalchemy.fragments.mesh import DEMeshSettings, build_de_mesh, gradient_normals
from fractalchemy.fragments.parameters import BoolParameter, FloatParameter, IntParameter, VectorParameter
from fractalchemy.fragments.render_settings import FragFinalSettings
from fractalchemy.fragments.session import AutosaveStore, Session, SessionTab
from fractalchemy.fragments.stereo import compose, compose_projection, region_projection, region_size, stereo_values
from fractalchemy.fragments.animation import AnimationSettings

from .test_fragments_render import prepared

JULIABULB = EXAMPLES_DIR / "Fractalchemy Collection" / "3D - Juliabulb.frag"
AMAZING = EXAMPLES_DIR / "Fractalchemy Collection" / "3D - Amazing Surf.frag"
SOURCE = """#define Bailout 4.0
uniform float Power; slider[1,8,16]
const vec3 Offset = vec3(1.0);
struct Hit { float d; };
float DE(vec3 p) { return length(p) - Power; }
vec3 color(vec3 p) { return Offset; }
"""


@pytest.fixture(scope="module")
def engine(_shared_gl_context):
    with _shared_gl_context:
        engine = FragEngine(_shared_gl_context)
        yield engine
        engine.close()


# --- definitions -----------------------------------------------------------------------------------------------------------
def test_definitions_find_functions_uniforms_defines_and_globals(tmp_path):
    assert find_definition(SOURCE, "DE").line == 5 and find_definition(SOURCE, "DE").kind == "function"
    assert find_definition(SOURCE, "Power").kind == "uniform" and find_definition(SOURCE, "Bailout").kind == "define"
    assert find_definition(SOURCE, "Offset").kind == "variable" and find_definition(SOURCE, "Hit").kind == "struct"
    assert find_definition(SOURCE, "nothing") is None and find_definition(SOURCE, "DE").signature == "float DE(vec3 p)"
    assert [d.name for d in all_definitions(SOURCE)] == ["Bailout", "Power", "Offset", "Hit", "DE", "color"]
    found = find_in_files("trace", [tmp_path / "missing.frag", INCLUDE_DIR / "DE-Raytracer.frag"])
    assert found is not None and found.file == INCLUDE_DIR / "DE-Raytracer.frag" and found.line > 0 and found.signature.startswith("vec3 trace(")
    assert find_in_files("DE", [INCLUDE_DIR / "DE-Raytracer.frag"]).text.rstrip().endswith(";") or "Must be" in find_in_files("DE", [INCLUDE_DIR / "DE-Raytracer.frag"]).text       # only the prototype lives there
    assert find_in_files("nothing_here", [INCLUDE_DIR / "DE-Raytracer.frag"]) is None


# --- stereo, regions, tiles --------------------------------------------------------------------------------------------------
def test_stereo_values_and_compositing():
    left, right = stereo_values({"Eye": (0, 0, -10), "Target": (0, 0, 0), "Up": (0, 1, 0)}, 0.1)
    assert left["Eye"][0] == pytest.approx(0.5) and right["Eye"][0] == pytest.approx(-0.5)        # FragM's Right = cross(Dir, Up)
    assert left["Target"][0] == pytest.approx(0.5) and left["Eye"][2] == -10
    a = np.full((2, 3, 4), 0.2, dtype=np.float32)
    b = np.full((2, 3, 4), 0.8, dtype=np.float32)
    anaglyph = compose("anaglyph", a, b)
    assert anaglyph[0, 0, 0] == pytest.approx(0.2) and anaglyph[0, 0, 1] == pytest.approx(0.8)
    assert compose("sbs", a, b).shape == (2, 6, 4)
    with pytest.raises(ValueError):
        compose("nope", a, b)
    same = stereo_values({"Eye": (0, 0, 0), "Target": (0, 0, 0)}, 0.1)
    assert same[0]["Eye"] == (0, 0, 0)


def test_region_projection_and_settings():
    assert region_projection(None) == IDENTITY
    quarter = region_projection((0.5, 0.5, 0.5, 0.5))
    assert quarter[0] == 0.5 and quarter[5] == 0.5 and quarter[12] == pytest.approx(0.5) and quarter[13] == pytest.approx(-0.5)
    assert compose_projection(IDENTITY, tile_projection(3, 2, 0.0)) == tile_projection(3, 2, 0.0)
    assert region_size((0.25, 0.25, 0.5, 0.5), 400, 300) == (200, 150) and region_size(None, 400, 300) == (400, 300)
    s = FragFinalSettings(tile_width=40, tile_height=30, tiles=2, subframes=1, output_path="x.png")
    assert s.tile_indices() == [0, 1, 2, 3] and s.with_(tile_range=(1, 2)).tile_indices() == [1, 2]
    assert s.with_(stereo="sbs").output_size() == (160, 60) and s.with_(stereo="anaglyph").eyes == 2
    assert s.with_(stereo="anaglyph").total_steps(1) == 8
    assert "region" in s.with_(region=(0.5, 0.5, 0.6, 0.6)).problems()[0]
    assert "selects no tile" in s.with_(tile_range=(9, 9)).problems()[0] and s.with_(tile_range=(9, 9), tile_dir="t").problems() == []
    assert "unknown stereo" in s.with_(stereo="x").problems()[0]
    restored = FragFinalSettings.from_dict({**s.to_dict(), "region": [0.1, 0.2, 0.3, 0.4], "tile_range": [0, 1]})
    assert restored.region == (0.1, 0.2, 0.3, 0.4) and restored.tile_range == (0, 1)
    assert "stereo sbs" in s.with_(stereo="sbs").describe_plan(1) and "assembling" in s.with_(tile_range=(-1, -1), tile_dir="t").describe_plan(1)


def test_renderer_region_stereo_and_tile_folder(engine, tmp_path):
    with engine.ctx:
        _source, request, state = prepared(engine)
        full = FragFinalSettings(tile_width=64, tile_height=64, subframes=1, output_path="x.png")
        frames = []
        FragFinalRenderer(engine, request, state, full, AnimationSettings(), None, [], False).run(frame_done=frames.append)
        crop = full.with_(tile_width=32, tile_height=32, region=(0.5, 0.5, 0.5, 0.5))
        FragFinalRenderer(engine, request, state, crop, AnimationSettings(), None, [], False).run(frame_done=frames.append)
        whole, region = frames
        assert region.rgba.shape == (32, 32, 4) and np.abs(whole.rgba[32:, 32:] - region.rgba).mean() < 0.05
        frames.clear()
        FragFinalRenderer(engine, request, state, full.with_(stereo="sbs"), AnimationSettings(), None, [], False).run(frame_done=frames.append)
        assert frames[0].rgba.shape == (64, 128, 4)
        frames.clear()
        FragFinalRenderer(engine, request, state, full.with_(stereo="anaglyph", eye_separation=0.2), AnimationSettings(), None, [], False).run(
            frame_done=frames.append)
        assert frames[0].rgba.shape == (64, 64, 4) and frames[0].complete
        # tile ranges: half the tiles on one "machine", the rest on another, then assembled from the folder
        tiled = full.with_(tile_width=32, tile_height=32, tiles=2, tile_dir=str(tmp_path / "tiles"))
        frames.clear()
        FragFinalRenderer(engine, request, state, tiled.with_(tile_range=(0, 1)), AnimationSettings(), None, [], False).run(frame_done=frames.append)
        assert frames[0].missing_tiles == [2, 3] and not frames[0].complete and len(list((tmp_path / "tiles").iterdir())) == 2
        frames.clear()
        FragFinalRenderer(engine, request, state, tiled.with_(tile_range=(2, 3)), AnimationSettings(), None, [], False).run(frame_done=frames.append)
        assert frames[0].complete and len(list((tmp_path / "tiles").iterdir())) == 4
        frames.clear()
        FragFinalRenderer(engine, request, state, tiled.with_(tile_range=(-1, -1)), AnimationSettings(), None, [], False).run(frame_done=frames.append)
        assert frames[0].complete and np.abs(frames[0].rgba - whole.rgba).mean() < 0.05


# --- LUTs and the post stack --------------------------------------------------------------------------------------------------
def test_cube_luts(tmp_path):
    lut = identity_lut(3)
    assert lut.size == 3 and lut.table.shape == (3, 3, 3, 3) and lut.table[2, 0, 0].tolist() == [0.0, 0.0, 1.0]
    swap = parse_cube('TITLE "swap"\nLUT_3D_SIZE 2\n0 0 0\n0 0 1\n0 1 0\n0 1 1\n1 0 0\n1 0 1\n1 1 0\n1 1 1\n')
    assert swap.title == "swap" and swap.table[0, 0, 1].tolist() == [0.0, 0.0, 1.0]
    one_d = parse_cube("LUT_1D_SIZE 3\n0 0 0\n0.25 0.5 0.5\n1 1 1\n")
    assert one_d.size == 3 and one_d.table[0, 0, 1].tolist() == [0.25, 0.0, 0.0]
    for bad in ("LUT_3D_SIZE 2\n0 0 0\n", "nothing", "LUT_3D_SIZE 2\n" + "a b c\n" * 8):
        with pytest.raises(LutError):
            parse_cube(bad)
    path = tmp_path / "t.cube"
    path.write_text("LUT_3D_SIZE 2\n" + "\n".join(" ".join(str(v) for v in (r, g, b)) for b in (0, 1) for g in (0, 1) for r in (0, 1)))
    assert read_cube(path).title == "t" and len(read_cube(path).bytes) == 8 * 3 * 4


def test_post_stack_uniforms_and_stage(engine, tmp_path):
    g = Grading(bloom=0.5, aberration=0.5, grain=0.2, lut=str(tmp_path / "x.cube"), lut_strength=0.5)
    assert g.has_bloom and g.has_lut and not g.is_identity
    u = g.uniforms()
    assert u["u_bloom"] == 0.5 and u["u_aberration"] == pytest.approx(0.01) and u["u_lut_strength"] == 0.5
    assert Grading.from_dict(g.to_dict()) == g and Grading(lut="x", lut_strength=0.0).uniforms()["u_lut_strength"] == 0.0
    with engine.ctx:
        ctx = engine.ctx
        source = ctx.texture((32, 16), 4, np.tile(np.array([0.9, 0.2, 0.2, 1.0], np.float32), (32 * 16, 1)).tobytes(), dtype="f4")
        out = ctx.texture((32, 16), 4, dtype="f4")
        fbo = ctx.framebuffer([out])

        def graded(grading):
            engine.grading.apply(grading, source, fbo, 32, 16)
            return np.frombuffer(fbo.read(components=4, dtype="f4"), np.float32).reshape(16, 32, 4)

        plain = graded(Grading())
        assert plain[8, 16, 0] == pytest.approx(0.9, abs=0.01)
        assert graded(Grading(bloom=1.0, bloom_threshold=0.1))[8, 16, 1] > plain[8, 16, 1]           # the glow brightens
        assert graded(Grading(lut=str(tmp_path / "missing.cube")))[8, 16, 0] == pytest.approx(0.9, abs=0.01)
        assert any("not found" in note for note in engine.grading.take_notes())
        (tmp_path / "swap.cube").write_text('LUT_3D_SIZE 2\n0 0 0\n0 0 1\n0 1 0\n0 1 1\n1 0 0\n1 0 1\n1 1 0\n1 1 1\n')
        swapped = graded(Grading(lut=str(tmp_path / "swap.cube")))
        assert swapped[8, 16, 2] == pytest.approx(0.9, abs=0.02) and swapped[8, 16, 0] == pytest.approx(0.2, abs=0.02)
        grainy = graded(Grading(grain=1.0))
        assert grainy[..., 1].std() > 0.01
        fbo.release()
        out.release()
        source.release()


# --- the DE exporter --------------------------------------------------------------------------------------------------------
def test_export_de_targets_compile_and_translate(engine):
    with engine.ctx:
        for path, expects_init in ((JULIABULB, False), (AMAZING, True)):
            ready = prepare(path, engine)
            text = ready.request.modern.fragment
            extraction = extract_de(text)
            assert any(f.name == "DE" for f in extraction.functions) and ("init" in {f.name for f in extraction.functions}) == expects_init
            glsl = export_de(text, ready.request.values, "glsl", path.stem)
            assert "const float Power" in glsl.code or "const float Scale" in glsl.code
            call = "init(); " if expects_init else ""
            shim = "#version 330 core\nout vec4 o;\n" + glsl.code + f"\nvoid main() {{ {call}o = vec4(DE(vec3(0.1))); }}\n"
            engine.ctx.program(vertex_shader="#version 330 core\nin vec4 vertex_position; void main(){gl_Position=vertex_position;}", fragment_shader=shim)
            toy = export_de(text, ready.request.values, "shadertoy", path.stem)
            assert "mainImage" in toy.code and "#version" not in toy.code and ("init();" in toy.code) == expects_init
            unity = export_de(text, ready.request.values, "unity", path.stem)
            assert unity.code.startswith('Shader "Fractalchemy/') and "float3 DE(" not in unity.code and "float DE(float3" in unity.code
            unreal = export_de(text, ready.request.values, "unreal", path.stem)
            assert "RaymarchDE" in unreal.code and unreal.suffix == ".ush"
    with pytest.raises(ValueError):
        extract_de("void main() {}")
    with pytest.raises(ValueError):
        export_de(SOURCE, {}, "nope")
    assert glsl_literal("vec3", (1, 2, 3)) == "vec3(1.0, 2.0, 3.0)" and glsl_literal("bool", True) == "true" and glsl_literal("int", 3.7) == "3"
    assert glsl_literal("float", 1e-7) == "1e-07" and glsl_literal("ivec2", (1, 2)) == "ivec2(1, 2)"
    hlsl, notes = to_hlsl("vec3 a = vec3(1.0); float c = atan(a.y, a.x) + atan(0.5); float d = mod(c, 2.0); vec2 e = mix(a.xy, a.xy, 0.5) + fract(a.xy); mat3 m;")
    assert "((float3)(1.0))" in hlsl and "atan2(a.y, a.x) + atan(0.5)" in hlsl and "glsl_mod(c, 2.0)" in hlsl and "lerp(" in hlsl and "frac(" in hlsl
    assert "float3x3 m;" in hlsl and any("mul(" in note for note in notes)
    baked = export_de(SOURCE, {"Power": 2.5}, "glsl", "s")
    assert "const float Power = 2.5;" in baked.code and "#define Bailout 4.0" not in baked.code and "vec3 color" not in baked.code


# --- sessions ------------------------------------------------------------------------------------------------------------
def test_sessions_round_trip_and_autosave(tmp_path):
    session = Session([SessionTab("/a/b.frag", None, "Power = 8", "Default", False), SessionTab(None, "void main(){}", "", "", True)], 1)
    path = session.write(tmp_path / "s")
    assert path.suffix == ".fasession" and Session.read(path).tabs[1].text == "void main(){}" and Session.read(path).current == 1
    assert "2 tabs" in session.describe() and "1 with unsaved edits" in session.describe()
    for bad in ("{", "[]", '{"tabs": 3}'):
        with pytest.raises(ValueError):
            Session.from_json(bad)
    store = AutosaveStore(tmp_path / "cache")
    assert not store.exists and store.read() is None
    store.write(session)
    assert store.exists and store.read().tabs[0].path == "/a/b.frag"
    store.clear()
    assert not store.exists


# --- library metadata ----------------------------------------------------------------------------------------------------
def test_library_meta_tags_ratings_and_search_words(tmp_path):
    meta = LibraryMeta(tmp_path / "meta.json")
    meta.set_tags(JULIABULB, ["IFS ", "Bulb"])
    meta.set_rating(JULIABULB, 4)
    meta.set_favourite(JULIABULB, True)
    again = LibraryMeta(tmp_path / "meta.json")
    assert again.tags(JULIABULB) == ["bulb", "ifs"] and again.rating(JULIABULB) == 4 and again.favourite(JULIABULB) and again.all_tags() == ["bulb", "ifs"]
    words = again.search_text(JULIABULB, recent=True).split()
    assert {"tag:ifs", "rating:4", "★★★★", "fav", "recent", "param:Power", "include:DE-Raytracer", "3d"} <= set(words)
    caption = again.caption(JULIABULB)
    assert caption.startswith("3D - Juliabulb.frag\n3D ·") and "★★★★" in caption and "bulb, ifs" in caption
    meta.set_rating(JULIABULB, 0)
    meta.set_tags(JULIABULB, [])
    meta.set_favourite(JULIABULB, False)
    assert LibraryMeta(tmp_path / "meta.json").search_text(JULIABULB).count("tag:") == 0
    info = scan_fragment("#camera 2D\n#info hello\n#group G\nuniform float A; slider[0,1,2]\n#include \"x.frag\"\n#preset P\n#endpreset\n")
    assert info.params == ["A"] and info.includes == ["x.frag"] and info.presets == ["P"] and info.camera == "2D" and info.info == ["hello"]
    assert info.caption_line == "2D · 1 preset · 1 parameter"
    assert LibraryMeta(None).info(tmp_path / "missing.frag").params == []


# --- mutation ------------------------------------------------------------------------------------------------------------
def test_mutated_values_stay_in_range():
    rng = np.random.default_rng(3)
    f = FloatParameter("F", "float", from_=0.0, default=0.5, to=1.0)
    for _ in range(50):
        assert 0.0 <= f.mutated_value(0.5, 0.2, rng) <= 1.0 and abs(f.mutated_value(0.5, 0.2, rng) - 0.5) <= 0.2 + 1e-9
    v = VectorParameter("V", "vec2", from_=(0.0, 0.0), default=(0.5, 0.5), to=(1.0, 2.0))
    out = v.mutated_value((0.5, 0.5), 1.0, rng)
    assert len(out) == 2 and 0.0 <= out[0] <= 1.0 and 0.0 <= out[1] <= 2.0
    i = IntParameter("I", "int", from_=0, default=5, to=10)
    assert isinstance(i.mutated_value(5, 0.5, rng), int)
    b = BoolParameter("B", "bool", default=True)
    assert b.mutated_value(True, 0.0, rng) is True


# --- snippets -------------------------------------------------------------------------------------------------------------
def test_snippet_expansion():
    from fractalchemy.ui.fragments.editor_tools import SnippetSession
    text, stops = SnippetSession.expand("uniform float ${1:Name}; slider[${2:0},$3]\n$0")
    assert text == "uniform float Name; slider[0,]\n" and [s[0] for s in stops] == [1, 2, 3, 0]
    assert stops[0][1:] == (14, 4) and stops[-1][1] == len(text)
    assert SnippetSession.expand("plain text") == ("plain text", [])


# --- mesh extras ----------------------------------------------------------------------------------------------------------
def test_gradient_normals_and_blender_script(tmp_path):
    n = 24
    axis = (np.arange(n) + 0.5) / n * 3.0 - 1.5
    x, y, z = np.meshgrid(axis, axis, axis, indexing="ij")
    distance = (np.sqrt(x * x + y * y + z * z) - 1.0).astype(np.float32)
    probe = ProbeResult(distance, None, Bounds((0.0, 0.0, 0.0), 3.0), 3.0 / n)
    result = build_de_mesh(probe, DEMeshSettings(resolution=n, fit=False, threshold_voxels=0.0, colors=False, clean="none", normals="gradient"))
    normals = result.full.normals
    radial = result.full.vertices / np.linalg.norm(result.full.vertices, axis=1, keepdims=True)
    assert normals is not None and (np.sum(normals * radial, axis=1) > 0.97).mean() > 0.95
    assert gradient_normals(result.full, probe).shape == normals.shape
    script = blender_script("sphere", [tmp_path / "sphere.ply", tmp_path / "sphere.stl"], tmp_path / "sphere_color.png", 0.001)
    assert "bpy.ops.wm.ply_import" in script and "sphere_color.png" in script and "obj.scale = (0.001, 0.001, 0.001)" in script
    assert blender_script("x", [tmp_path / "x.txt"], None).startswith("# no importable")


# --- controllers ---------------------------------------------------------------------------------------------------------
def test_controller_protocols_and_mapping():
    import struct

    from fractalchemy.fragments.controllers import Binding, Control, ControlMapping, MidiParser, apply_control, parse_joystick_events
    data = struct.pack("IhBB", 1, 32767, 0x02, 1) + struct.pack("IhBB", 2, 1, 0x81, 3) + b"\x01\x02"
    events, rest = parse_joystick_events(data)
    assert [(e.kind, e.number, e.value) for e in events] == [("axis", 1, 1.0), ("button", 3, 1.0)] and rest == b"\x01\x02"
    parser = MidiParser()
    first = parser.feed(bytes([0xB0, 74, 127, 74, 0, 0x90, 60, 100, 0xF8, 0xB1, 7]))
    assert [(e.number, e.value, e.channel) for e in first] == [(74, 1.0, 0), (74, 0.0, 0)] and parser.feed(bytes([64]))[0].channel == 1
    absolute = Binding("Power1", "absolute")
    assert apply_control(absolute, Control("cc", 74, 0.5), 0.0, 1.0, 9.0, 0.1) == 5.0
    assert apply_control(Binding("Power1", "absolute", invert=True), Control("cc", 74, 0.0), 0.0, 1.0, 9.0, 0.1) == 9.0
    assert apply_control(absolute, Control("axis", 0, -1.0), 0.0, 1.0, 9.0, 0.1) == 1.0
    relative = Binding("Power1", "relative", speed=1.0)
    assert apply_control(relative, Control("axis", 1, 1.0), 5.0, 1.0, 9.0, 0.5) == 9.0
    assert apply_control(relative, Control("axis", 1, 0.02), 5.0, 1.0, 9.0, 0.5) == 5.0          # dead zone
    mapping = ControlMapping()
    mapping.bind("cc 74", absolute)
    restored = ControlMapping.from_dict({**mapping.to_dict(), "bad": {"mode": "x"}, "axis 1": {"slider": "S1", "mode": "weird"}})
    assert restored.bindings["cc 74"].slider == "Power1" and restored.bindings["axis 1"].mode == "absolute" and "bad" not in restored.bindings
    assert restored.for_control(Control("cc", 74, 0.0)) is absolute or restored.for_control(Control("cc", 74, 0.0)).slider == "Power1"
    mapping.unbind("cc 74")
    assert mapping.bindings == {}
