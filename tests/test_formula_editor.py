"""The Formula Editor: the workbench helpers, the session's compile pipeline and files, the C editor, and the window
driven through its widgets — live compiling, the transform grid, saving into the user's folder, the gradient link."""

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QInputDialog, QMessageBox

from fractalchemy.formulas import authoring as A, completion as FC, loader, verify, workbench as W
from fractalchemy.formulas.lang import compile_source
from fractalchemy.fractal import variations as V
from fractalchemy.fractal.scene import XForm
from fractalchemy.ui.formula_session import ORIGIN_FILE, ORIGIN_NEW, ORIGIN_REGISTERED, FormulaNameTaken, FormulaSession
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
    text = A.new_formula_text("my fx!")
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
    assert session.taken_by() is None
    session.set_text(HALF.replace('"half"', '"whorl"'))
    wait_until(lambda: session.name == "whorl" and not session.compiling)
    assert session.taken_by() and "whorl.c" in session.taken_by()
    with pytest.raises(FormulaNameTaken):                          # bundled names are read-only
        session.save()
    assert not (user / "whorl.c").exists() and V.REGISTRY["whorl"].origin.endswith("apophysis7x/whorl.c")
    with pytest.raises(FormulaNameTaken):                          # and so is anything inside the package
        session.save(W.PACKAGE_DIR / "formulas" / "library" / "nope.c")
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
    assert session.original is V.REGISTRY["whorl"] and W.original_variation().numpy is V.REGISTRY["whorl"].numpy
    assert not session.load_registered("no-such-formula")
    # rename / duplicate: the variable prefixes follow, and the copy is the user's own
    session.set_text(session.text + "\n")
    assert session.taken_by() and session.duplicate_as_new() == "whorl_mine" and session.origin == ORIGIN_NEW and session.path is None
    assert 'APO_PLUGIN("whorl_mine")' in session.text and "VAR(whorl_mine_inside)" in session.text and session.taken_by() is None
    wait_until(lambda: not session.compiling)
    assert session.variation.params == {"whorl_mine_inside": 1.0, "whorl_mine_outside": 1.0} and session.default_path() == user / "whorl_mine.c"
    assert session.generated_glsl and "def calc" in session.generated_numpy and session.warnings == []
    assert session.rename("whorl_again") == "whorl_again" and "VAR(whorl_again_inside)" in session.text
    # revert: a user file comes back from disk
    saved = session.save()
    session.set_text(session.text.replace("VVAR", "2.0 * VVAR"))
    assert session.modified and session.revert() and not session.modified and session.text == saved.read_text()
    session.delete()
    # drafts round-trip; an untouched registered formula is reloaded from the registry
    session.load_registered("whorl")
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
    assert fe.variables.table.table.names() == ["new_formula_amount"]
    assert fe.variables.table.rows()[0].info == "new_formula" and fe.variables.table.table.item(0, 2).text() == "new_formula"
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
    wait_until(lambda: fe.session.error is None and not fe.session.compiling and fe.variables.table.table.names() == ["half_k"])
    points = fe.view._preview_points.copy()
    fe.variables.table.table.value_edited.emit("half_k", 1.0)
    assert fe.document.flame.xforms[0].params["half_k"] == 1.0 and fe.document.can_undo
    assert not np.allclose(fe.view._preview_points, points)


def test_choosing_a_formula_from_the_list_loads_its_code_and_the_real_formula_renders_until_edited(main, tmp_path, monkeypatch):
    fe = formula_editor(main, tmp_path)
    assert "whorl" in fe.formula_list.visible_names() and fe.formula_list.count_label.text().endswith("formulas")
    fe.formula_list.search.setText("whorl")
    fe.formula_list.apply_filter()
    assert fe.formula_list.visible_names() == ["dc_whorl2", "whorl"] and fe.formula_list.count_label.text() == "2 of 566 formulas"
    fe.formula_list.select("whorl")
    fe.formula_list.tree.itemClicked.emit(fe.formula_list.tree.currentItem(), 1)   # (column 0 is the favourite star)
    assert fe.session.name == "whorl" and fe.session.origin == ORIGIN_REGISTERED and 'APO_PLUGIN("whorl")' in fe.code.text()
    assert fe.formula_list.current_name() == "whorl" and "bundled" in fe.source_label.text()
    assert V.REGISTRY[W.SCRATCH_NAME].params == V.REGISTRY["whorl"].params and not fe.session.compiling
    assert fe.variables.table.table.names() == ["whorl_inside", "whorl_outside"] and fe.view.variation_preview_count > 1000
    assert "PluginVarCalc" in fe.code.textCursor().block().text()          # scrolled past the licence header
    assert not fe.actions.delete_formula.isEnabled()
    # a native built-in: the skeleton shows the reference, the real formula is in the scratch slot
    fe.formula_list.search.clear()
    fe.load_formula("julian")
    assert "native built-in" in fe.code.text() and V.REGISTRY[W.SCRATCH_NAME].numpy is V.REGISTRY["julian"].numpy
    assert fe.variables.table.table.names() == ["julian_power", "julian_dist"]
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
    # a bundled name is never saved over: Save offers a name of your own, declining saves nothing
    fe.code.set_text(HALF.replace('"half"', '"whorl"'))
    wait_until(lambda: not fe.session.compiling and fe.session.name == "whorl")
    assert "bundled formula's name" in fe.source_label.text()
    asked = []
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.Cancel))
    assert not fe.save_formula() and asked and "read-only" in asked[0] and "whorl_mine" in asked[0]
    assert not (user / "whorl.c").exists() and V.REGISTRY["whorl"].origin.endswith("apophysis7x/whorl.c") and fe.session.name == "whorl"
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    assert fe.save_formula() and (user / "whorl_mine.c").exists() and fe.session.name == "whorl_mine" and "whorl_mine" in V.REGISTRY
    assert 'APO_PLUGIN("whorl_mine")' in fe.code.text() and V.REGISTRY["whorl"].origin.endswith("apophysis7x/whorl.c")
    # a bundled file opened by hand is read-only too
    assert fe.open_path(W.origin_path(V.REGISTRY["whorl"])) and fe.session.own_file is None and "read-only" in fe.source_label.text()
    assert not fe.actions.delete_formula.isEnabled()
    fe.session.modified = False
    # save as: a file name of your own
    fe.new_formula()
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


# --- authoring helpers, completion, the verifier (Qt-free) -------------------------------------------------------------
def test_authoring_templates_variables_rename_rigs_and_gradients():
    for template in A.TEMPLATES:
        var = compile_source(A.new_formula_text("my fx", template.key)).variation
        assert var.name == template.prefix + "my_fx" and len(var.params) == 1, template.key
    assert compile_source(A.new_formula_text("x", "dc")).variation.dc and compile_source(A.new_formula_text("x", "3d")).variation.z == V.Z_FORMULA
    assert compile_source(A.new_formula_text("x", "blur")).variation.random and compile_source(A.new_formula_text("x", "pre")).variation.kind == V.PRE
    text = A.new_formula_text("my_fx")
    text, expression = A.add_variable(text, "power", 2.0, "int", (1, 9))
    assert expression == "VAR(my_fx_power)" and A.declared_variables(text) == ["my_fx_amount", "my_fx_power"]
    info = compile_source(text).variation.param_info["my_fx_power"]
    assert info.type == "int" and (info.default, info.min, info.max) == (2, 1, 9)
    with pytest.raises(ValueError):
        A.add_variable(text, "power")
    with pytest.raises(ValueError):
        A.add_variable(text, "9bad")
    bare = 'APO_PLUGIN("x");\nint PluginVarCalc(Variation* vp) { FPx += VVAR * FTx; return TRUE; }'
    grown, expression = A.add_variable(bare, "k", 0.5)
    assert expression == "VAR(x_k)" and compile_source(grown).variation.params == {"x_k": 0.5}
    renamed = A.rename_formula(text, "my_fx", "other")
    assert W.formula_name(renamed) == "other" and compile_source(renamed).variation.params == {"other_amount": 1.0, "other_power": 2}
    assert A.rename_formula(text, "my_fx", "other", variables=False).count("my_fx_amount") == text.count("my_fx_amount")
    assert A.stem_of("pre_fx") == "fx" and A.stem_of("post_") == "post_" and A.derived_name("a", {"a_mine", "a_mine2"}) == "a_mine3"
    assert "VAR(my_fx_k)" in A.snippet_text(next(s for s in A.SNIPPETS if "Derived" in s.title), text)
    rig = A.test_rig("Sierpinski")
    assert len(rig.xforms) == 4 and rig.xforms[0].variations == {W.SCRATCH_NAME: 1.0} and rig.xforms[1].variations == {"linear": 1.0}
    assert A.test_rig("Two formulas").xforms[1].variations == {W.SCRATCH_NAME: 1.0} and A.test_rig("nope").name == "Formula alone"
    assert len(A.preset_gradient("Fire").stops) == 3 and len(A.random_gradient(count=4).stops) == 4
    assert A.random_gradient(__import__("random").Random(1)).sample(4) == A.random_gradient(__import__("random").Random(1)).sample(4)


def test_dialect_completion_knows_the_names_and_what_the_file_declares():
    text = A.new_formula_text("my_fx")
    at = text.index("FPx +=")
    items = {i.name: i for i in FC.complete(text[:at] + "my_", at + 3, explicit=True).items}
    assert "my_fx_amount" in items and items["my_fx_amount"].kind == "variable"
    names = [i.name for i in FC.complete(text[:at] + "fsi", at + 3).items]
    assert names == ["fsincos"] and FC.complete(text[:at] + "fsi", at + 3).items[0].sig == "fsincos(a, &s, &c)"
    assert [i.name for i in FC.complete(text[:at] + "FT", at + 2).items] == ["FTx", "FTy", "FTz"]
    assert {i.name for i in FC.complete(text[:at] + "M_P", at + 3).items} >= {"M_PI", "M_PI_2", "M_PI_4"}
    assert FC.complete(text[:at] + "f", at + 1).items == [] and FC.complete(text[:at] + "f", at + 1, explicit=True).items
    assert FC.complete("// fsin", 7).items == [] and FC.complete('APO_PLUGIN("fsi', 15).items == []   # comments and strings
    assert FC.complete("/* open\n fsi", 12).items == []
    assert FC.reference("VVAR").group == "point state" and FC.reference("atan2").sig == "atan2(x, y)" and FC.reference("nope") is None
    groups = {r.group for r in FC.CATALOGUE}
    assert groups == {"point state", "plugin API", "function", "constant", "keyword"} and len(FC.CATALOGUE) > 120


def test_verifier_probes_and_compares_the_engines():
    whorl = V.REGISTRY["whorl"]
    out = verify.evaluate_numpy(whorl)
    assert out.shape == (len(verify.SAMPLE_POINTS), 7) and np.isfinite(out).all()
    result = verify.probe(V.REGISTRY["spherical"], (0.5, 0.5, 0.0))
    assert result.glsl is None and result.numpy[3] == pytest.approx(0.2 + 0.5 / 0.5) and "FPx" in result.lines()[3]
    result = verify.probe(V.REGISTRY["julian"], (0.5, 0.5, 0.0), {"julian_power": 3})
    assert np.isfinite(result.numpy).all()
    try:
        ctx = verify.create_context()
    except Exception:  # noqa: BLE001 - no OpenGL here
        pytest.skip("no OpenGL context")
    try:
        report = verify.compare(whorl, ctx)
        assert report.ok and report.bad_rows == 0 and "agree on 12 of 12" in report.message
        assert verify.compare(V.REGISTRY["blur"], ctx).random
        probed = verify.probe(V.REGISTRY["spherical"], (0.5, 0.5, 0.0), ctx=ctx)
        assert probed.glsl is not None and probed.glsl[3] == pytest.approx(probed.numpy[3], abs=1e-5)
    finally:
        ctx.release()


# --- the window's new conveniences ---------------------------------------------------------------------------------------
def test_list_filters_favourites_and_authors(main, tmp_path):
    fe = formula_editor(main, tmp_path)
    panel = fe.formula_list
    panel.kind_filter.setCurrentText("pre")
    assert panel.visible_names() and all(n.startswith("pre_") for n in panel.visible_names())
    panel.kind_filter.setCurrentText("Any kind")
    panel.origin_filter.setCurrentText("Built-in")
    assert "julian" in panel.visible_names() and "whorl" not in panel.visible_names()
    panel.origin_filter.setCurrentText("Favourites")
    assert panel.visible_names() == []
    assert panel.toggle_favourite("whorl") and panel.visible_names() == ["whorl"] and panel._item("whorl").text(0) == "★"
    assert QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat).value("formula_editor/favourites") in (["whorl"], "whorl")
    assert not panel.toggle_favourite("whorl") and panel.visible_names() == []
    panel.origin_filter.setCurrentText("All")
    panel.search.setText("faber")
    panel.apply_filter()
    assert "whorl" in panel.visible_names() and panel._item("whorl").text(4) == "Michael Faber"


def test_templates_snippets_variables_and_rename_from_the_window(main, tmp_path, monkeypatch):
    fe = formula_editor(main, tmp_path)
    assert fe.new_formula("post") and fe.session.name.startswith("post_") and "post_" in fe.code.text()
    wait_until(lambda: fe.session.variation is not None and fe.session.kind == V.POST)
    assert "post" in fe.compile_label.text()
    assert [a.text() for a in fe.actions.templates_menu.actions()] == [t.title for t in A.TEMPLATES]
    fe.new_formula()
    wait_until(lambda: fe.session.variation is not None and fe.session.kind == V.NORMAL)
    start = fe.code.text().index("VAR(new_formula_amount)")
    fe.code.replace_range(start, start, "")                       # the cursor at the amount's use …
    cursor = fe.code.textCursor()
    cursor.setPosition(start + len("VAR(new_formula_amount)"), cursor.MoveMode.KeepAnchor)   # … selecting it
    fe.code.setTextCursor(cursor)
    assert fe.add_variable("power", 3.0) and "VAR(new_formula_power)" in fe.code.text() and "double new_formula_power;" in fe.code.text()
    assert "r2 * VAR(new_formula_power)" in fe.code.text()        # the selection was replaced by the new variable
    wait_until(lambda: not fe.session.compiling and fe.session.error is None)
    assert fe.variables.table.table.names() == ["new_formula_amount", "new_formula_power"]
    assert not fe.add_variable("power")            # declared already: refused with a message
    fe.code.goto_line(fe.code.text().count("\n", 0, fe.code.text().index("double s, c;")) + 1)   # a statement boundary
    fe.insert_snippet(next(s for s in A.SNIPPETS if s.title == "Polar coordinates"))
    assert "double r = sqrt(FTx * FTx + FTy * FTy);" in fe.code.text()
    wait_until(lambda: not fe.session.compiling and fe.session.error is None)
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("renamed fx", True)))
    assert fe.rename_formula() and fe.session.name == "renamed_fx" and "VAR(renamed_fx_power)" in fe.code.text()
    wait_until(lambda: not fe.session.compiling and fe.session.name == "renamed_fx")
    assert fe.windowTitle().startswith("Formula Editor — renamed_fx")
    # the variable tools
    fe.variables.reset_all()
    assert fe.document.flame.xforms[0].params["renamed_fx_power"] == 3.0
    fe.variables.randomise(__import__("random").Random(2))
    assert fe.document.flame.xforms[0].params["renamed_fx_power"] != 3.0
    fe.variables.sweep_combo.setCurrentText("renamed_fx_amount")
    fe.variables.sweep_button.setChecked(True)
    assert fe.variables.sweeping
    spin(150)
    fe.variables.sweep_button.setChecked(False)
    assert not fe.variables.sweeping and fe.document.flame.xforms[0].params["renamed_fx_amount"] != 1.0
    # duplicate as my own from a bundled formula, and revert
    fe.session.modified = False
    fe.load_formula("whorl")
    assert fe.duplicate_formula() and fe.session.name == "whorl_mine" and fe.session.origin == ORIGIN_NEW and fe.session.modified
    fe.session.modified = False
    fe.load_formula("whorl")
    fe.code.set_text(fe.code.text() + "\n// edited\n")
    assert fe.actions.revert_formula.isEnabled()
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    assert fe.revert_formula() and not fe.session.modified and "// edited" not in fe.code.text()


def test_rigs_compare_preview_options_drawer_and_recent(main, tmp_path):
    fe = formula_editor(main, tmp_path)
    fe.load_formula("whorl")
    fe.load_rig("Julia pair")
    assert [x.name for x in fe.document.flame.xforms] == ["formula", "julian"] and fe.document.can_undo
    assert [a.text() for a in fe.actions.rigs_menu.actions()] == list(A.RIGS)
    # compare with the original renders the registered formula in a second preview
    assert fe.actions.compare.isEnabled() and not fe.original_preview.isVisible()
    fe.actions.compare.setChecked(True)
    assert fe.original_preview.isVisible() and fe._original_flame().xforms[0].variations == {W.ORIGINAL_NAME: 1.0}
    fe.code.set_text(fe.code.text().replace("FPx += VVAR*r*cosa;", "FPx += 2.0 * VVAR*r*cosa;"))
    wait_until(lambda: not fe.session.compiling and fe.session.error is None)
    assert V.REGISTRY[W.ORIGINAL_NAME].numpy is V.REGISTRY["whorl"].numpy and V.REGISTRY[W.SCRATCH_NAME] is not V.REGISTRY["whorl"]
    wait_until(lambda: preview_settled(fe.original_preview) and fe.original_preview.image is not None, 60000)
    assert lit_pixels(fe.original_preview.image) > 100
    fe.actions.compare.setChecked(False)
    assert not fe.original_preview.isVisible()
    # the variation preview options
    before = fe.view.variation_preview_count
    fe.preview_options.sliders["density"].setValue(3)
    assert fe.view.variation_preview_count > before and fe.preview_options.settings()[2] == 3
    fe.preview_options.show_inputs.setChecked(True)
    assert fe.view._input_points is not None and len(fe.view._input_points) >= fe.view.variation_preview_count   # (non-finite outputs dropped)
    fe.preview_options.show_inputs.setChecked(False)
    assert fe.view._input_points is None
    # the drawer: reference, compiler output, probe
    fe.show_drawer_tab("compiler")
    assert not fe.outer_splitter.is_last_collapsed() and fe.actions.drawer.isChecked() and fe.drawer.currentIndex() == 1
    assert "v.x = " in fe.drawer.compiler.output.toPlainText()                      # the GLSL body
    fe.drawer.compiler.which.setCurrentIndex(1)
    assert "def calc" in fe.drawer.compiler.output.toPlainText()
    fe.drawer.reference.show_mode("names")
    fe.drawer.reference.search.setText("fsincos")
    fe.drawer.reference.render()
    assert "fsincos" in fe.drawer.reference.browser.toPlainText()
    fe.drawer.reference.show_mode("guide")
    fe.drawer.reference.search.clear()
    fe.drawer.reference.render()
    assert "PluginVarCalc" in fe.drawer.reference.browser.toPlainText()
    fe.drawer.reference.show_mode("formula")
    assert "whorl_inside" in fe.drawer.reference.browser.toPlainText()
    fe.drawer.reference.insert_requested.emit("atan2")
    assert "atan2" in fe.code.text()
    fe.show_drawer_tab("probe")
    fe.drawer.probe.probe()
    wait_until(lambda: not fe.drawer.probe.busy, 60000)
    assert "FPx  numpy" in fe.drawer.probe.result.toPlainText()
    fe.drawer.probe.check()
    wait_until(lambda: not fe.drawer.probe.busy, 90000)
    text = fe.drawer.probe.result.toPlainText()
    assert text.startswith("✓") or "no OpenGL" in text or "Could not run" in text
    fe.actions.drawer.setChecked(False)
    assert fe.outer_splitter.is_last_collapsed()
    # recent formulas, the side panel toggle, focus switching, gradient presets
    assert fe._recent[0] == "registered:whorl" and fe.actions.recent_menu.actions()[0].text() == "whorl"
    fe.actions.side_panel.setChecked(False)
    assert not fe.side_panel.isVisible()
    fe.actions.side_panel.setChecked(True)
    fe.code.setFocus()
    fe.toggle_focus()
    assert fe.view.hasFocus()
    fe.gradient_presets.gradient_chosen.emit(A.preset_gradient("Fire"))
    assert fe.document.flame.palette[0] == (255, 240, 120) and fe.gradient.name == "Fire"
    fe.session.modified = False


def test_use_current_fractal_and_send_to_main(main, tmp_path):
    fe = formula_editor(main, tmp_path)
    open_flame_and_wait(main, SAMPLE, 0)
    fe.new_formula()
    wait_until(lambda: fe.session.variation is not None)
    fe.actions.use_current.trigger()
    assert len(fe.document.flame.xforms) == len(main.document.flame.xforms) and fe.document.flame.palette == main.document.flame.palette
    fe.use_formula()
    assert fe.document.flame.xforms[0].variations == {W.SCRATCH_NAME: 1.0}
    fe.actions.send_to_main.trigger()                    # unsaved: the formula transform goes out as linear
    assert main.document.flame.name == "new_formula" and main.document.flame.xforms[0].variations == {"linear": 1.0}
    assert fe.save_formula()
    fe.actions.send_to_main.trigger()
    assert main.document.flame.xforms[0].variations == {"new_formula": 1.0}
    fe.session.modified = False
