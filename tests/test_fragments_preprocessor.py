"""The .frag preprocessor, the parameter model, the settings text and the preset helpers (Qt-free)."""

from pathlib import Path

import pytest

from fractalchemy.fragments import presets
from fractalchemy.fragments.annotations import rewrite_bound
from fractalchemy.fragments.examples import INCLUDE_DIR, all_examples, example_tree, is_include
from fractalchemy.fragments.files import FileManager, IncludeNotFound
from fractalchemy.fragments.parameters import (BoolParameter, ColorParameter, FloatColorParameter, FloatParameter, IntMenuParameter,
                                               IntParameter, LockType, SamplerParameter, SliderType, VectorParameter, format_number,
                                               glsl_float, locked_substitution, parse_settings, settings_line)
from fractalchemy.fragments.preprocessor import MAIN_RENAMED, Preprocessor
from fractalchemy.fragments.state import ParameterState

ANNOTATED = """#version 120
#info A test fragment
#group Shape
// The power
uniform float Power; slider[1,8,16] Logarithmic Locked
uniform double Fine; slider[0,0.5,1]
uniform vec3 Dir; slider[(0,0,0),(0,1,0),(0,0,0)]
uniform vec3 Up; slider[(0,0,0),(0,1,0),(0,0,0)]
uniform vec2 Center; slider[(-2,-2),(0.5,0),(2,2)] NotLockable
uniform dvec4 Q; slider[(0,0,0,0),(1,1,1,1),(2,2,2,2)]
uniform vec3 Tint; color[1,0.5,0.25]
uniform vec4 Glow; color[0,0.7,1,0.9,0.8,0.1]
uniform int Iterations; slider[1,12,100]
uniform int Mode; menu[1,Linear;Filmic;Reinhard]
uniform bool Julia; checkbox[true]
uniform sampler2D Tex; file[texture.jpg]
uniform sampler2D Hdr; file[Ditch-River_Env.hdr, R;G;B;A]
uniform float Broken; slider[,5,]
#group default
uniform float Plain; slider[0,1,2]
#define DontClearOnChange
#define IterationsBetweenRedraws 3
#define SubframeMax 40
#TexParameter Tex GL_TEXTURE_WRAP_S GL_REPEAT
#camera 3D
#buffer RGBA16F
#replace "OLD" "NEW"
float f() { return OLD; }
void main() { gl_FragColor = vec4(Power); }
#preset Default
Power = 2
Center = 1,1
#endpreset
#preset KeyFrame.0002
Eye = 1,2,3
#endpreset
"""


def parse(text: str, path: Path | None = None, **kw):
    return Preprocessor(FileManager(original=path), **kw).parse(text, path)


def test_examples_tree_and_includes_are_bundled():
    folders = dict(example_tree())
    assert any(folder.name == "Historical 3D Fractals" for folder in folders)
    assert (INCLUDE_DIR / "DE-Raytracer.frag").is_file() and is_include(INCLUDE_DIR / "DE-Raytracer.frag")
    assert len(all_examples()) > 150 and all(not is_include(p) for p in all_examples())


def test_file_manager_resolution_order(tmp_path):
    (tmp_path / "MathUtils.frag").write_text("// shadow")
    frag = tmp_path / "a.frag"
    frag.write_text("")
    files = FileManager(original=frag)
    assert files.resolve_name("MathUtils.frag", frag) == tmp_path / "MathUtils.frag"     # beside the fragment first
    assert files.resolve_name("DE-Raytracer.frag", frag) == INCLUDE_DIR / "DE-Raytracer.frag"
    with pytest.raises(IncludeNotFound) as info:
        files.resolve_name("nope.frag", frag)
    assert tmp_path / "nope.frag" in info.value.tried and INCLUDE_DIR / "nope.frag" in info.value.tried
    assert "DE-Raytracer.frag" in files.fragment_files() and files.image_files()


def test_annotations_become_parameters_with_fragm_semantics():
    source = parse(ANNOTATED)
    by_name = {p.name: p for p in source.params}
    power = by_name["Power"]
    assert isinstance(power, FloatParameter) and (power.from_, power.default, power.to) == (1, 8, 16)
    assert power.lock == LockType.LOCKED and power.slider == SliderType.LOGARITHMIC and power.group == "Shape"
    assert power.tooltip == "The power"
    assert by_name["Fine"].is_double and by_name["Fine"].precision == 18
    direction = by_name["Dir"]
    assert isinstance(direction, VectorParameter) and direction.normalize and direction.from_ == (-1, -1, -1)
    assert not by_name["Up"].normalize                            # FragM's exception for the camera's Up
    assert by_name["Center"].lock == LockType.NOT_LOCKABLE and by_name["Center"].tooltip == ""
    assert by_name["Q"].components == 4 and by_name["Q"].is_double
    assert isinstance(by_name["Tint"], ColorParameter) and by_name["Tint"].default == (1, 0.5, 0.25)
    glow = by_name["Glow"]
    assert isinstance(glow, FloatColorParameter) and glow.default == (0.9, 0.8, 0.1, 0.7) and (glow.from_, glow.to) == (0, 1)
    assert isinstance(by_name["Iterations"], IntParameter) and by_name["Iterations"].default == 12
    assert isinstance(by_name["Mode"], IntMenuParameter) and by_name["Mode"].texts == ("Linear", "Filmic", "Reinhard")
    assert isinstance(by_name["Julia"], BoolParameter) and by_name["Julia"].default is True
    assert isinstance(by_name["Tex"], SamplerParameter) and by_name["Tex"].lock == LockType.ALWAYS_LOCKED
    assert by_name["Hdr"].channels == "R;G;B;A" and source.textures["Hdr"] == INCLUDE_DIR / "Ditch-River_Env.hdr"
    assert "Broken" not in by_name and any("Broken" in m.text for m in source.messages if m.level == "warning")
    assert by_name["Plain"].group == ""                            # `#group default` is the Default group
    # the declaration lines became bare uniforms
    assert "uniform float Power;" in source.fragment and not any("slider[" in line and "Power" in line for line in source.fragment)


def test_directives_flags_presets_and_replacements():
    source = parse(ANNOTATED)
    assert source.camera == "3D" and source.camera_kind == "3D" and source.buffer == "RGBA16F"
    assert not source.clear_on_change and source.subframes_between_redraws == 3 and source.subframe_max == 40
    assert source.texture_params == {"Tex": {"GL_TEXTURE_WRAP_S": "GL_REPEAT"}}
    assert set(source.presets) == {"Default", "KeyFrame.0002"} and source.presets["Default"] == "Power = 2\nCenter = 1,1"
    assert source.keyframe_names() == ["KeyFrame.0002"]
    assert not any(line.strip().startswith("#preset") for line in source.fragment)
    assert "float f() { return NEW; }" in source.fragment                 # #replace applies to later lines
    assert any(line.startswith(f"void {MAIN_RENAMED}") for line in source.fragment)
    assert source.fragment[-2] == f"void main() {{ {MAIN_RENAMED}(); }}"   # moveMain
    assert source.version_line == "#version 120"
    assert any(m.level == "script" and m.text == "A test fragment" for m in source.messages)
    assert source.runnable
    # every emitted line keeps its origin (1-based line of the only file), generated lines map to None
    origin = source.line_map.origin(source.fragment.index("uniform float Power;") + 1)
    assert origin == (None, 5)
    assert source.line_map.origin(len(source.fragment) - 1) is None


def test_move_main_off_and_vertex_section():
    text = "#vertex\nvarying vec2 c;\nvoid main() { gl_Position = gl_Vertex; c = gl_Vertex.xy; }\n#endvertex\nvarying vec2 c;\nvoid main() { gl_FragColor = vec4(c, 0, 1); }\n"
    source = parse(text, move_main=False)
    assert source.vertex == ["varying vec2 c;", "void main() { gl_Position = gl_Vertex; c = gl_Vertex.xy; }"]
    assert all(line.startswith("//") for line in source.fragment[:4])    # the vertex lines are commented out in the fragment
    assert "void main() { gl_FragColor = vec4(c, 0, 1); }" in source.fragment and MAIN_RENAMED not in source.text()
    assert source.vertex_line_map.origin(1) == (None, 2)


def test_includes_are_textual_every_time_and_only_at_column_zero(tmp_path):
    (tmp_path / "inc.frag").write_text("uniform float FromInclude; slider[0,1,2]\n#group Inc\n")
    frag = tmp_path / "main.frag"
    frag.write_text('#include "inc.frag"\n#include "inc.frag"\n/*\n  #include "inc.frag"\n*/\nuniform float After; slider[0,1,2]\n')
    source = parse(frag.read_text(), frag)
    assert [p.name for p in source.params] == ["FromInclude", "FromInclude", "After"]
    assert source.params[2].group == ""                   # `#group default` after every include
    assert source.dependencies == [tmp_path / "inc.frag", tmp_path / "inc.frag"]
    assert "  #_include" not in source.text() and '  #include "inc.frag"' in source.fragment  # left for the GLSL comment (the layer disarms it)


def test_missing_include_is_critical_but_parsing_continues(tmp_path):
    frag = tmp_path / "m.frag"
    frag.write_text('#include "nowhere.frag"\nuniform float A; slider[0,1,2]\n')
    source = parse(frag.read_text(), frag)
    assert [p.name for p in source.params] == ["A"]
    assert any(m.level == "critical" and "nowhere.frag" in m.text for m in source.messages)
    assert any(m.text.startswith("Tried path:") for m in source.messages)


def test_include_cycle_is_an_error_not_a_crash(tmp_path):
    (tmp_path / "a.frag").write_text('#include "b.frag"\n')
    (tmp_path / "b.frag").write_text('#include "a.frag"\n')
    source = parse((tmp_path / "a.frag").read_text(), tmp_path / "a.frag")
    assert any("cycle" in m.text for m in source.messages if m.level == "critical")


def test_buffer_shader_is_parsed_separately_and_takes_the_version(tmp_path):
    (tmp_path / "post.frag").write_text("uniform float Gamma; slider[0,2,5]\nvoid main() { gl_FragColor = vec4(Gamma); }\n")
    frag = tmp_path / "m.frag"
    frag.write_text('#version 130\n#buffershader "post.frag"\nuniform float A; slider[0,1,2]\nvoid main() {}\n')
    source = parse(frag.read_text(), frag)
    assert source.buffer_shader is not None and source.buffer_shader.version_line == "#version 130"
    assert source.buffer_shader.fragment[0] == "#version 130"
    assert [p.name for p in source.buffer_shader.params] == ["Gamma"] and MAIN_RENAMED not in source.buffer_shader.text()
    assert [p.name for p in source.all_params] == ["A", "Gamma"]


def test_autosave_fragment_drops_presets_but_keeps_keyframes_and_lists_dependencies(tmp_path):
    frag = tmp_path / "m.frag"
    frag.write_text('#include "MathUtils.frag"\n#preset Default\nA = 1\n#endpreset\n#preset KeyFrame.0001\nEye = 1,2,3\n#endpreset\nfloat x;\n')
    text, dependencies = Preprocessor(FileManager(original=frag)).create_autosave_fragment(frag.read_text(), frag)
    assert "#preset Default" not in text and "#preset KeyFrame.0001" in text and '#include "MathUtils.frag"' in text
    assert dependencies == [INCLUDE_DIR / "MathUtils.frag"]


def test_donotrun_counts_only_in_the_users_file():
    bulb = next(p for p in all_examples() if p.name == "Mandelbulb.frag")
    source = parse(bulb.read_text(), bulb)
    assert source.runnable and source.camera_kind == "3D" and source.buffer_shader is not None
    assert len(source.params) == 69 and source.presets.keys() == {"Default", "Octobulb"}


# --- parameters and settings text ----------------------------------------------------------------------------------------------
def test_number_formatting_and_glsl_literals():
    assert format_number(0.1 + 0.2) == "0.3" and format_number(1e-7) == "1e-07" and format_number(-0.0) == "0"
    assert glsl_float(2) == "2.0" and glsl_float(0.5) == "0.5" and glsl_float(1e-7) == "1e-07"
    power = FloatParameter("Power", "float", default=8.0, from_=1, to=16)
    assert power.glsl_literal(8) == "8.0" and power.format(0.1234567891234) == "0.123456789"
    fine = FloatParameter("Fine", "double", default=0.5, from_=0, to=1)
    assert len(fine.format(0.1234567891234567891).lstrip("0.")) == 18     # eighteen significant digits for doubles
    assert locked_substitution(power, 8, True) == "#define Power 8.0" and locked_substitution(power, 8, False) == "const float Power = 8.0;"
    eye = VectorParameter("Eye", "vec3", default=(0, 0, -10), from_=(-50,) * 3, to=(50,) * 3)
    assert locked_substitution(eye, (1, 2, 3)) == "#define Eye vec3(1.0,2.0,3.0)"
    assert locked_substitution(SamplerParameter("T", "sampler2D", default="a.png"), "a.png") is None


def test_settings_line_suffixes_and_parsing():
    power = FloatParameter("Power", "float", default=8.0, from_=1, to=16)
    assert settings_line(power, 8, LockType.NOT_LOCKED, SliderType.LINEAR) == "Power = 8"
    assert settings_line(power, 8, LockType.LOCKED, SliderType.LOGARITHMIC) == "Power = 8 Logarithmic Locked"
    parsed = parse_settings("// Generated by: x\nPower = 8 Logarithmic Locked\nEye = 1,2,3\nPower1:Linear:0:1:2:0:10:0.3:1:1.7:1:0\nbad\n#x\n")
    assert [(l.name, l.value_text, l.lock, l.slider) for l in parsed.lines] == [
        ("Power", "8", LockType.LOCKED, SliderType.LOGARITHMIC), ("Eye", "1,2,3", None, SliderType.LINEAR)]
    assert parsed.easing == ["Power1:Linear:0:1:2:0:10:0.3:1:1.7:1:0"] and parsed.warnings == ["Expected a key value pair, found: bad"]


def test_parameter_state_apply_clamp_reset_and_rebuild():
    source = parse(ANNOTATED)
    state = ParameterState(source.all_params)
    assert state.get("Power") == 8 and state.is_locked("Power") and state.get("Julia") is True
    result = state.apply_settings("Power = 32\nJulia = false\nNope = 1\nCenter = 0.25,0.5 Locked\nMode = 7\n")
    assert state.get("Power") == 16 and any("clamped" in w for w in result.warnings)
    assert state.get("Julia") is False and state.get("Center") == (0.25, 0.5) and state.get("Mode") == 2
    assert any(w.startswith("Could not find: Nope") for w in result.warnings) and result.recompile      # Power is locked: its value is in the source
    assert state.locked_names() == ["Power", "Center"] and "Tex" not in state.locked_names()
    text = state.to_text()
    assert "Power = 16 Logarithmic" not in text and "Power = 16" in text      # defaults of the annotation are not repeated
    assert "Center = 0.25,0.5 Locked" in text
    assert state.camera_text("3D") == "Up = 0,1,0" and state.camera_text("2D") == "Center = 0.25,0.5 Locked"
    assert state.reset(["Power"]) == ["Power"] and state.get("Power") == 8
    # a rebuild keeps values for unchanged parameters and starts over where the range changed
    changed = [FloatParameter("Power", "float", default=8.0, from_=1, to=32, lock=LockType.LOCKED, slider=SliderType.LOGARITHMIC)]
    rebuilt = state.rebuilt(changed + [p for p in source.all_params if p.name != "Power"])
    assert rebuilt.get("Power") == 8 and rebuilt.get("Center") == (0.25, 0.5) and rebuilt.is_locked("Center")
    assert state.diff(rebuilt) == ["Power"]          # the one that started over


def test_preset_text_helpers():
    text = "float x;\n#preset Default\nA = 1\n#endpreset\n"
    assert presets.preset_names(text) == ["Default"] and presets.find_preset(text, "default") == (9, len(text))
    replaced = presets.replace_preset(text, "Default", "A = 2")
    assert "A = 2" in replaced and "A = 1" not in replaced
    appended = presets.replace_preset(text, "KeyFrame.0001", "Eye = 1,2,3")
    assert appended.endswith("#preset KeyFrame.0001\nEye = 1,2,3\n#endpreset\n")
    assert presets.remove_preset(appended, "Default").count("#preset") == 1
    assert presets.next_keyframe_name(["Default", "KeyFrame.0001"]) == "KeyFrame.0002" and presets.keyframe_index("KeyFrame.0012") == 12
    assert presets.is_range("Range-0010-0100") and not presets.is_keyframe("Range-1")
    assert presets.selected_preset_name("#preset Foo\nA = 1\n#endpreset") == "Foo" and presets.selected_preset_name("A = 1") is None


def test_rewrite_bound_edits_the_declaration_in_place():
    text = "uniform float Power; slider[1,8,16]\nuniform vec3 Eye; slider[(-50,-50,-50),(0,0,-10),(50,50,50)]\nuniform int It; slider[1,12,100]"
    assert rewrite_bound(text, "Power", 1, 2, 32).splitlines()[0] == "uniform float Power; slider[1,8,32]"
    assert rewrite_bound(text, "Eye", 2, 1, -99).splitlines()[1] == "uniform vec3 Eye; slider[(-50,-99,-50),(0,0,-10),(50,50,50)]"
    assert rewrite_bound(text, "It", 1, 2, 500).splitlines()[2] == "uniform int It; slider[1,12,500]"
    assert rewrite_bound(text, "Nope", 1, 2, 3) is None
