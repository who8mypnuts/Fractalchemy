"""The Formula Editor: the workbench helpers, the session's compile pipeline and files, the C editor, and the window
driven through its widgets — live compiling, the transform grid, saving into the user's folder, the gradient link."""

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from fractalchemy.formulas import loader, workbench as W
from fractalchemy.formulas.lang import compile_source
from fractalchemy.fractal import variations as V
from fractalchemy.fractal.scene import XForm
from fractalchemy.ui.formula_session import ORIGIN_FILE, ORIGIN_NEW, ORIGIN_REGISTERED, FormulaSession
from fractalchemy.widgets.formula_code_editor import CHighlighter, FormulaCodeEditor
from tests.conftest import open_flame_and_wait, spin, wait_until

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "sample flames" / "candy.flame"
BROKEN = 'APO_PLUGIN("broken");\nint PluginVarCalc(Variation* vp)\n{\n    FPx += VVAR * FTx\n    return TRUE;\n}\n'
HALF = ('typedef struct { double half_k; } Variables;\nAPO_PLUGIN("half");\nAPO_VARIABLES(VAR_REAL(half_k, 0.5));\n'
        'int PluginVarPrepare(Variation* vp) { return TRUE; }\n'
        'int PluginVarCalc(Variation* vp) { FPx += VVAR * VAR(half_k) * FTx; FPy += VVAR * VAR(half_k) * FTy; return TRUE; }\n')


def preview_settled(preview) -> bool:
    return preview.stats is not None and preview.stats.finished and not preview.busy and not preview._pending


def lit_pixels(image) -> int:
    array = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(image.height(), image.width(), 4)
    return int((array[..., :3].sum(axis=2) > 0).sum())


# --- workbench (Qt-free) ------------------------------------------------------------------------------------------
def test_workbench_template_sources_scratch_slot_and_error_lines():
    text = W.new_formula_text("my fx!")
    assert W.formula_name(text) == "my_fx_" and W.safe_file_name("a b/c") == "a_b_c"
    compiled = W.compile_formula(text)
    assert compiled.variation.name == "my_fx_" and compiled.variation.params == {"my_fx__amount": 1.0}
    scratch = W.register_scratch(compiled.variation)
    assert scratch.name == W.SCRATCH_NAME and V.REGISTRY[W.SCRATCH_NAME] is scratch and scratch.params == compiled.variation.params
    assert W.scratch_variation() is scratch
    W.unregister_scratch()
    assert W.scratch_variation() is None and W.SCRATCH_NAME not in V.REGISTRY
    # a library formula's source is its file; a native one gets a dialect skeleton that compiles and declares its variables
    whorl = W.source_of(V.REGISTRY["whorl"])
    assert 'APO_PLUGIN("whorl")' in whorl and W.origin_path(V.REGISTRY["whorl"]).name == "whorl.c"
    julian = W.source_of(V.REGISTRY["julian"])
    assert W.origin_path(V.REGISTRY["julian"]) is None and "native built-in" in julian and "p.rnd()" in julian
    skeleton = compile_source(julian).variation
    assert skeleton.name == "julian" and set(skeleton.params) == {"julian_power", "julian_dist"}
    assert W.error_line("line 12: expected ';'") == 12 and W.error_line("unexpected character '$' at offset 9", "ab\ncd\nef$") == 3
    assert W.error_line("unknown name 'x'") is None
    # pre_ / post_ formulas get linear beside them when rendered alone; a normal one is left alone
    pre = compile_source('APO_PLUGIN("pre_half");\nint PluginVarCalc(Variation* vp) { FTx *= 0.5; return TRUE; }').variation
    xform = W.formula_xform()
    assert W.uses_scratch(xform) and W.prepared_xform(xform, pre).variations == {W.SCRATCH_NAME: 1.0, "linear": 1.0}
    assert W.prepared_xform(xform, compiled.variation).variations == {W.SCRATCH_NAME: 1.0}
    assert W.prepared_xform(XForm(variations={"linear": 1.0}), pre).variations == {"linear": 1.0}
    assert xform.variations == {W.SCRATCH_NAME: 1.0}       # the original is untouched


# --- the session ----------------------------------------------------------------------------------------------------
def test_session_compiles_in_the_background_keeps_the_last_good_formula_and_saves_into_the_user_folder(qapp, tmp_path):
    user = tmp_path / "formulas"
    session = FormulaSession(user_dir=user)
    compiled, failed = [], []
    session.compiled.connect(compiled.append)
    session.failed.connect(lambda message, line: failed.append((message, line)))
    session.load_new("fresh")
    wait_until(lambda: compiled)
    assert session.name == "fresh" and session.origin == ORIGIN_NEW and not session.modified and session.path is None
    assert compiled[0].name == W.SCRATCH_NAME and V.REGISTRY[W.SCRATCH_NAME] is compiled[0] and session.compiled_real.name == "fresh"
    good = session.variation
    session.set_text(BROKEN)
    assert session.modified and session.name == "broken" and session.compiling
    wait_until(lambda: failed)
    assert failed[0][1] == 5 and "expected" in failed[0][0] and session.error_line == 5   # (where the parser noticed: `return`)
    assert session.variation is good and V.REGISTRY[W.SCRATCH_NAME] is good         # the last good one stays
    # typing while a compile runs: only the newest text counts
    session.set_text(HALF.replace("0.5", "0.4"))
    session.compile_now()
    session.set_text(HALF)
    session.compile_now()
    wait_until(lambda: len(compiled) >= 2 and session.variation.params == {"half_k": 0.5} and not session.compiling, 10000)
    assert session.error is None and session.kind == V.NORMAL
    # save: the file lands in the user's folder and the formula is registered under its own name
    assert session.default_path() == user / "half.c" and session.own_file is None
    path = session.save()
    assert path == user / "half.c" and path.read_text() == HALF and not session.modified and session.origin == ORIGIN_FILE
    assert session.own_file == path and session.is_user_file and V.REGISTRY["half"].origin == str(path)
    assert session.overrides_bundled() is None
    session.set_text(HALF.replace('"half"', '"whorl"'))
    wait_until(lambda: session.name == "whorl" and not session.compiling)
    assert session.overrides_bundled() and "whorl.c" in session.overrides_bundled()
    # delete: the file goes, the registry entry goes, the bundled library is intact
    session.set_text(HALF)
    wait_until(lambda: not session.compiling)
    assert session.delete() and not path.exists() and "half" not in V.REGISTRY and session.path is None and session.modified
    assert "whorl" in V.REGISTRY and V.REGISTRY[W.SCRATCH_NAME] is session.variation
    assert not session.delete()
    # a registered formula: its own self in the scratch slot, no compile until the text changes; a bundled file is never Save's target
    session.load_registered("whorl")
    assert session.origin == ORIGIN_REGISTERED and session.variation.params == V.REGISTRY["whorl"].params and not session.compiling
    assert session.path.name == "whorl.c" and session.own_file is None and session.default_path() == user / "whorl.c"
    assert not session.load_registered("no-such-formula")
    # drafts round-trip; an untouched registered formula is reloaded from the registry
    draft = session.draft()
    other = FormulaSession(user_dir=user)
    other.restore(**draft)
    assert other.name == "whorl" and other.origin == ORIGIN_REGISTERED and other.variation.name == W.SCRATCH_NAME
    other.restore(HALF, "half", "", ORIGIN_NEW, True)
    wait_until(lambda: other.variation is not None and other.variation.params == {"half_k": 0.5})
    assert other.modified
    other.load_blank()
    assert other.text == "" and other.variation is None and W.scratch_variation() is None
    W.unregister_scratch()


# --- the C editor ---------------------------------------------------------------------------------------------------
def test_formula_code_editor_highlights_comments_and_indents_braces(qapp):
    editor = FormulaCodeEditor()
    editor.set_text("/* a\n   comment */ double x = 1.5; // note\nAPO_PLUGIN(\"x\");\n#include \"apoplugin.h\"\nFPx += VVAR * sin(M_PI);\n")
    assert isinstance(editor.highlighter, CHighlighter)
    doc = editor.document()
    spin(20)
    def formats(line: int):
        block = doc.findBlockByNumber(line)
        return [(r.start, r.length, r.format.foreground().color().name()) for r in block.layout().formats()]
    assert formats(0) and formats(0)[0][2] == "#8a8a8a"                      # the open comment
    line1 = formats(1)
    assert any(color == "#8a8a8a" and start == 0 for start, _l, color in line1)   # its continuation
    assert any(color == "#1565c0" for _s, _l, color in line1)                # double
    assert any(color == "#c45200" for _s, _l, color in line1)                # 1.5
    assert formats(2)[0][2] == "#0d47a1" and formats(3)[0][2] == "#4a7a48"   # APO_PLUGIN, #include
    colors = {color for _s, _l, color in formats(4)}
    assert {"#8d5a00", "#3b5f9e", "#7a3a3a"} <= colors                      # FPx / VVAR, sin, M_PI
    editor.set_text("int f()\n{")
    editor.goto_line(2, 2)
    editor._on_return()
    assert editor.text() == "int f()\n{\n    "
    editor.goto_line(1)
    editor.toggle_comment()
    assert editor.text().startswith("// int f()")
    editor.toggle_comment()
    assert editor.text().startswith("int f()")
    editor.set_text("{\n    ")
    editor.goto_line(2, 5)
    assert editor._close_brace() and editor.text() == "{\n}"
    assert editor.comment_prefix == "//"


# --- the window -----------------------------------------------------------------------------------------------------
@pytest.fixture
def main(main_window_factory, tmp_path, monkeypatch):
    monkeypatch.setenv(loader.ENV_VAR, str(tmp_path / "formulas"))   # the test's user folder is scanned by reloads, like the real one
    win = main_window_factory(cheap_renders=True)
    yield win
    if win._formula_editor is not None:
        win._formula_editor.session.modified = False
    W.unregister_scratch()
    loader.load_all(force=True)


def formula_editor(win, tmp_path):
    win.actionFormulaEditor.trigger()
    editor = win.formula_editor
    editor.session.user_dir = tmp_path / "formulas"
    editor.formula_list.user_dir = tmp_path / "formulas"
    wait_until(lambda: editor.isVisible())
    return editor


def test_formula_editor_opens_from_the_windows_menu_and_the_toolbar_with_one_formula_transform(main, tmp_path):
    assert main._formula_editor is None
    assert main.actionFormulaEditor in main.menuWindows.actions() and main.actionFormulaEditor in main.toolBar.actions()
    assert main.actionFormulaEditor.shortcut().toString() == "F10" and not main.actionFormulaEditor.icon().isNull()
    fe = formula_editor(main, tmp_path)
    assert fe.parent() is main and fe.isWindow() and fe.windowTitle().startswith("Formula Editor")
    flame = fe.document.flame
    assert [x.variations for x in flame.xforms] == [{W.SCRATCH_NAME: 1.0}] and flame.xforms[0].name == "formula"
    assert [e.label for e in fe.view.entries()] == ["1 · formula"] and fe.transform_combo.count() == 1
    assert fe.actions.var_preview.isChecked() and fe.view.variation_preview_count == 0      # nothing to send the grid through yet
    assert fe.code.text() == "" and "No formula" in fe.compile_label.text() and fe.session.variation is None
    assert len(fe.gradient.stops) == 3 and fe.gradient_bar.palette_colors == flame.palette and flame.palette[0] == (255, 210, 48)
    assert [a.text() for a in fe.menuBar().actions()] == ["Formula", "Edit", "Transform", "View"]
    fe.hide()
    main.actionFormulaEditor.trigger()
    assert fe.isVisible() and main.formula_editor is fe


def test_new_formula_compiles_live_and_feeds_the_grid_preview_and_the_rendered_preview(main, tmp_path):
    fe = formula_editor(main, tmp_path)
    fe.formula_list.new_button.click()
    assert fe.session.origin == ORIGIN_NEW and 'APO_PLUGIN("new_formula")' in fe.code.text() and fe.code.text() == fe.session.text
    wait_until(lambda: fe.session.variation is not None)
    assert fe.compile_label.text().startswith("✓ new_formula") and fe.view.variation_preview_count > 1000
    assert fe.variables_tab.table.names() == ["new_formula_amount"]
    assert fe.variables_tab.rows()[0].info == "new_formula" and fe.variables_tab.table.item(0, 2).text() == "new_formula"
    wait_until(lambda: preview_settled(fe.preview) and fe.preview.generation >= 1, 60000)
    assert lit_pixels(fe.preview.image) > 500
    # typing: the grid follows the code a moment later
    before = fe.view._preview_points.copy()
    fe.code.set_text(fe.code.text().replace("FPx += VVAR * (FTx * c - FTy * s);", "FPx += 2.0 * VVAR * (FTx * c - FTy * s);"))
    assert fe.session.modified and fe.isWindowModified() and fe.compile_label.text() == "Compiling…"
    wait_until(lambda: not fe.session.compiling and fe.session.error is None)
    assert not np.allclose(fe.view._preview_points[:, 0], before[:, 0])
    # a broken edit: the error is shown with its line, the last good formula keeps rendering
    good = fe.session.variation
    fe.code.set_text(BROKEN)
    wait_until(lambda: fe.session.error is not None)
    assert fe.compile_label.text().startswith("✗ line 5") and fe.code.error_line == 5
    assert fe.session.variation is good and V.REGISTRY[W.SCRATCH_NAME] is good and fe.view.variation_preview_count > 1000
    # a parameter edit goes to the transform (undoable) and the grid follows
    fe.code.set_text(HALF)
    wait_until(lambda: fe.session.error is None and not fe.session.compiling and fe.variables_tab.table.names() == ["half_k"])
    points = fe.view._preview_points.copy()
    fe.variables_tab.table.value_edited.emit("half_k", 1.0)
    assert fe.document.flame.xforms[0].params["half_k"] == 1.0 and fe.document.can_undo
    assert not np.allclose(fe.view._preview_points, points)


def test_choosing_a_formula_from_the_list_loads_its_code_and_the_real_formula_renders_until_edited(main, tmp_path, monkeypatch):
    fe = formula_editor(main, tmp_path)
    assert "whorl" in fe.formula_list.visible_names() and fe.formula_list.count_label.text().endswith("formulas")
    fe.formula_list.search.setText("whorl")
    fe.formula_list.apply_filter()
    assert fe.formula_list.visible_names() == ["dc_whorl2", "whorl"] and fe.formula_list.count_label.text() == "2 of 566 formulas"
    fe.formula_list.select("whorl")
    fe.formula_list.tree.itemClicked.emit(fe.formula_list.tree.currentItem(), 0)
    assert fe.session.name == "whorl" and fe.session.origin == ORIGIN_REGISTERED and 'APO_PLUGIN("whorl")' in fe.code.text()
    assert fe.formula_list.current_name() == "whorl" and "bundled" in fe.source_label.text()
    assert V.REGISTRY[W.SCRATCH_NAME].params == V.REGISTRY["whorl"].params and not fe.session.compiling
    assert fe.variables_tab.table.names() == ["whorl_inside", "whorl_outside"] and fe.view.variation_preview_count > 1000
    assert "PluginVarCalc" in fe.code.textCursor().block().text()          # scrolled past the licence header
    assert not fe.actions.delete_formula.isEnabled()
    # a native built-in: the skeleton shows the reference, the real formula is in the scratch slot
    fe.formula_list.search.clear()
    fe.load_formula("julian")
    assert "native built-in" in fe.code.text() and V.REGISTRY[W.SCRATCH_NAME].numpy is V.REGISTRY["julian"].numpy
    assert fe.variables_tab.table.names() == ["julian_power", "julian_dist"]
    # unsaved edits are guarded
    fe.code.set_text(HALF)
    wait_until(lambda: not fe.session.compiling)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel))
    assert not fe.load_formula("whorl") and fe.session.name == "half" and fe.formula_list.current_name() is None
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard))
    assert fe.load_formula("whorl") and fe.session.name == "whorl"
    assert fe.load_formula("whorl")                                          # already loaded: nothing to ask
    assert not fe.load_formula("no-such-formula")


def test_transforms_can_be_added_deleted_flipped_and_undone_from_the_toolbar_the_combo_and_the_canvas(main, tmp_path):
    fe = formula_editor(main, tmp_path)
    fe.new_formula()
    wait_until(lambda: fe.session.variation is not None)
    fe.actions.add_linear.trigger()
    fe.actions.add_spherical.trigger()
    fe.actions.add_formula.trigger()
    flame = fe.document.flame
    assert [x.name for x in flame.xforms] == ["formula", "linear", "spherical", "formula"]
    assert [x.variations for x in flame.xforms][1:] == [{"linear": 1.0}, {"spherical": 1.0}, {W.SCRATCH_NAME: 1.0}]
    assert len({x.color for x in flame.xforms}) == 4 and fe.context.selected == 3 and fe.transform_combo.currentIndex() == 3
    assert fe.transform_combo.count() == 4 and fe.transform_combo.itemText(1) == "2 - linear"
    fe.transform_combo.setCurrentIndex(1)
    assert fe.context.selected == 1 and fe.view.selected_key == 1 and fe.view.variation_preview_count > 1000
    fe.actions.flip_h.trigger()
    assert flame.xforms[1].coefs[0] == -1.0
    fe.actions.rot_ccw.trigger()
    fe.actions.use_formula.trigger()
    assert flame.xforms[1].variations == {W.SCRATCH_NAME: 1.0} and flame.xforms[1].name == "formula"
    fe.actions.make_spherical.trigger()
    assert flame.xforms[1].variations == {"spherical": 1.0}
    fe.actions.make_linear.trigger()
    assert flame.xforms[1].variations == {"linear": 1.0}
    fe.actions.duplicate.trigger()
    assert len(flame.xforms) == 5 and fe.context.selected == 4
    fe.actions.delete.trigger()
    assert len(flame.xforms) == 4
    steps = 0
    while fe.actions.undo.isEnabled() and steps < 20:
        fe.actions.undo.trigger()
        steps += 1
    assert steps >= 8 and [x.name for x in fe.document.flame.xforms] == ["formula"] and fe.transform_combo.count() == 1
    fe.actions.redo.trigger()
    assert [x.name for x in fe.document.flame.xforms] == ["formula", "linear"]
    assert not fe.actions.delete.isEnabled() or fe.context.xform() is not None
    # the canvas: keys and the context menu route through the same operations
    fe.view.setFocus()
    fe.context.select(1)
    fe.view.triangle_command.emit(1, "move-right")
    assert fe.document.flame.xforms[1].coefs[4] == pytest.approx(0.1)
    fe.view.triangle_command.emit(1, "delete")
    assert len(fe.document.flame.xforms) == 1
    fe.view.triangle_command.emit(0, "toggle-var-preview")
    assert not fe.actions.var_preview.isChecked() and fe.view.variation_preview_count == 0
    fe.view.triangle_command.emit(0, "toggle-var-preview")
    assert fe.actions.var_preview.isChecked() and fe.view.variation_preview_count > 1000
    assert fe.view.hit_at((0.2, 0.2)) is not None and fe.view.hit_at((-1.5, -1.5)) is None
    on_triangle = [a.text() for a in fe.actions.context_menu(fe, True).actions() if a.text()]
    assert on_triangle[:3] == ["Use the formula on this transform", "Make it linear", "Make it spherical"]
    assert {"Delete transform", "Duplicate transform", "Flip horizontally", "Add linear transform", "Undo", "Variation preview"} <= set(on_triangle)
    on_empty = [a.text() for a in fe.actions.context_menu(fe, False).actions() if a.text()]
    assert on_empty[0] == "Add linear transform" and "Delete transform" not in on_empty
    fe.actions.new_flame.trigger()
    assert [x.name for x in fe.document.flame.xforms] == ["formula"]


def test_save_registers_the_formula_for_every_window_and_delete_removes_it(main, tmp_path, monkeypatch):
    fe = formula_editor(main, tmp_path)
    user = tmp_path / "formulas"
    fe.new_formula()
    wait_until(lambda: fe.session.variation is not None)
    fe.code.set_text(HALF)
    wait_until(lambda: not fe.session.compiling and fe.session.name == "half")
    assert fe.actions.save_formula.trigger() is None and (user / "half.c").exists()
    assert fe.session.origin == ORIGIN_FILE and not fe.isWindowModified() and fe.actions.delete_formula.isEnabled()
    assert "half" in V.REGISTRY and V.REGISTRY["half"].origin == str(user / "half.c")
    assert "half" in fe.formula_list.visible_names() and fe.formula_list.current_name() == "half"
    assert "half" in main.editor.variations_tab.table.names()                 # the Transform Editor lists it at once
    # saving over a bundled name asks first
    fe.code.set_text(HALF.replace('"half"', '"whorl"'))
    wait_until(lambda: not fe.session.compiling and fe.session.name == "whorl")
    asked = []
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.No))
    assert not fe.save_formula() and asked and "bundled" in asked[0]
    # save as: a file name of your own
    fe.code.set_text(HALF.replace('"half"', '"half2"'))
    wait_until(lambda: not fe.session.compiling and fe.session.name == "half2")
    monkeypatch.setattr("fractalchemy.ui.formula_editor_window.QFileDialog.getSaveFileName",
                        staticmethod(lambda *a, **k: (str(user / "mine"), "")))
    assert fe.save_formula_as() and (user / "mine.c").exists() and "half2" in V.REGISTRY
    # delete: confirmed, the file and the registry entry go
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    assert fe.delete_formula() and not (user / "mine.c").exists() and "half2" not in V.REGISTRY
    assert fe.session.path is None and fe.session.modified and fe.code.text().strip() == HALF.replace('"half"', '"half2"').strip()
    assert "half2" not in fe.formula_list.visible_names() and "half" in V.REGISTRY
    assert not fe.delete_formula()
    # open a file from anywhere
    elsewhere = tmp_path / "elsewhere.c"
    elsewhere.write_text(HALF.replace('"half"', '"elsewhere"'))
    assert fe.open_path(elsewhere) and fe.session.origin == ORIGIN_FILE and fe.session.own_file == elsewhere
    wait_until(lambda: fe.session.variation is not None and fe.session.name == "elsewhere")
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warned.append(a[1])))
    assert not fe.open_path(tmp_path / "missing.c") and warned == ["Cannot open formula"]
    # the draft survives hiding the window
    fe.hide()
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    assert settings.value("formula_editor/draft_name") == "elsewhere"


def test_the_gradient_bar_hands_the_gradient_to_the_library_and_follows_its_edits(main, tmp_path, monkeypatch):
    fe = formula_editor(main, tmp_path)
    open_flame_and_wait(main, SAMPLE, 0)
    fe.new_formula()
    wait_until(lambda: fe.session.variation is not None)
    own = list(fe.document.flame.palette)
    assert not fe.gradient_linked and main.document.flame.palette != own
    library = main.gradient_library
    library.document.set_color(0, (9, 9, 9))                     # an edit before the bar is clicked: not ours
    assert fe.document.flame.palette == own and library.document.modified
    asked = []
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: asked.append(a[1]) or QMessageBox.StandardButton.Discard))
    fe.gradient_bar.clicked.emit()
    assert asked == ["Unsaved changes"]                           # the library's unsaved edit was not thrown away silently
    assert fe.gradient_linked and library.isVisible()
    assert main.document.flame.palette == fe.document.flame.palette == own         # one gradient everywhere
    assert library.document.gradient.sample(8) == fe.gradient.sample(8) and len(library.document.gradient.stops) == 3
    library.document.set_color(0, (1, 2, 3))
    assert fe.document.flame.palette[0] == (1, 2, 3) == main.document.flame.palette[0]
    assert fe.gradient_bar.palette_colors[0] == (1, 2, 3)
    assert fe.document.can_undo
    fe.choose_gradient()                                          # a second click only raises the library
    assert fe.document.flame.palette[0] == (1, 2, 3)
    library.document.modified = False
