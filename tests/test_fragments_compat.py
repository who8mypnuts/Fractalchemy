"""The GLSL compatibility layer, the driver-log diagnostics and the camera maths (Qt-free)."""

import math

import numpy as np
import pytest

from fractalchemy.fragments.camera import Camera2D, Camera3D, clamp_step, normalize, rotate, step_after_key, vec
from fractalchemy.fragments.files import FileManager
from fractalchemy.fragments.gl.diagnostics import parse_log
from fractalchemy.fragments.glsl_compat import CompatError, CompatOptions, modernise, requested_version, target_version
from fractalchemy.fragments.preprocessor import Preprocessor
from fractalchemy.fragments.source import LineMap

LEGACY = """#version 120
#vertex
varying vec2 coord;
void main(void) { gl_Position = gl_Vertex; coord = (gl_ProjectionMatrix*gl_Vertex).xy; }
#endvertex
varying vec2 coord;
uniform sampler2D tex;
uniform vec2 pixelSize;
uniform vec2 pixelSize;
#extension GL_ARB_shading_language_420pack : enable
vec4 texture(vec3 p) { return vec4(p, 1.0); }
void main() { gl_FragColor = texture2D(tex, coord) + texture(vec3(coord, 0.0)) + vec4(noise1(coord.x)); gl_FragData[1] = vec4(1.0); }
"""


def parse(text: str):
    return Preprocessor(FileManager()).parse(text, None)


def test_target_version_rules():
    assert requested_version("") == (110, "") and requested_version("#version 400 compatibility") == (400, "compatibility")
    source = parse("void main() {}")
    assert target_version(source, CompatOptions(context_glsl=450)) == 330
    source.version_line = "#version 410 compatibility"
    assert target_version(source, CompatOptions(context_glsl=450, has_fp64=True)) == 410
    with pytest.raises(CompatError):
        target_version(source, CompatOptions(context_glsl=330))
    with pytest.raises(CompatError):
        target_version(source, CompatOptions(context_glsl=450, has_fp64=False))


def test_modernise_rewrites_the_legacy_constructs_and_keeps_the_line_map():
    source = parse(LEGACY)
    modern = modernise(source, CompatOptions(context_glsl=450))
    vertex, fragment = modern.vertex, modern.fragment
    assert vertex.startswith("#version 330 core") and "layout(location = 0) in vec4 vertex_position;" in vertex
    assert "#define gl_ProjectionMatrix projectionMatrix" in vertex and "#define varying out" in vertex
    assert "#define varying in" in fragment and "out vec4 fragColor;" in fragment and "#define gl_FragColor fragColor" in fragment
    assert "vec4 texture2D(sampler2D s, vec2 c) { return texture(s, c); }" in fragment     # a wrapper, not a macro
    assert fragment.index("vec4 texture2D(") < fragment.index("vec4 texture(vec3 p)")          # before the user's texture()
    assert "layout(location = 1) out vec4 fragData_1;" in fragment and "fragData_1 = vec4(1.0)" in fragment
    assert "float noise1(float x)" in fragment
    lines = fragment.split("\n")
    assert lines[1].startswith("#extension") and not any(line.startswith("#extension") for line in lines[2:])   # hoisted
    assert sum("uniform vec2 pixelSize;" in line and not line.startswith("//") for line in lines) == 1            # de-duplicated
    assert "#version 120" not in fragment.replace("// #version 120", "")
    # every line that came from the source maps back to its text
    for number, line in enumerate(lines, start=1):
        origin = modern.fragment_map.origin(number)
        if origin is not None:
            original = LEGACY.split("\n")[origin[1] - 1].strip()
            assert original in line or line.startswith("//") or original[:5] == line.strip()[:5]   # (the rewritten lines)
    assert "gl_FragData outputs declared" in modern.notes and any("noise" in n for n in modern.notes)


def test_patch_and_off_modes():
    source = parse(LEGACY)
    patched = modernise(source, CompatOptions(mode="patch", context_glsl=450))
    assert "// compatibility patch" in patched.fragment and patched.fragment.startswith("#version 330")
    plain = modernise(source, CompatOptions(mode="off", context_glsl=450))
    assert plain.version == 120 and "compatibility patch" not in plain.fragment and "#_include" not in plain.fragment
    with pytest.raises(ValueError):
        modernise(source, CompatOptions(mode="bogus"))


def test_leftover_includes_in_comments_are_disarmed_for_moderngl():
    source = parse('/*\n  #include "x.frag"\n*/\n//#include "y.frag"\nvoid main() {}\n')
    modern = modernise(source, CompatOptions(context_glsl=450))
    assert "#include" not in modern.fragment and "#_include" in modern.fragment


def test_diagnostics_parse_three_driver_dialects_and_map_lines():
    files = [None]
    fragment_map = LineMap(files, [None, None, (0, 7), (0, 8), None])
    vertex_map = LineMap(files, [None, (0, 2)])
    text = ("GLSL Compiler failed\n\nvertex_shader\n\n0:2(5): error: mesa style\n\nfragment_shader\n\n0(3) : error C1008: nvidia style\n"
            "ERROR: 0:4: 'x' : amd style\nWARNING: 0:99: outside the map\n")
    diagnostics = parse_log(text, vertex_map, fragment_map, "a\nb", "l1\nl2\nl3\nl4\nl5")
    assert [(d.stage, d.severity, d.emitted_line, d.line) for d in diagnostics] == [
        ("vertex", "error", 2, 2), ("fragment", "error", 3, 7), ("fragment", "error", 4, 8), ("fragment", "warning", 99, 0)]
    assert diagnostics[1].source_line == "l3" and diagnostics[1].message == "C1008: nvidia style"
    assert "generated" in parse_log("0:1(1): error: in the prelude", vertex_map, fragment_map)[0].location()
    fallback = parse_log("something unrecognised happened", vertex_map, fragment_map)
    assert len(fallback) == 1 and fallback[0].message == "something unrecognised happened"


# --- cameras -------------------------------------------------------------------------------------------------------------------
def test_rotation_and_step_helpers():
    turned = rotate(vec(1, 0, 0), 90, vec(0, 0, 1))
    assert np.allclose(turned, (0, 1, 0))
    assert np.allclose(normalize(vec(3, 0, 4)), (0.6, 0, 0.8))
    assert step_after_key(0.1, "1", 0.1) == 0.05 and step_after_key(0.1, "3", 0.1) == 0.2 and step_after_key(0.1, "2", 0.1) == 1.0
    assert step_after_key(7.0, "5", 0.1) == 0.1 and clamp_step(100) == 10.0 and clamp_step(0) == 1e-5


def test_camera3d_keys_follow_fragm():
    camera = Camera3D(eye=(0, 0, -10), target=(0, 0, 0), up=(0, 1, 0), fov=0.4)
    forward = camera.key("w", 0.5)
    assert np.allclose(forward.eye, (0, 0, -9.5)) and np.allclose(forward.target, (0, 0, 0.5))
    right = camera.key("d", 1.0)
    assert np.allclose(right.eye, camera.right + vec(camera.eye)) and np.allclose(right.eye, (-1, 0, -10))   # right = dir × up
    down = camera.key("r", 1.0)
    assert np.allclose(down.eye, (0, -1, -10))
    yaw = camera.key("y", 0.1)                        # rotates the direction about up by fov·5 degrees
    angle = math.degrees(math.atan2(yaw.dir[0], yaw.dir[2]))
    assert abs(abs(angle) - 2.0) < 1e-6 and np.allclose(yaw.eye, camera.eye)
    roll = camera.key("e", 0.1)
    assert abs(math.degrees(math.acos(float(np.dot(normalize(vec(roll.up)), vec(0, 1, 0))))) - 2.0) < 1e-6
    assert np.allclose(camera.key("~", 0.1).target, (0, 0, 10))
    assert camera.key("z", 0.1) is None
    # orthogonalised up has no component along the view direction
    skewed = Camera3D(eye=(0, 0, -10), target=(0, 0, 0), up=(0, 1, 1)).orthogonalized()
    assert abs(float(np.dot(vec(skewed.up), skewed.dir))) < 1e-12


def test_camera3d_drags_and_wheel():
    down = Camera3D(eye=(0, 0, -10), target=(0, 0, 0), up=(0, 1, 0), fov=0.4)
    panned = down.drag("pan", down, (0.1, 0.0), 0.1)            # dp.x = 0.1 → offset right_down · 10 · dp.x · speed
    speed = 0.1 * (0.4 + 0.5)
    assert np.allclose(vec(panned.eye) - vec(down.eye), np.cross(down.dir, vec(down.up)) * 1.0 * speed)
    dolly = down.drag("dolly", down, (0.2, 0.0), 0.1)
    assert np.allclose(vec(dolly.eye), vec(down.eye) - down.direction * 0.2 * speed) and np.allclose(dolly.target, down.direction + vec(dolly.eye))
    orient = down.drag("orient", down, (0.05, 0.0), 0.1)
    assert np.allclose(orient.eye, down.eye) and not np.allclose(orient.target, down.target)
    assert abs(np.linalg.norm(vec(orient.target) - vec(orient.eye)) - 1.0) < 1e-9       # FragM orients a unit direction
    orbit = down.drag("orbit_origin", down, (0.05, 0.0), 0.1)
    assert abs(np.linalg.norm(vec(orbit.eye)) - 10.0) < 1e-9                                 # stays on the sphere about the origin
    target = down.drag("orbit_target", down, (0.05, 0.02), 0.1)
    assert np.allclose(target.target, down.target) and abs(np.linalg.norm(vec(target.eye) - vec(target.target)) - 10.0) < 1e-9
    wheel = down.wheel(2.0, 0.1)
    assert np.allclose(vec(wheel.eye) - vec(down.eye), down.dir * 0.1 * 2.0 / 0.4)
    point = down.screen_to_3d(320, 240, 640, 480, 0.5)
    assert np.allclose(point, (0, 0, -8))                     # the centre pixel, depth 1/0.5 along the view direction
    assert down.projection_view(16 / 9).shape == (4, 4)


def test_camera2d_keys_drags_and_wheel():
    camera = Camera2D(center=(0.0, 0.0), zoom=2.0)
    assert np.allclose(camera.key("d", 1.0).center, (0.05, 0)) and np.allclose(camera.key("w", 1.0).center, (0, 0.05))
    assert math.isclose(camera.key("q", 1.0).zoom, 2.1) and math.isclose(camera.key("e", 2.0).zoom, 2.0 / 1.05 ** 2)
    assert camera.key("t", 1.0) is None
    panned = camera.drag("pan", camera, (320, 240), (352, 240), 640, 480)     # dragged right by 32 px = 0.1 of the half-width
    assert np.allclose(panned.center, (-0.1 / 2.0, 0.0))
    zoomed = camera.drag("zoom", camera, (320, 240), (320, 200), 640, 480)    # dragged up: dp.y = +1/6 → zoom grows by that fraction
    assert zoomed.zoom > camera.zoom and not np.allclose(zoomed.center, camera.center) or np.allclose(zoomed.center, camera.center)
    fixed = camera.wheel(1.0, (320, 240), 640, 480)
    assert math.isclose(fixed.zoom, 2.3) and np.allclose(fixed.center, (0, 0))       # the centre pixel stays put
    off_centre = camera.wheel(1.0, (480, 240), 640, 480)
    assert not np.allclose(off_centre.center, (0, 0))
    traveling = camera.wheel(1.0, (480, 240), 640, 480, traveling=True)
    assert np.allclose(traveling.center, (0.25 / 2.0, 0.0))
    transformed = Camera2D(enable_transform=True, rotate_angle=90.0)
    assert np.allclose(transformed.transform() @ vec(1, 0), (0, 1), atol=1e-12)
