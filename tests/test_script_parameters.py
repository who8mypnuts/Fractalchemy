"""`param()` and the live-run rules (Qt-free): declarations, coercion, restricted runs, static blockers, baking defaults."""

import threading

import pytest

from fractalchemy.fractal.scene import Flame, XForm
from fractalchemy.scripting.parameters import ParameterError, bake_defaults, coerce, live_blockers, make_spec
from fractalchemy.scripting.runner import run_script


def _run(code, parameters=None, restricted=None, seed=7, flame=None):
    return run_script(code, flame or Flame("x", [XForm(), XForm(coefs=(0.5, 0, 0, 0.5, 0.5, 0))]), None, threading.Event(),
                      seed=seed, parameters=parameters, restricted=restricted)


@pytest.mark.parametrize("args, kind", [
    (("A", 30, -180, 180), "int"), (("A", 30.0, -180, 180), "float"), (("A", 0.5, 0, 1), "float"), (("A", 3, 1, 12, 1), "int"),
    (("A", 3, 1, 12, 0.5), "float"), (("A", True), "bool"), (("A", "hello"), "text"), (("A", 2), "int"), (("A", 2.5), "float"),
])
def test_the_kind_follows_the_default(args, kind):
    spec = make_spec(*args)
    assert spec.kind == kind
    if kind == "int":
        assert isinstance(spec.default, int) and spec.decimals == 0


def test_choices_and_decimals():
    spec = make_spec("Palette", "Fire", choices=["Fire", "Ocean"])
    assert spec.kind == "choice" and spec.choices == ("Fire", "Ocean")
    assert make_spec("A", 0.5, 0, 1, 0.05).decimals == 2 and make_spec("A", 0.1, 0, 0.2).decimals == 3
    assert make_spec("A", 0.5, decimals=5).decimals == 5 and not make_spec("A", 0.5).bounded


@pytest.mark.parametrize("kwargs, message", [
    (dict(name="", default=1), "needs a name"), (dict(name="A", default=5, minimum=10, maximum=1), "greater than"),
    (dict(name="A", default=50, minimum=0, maximum=10), "outside"), (dict(name="A", default=True, minimum=0), "check box"),
    (dict(name="A", default="x", maximum=3), "text has no"), (dict(name="A", default="z", choices=["x", "y"]), "not one of"),
    (dict(name="A", default="x", choices=[]), "must not be empty"), (dict(name="A", default=[1, 2]), "must be a number"),
    (dict(name="A", default=1.0, step=0), "positive"), (dict(name="A", default=float("nan")), "finite"),
])
def test_misuse_is_reported(kwargs, message):
    with pytest.raises(ParameterError, match=message):
        make_spec(**kwargs)


def test_coercion():
    number = make_spec("A", 30, -180, 180)
    assert coerce(number, 500) == 180 and coerce(number, 12.6) == 13 and coerce(number, "x") == 30 and coerce(number, None) == 30
    assert coerce(make_spec("B", 0.5, 0, 1), -3.0) == 0.0 and coerce(make_spec("B", 0.5), 1e9) == 1e9
    assert coerce(make_spec("C", True), 1) is True and coerce(make_spec("C", True), False) is False
    assert coerce(make_spec("D", "Fire", choices=["Fire", "Ocean"]), "Sea") == "Fire"
    assert coerce(make_spec("E", "t"), 5) == "t"


def test_runs_use_the_given_values_or_the_defaults_and_report_the_declarations():
    code = ("angle = param('Angle', 30, min=-180, max=180)\n"
            "keep = param('Keep', True)\n"
            "for t in transforms:\n    t.rotate(angle)\n"
            "print(angle, keep)\n")
    default = _run(code)
    assert default.ok and default.values == {"Angle": 30, "Keep": True}
    assert [(d.name, d.kind, d.line) for d in default.declarations] == [("Angle", "int", 1), ("Keep", "bool", 2)]
    custom = _run(code, {"Angle": 90, "Keep": False, "Unknown": 3})
    assert custom.values == {"Angle": 90, "Keep": False}
    assert custom.flame.xforms[0].coefs != default.flame.xforms[0].coefs


def test_same_seed_and_values_give_the_same_flame_and_random_draws_hold_still():
    code = ("m = param('Max', 45, min=0, max=360)\n"
            "for t in transforms:\n    t.rotate(random(-1, 1) * m)\n")
    a, b = _run(code, {"Max": 45}), _run(code, {"Max": 45})
    assert a.flame.xforms[0].coefs == b.flame.xforms[0].coefs
    doubled = _run(code, {"Max": 90})
    # the random factor is the same draw: doubling the maximum doubles the angle, it does not pick a new one
    import math
    angle = lambda f: math.degrees(math.atan2(f.xforms[0].coefs[1], f.xforms[0].coefs[0]))  # noqa: E731
    assert angle(doubled.flame) == pytest.approx(2 * angle(a.flame), abs=1e-6)


def test_redeclaring_a_parameter():
    same = _run("a = param('A', 1, min=0, max=5)\nb = param('A', 1, min=0, max=5)\nassert a == b\n")
    assert same.ok
    clash = _run("a = param('A', 1, min=0, max=5)\nb = param('A', 2)\n")
    assert not clash.ok and "declared twice" in clash.error.message and "lines 1 and 2" in clash.error.message
    many = _run("for i in range(100):\n    param(f'p{i}', 1)\n")
    assert not many.ok and "at most" in many.error.message


@pytest.mark.parametrize("line, effect", [
    ("save_flame(r'{path}')", "write"), ("message('hi')", "message"), ("input_number('n?', 2)", "prompt"),
    ("confirm('sure?')", "prompt"), ("update()", "update"), ("sleep(0.01)", "sleep"),
])
def test_restricted_runs_refuse_side_effects_before_they_happen(tmp_path, line, effect):
    path = tmp_path / "out.flame"
    code = f"a = param('A', 1.0)\ntry:\n    {line.format(path=path)}\nexcept Exception:\n    print('swallowed')\n"
    free = _run(code)
    assert free.ok and effect in free.effects and not free.refused
    restricted = _run(code, restricted="while its controls update live")
    assert restricted.ok and restricted.stopped and "so it does not run while its controls update live" in restricted.refused
    assert "(line 3)" in restricted.refused and not restricted.output_lines           # `except Exception` did not catch it
    if effect == "write":
        path.unlink()
        _run(code, restricted="live")
        assert not path.exists()


def test_reading_is_allowed_when_restricted(samples):
    result = _run(f"load_flame(r'{samples / 'sample flames' / 'candy.flame'}', 2)\n", restricted="live")
    assert result.ok and not result.refused and "read" in result.effects


def test_live_blockers_see_imports_and_dangerous_calls():
    assert live_blockers("import math, colorsys\nfrom random import random\nx = param('A', 1)\n") == []
    found = [str(b) for b in live_blockers("import os\nfrom pathlib import Path\nopen('x')\nexec('1')\n")]
    assert found == ["it imports os (line 1)", "it imports from pathlib (line 2)", "it calls open() (line 3)", "it calls exec() (line 4)"]
    assert live_blockers("def (:") == []


def test_bake_defaults_rewrites_only_the_literals():
    code = ("# tool\n"
            "angle = param('Angle', 30, min=-180, max=180)   # turn\n"
            "name = param(\"Name\", default='it\\'s')\n"
            "neg = param('Neg', -2.5)\n"
            "pair = param('Pair', 4)\n"
            "calc = param('Calc', 2 * 3)\n"
            "chosen = param('Pal', 'Fire', choices=['Fire', 'Ocean'])\n")
    new, skipped = bake_defaults(code, {"Angle": 45, "Name": 'say "hi"', "Neg": 1.25, "Calc": 7, "Pal": "Ocean", "Absent": 1})
    assert skipped == ["Calc"]
    assert "angle = param('Angle', 45, min=-180, max=180)   # turn" in new
    assert "param(\"Name\", default='say \"hi\"')" in new and "param('Neg', 1.25)" in new and "param('Pal', 'Ocean', choices" in new
    assert "param('Pair', 4)" in new and "param('Calc', 2 * 3)" in new
    compile(new, "x", "exec")
    assert _run(new).values["Angle"] == 45


def test_gradient_presets():
    result = _run("names = list_gradient_presets()\ngradient.preset(names[1])\nprint(names)\n")
    assert result.ok and result.flame.palette[0] != Flame().palette[0]
    assert not _run("gradient.preset('Aurora')").ok
