"""The gradient bridge: GIMP .ggr parsing / evaluation, the host format round trip and the emitted GLSL."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from fractalchemy.formats import load_gradient, save_gradient
from fractalchemy.formats.ggr import (BlendType, ColorType, Segment, evaluate_segments, format_ggr, parse_ggr, sample_segments,
                                      segments_from_gradient)
from fractalchemy.fragments.gradient_glsl import GradientGlslOptions, gradient_glsl, write_strip
from fractalchemy.model import Gradient

GGR = """GIMP Gradient
Name: Test
4
0.000000 0.250000 0.500000 1.000000 0.000000 0.000000 1.000000 0.000000 1.000000 0.000000 1.000000 0 0
0.500000 0.750000 0.800000 0.000000 1.000000 0.000000 1.000000 0.000000 0.000000 1.000000 1.000000 2 1
0.800000 0.900000 0.950000 0.000000 0.000000 1.000000 1.000000 1.000000 1.000000 0.000000 1.000000 1 2
0.950000 0.970000 1.000000 0.2 0.3 0.4 1.000000 0.9 0.8 0.7 1.000000 3 0 0 0
"""


def _close(a, b, tol=1e-6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def test_parse_and_evaluate_gimp_shapes():
    name, segments = parse_ggr(GGR)
    assert name == "Test" and len(segments) == 4
    assert segments[1].blend == BlendType.SINE and segments[1].color == ColorType.HSV_CCW
    assert _close(evaluate_segments(segments, 0.0), (1, 0, 0))
    assert _close(evaluate_segments(segments, 0.25), (0.5, 0.5, 0))      # linear midpoint is exactly half way
    assert _close(evaluate_segments(segments, 0.5), (0, 1, 0))
    assert _close(evaluate_segments(segments, 0.75), (0, 1, 1))          # sine / HSV ccw: green → blue through cyan at the middle
    assert _close(evaluate_segments(segments, 0.9), (0, 1, 0.5))         # curved / HSV cw: half way at the midpoint
    assert _close(evaluate_segments(segments, 1.0), (0.9, 0.8, 0.7))


def test_curved_shape_hits_half_at_the_midpoint():
    segment = Segment(0.0, 0.2, 1.0, (0, 0, 0), (1, 1, 1), BlendType.CURVED)
    assert abs(segment.blend_factor(0.2) - 0.5) < 1e-9
    increasing = Segment(0.0, 0.5, 1.0, (0, 0, 0), (1, 1, 1), BlendType.SPHERE_INCREASING)
    values = [increasing.blend_factor(t) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert values == sorted(values) and values[0] == 0.0 and abs(values[-1] - 1.0) < 1e-9


def test_bad_files_are_reported():
    with pytest.raises(Exception, match="GIMP"):
        parse_ggr("not a gradient")
    with pytest.raises(Exception, match="segment"):
        parse_ggr("GIMP Gradient\nName: x\n1\n0 0.5 1 1 0\n")


def test_format_round_trip_through_the_registry(tmp_path: Path):
    path = tmp_path / "t.ggr"
    path.write_text(GGR)
    gradient = load_gradient(path)
    assert gradient.name == "Test" and len(gradient) > 4
    assert gradient.color_at(0.0) == (255, 0, 0) and gradient.color_at(0.5) == (0, 255, 0)
    simple = Gradient.from_colors("rgb", [(255, 0, 0), (0, 255, 0), (0, 0, 255)])
    save_gradient(simple, tmp_path / "out.ggr")
    back = load_gradient(tmp_path / "out.ggr")
    assert [s.color for s in back.stops] == [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    assert format_ggr("x", segments_from_gradient(simple)).startswith("GIMP Gradient\nName: x\n2\n")


def test_host_gradient_wrap_becomes_end_segments():
    gradient = Gradient("w", [])
    gradient.stops = []
    gradient = Gradient.from_colors("w", [(0, 0, 0), (255, 255, 255)])
    gradient.move_stop(0, 0.25)
    segments = segments_from_gradient(gradient)
    assert segments[0].left == 0.0 and segments[-1].right == 1.0
    assert _close(evaluate_segments(segments, 0.0), tuple(c / 255 for c in gradient.color_at(0.0)), 1 / 255)


def test_glsl_text_forms():
    name, segments = parse_ggr(GGR)
    text = gradient_glsl(name, segments, GradientGlslOptions(function_name="my grad"))
    assert "vec3 my_grad(float t)" in text and "my_grad_left[4]" in text
    table = gradient_glsl(name, segments, GradientGlslOptions(form="table", table_size=16, role="object"))
    assert "gradient_table[16]" in table and "#define providesColor" in table and "vec3 baseColor(" in table
    texture = gradient_glsl(name, segments, GradientGlslOptions(form="texture", texture_file="g.png", role="background"))
    assert "uniform sampler2D gradientTex; file[g.png]" in texture and "backgroundColor(" in texture


def test_strip_png(tmp_path: Path):
    from PIL import Image

    _name, segments = parse_ggr(GGR)
    write_strip(segments, tmp_path / "g.png", 64)
    image = Image.open(tmp_path / "g.png")
    assert image.size == (64, 1) and image.getpixel((0, 0))[:3] == (255, 0, 0)


@pytest.mark.parametrize("form", ["segments", "table"])
def test_emitted_glsl_matches_the_python_reference(gl_context, form):
    name, segments = parse_ggr(GGR)
    width = 512
    code = gradient_glsl(name, segments, GradientGlslOptions(form=form, table_size=width))
    program = gl_context.program(
        vertex_shader="#version 330\nin vec2 p; void main() { gl_Position = vec4(p, 0.0, 1.0); }",
        fragment_shader=f"#version 330\nout vec4 o;\n{code}\nvoid main() {{ o = vec4(gradient((gl_FragCoord.x - 0.5) / {width - 1}.0), 1.0); }}")
    fbo = gl_context.simple_framebuffer((width, 1))
    fbo.use()
    vbo = gl_context.buffer(np.array([-1, -1, 3, -1, -1, 3], dtype="f4").tobytes())
    gl_context.simple_vertex_array(program, vbo, "p").render()
    got = np.frombuffer(fbo.read(components=3, dtype="f4"), dtype="f4").reshape(width, 3)
    positions = [i / (width - 1) for i in range(width)]
    if form == "segments":
        reference = np.array([evaluate_segments(segments, t) for t in positions])
        assert np.abs(got - reference).max() <= 1.0 / 255
    else:
        table = np.array(sample_segments(segments, width))   # pixel i samples t = i/(N-1): exactly table entry i
        assert np.abs(got - table).max() <= 1.0 / 255
    fbo.release()
    program.release()
    vbo.release()
