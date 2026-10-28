"""The scripting API, the runner, completion / context help, templates, Flame → Script, and the Script Editor window."""

import threading
import time

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QInputDialog, QMessageBox, QToolButton

from fractalchemy.fractal import variations as V
from fractalchemy.fractal.formats import load_flame, load_flames
from fractalchemy.fractal.scene import Flame, XForm
from fractalchemy.scripting import completion as C
from fractalchemy.scripting import docs as D
from fractalchemy.scripting import templates as T
from fractalchemy.scripting.api import ScriptContext, ScriptError, ScriptHost
from fractalchemy.scripting.generate import flame_to_script
from fractalchemy.scripting.runner import check_syntax, run_script
from tests.conftest import spin, wait_until


class RecordingHost(ScriptHost):
    """Collects output; answers prompts from a queue (default: the default value / yes)."""

    def __init__(self, answers=()):
        self.lines: list[str] = []
        self.messages: list[str] = []
        self.updates: list[Flame] = []
        self.answers = list(answers)

    def print(self, text):
        self.lines.append(text)

    def clear(self):
        self.lines.clear()

    def message(self, text):
        self.messages.append(text)

    def input_text(self, prompt, default):
        return self.answers.pop(0) if self.answers else default

    def confirm(self, text):
        return self.answers.pop(0) if self.answers else True

    def update(self, flame, wait):
        self.updates.append(flame)


def two_transforms() -> Flame:
    return Flame("two", [XForm(weight=1.0, coefs=(0.5, 0, 0, 0.5, -0.5, 0)), XForm(weight=0.5, color=1.0, variations={"spherical": 1.0})])


def run(code: str, flame: Flame | None = None, host: RecordingHost | None = None, stop=None):
    return run_script(code, flame if flame is not None else two_transforms(), host or RecordingHost(), stop)


# --- the API --------------------------------------------------------------------------------------------
def test_transform_attributes_affine_helpers_and_chaining():
    ctx = ScriptContext(two_transforms())
    t = ctx.transforms[0]
    assert (t.a, t.b, t.c, t.d, t.e, t.f) == (0.5, 0, 0, 0.5, -0.5, 0) and t.index == 0 and not t.is_final
    t.rotate(90)
    assert t.a == pytest.approx(0) and t.b == pytest.approx(-0.5) and t.c == pytest.approx(0.5) and t.d == pytest.approx(0)
    t.reset_affine().scale(2, 3).translate(0.1, 0.2)
    assert t.coefs == (2, 0, 0, 3, 0.1, 0.2)
    t.multiply(0, 1, 1, 0)                      # swap the axes
    assert t.coefs == (0, 3, 2, 0, 0.1, 0.2)
    t.origin = (1, 1)
    t.flip_horizontal()
    assert t.origin == (-1, 1) and t.a == 0 and t.c == -2
    t.post.a = 1.5
    assert t.xform.post[0] == 1.5 and t.post.coefs[0] == 1.5
    t.post.reset()
    assert not t.xform.has_post()
    t.symmetry = 0.5
    assert t.color_speed == 0.25
    t.weight = -1
    assert t.weight == 0.0 and repr(t).startswith("<Transform #1")
    assert ctx.transforms[1].is_final is False and ctx.transforms[-1] == ctx.transforms[1]
    with pytest.raises(ScriptError):
        ctx.transforms[5]


def test_variations_map_validates_names_fills_defaults_and_removes_on_zero():
    ctx = ScriptContext(two_transforms())
    t = ctx.transforms[0]
    t.variations["julian"] = 1
    assert t.xform.variations == {"linear": 1.0, "julian": 1.0} and t.params["julian_power"] == 1.0 and "julian_dist" in t.params
    t.set_variation("linear", 0)
    assert t.variation_names == ["julian"] and t.get_variation("linear") == 0 and t.has_variation("julian")
    with pytest.raises(ScriptError, match="unknown variation"):
        t.set_variation("no_such_thing", 1)
    t.params["julian_power"] = 4
    assert t.get_param("julian_power") == 4 and t.get_param("julian_dist") == 1.0
    with pytest.raises(ScriptError, match="unknown parameter"):
        t.set_param("julian_bogus", 1)
    t.variations = {"spherical": 0.7, "linear": 0.3}
    assert t.total_variation_weight() == pytest.approx(1.0)
    t.normalize_variations().clear_variations()
    assert t.variation_names == []


def test_adding_removing_moving_transforms_keeps_xaos_in_step_and_tracks_the_active_one():
    ctx = ScriptContext(two_transforms())
    ctx.xaos.set(0, 1, 0)
    added = ctx.add_transform(weight=2, color=0.5, variations={"swirl": 1}, a=0.3)
    assert ctx.active == 2 and ctx.transform == added and added.a == 0.3 and added.xform.params == {}
    assert ctx.xaos.matrix == [[1, 0, 1], [1, 1, 1], [1, 1, 1]]
    ctx.remove_transform(0)
    assert len(ctx.transforms) == 2 and ctx.xaos.matrix == [[1, 1], [1, 1]] and ctx.transform.variation_names == ["swirl"]
    copy = ctx.copy_transform(0)
    assert len(ctx.transforms) == 3 and copy.variation_names == ["spherical"] and ctx.active == 2
    ctx.set_active_transform(0)
    assert ctx.transform.index == 0
    ctx.swap_transforms(0, 2)
    assert ctx.transforms[2].variation_names == ["spherical"]
    ctx.move_transform(2, 0)
    assert ctx.transforms[0].variation_names == ["spherical"] and ctx.active == 0
    with pytest.raises(ScriptError):
        ctx.add_transform(bogus=1)
    final = ctx.set_final_transform(variations={"bubble": 1})
    assert final.is_final and final.color_speed == 0 and ctx.final_transform() == final
    ctx.set_final_transform(None)
    assert ctx.final_transform() is None
    ctx.clear_transforms()
    with pytest.raises(ScriptError, match="no transforms"):
        ctx.transform.weight


def test_camera_gradient_xaos_and_coloring_helpers(samples):
    ctx = ScriptContext(load_flame(samples / "sample flames" / "candy.flame", 2))
    ctx.clear_transforms()
    ctx.set_flame(two_transforms())
    ctx.add_transform(weight=1, variations={"swirl": 0.6, "linear": 0.4}, a=0.6, d=0.6, e=0.3)
    cam = ctx.camera
    cam.x, cam.y, cam.zoom, cam.rotate, cam.pitch = 0.5, -0.25, 1, 30, 45
    assert ctx.flame.camera.center == (0.5, -0.25) and ctx.flame.camera.pitch == pytest.approx(0.7853981)
    cam.zoom_by(2).rotate_by(350).pan(0.1, 0).set_size(400, 300)
    assert cam.zoom == 2 and cam.rotate == 20 and cam.x == pytest.approx(0.6) and cam.size == (400, 300)
    assert cam.fit() and ctx.flame.camera.scale > 1 and ctx.flame.camera.zoom == 0
    cam.reset_3d().reset()
    assert ctx.flame.camera.pitch == 0 and ctx.flame.camera.scale == 200 and cam.width == 400
    g = ctx.gradient
    g.set_stops([(0, "#000000"), (1, (255, 255, 255))])
    assert g.get_color(0) == (0, 0, 0) and g.get_color(255) == (255, 255, 255) and len(g.colors) == 256
    g.invert().reverse()
    assert g.get_color(0) == (0, 0, 0)
    g.rotate(0.5)
    assert g.get_color(128) == (0, 0, 0)
    g.from_colors(["#ff0000", "#00ff00"]).hue_shift(120)
    assert g.get_color(0)[1] > 200 and g.color_at(0.0) == g.get_color(0)
    g.random()
    assert len(g.stops) >= 3
    g.blend([(0, 0, 0)] * 256, 1.0)
    assert g.get_color(100) == (0, 0, 0)
    with pytest.raises(ScriptError):
        g.set_color(0, "not a colour")
    ctx.remove_transform(2)
    x = ctx.xaos
    x.chain()
    assert x.matrix == [[0, 1], [1, 0]] and not x.is_default
    x.reset()
    assert x.is_default and x.get(0, 1) == 1
    x.isolate(1)
    assert x.matrix == [[1, 0], [0, 1]]
    x.from_function(lambda i, j: i + j).set_row(0, [5, 5])
    assert x.matrix == [[5, 5], [1, 2]] and "5  5" in str(x)
    with pytest.raises(ScriptError):
        x.set(0, 9, 1)
    c = ctx.coloring
    c.brightness, c.gamma, c.background = 6, 2.5, "#102030"
    assert ctx.flame.coloring.background == (16, 32, 48) and c.background_hex == "#102030"
    c.reset()
    assert ctx.flame.coloring.brightness == 4.0


def test_flame_level_functions(tmp_path, samples):
    ctx = ScriptContext(two_transforms())
    ctx.snapshot("a")
    ctx.new_flame("fresh")
    assert ctx.flame.name == "fresh" and ctx.flame.xforms == [] and ctx.flame.camera.width == 800 and len(ctx.transforms) == 0
    ctx.restore("a")
    assert len(ctx.transforms) == 2
    ctx.random_flame(["linear", "spherical"], transforms=3, seed=5)
    assert len(ctx.transforms) == 3 and all(set(t.variation_names) <= {"linear", "spherical"} for t in ctx.transforms)
    ctx.load_flame(samples / "sample flames" / "candy.flame", 2)
    assert ctx.flame.name == "rotated" and len(ctx.transforms) == 6
    text = ctx.flame_text()
    ctx.new_flame()
    ctx.from_text(text)
    assert ctx.flame.name == "rotated"
    assert "<flame" in ctx.flame_xml()
    out = tmp_path / "out.flame"
    assert ctx.save_flame(out, "first") == 0 and ctx.save_flame(out) == 1
    assert [f.name for f in load_flames(out)] == ["first", "rotated"]
    with pytest.raises(ScriptError):
        ctx.load_flame(tmp_path / "missing.flame")
    with pytest.raises(ScriptError):
        ctx.save_flame(tmp_path / "x.chaos")
    assert ctx.validate() == []
    ctx.clear_transforms()
    assert ctx.validate() == ["no transform with a positive weight"]
    assert "julian" in ctx.list_variations("juli") and ctx.variation_info("julian")["params"]["julian_power"] == 1.0
    assert ctx.variation_params("julian") == ["julian_power", "julian_dist"]
    ctx.seed(3)
    a = ctx.random()
    ctx.seed(3)
    assert ctx.random() == a and 1 <= ctx.random_int(1, 3) <= 3 and ctx.random_choice([7]) == 7 and ctx.random_variation() in V.REGISTRY


# --- the runner ---------------------------------------------------------------------------------------------
def test_run_script_reports_errors_with_their_line_and_keeps_the_flame_for_successes():
    host = RecordingHost()
    result = run("for t in transforms:\n    t.rotate(10)\nprint('done', len(transforms))\n", host=host)
    assert result.ok and not result.stopped and host.lines == ["done 2\n"] and result.output_lines == 1
    assert result.flame.xforms[0].coefs[1] == pytest.approx(-0.5 * 0.17364817766, abs=1e-6)
    failed = run("print(1)\n\nx = transforms[7]\n")
    assert not failed.ok and failed.error.kind == "ScriptError" and failed.error.line == 3 and "out of range" in failed.error.message
    syntax = run("x = (1,\n")
    assert syntax.error.kind == "SyntaxError" and syntax.error.line in (1, 2) and check_syntax("a b c") is not None and check_syntax("a = 1") is None
    inside = run("def f():\n    return 1 / 0\n\nf()\n")
    assert inside.error.kind == "ZeroDivisionError" and inside.error.line == 2 and "line 4" in inside.error.details
    nested = run("try:\n    stop('x')\nexcept Exception:\n    print('swallowed')\n", host=host)
    assert nested.ok and nested.stopped and nested.stop_reason == "x" and "swallowed\n" not in host.lines
    exited = run("print('a')\nexit()\nprint('b')\n", host=host)
    assert exited.ok and exited.stopped and host.lines[-1] == "a\n"


def test_stop_event_interrupts_loops_sleeps_and_prompts():
    for code in ("while True:\n    pass\n", "sleep(60)\n", "x = input_text('?')\n"):
        stop = threading.Event()
        box = {}

        class BlockingHost(RecordingHost):
            def input_text(self, prompt, default):
                while not stop.is_set():
                    time.sleep(0.01)
                raise_stop = getattr(self, "check_stop", None)
                if raise_stop:
                    raise_stop()
                return default

        thread = threading.Thread(target=lambda: box.update(r=run(code, host=BlockingHost(), stop=stop)), daemon=True)
        thread.start()
        time.sleep(0.2)
        stop.set()
        thread.join(5)
        assert not thread.is_alive() and box["r"].stopped and box["r"].user_stopped, code


def test_prompts_messages_updates_and_apophysis_aliases_go_through_the_host():
    host = RecordingHost(answers=["7", False])
    code = ("n = input_number('n?', 3)\nok = confirm('go?')\nmessage('hi')\nupdate(wait=False)\nprogress(0.5)\n"
            "print(n, ok)\nAddTransform()\nRotate(10)\nPrint('apo', Random(1))\nassert Transform.index == 2\n")
    result = run(code, host=host)
    assert result.ok, result.error
    assert host.messages == ["hi"] and len(host.updates) == 1 and host.lines == ["7 False\n", "apo 0\n"] and len(result.flame.xforms) == 3
    bad = run("x = input_number('n?', 1)\nprint(x)\n", host=RecordingHost(answers=["abc", "2.5"]))
    assert bad.ok and bad.flame is not None


# --- documentation and completion --------------------------------------------------------------------------------
def test_documentation_matches_the_real_api():
    namespace = ScriptContext(two_transforms()).namespace()
    assert not [n for n in namespace if n not in D.GLOBALS and not n.startswith("__")]
    assert not [n for n in D.GLOBALS if n not in namespace]
    from fractalchemy.scripting import api
    for type_name, cls in (("Transform", api.Transform), ("Camera", api.CameraHelper), ("Coloring", api.ColoringHelper),
                           ("Gradient", api.GradientHelper), ("Xaos", api.XaosHelper), ("Affine", api.Affine6)):
        members = D.TYPES[type_name].members
        assert not [m for m in members if not hasattr(cls, m)], type_name
        assert not [m for m in dir(cls) if not m.startswith("_") and m not in members], type_name
    categorised = {n for _title, names in D.CATEGORIES for n in names}
    assert set(D.GLOBALS) == categorised
    assert len(D.options(D.VARIATIONS)) == len(V.REGISTRY) and any(o.name == "julian_power" for o in D.options(D.PARAMS))


def names(code: str, explicit: bool = False) -> list[str]:
    return [i.text for i in C.complete(code, len(code), explicit).items]


def test_completion_resolves_members_strings_locals_and_keyword_arguments():
    assert names("flame.na")[0] == "name"
    assert {"set_variation", "weight", "rotate"} <= set(names("transforms[0]."))
    assert names("transform.variations['jul")[0].startswith("julia") and C.complete("transform.variations['jul", 24).in_string
    assert "julian_power" in names("transform.params['julian_")
    assert names("transform.set_variation('spheri")[0] == "spherical"
    assert names("t = add_transform()\nt.rot")[0] == "rotate"
    assert names("for x in transforms:\n    x.sc")[0] == "scale"
    assert {"color", "color_speed"} <= set(names("for i, x in enumerate(transforms):\n    x.col"))
    assert "flip_horizontal" in names("for_each_transform(lambda tr, i: tr.fl")
    assert "fit" in names("camera.") and "chain" in names("xaos.") and "atan2" in names("math.")
    assert names("add_tr")[0] == "add_transform" and names("for")[0] == "for"
    assert "weight=" in names("add_transform(") and names("add_transform(wei")[0] == "weight="
    assert "red" in names("coloring.reset_curves('")
    assert names("# flame.") == [] and names("x = 1\n") == [] and names("x = 1\n", explicit=True)
    assert "color_at" in names("g = gradient.stops\ng.")


def test_context_help_describes_calls_members_and_subscripts():
    cx = C.context("transform.set_variation('jul", 28)
    assert cx.kind == "call" and cx.name == "set_variation" and cx.owner == "Transform" and cx.arg_index == 0
    assert cx.param.name == "name" and all("jul" in o.name.lower() for o in cx.options) and cx.options
    cx = C.context("xaos.set(0, 1, ", 15)
    assert cx.kind == "call" and cx.arg_index == 2 and cx.param.name == "weight"
    cx = C.context("camera.zo", 9)
    assert cx.kind == "members" and cx.owner == "Camera" and cx.prefix == "zo" and any(m.name == "zoom" for m in cx.members)
    cx = C.context("add_transform", 3)
    assert cx.kind == "symbol" and cx.entry.kind == "function"
    cx = C.context("t = add_transform()\nt.rotate(45)", 30)
    assert cx.kind == "call" and cx.name == "rotate" and cx.owner == "Transform"
    cx = C.context("transform.variations['sp", 24)
    assert cx.kind == "subscript" and cx.name == "variations" and all("sp" in o.name.lower() for o in cx.options)
    assert C.context("# hello", 4).kind == "comment"
    cx = C.context("", 0)
    assert cx.kind == "none"


# --- templates and generation ---------------------------------------------------------------------------------------
def test_builtin_templates_have_metadata_and_all_run(samples, tmp_path):
    flame = load_flame(samples / "sample flames" / "candy.flame", 2)
    templates = T.builtin_templates()
    assert len(templates) >= 30 and {t.category for t in templates} == {"Transforms", "Colours", "Xaos", "Camera", "Flame"}
    assert all(t.builtin and t.description and t.name for t in templates)
    assert any(t.name == "Random rotate all transforms" for t in templates)
    for template in templates:
        answers = {"Gradient file": str(samples / "sample gradients" / "ag6.ugr"), "which": str(tmp_path / "variants.flame")}

        class H(RecordingHost):
            def input_text(self, prompt, default):
                return next((v for k, v in answers.items() if k.lower() in prompt.lower()), default)

        result = run_script(template.code, flame, H(), threading.Event())
        assert result.ok, f"{template.name}: {result.error}"


def test_user_templates_are_files_with_metadata(tmp_path):
    folder = tmp_path / "templates"
    saved = T.save_user_template("My thing", "# @description old\nprint(1)\n", "does things", folder)
    assert saved.path.parent == folder and saved.name == "My thing" and saved.category == T.USER_CATEGORY and saved.description == "does things"
    assert T.parse_metadata(saved.code) == {"name": "My thing", "description": "does things"}
    again = T.save_user_template("My thing", "print(2)\n", "", folder)
    assert again.path != saved.path and len(T.user_templates(folder)) == 2
    renamed = T.rename_user_template(saved, "Renamed")
    assert renamed.name == "Renamed" and renamed.path == saved.path
    T.delete_user_template(again)
    assert [t.name for t in T.user_templates(folder)] == ["Renamed"]
    with pytest.raises(ValueError):
        T.delete_user_template(T.builtin_templates()[0])
    assert T.strip_metadata("# @name x\n\nprint(1)\n") == "print(1)\n"
    assert T.all_templates(folder)[0].name == "Renamed" and T.all_templates(tmp_path / "none")[0].builtin


def test_flame_to_script_rebuilds_the_flame(samples):
    for path, index in (("candy.flame", 2), ("flamepack1.flame", 5), ("satania_spikobius.chaos", 0)):
        flame = load_flame(samples / "sample flames" / path, index)
        result = run_script(flame_to_script(flame), Flame("empty", []), RecordingHost(), threading.Event())
        assert result.ok, result.error
        rebuilt = result.flame
        assert rebuilt.name == flame.name and len(rebuilt.xforms) == len(flame.xforms) and (rebuilt.final is None) == (flame.final is None)
        assert rebuilt.palette == flame.palette and rebuilt.camera.width == flame.camera.width
        n = len(flame.xforms)
        row = lambda x: [float(x.chaos[j]) if x.chaos is not None and j < len(x.chaos) else 1.0 for j in range(n)]   # noqa: E731
        for a, b in zip(rebuilt.xforms, flame.xforms):
            assert a.variations.keys() == b.variations.keys() and a.coefs == pytest.approx(b.coefs, abs=1e-6) and row(a) == row(b)
            assert a.weight == pytest.approx(b.weight, abs=1e-6)
        assert rebuilt.coloring.brightness == pytest.approx(flame.coloring.brightness)


# --- the window --------------------------------------------------------------------------------------------------------------
@pytest.fixture
def main(qapp, tmp_path, samples):
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.ui.main_window import MainWindow

    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    win = MainWindow(LibraryRoots(settings), LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key), prefer_gpu=False, settings=settings)
    win.show()
    win.open_path(samples / "sample flames" / "candy.flame", 2)
    wait_until(lambda: win.document.flame is not None and win.document.flame.name == "rotated")
    yield win
    win.gradient_library.document.modified = False
    if win._script_editor is not None:
        win._script_editor.user_dir = tmp_path / "scripts"
    win.close()


def finish(editor) -> None:
    wait_until(lambda: not editor.runner.running, 15000)
    spin(150)


def test_script_editor_opens_from_the_windows_menu_and_the_toolbar_and_hides_on_close(main):
    assert main._script_editor is None
    assert main.actionScriptEditor in main.menuWindows.actions()
    main.actionScriptEditor.trigger()
    editor = main.script_editor
    assert editor.isVisible() and editor.parent() is main and editor.isWindow() and editor.windowTitle().startswith("Script Editor")
    assert [editor.drawer.tabText(i) for i in range(editor.drawer.count())] == ["Context", "Reference", "Info", "Templates"]
    assert [a.text() for a in editor.menuBar().actions()] == ["File", "Edit", "Script", "View"]
    toolbar = [a.text() for a in editor.toolBar.actions() if a.text()]
    assert toolbar[:6] == ["New Script", "Open Script…", "Save Script", "Save Script As…", "Run", "Stop"]
    assert {"Check Syntax", "Flame → Script", "Revert Flame", "Save as Template…", "Clear Output", "Show/Hide Drawer"} <= set(toolbar)
    editor.editor.set_text("print('kept')")
    editor.close()
    assert not editor.isVisible()
    button = main.toolBar.widgetForAction(main.actionScriptEditor)
    assert isinstance(button, QToolButton) and not main.actionScriptEditor.icon().isNull()
    button.click()
    assert editor.isVisible() and editor.editor.text() == "print('kept')"
    assert main.actionScriptEditor.shortcut().toString() == "F8"


def test_running_a_script_edits_the_fractal_as_one_undo_step_and_rerenders(main):
    editor = main.script_editor
    editor.bring_to_front()
    editor.editor.set_text("for t in transforms:\n    t.rotate(15)\nxaos.chain()\ncamera.zoom = 1.5\nprint('n =', len(transforms))\n")
    before = main.document.flame.copy()
    generation = main.viewport.generation
    editor.run()
    finish(editor)
    flame = main.document.flame
    assert flame.xforms[0].chaos == [0.0, 1.0, 0.0, 0.0, 0.0, 0.0] and flame.camera.zoom == 1.5 and flame.xforms[0].coefs != before.xforms[0].coefs
    assert main.document.modified and main.document.can_undo and main.windowTitle().endswith("*")
    text = editor.output.toPlainText()
    assert "n = 6" in text and "Finished" in text and editor.actionRevert.isEnabled()
    wait_until(lambda: main.viewport.generation > generation)
    main.actionUndo.trigger()
    assert main.document.flame.camera.zoom == before.camera.zoom and main.document.flame.xforms[0].chaos == before.xforms[0].chaos
    main.actionRedo.trigger()
    assert main.document.flame.camera.zoom == 1.5
    editor.revert_flame()
    assert main.document.flame.camera.zoom == before.camera.zoom and main.document.can_undo
    info = editor.drawer.info.browser.toPlainText()
    assert "finished" in info and "rotated" in info


def test_errors_show_their_line_and_leave_the_fractal_alone(main):
    editor = main.script_editor
    editor.bring_to_front()
    before = main.document.flame.to_dict()
    editor.editor.set_text("transform.weight = 2\nupdate(wait=False)\nprint('half way')\ntransforms[9].weight = 1\n")
    editor.run()
    finish(editor)
    assert main.document.flame.to_dict() == before                       # the intermediate update() was rolled back
    assert editor.editor.error_line == 4 and editor.editor.line_column()[0] == 4
    assert "line 4" in editor.output.toPlainText() and "half way" in editor.output.toPlainText()
    editor.editor.set_text("x = (\n")
    editor.run()
    assert not editor.runner.running and editor.editor.error_line is not None and "SyntaxError" in editor.output.toPlainText()
    editor.editor.set_text("print(1)")
    assert editor.check_syntax() and "Syntax OK" in editor.output.toPlainText()


def test_stop_button_ends_an_endless_loop(main):
    editor = main.script_editor
    editor.bring_to_front()
    editor.editor.set_text("n = 0\nwhile True:\n    n += 1\n")
    editor.run()
    spin(200)
    assert editor.runner.running and editor.actionStop.isEnabled() and not editor.actionRun.isEnabled()
    editor.actionStop.trigger()
    finish(editor)
    assert not editor.runner.running and "Stopped" in editor.output.toPlainText() and editor.actionRun.isEnabled()


def test_prompts_use_dialogs_and_update_waits_for_the_viewport(main, monkeypatch):
    editor = main.script_editor
    editor.bring_to_front()
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("3", True)))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    shown = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda parent, title, text, *a: shown.append(text)))
    editor.editor.set_text("n = input_number('n?', 1)\nok = confirm('?')\nmessage('hello')\n"
                           "for i in range(int(n)):\n    camera.rotate_by(10)\n    update()\n    progress(i / n)\nprint(n, ok, camera.rotate)\n")
    rotate = main.document.flame.camera.rotate
    editor.run()
    finish(editor)
    assert shown == ["hello"] and "3 True" in editor.output.toPlainText()
    assert main.document.flame.camera.rotate == pytest.approx((rotate + 30) % 360)
    assert len(main.document._undo) == 1            # the three update() calls and the result: one undo step


def test_completion_popup_context_tab_and_insertion_from_the_drawer(main):
    editor = main.script_editor
    editor.bring_to_front()
    code = editor.editor
    code.set_text("t = add_transform()\nt.set_variation('jul")
    code.moveCursor(code.textCursor().MoveOperation.End)
    code.open_completion(True)
    assert code.popup.isVisible() and code.popup.current().name.startswith("julia")
    code.popup.move_selection(2)
    code.accept_completion()
    assert not code.popup.isVisible() and code.text().endswith("'julian'") or code.text().endswith("'julian")
    spin(200)
    editor._refresh_context()
    assert editor.drawer.context.kind == "call" and "set_variation" in editor.drawer.context.browser.toPlainText()
    code.set_text("camera.")
    code.moveCursor(code.textCursor().MoveOperation.End)
    editor._refresh_context()
    assert editor.drawer.context.kind == "members" and "zoom_by" in editor.drawer.context.browser.toPlainText()
    editor.insert_name("zoom_by", "method")
    assert code.text() == "camera.zoom_by()" and code.line_column() == (1, 16)
    code.set_text("t.variations['")
    code.moveCursor(code.textCursor().MoveOperation.End)
    editor.insert_option("spherical")
    assert code.text() == "t.variations['spherical'"
    code.set_text("")
    editor.drawer.reference.show_mode("api")
    editor.drawer.reference.search.setText("xaos")
    editor.drawer.reference.render()
    assert "chain" in editor.drawer.reference.browser.toPlainText()
    editor.drawer.reference.search.clear()
    editor.drawer.reference.show_mode("variations")
    assert "julian" in editor.drawer.reference.browser.toPlainText()
    editor.drawer.reference.search.setText("julian_power")
    editor.drawer.reference.render()
    text = editor.drawer.reference.browser.toPlainText()
    assert "julian" in text and "swirl" not in text


def test_editor_conveniences(main):
    main.script_editor.bring_to_front()
    code = main.script_editor.editor
    code.set_text("a = 1\nb = 2\n")
    code.goto_line(1)
    code.toggle_comment()
    assert code.text().startswith("# a = 1")
    code.toggle_comment()
    assert code.text().startswith("a = 1")
    code.duplicate_line()
    assert code.text().split("\n")[:3] == ["a = 1", "a = 1", "b = 2"]
    code.delete_line()
    code.goto_line(1)
    code.indent()
    assert code.text().startswith("    a = 1")
    code.outdent()
    assert code.text().startswith("a = 1")
    code.move_line(1)
    assert code.text().split("\n")[0] == "b = 2"
    assert code.count_matches("= ") == 2 and code.find_text("b =") and code.selected_text() == "b ="
    assert code.replace_all("= ", "== ") == 2 and "a == 1" in code.text()
    main.script_editor.find_bar.open(True)
    assert main.script_editor.find_bar.isVisible()
    main.script_editor.find_bar.dismiss()
    assert not main.script_editor.find_bar.isVisible()


def test_templates_tab_loads_runs_saves_and_deletes(main, monkeypatch, tmp_path):
    editor = main.script_editor
    editor.user_dir = tmp_path / "scripts"
    editor.refresh_templates()
    editor.bring_to_front()
    tab = editor.drawer.templates
    assert len(tab.visible_names()) >= 30 and "Normalize weights" in tab.visible_names()
    tab.search.setText("normalize")
    assert tab.visible_names() == ["Normalize weights"]
    tab.select(next(t.id for t in editor._templates if t.name == "Normalize weights"))
    assert tab.current().name == "Normalize weights" and not tab.delete_button.isEnabled()
    editor.editor.set_text("")
    editor.editor.document().setModified(False)
    tab.run_button.click()
    finish(editor)
    assert "Normalize weights" in editor.windowTitle() and sum(x.weight for x in main.document.flame.xforms) == pytest.approx(1.0)
    editor.editor.set_text("# @name Mine\n# @description all mine\nprint('mine')\n")
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Mine", True)))
    editor.save_as_template()
    mine = next(t for t in editor._templates if not t.builtin)
    assert mine.name == "Mine" and mine.description == "all mine" and mine.path.parent == tmp_path / "scripts" / "templates"
    assert tab.current() is not None and tab.current().name == "Mine" and tab.delete_button.isEnabled()
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    editor.editor.set_text("print('changed')\n")
    editor.overwrite_template(mine)
    assert "changed" in next(t for t in editor._templates if t.name == "Mine").code
    editor.delete_template(next(t for t in editor._templates if t.name == "Mine"))
    assert all(t.builtin for t in editor._templates)
    editor.editor.set_text("x")
    editor.editor.document().setModified(True)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel))
    assert not editor.load_template(editor._templates[0]) and editor.editor.text() == "x"


def test_flame_to_script_save_load_and_drawer_state(main, tmp_path, monkeypatch):
    editor = main.script_editor
    editor.bring_to_front()
    editor.editor.document().setModified(False)
    editor.flame_to_script()
    assert "new_flame('rotated'" in editor.editor.text() and "Flame: rotated" in editor.windowTitle()
    path = tmp_path / "rotated.py"
    monkeypatch.setattr("fractalchemy.ui.script_editor_window.QFileDialog.getSaveFileName", staticmethod(lambda *a, **k: (str(path), "")))
    assert editor.save_script(False) and path.exists() and not editor.isWindowModified() and editor.script_path == path
    editor.editor.set_text("")
    editor.editor.document().setModified(False)
    editor.open_path(path)
    assert "new_flame('rotated'" in editor.editor.text()
    editor.run()
    finish(editor)
    assert main.document.flame.name == "rotated" and len(main.document.flame.xforms) == 6
    editor.splitter.set_last_collapsed(True)
    assert editor.splitter.is_last_collapsed() and not editor.actionToggleDrawer.isChecked()
    editor.actionToggleDrawer.trigger()
    assert not editor.splitter.is_last_collapsed()
    editor.show_tab("templates")
    assert editor.drawer.currentIndex() == 3
    editor.save_state()
    assert editor._settings.value("script/drawer_tab") in (3, "3")
