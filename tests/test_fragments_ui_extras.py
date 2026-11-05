"""The Fragments window's later additions, Qt side: editor tools, the walkthrough, diff / revert, favourites, the history
strip, the preset gallery, viewport overlays, the render queue, the graph editor, the DE export dialog, library extras,
sessions, slider nudging, the post stack page and the render window's view panel."""

from __future__ import annotations


import pytest
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from fractalchemy.fragments import presets
from fractalchemy.fragments.easing import EasingSetting
from fractalchemy.fragments.examples import EXAMPLES_DIR
from fractalchemy.fragments.parameters import FloatParameter, VectorParameter
from fractalchemy.ui.fragments import FragmentsWindow
from fractalchemy.ui.fragments.diff_dialog import DiffDialog, unified_diff
from fractalchemy.ui.fragments.export_de_dialog import ExportDEDialog
from fractalchemy.ui.fragments.graph_editor import GraphCanvas, keyframe_tracks
from fractalchemy.ui.fragments.parameter_panel import FAVOURITES_GROUP
from fractalchemy.ui.fragments.parameter_widgets import ComboSlider
from fractalchemy.ui.fragments.preset_gallery import PresetGalleryDialog
from fractalchemy.ui.fragments.walkthrough_panel import outline_of, steps_of

from .conftest import spin, wait_until

MANDELBULB = EXAMPLES_DIR / "Historical 3D Fractals" / "Mandelbulb.frag"
JULIABULB = EXAMPLES_DIR / "Fractalchemy Collection" / "3D - Juliabulb.frag"
TUTORIAL = EXAMPLES_DIR / "Fractalchemy Tutorials"
BROKEN = "#include \"DE-Raytracer.frag\"\nfloat DE(vec3 p) {\n  return length(p) - 1.0\n}\n"


@pytest.fixture
def window(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "fragments.ini"), QSettings.Format.IniFormat)
    win = FragmentsWindow(None, settings)
    win.resize(1000, 640)
    win.show()
    wait_until(lambda: win._capabilities is not None, 30000)
    yield win
    for tab in win.tabs.tabs:
        tab.document._modified = False
    win.shutdown()
    win.close()


def rendered(win, passes: int = 1, timeout_ms: int = 60000) -> None:
    wait_until(lambda: win.driver.stats is not None and win.driver.stats.passes_done >= passes and win.viewport.image is not None, timeout_ms)


def key(widget, k, text="", mods=Qt.KeyboardModifier.NoModifier) -> None:
    QApplication.sendEvent(widget, QKeyEvent(QEvent.Type.KeyPress, k, mods, text))


def mouse(widget, kind, pos: QPointF, button, buttons, mods=Qt.KeyboardModifier.NoModifier) -> None:
    QApplication.sendEvent(widget, QMouseEvent(kind, pos, widget.mapToGlobal(pos.toPoint()), button, buttons, mods))


# --- editor tools ----------------------------------------------------------------------------------------------------------
def test_editor_diagnostics_definitions_snippets_and_multi_cursor(window):
    document = window.open_text(BROKEN)
    window.build_document(document)
    editor = window.tabs.editor
    wait_until(lambda: editor.diagnostics.count > 0, 30000)
    assert editor.diagnostics.message_at(3) or editor.diagnostics.message_at(4)
    assert editor.hover_text(editor.cursorRect(editor.textCursor()).topLeft()) is not None
    # go to definition: DE is here, trace lives in the include (opened read-only at its line)
    assert editor.goto_definition("DE") and editor.line_column()[0] == 2
    window.goto_include_definition(document, "trace")
    assert window.tabs.document is not document and window.tabs.document.path.name == "DE-Raytracer.frag" and window.tabs.current.read_only
    window.tabs.set_current(document)
    # snippets with stops
    editor.set_text("")
    window.insert_template("uniform float ${1:Name}; slider[${2:0},${3:1},${4:2}]\n$0")
    assert editor.textCursor().selectedText() == "Name"
    key(editor, Qt.Key.Key_P, "P")
    key(editor, Qt.Key.Key_Tab)
    assert editor.textCursor().selectedText() == "0"
    for _ in range(3):
        key(editor, Qt.Key.Key_Tab)
    assert editor.toPlainText() == "uniform float P; slider[0,1,2]\n"
    # multi-selection editing
    editor.set_text("float a = b + b;\nfloat c = b;\n")
    cursor = editor.textCursor()
    cursor.setPosition(10)
    editor.setTextCursor(cursor)
    key(editor, Qt.Key.Key_D, "", Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    key(editor, Qt.Key.Key_L, "", Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert editor.multi.count == 3
    key(editor, Qt.Key.Key_Z, "z")
    assert editor.toPlainText() == "float a = z + z;\nfloat c = z;\n"
    key(editor, Qt.Key.Key_Escape)
    assert not editor.multi.active
    editor.undo()
    assert editor.toPlainText() == "float a = b + b;\nfloat c = b;\n"


def test_walkthrough_lists_steps_and_outline(window):
    tutorial = sorted(TUTORIAL.glob("*.frag"))[0]
    window.open_path(tutorial)
    window.walkthrough_dock.show()
    window.walkthrough.refresh()
    text = window.tabs.document.text
    steps = steps_of(text)
    assert len(steps) >= 3 and steps[0][0] == 1 and any(kind == "function" for kind, _l, _t in outline_of(text))
    assert window.walkthrough.list.count() >= len(steps) and "steps" in window.walkthrough.summary.text()
    window.walkthrough.list.itemClicked.emit(window.walkthrough.list.item(1))
    assert window.tabs.editor.line_column()[0] == steps[1][1]


def test_compare_with_original_and_revert(window, tmp_path):
    window.open_path(MANDELBULB)
    document = window.tabs.document
    original = document.text
    window.replace_text(original.replace("#include \"DE-Raytracer.frag\"", "#include \"DE-Raytracer.frag\"\n// my edit", 1))
    lines = unified_diff(original, document.text, "a", "b")
    assert any(line.startswith("+// my edit") for line in lines)
    dialog = DiffDialog(window, original, document.text, "a", "b", MANDELBULB)
    assert "1 lines added" in dialog.summary.text() and dialog.revert_button.isEnabled()
    dialog.revert_requested.connect(window.replace_text)
    dialog._revert()
    assert document.text == original
    # saving a bundled example elsewhere records its origin
    target = tmp_path / "mine.fafrag"
    window.files._write(document, target)
    assert document.metadata.tabs["origin"].endswith("Mandelbulb.frag")
    from fractalchemy.ui.fragments.file_actions import origin_path
    assert origin_path(document) == MANDELBULB


# --- parameters: favourites, nudging, history / mutate ---------------------------------------------------------------------
def test_favourites_nudging_history_and_mutate(window):
    window.open_path(MANDELBULB)
    rendered(window)
    document = window.tabs.document
    panel = window.parameters
    panel.set_favourite("Power", True)
    assert FAVOURITES_GROUP in panel.groups.groups() and document.metadata.tabs["favourites"] == ["Power"]
    assert panel.group_names(FAVOURITES_GROUP) == ["Power"] and panel.widgets["Power"].is_pinned()
    panel.set_favourite("Power", False)
    assert FAVOURITES_GROUP not in panel.group_names_all()
    # keyboard nudging: Shift × 10
    slider = panel.widgets["Power"].slider
    assert isinstance(slider, ComboSlider)
    before = slider.value
    key(slider.slider, Qt.Key.Key_Right)
    plain = slider.value - before
    key(slider.slider, Qt.Key.Key_Right, "", Qt.KeyboardModifier.ShiftModifier)
    assert plain > 0 and slider.value - before - plain == pytest.approx(plain * 10, rel=0.01)
    # history strip + mutate
    window.explore.dock.show()
    assert window.explore.snapshot("one") and window.explore.strip.count == 1
    own = document.source.own_param_names()
    before = {n: document.state.get(n) for n in own}
    detail = document.state.get("Detail")
    window.explore.mutate(0.3)
    assert window.explore.strip.count == 1           # the look before the mutation was already the last snapshot (no duplicate)
    assert any(document.state.get(n) != before[n] for n in own) and document.state.get("Detail") == detail   # the raytracer's stay put
    assert window.explore.snapshot("after") and window.explore.strip.count == 2
    window.explore.restore(window.explore.strip.entries()[0])
    assert all(document.state.get(n) == pytest.approx(before[n]) for n in own if isinstance(before[n], float))
    assert panel.mutate(0.0) == 0


def test_preset_gallery_renders_and_applies(window):
    window.open_path(MANDELBULB)
    rendered(window)
    document = window.tabs.document
    dialog = PresetGalleryDialog(window, document, window.service)
    assert dialog.list.count() == len(document.source.presets) >= 2
    wait_until(lambda: not dialog._pending, 60000)
    chosen = []
    dialog.preset_chosen.connect(chosen.append)
    dialog._choose(dialog.list.item(1))
    assert chosen == [dialog.list.item(1).text()]
    dialog.close()


# --- viewport overlays --------------------------------------------------------------------------------------------------------
def test_viewport_region_compare_minimap_and_keyframe_handles(window):
    window.library_dock.hide()
    window.splitter.setSizes([250, 700])            # a viewport wide enough to drag in
    window.open_path(MANDELBULB)
    rendered(window)
    wait_until(lambda: window.viewport.width() > 300, 5000)
    viewport, document = window.viewport, window.tabs.document
    regions = []
    viewport.region_selected.connect(regions.append)
    rect = viewport.image_rect()
    start = QPointF(rect.x() + rect.width() * 0.25, rect.y() + rect.height() * 0.25)
    end = QPointF(rect.x() + rect.width() * 0.75, rect.y() + rect.height() * 0.75)
    mouse(viewport, QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
    mouse(viewport, QEvent.Type.MouseMove, end, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
    mouse(viewport, QEvent.Type.MouseButtonRelease, end, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier)
    assert len(regions) == 1 and regions[0][0] == pytest.approx(0.25, abs=0.02) and regions[0][2] == pytest.approx(0.5, abs=0.02)
    assert window.render_window.current_settings().region is not None and "region" in window.render_window.plan_label.text()
    window.render_window.tiles_panel.set_region(None)
    assert window.render_window.current_settings().region is None
    # A/B compare
    window.freeze_reference()
    assert viewport.compare.active and window.actions.compare.isChecked()
    divider = QPointF(viewport.compare.divider_x(rect), rect.center().y())
    mouse(viewport, QEvent.Type.MouseButtonPress, divider, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    mouse(viewport, QEvent.Type.MouseMove, QPointF(rect.x() + rect.width() * 0.2, divider.y()), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
    mouse(viewport, QEvent.Type.MouseButtonRelease, QPointF(rect.x() + rect.width() * 0.2, divider.y()), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
    assert viewport.compare.position == pytest.approx(0.2, abs=0.02)
    viewport.set_compare(False)
    assert not viewport.compare.active
    # mini-map paints for both camera kinds
    viewport.set_minimap(True)
    assert not viewport.grab().isNull()
    # keyframe handles: drag the first keyframe's eye in the screen plane
    text = presets.replace_preset(document.text, "KeyFrame.0001", "Eye = 0,0,-4\nTarget = 0,0,0\nUp = 0,1,0")
    text = presets.replace_preset(text, "KeyFrame.0002", "Eye = 1,0,-4\nTarget = 0,0,0\nUp = 0,1,0")
    window.replace_text(text)
    window.build_document(document)
    document.set_values({"Eye": (0.0, 0.0, -8.0), "Target": (0.0, 0.0, 0.0), "Up": (0.0, 1.0, 0.0)})
    wait_until(lambda: viewport.path is not None and viewport.path.valid, 10000)
    viewport.grab()                                   # paints → the handle positions are known
    screen = viewport.handles._projected["KeyFrame.0001"][0]
    mouse(viewport, QEvent.Type.MouseButtonPress, screen, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    assert viewport.handles.dragging == "KeyFrame.0001"
    moved = screen + QPointF(60, 0)
    mouse(viewport, QEvent.Type.MouseMove, moved, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
    mouse(viewport, QEvent.Type.MouseButtonRelease, moved, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
    body = document.source.presets["KeyFrame.0001"]
    eye = [float(v) for v in body.split("Eye =")[1].splitlines()[0].split(",")]
    assert abs(eye[0]) > 0.1 and abs(eye[2] + 4.0) < 0.5           # moved sideways in the screen plane, same depth


# --- render queue, view panel -------------------------------------------------------------------------------------------------
def test_render_queue_runs_jobs_in_turn(window, tmp_path):
    window.open_path(MANDELBULB)
    rendered(window)
    rw = window.render_window
    rw.prepare_for(window.tabs.document, (32, 24))
    rw.tiles_panel.set_tile_size(32, 24)
    rw.quality_panel.subframes_spin.setValue(1)
    rw.view_panel.stereo.setCurrentIndex(rw.view_panel.stereo.findData("anaglyph"))
    assert rw.current_settings().stereo == "anaglyph" and "stereo anaglyph" in rw.plan_label.text()
    rw.view_panel.stereo.setCurrentIndex(0)
    rw.output_panel.set_path(str(tmp_path / "q1.png"))
    rw.output_panel._on_path_edited()
    window.queue_current_render()
    rw.output_panel.set_path(str(tmp_path / "q2.png"))
    rw.output_panel._on_path_edited()
    window.queue_current_render()
    queue = window.render_queue
    assert len(queue.entries) == 2 and queue.isVisible()
    queue.start()
    wait_until(lambda: not queue.running, 180000)
    assert [e.state for e in queue.entries] == ["done", "done"] and (tmp_path / "q1.png").is_file() and (tmp_path / "q2.png").is_file()
    queue.clear_finished()
    assert queue.entries == []


# --- graph editor ---------------------------------------------------------------------------------------------------------------
def test_graph_editor_drags_curve_handles(qapp):
    canvas = GraphCanvas()
    canvas.resize(600, 300)
    canvas.show()
    curve = EasingSetting("Power1", 0, 2.0, 8.0, 10, 60)
    canvas.set_data([curve], {"Scale": [(0, 1.0), (100, 2.0)]}, 100, 0)
    changed = []
    canvas.curve_changed.connect(changed.append)
    handles = canvas.handles()
    end = next(point for _i, which, point in handles if which == "end")
    mouse(canvas, QEvent.Type.MouseButtonPress, end, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    target = QPointF(end.x() + 60, end.y() + 40)
    mouse(canvas, QEvent.Type.MouseMove, target, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
    mouse(canvas, QEvent.Type.MouseButtonRelease, target, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
    assert len(changed) == 1 and changed[0].last_frame > 60 and changed[0].end < 8.0 and changed[0].slider == "Power1"
    frames = []
    canvas.frame_clicked.connect(frames.append)
    mouse(canvas, QEvent.Type.MouseButtonPress, QPointF(canvas.plot_rect().center()), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    assert frames and 40 <= frames[0] <= 60
    assert not canvas.grab().isNull()
    tracks = keyframe_tracks({"KeyFrame.0001": "Power = 2\nJuliaC = 1,2,3", "KeyFrame.0002": "Power = 4"},
                             {"Power": FloatParameter("Power", "float", to=10.0), "JuliaC": VectorParameter("JuliaC", "vec3", from_=(0, 0, 0), to=(5, 5, 5))}, 100)
    assert tracks["Power"] == [(0, 2.0), (99, 4.0)] and tracks["JuliaC.2"] == [(0, 2.0)]
    canvas.close()


# --- DE export dialog, library extras, sessions, grading page ------------------------------------------------------------------
def test_export_de_dialog_library_extras_sessions_and_post_stack(window, tmp_path, monkeypatch):
    window.open_path(JULIABULB)
    rendered(window)
    document = window.tabs.document
    dialog = ExportDEDialog(window, document.request().modern.fragment, document.request().values, document.name, tmp_path)
    assert "float DE(vec3" in dialog.editor.toPlainText() and dialog.result_export.target == "glsl"
    dialog.target.setCurrentIndex(dialog.target.findData("unity"))
    assert dialog.editor.toPlainText().startswith('Shader "Fractalchemy/')
    monkeypatch.setattr("fractalchemy.ui.fragments.export_de_dialog.QFileDialog.getSaveFileName", staticmethod(lambda *a, **k: (str(tmp_path / "de.shader"), "")))
    dialog.save()
    assert (tmp_path / "de.shader").read_text().startswith("Shader")
    dialog.close()
    # library extras: tags → search words → the Show filter
    extras = window.library_extras
    from fractalchemy.library.items import Kind, LibraryItem
    item = LibraryItem(Kind.FILE, JULIABULB, name=JULIABULB.name)
    wait_until(lambda: window.library_panel.model.index_for(item).isValid(), 30000)
    extras.meta.store = tmp_path / "meta.json"
    extras.set_favourite(item, True)
    extras.set_rating(item, 5)
    monkeypatch.setattr("fractalchemy.ui.fragments.library_extras.QInputDialog.getText", staticmethod(lambda *a, **k: ("bulb, julia", True)))
    extras.edit_tags(item)
    assert extras.meta.tags(JULIABULB) == ["bulb", "julia"]
    extras.show_combo.setCurrentIndex(extras.show_combo.findData("fav"))
    spin(50)
    proxy = window.library_panel.tree.model()
    assert proxy.rowCount() >= 1
    window.library_panel.search.setText("tag:julia")
    extras.apply_query()
    assert proxy.rowCount() >= 1
    window.library_panel.search.setText("tag:nothing-like-this")
    extras.apply_query()
    assert proxy.rowCount() == 0
    window.library_panel.search.setText("")
    extras.show_combo.setCurrentIndex(0)
    extras.apply_query()
    extras.size_combo.setCurrentIndex(2)
    assert window.thumbnails.size.width() == 320
    # sessions: capture, autosave, restore
    document.set_value("Power", 5.0)
    session = window.sessions.capture()
    assert len(session.tabs) == 1 and "Power = 5" in session.tabs[0].settings
    window.sessions.autosave.path = tmp_path / "autosave.fasession"
    window.sessions.autosave_now()
    assert window.sessions.pending_recovery() is not None
    document._modified = False
    window.tabs.close_all()
    assert window.sessions.restore(session) == 1
    wait_until(lambda: window.tabs.document is not None and window.tabs.document.source is not None, 30000)
    assert window.tabs.document.state.get("Power") == 5.0
    window.sessions.clean_shutdown()
    assert not window.sessions.autosave.exists
    # the post stack page writes into the document's grading
    panel = window.grading_panel
    panel.post_rows["bloom"].set_value(0.7)
    panel._changed()
    assert window.tabs.document.grading.bloom == pytest.approx(0.7) and panel.state.text() == "active"
    panel._set_lut(str(tmp_path / "x.cube"))
    assert window.tabs.document.grading.lut.endswith("x.cube")
    panel.reset.click()
    assert window.tabs.document.grading.is_identity


def test_controller_coordinator_learns_and_drives_sliders(window):
    from fractalchemy.fragments.controllers import Control
    from fractalchemy.ui.fragments.controller_input import ControllerDialog
    window.open_path(MANDELBULB)
    rendered(window)
    document = window.tabs.document
    c = window.controllers
    assert "Power1" in c.slider_names() and "JuliaC3" in c.slider_names()
    learned = []
    c.learned.connect(lambda key, slider: learned.append((key, slider)))
    c.learn("Power1")
    c._on_control(Control("cc", 74, 0.3))
    assert learned == [("cc 74", "Power1")] and document.metadata.tabs["controllers"]["cc 74"]["slider"] == "Power1"
    c._on_control(Control("cc", 74, 1.0))
    c._apply_pending()
    assert document.state.get("Power") == pytest.approx(document.state.params["Power"].to)
    c.learn("JuliaC2")
    c._on_control(Control("axis", 1, 0.9))
    assert learned[-1] == ("axis 1", "JuliaC2") and c.mapping().bindings["axis 1"].mode == "relative"
    before = document.state.get("JuliaC")[1]
    c._on_control(Control("axis", 1, 1.0))
    c._last_apply -= 0.5
    c._apply_pending()
    assert document.state.get("JuliaC")[1] > before
    dialog = ControllerDialog(window, c)
    assert dialog.table.rowCount() == 2 and dialog.devices.count() >= 1
    dialog.table.selectRow(0)
    dialog._remove()
    assert dialog.table.rowCount() == 1
    dialog.close()
    c.shutdown()


def test_editor_themes_occlusion_and_exr_channel_boxes(window, tmp_path):
    import numpy as np
    from PySide6.QtGui import QPalette

    from fractalchemy.render.exr import write_exr
    window.library_dock.hide()
    window.splitter.setSizes([250, 700])
    window.open_path(MANDELBULB)
    rendered(window)
    document, editor = window.tabs.document, window.tabs.editor
    # themes: every tab and new tabs follow, the preference remembers
    window.set_editor_theme("Monokai")
    assert editor.theme_name == "Monokai" and editor.palette().color(QPalette.ColorRole.Base).name() == "#272822"
    assert window.prefs.editor_theme == "Monokai" and window.actions.theme_group.checkedAction().text() == "Monokai"
    other = window.open_text("float x;")
    assert window.tabs.editor.theme_name == "Monokai"
    window.tabs.set_current(document)
    window.set_editor_theme("Default")
    assert editor.palette().color(QPalette.ColorRole.Base) == editor.style().standardPalette().color(QPalette.ColorRole.Base)
    other._modified = False
    # spline occlusion: a path through the bulb is dashed where the surface is in front of it
    text = presets.replace_preset(document.text, "KeyFrame.0001", "Eye = -3,0.2,-3\nTarget = 0,0,0\nUp = 0,1,0")
    text = presets.replace_preset(text, "KeyFrame.0002", "Eye = 3,0.2,3\nTarget = 0,0,0\nUp = 0,1,0")
    window.replace_text(text)
    window.build_document(document)
    document.set_values({"Eye": (0.0, 2.5, -5.0), "Target": (0.0, 0.0, 0.0), "Up": (0.0, 1.0, 0.0)})
    viewport = window.viewport
    wait_until(lambda: viewport.path is not None, 10000)
    assert window.driver.want_depth
    wait_until(lambda: window.driver.depth_buffer is not None, 30000)
    rect = viewport.image_rect()
    camera = document.camera3d()
    matrix = camera.projection_view(rect.width() / max(1, rect.height()))
    behind = viewport._project([(0.0, 0.0, 0.0)], matrix, rect)[0]          # the target sits inside the bulb
    assert viewport._hidden((0.0, 0.0, 0.0), behind, rect, camera.eye)
    far_out = viewport._project([(-3.0, 0.2, -3.0)], matrix, rect)[0]
    assert far_out is None or not viewport._hidden((-3.0, 0.2, -3.0), far_out, rect, camera.eye)
    assert not viewport.grab().isNull()
    viewport.set_occlusion(False)
    assert not window.driver.want_depth and not viewport._hidden((0.0, 0.0, 0.0), behind, rect, camera.eye)
    window.animation.set_occlude_paths(True)
    assert window.driver.want_depth and window.prefs.occlude_paths
    # the 3D pick converts FragM's occlusion depth encoding to a distance
    from fractalchemy.fragments.camera import depth_to_distance
    assert window.driver.depth_buffer is not None
    centre = window.driver.depth_buffer[window.driver.depth_buffer.shape[0] // 2, window.driver.depth_buffer.shape[1] // 2]
    distance = depth_to_distance(centre, bool(document.state.get("DepthToAlpha")))
    assert distance is not None and 1.0 < distance < 6.0
    # EXR channel boxes on a sampler widget
    write_exr(tmp_path / "depth.exr", {"R": np.zeros((2, 2), np.float32), "Z": np.ones((2, 2), np.float32)})
    fragment = tmp_path / "tex.frag"
    fragment.write_text('#include "Progressive2D.frag"\nuniform sampler2D tex; file[depth.exr]\nvec3 color(vec2 p) { return texture2D(tex, p).rgb; }\n')
    window.open_path(fragment)
    wait_until(lambda: window.tabs.document.source is not None, 30000)
    widget = window.parameters.widgets["tex"]
    assert [widget.channels[0].itemText(i) for i in range(widget.channels[0].count())] == ["R", "Z"]
    widget.channels[0].setCurrentText("Z")
    widget.channels[0].activated.emit(widget.channels[0].currentIndex())
    assert "depth.exr Z;" in window.tabs.document.state.get("tex")
    for tab in window.tabs.tabs:
        tab.document._modified = False


def test_view_actions_trigger_from_the_toolbar(window):
    """The view actions are QActions: `triggered(bool)` must not swallow the side name (a toolbar click once raised KeyError: False)."""
    window.open_path(MANDELBULB)
    rendered(window)
    document = window.tabs.document
    for side, action in window.actions.views.items():
        action.trigger()
        eye, target = document.camera3d().eye, document.camera3d().target
        assert document.camera3d().view_from(side).eye == pytest.approx(eye), side
        assert target == pytest.approx(document.camera3d().target)
    before = document.camera3d().eye
    window.actions.flip_view.trigger()
    assert document.camera3d().eye != pytest.approx(before)
    window.actions.frame_origin.trigger()
    assert document.camera3d().target == pytest.approx((0.0, 0.0, 0.0))
