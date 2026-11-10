"""The Mutate & Breed window: offspring around the current fractal, adopting one (undoable, the gradient editor follows
without asking), breeding with a second parent, following the main window, persistence and the render plumbing."""

import shutil

import numpy as np
import pytest
from PySide6.QtCore import QSettings, QSize
from PySide6.QtWidgets import QMessageBox

from fractalchemy.fractal import mutation as M
from fractalchemy.fractal.formats import load_flame
from fractalchemy.fractal.mutation import Offspring
from fractalchemy.render.settings import RenderStats
from fractalchemy.ui.grid_renderer import GridRenderer
from fractalchemy.ui.mutation_window import OFFSPRING_CELLS, MutationWindow
from fractalchemy.widgets.flame_grid import CENTRE
from tests.conftest import open_flame_and_wait, wait_until


@pytest.fixture
def workdir(samples, tmp_path):
    shutil.copy(samples / "sample flames" / "candy.flame", tmp_path / "candy.flame")
    shutil.copy(samples / "sample flames" / "stuff.flame", tmp_path / "stuff.flame")
    return tmp_path


@pytest.fixture
def win(main_window_factory):
    return main_window_factory(cheap_renders=True)


def offspring_ready(window: MutationWindow, timeout_ms: int = 60000) -> None:
    wait_until(lambda: window.ready and len(window.offspring) == len(OFFSPRING_CELLS), timeout_ms)


def test_ctrl_m_opens_the_window_with_eight_mutants_around_the_parent(win, workdir):
    open_flame_and_wait(win, workdir / "candy.flame", 0)
    assert win.actionMutate.shortcut().toString() == "Ctrl+M" and win.actionMutate in win.toolBar.actions()
    win.actionMutate.trigger()
    window = win.mutation_window
    assert window.isVisible() and not window.breeding
    offspring_ready(window)
    grid = window.grid
    assert grid.parent_cell == CENTRE and "Parent" in grid.cells[CENTRE].caption
    assert all(grid.cells[c].caption and grid.cells[c].tooltip.startswith("original · m") for c in OFFSPRING_CELLS)
    wait_until(lambda: all(cell.image is not None for cell in grid.cells), 90000)


def test_choosing_a_mutant_is_one_undoable_edit_that_keeps_the_file_link_and_name(win, workdir):
    open_flame_and_wait(win, workdir / "candy.flame", 0)
    win.show_mutation()
    window = win.mutation_window
    offspring_ready(window)
    before = win.document.flame.copy()
    chosen = window.offspring[OFFSPRING_CELLS[2]].flame
    generation = window.generation
    window.grid.chosen.emit(OFFSPRING_CELLS[2])
    flame = win.document.flame
    assert flame.name == before.name and flame.xforms == chosen.xforms and flame.palette == chosen.palette
    assert win.document.is_showing(workdir / "candy.flame", 0) and win.document.modified and "*" in win.windowTitle()
    assert window.generation == generation + 1                              # new offspring around the new parent
    win.document.undo()
    assert win.document.flame.to_dict() == before.to_dict()


def test_adopting_a_new_gradient_updates_the_gradient_editor_without_asking(win, workdir, monkeypatch):
    """The brief: the gradient editor follows as when a new fractal is chosen, but never prompts about unsaved edits."""
    open_flame_and_wait(win, workdir / "candy.flame", 0, gradient_too=True)
    gradients = win.gradient_library.document
    gradients.set_color(0, (1, 2, 3))                                       # unsaved edits in the gradient editor
    assert gradients.modified

    def fail(*_args, **_kwargs):
        raise AssertionError("adopting a mutant must not ask about the unsaved gradient")
    monkeypatch.setattr(QMessageBox, "question", fail)
    win.show_mutation()
    window = win.mutation_window
    offspring_ready(window)
    mutant = win.document.flame.copy()
    mutant.palette = [(0, 200, 0)] * 128 + [(200, 0, 200)] * 128             # a gradient mutation, made obvious
    window.offspring[OFFSPRING_CELLS[0]] = Offspring(mutant, ["gradient"])
    assert window.adopt(OFFSPRING_CELLS[0])
    assert {s.color for s in gradients.gradient.stops} == {(0, 200, 0), (200, 0, 200)}
    assert not gradients.modified and gradients.is_showing(workdir / "candy.flame", 0)   # still the fractal's own entry
    win.document.undo()                                                     # and back, again without a prompt
    assert gradients.gradient.stops[0].color == (1, 2, 3)


def test_breeding_with_a_second_parent(win, workdir):
    open_flame_and_wait(win, workdir / "candy.flame", 0)
    win.show_mutation()
    window = win.mutation_window
    window.tabs.setCurrentIndex(1)
    assert window.breeding
    wait_until(lambda: window.grid.message != "" or window.offspring == {}, 5000)
    assert window.breed_panel.parent_b is None
    window.use_current_as_parent_b()
    assert window.breed_panel.parent_b.name == "original"
    open_flame_and_wait(win, workdir / "stuff.flame", 1)                     # parent A is now another fractal
    offspring_ready(window)
    assert all(" × " in child.flame.name for child in window.offspring.values())
    window.load_parent_b(workdir / "stuff.flame", 2)                        # what a Fractal Library drop does
    wait_until(lambda: window.breed_panel.parent_b is not None and window.breed_panel.parent_b.name == load_flame(workdir / "stuff.flame", 2).name)
    offspring_ready(window)
    child = window.offspring[OFFSPRING_CELLS[0]].flame
    window.adopt(OFFSPRING_CELLS[0])
    assert win.document.flame.xforms == child.xforms


def test_the_cell_menu_opens_a_child_as_a_new_fractal_or_uses_it_as_parent_b(win, workdir):
    open_flame_and_wait(win, workdir / "candy.flame", 0)
    win.show_mutation()
    window = win.mutation_window
    offspring_ready(window)
    cell = OFFSPRING_CELLS[1]
    texts = [a.text() for a in window.cell_menu(cell).actions() if not a.isSeparator()]
    assert texts == [f"Make it the fractal ({cell + 1})", "Open as new unsaved fractal", "Use as parent B", "Copy parameters"]
    assert [a.text() for a in window.cell_menu(CENTRE).actions()] == ["Use as parent B", "Copy parameters"]
    child = window.offspring[cell].flame
    next(a for a in window.cell_menu(cell).actions() if a.text() == "Use as parent B").trigger()
    assert window.breed_panel.parent_b.xforms == child.xforms
    next(a for a in window.cell_menu(cell).actions() if a.text() == "Open as new unsaved fractal").trigger()
    assert win.document.source_path is None and win.document.flame.name == child.name


def test_the_window_follows_the_main_window(win, workdir):
    open_flame_and_wait(win, workdir / "candy.flame", 0)
    win.show_mutation()
    window = win.mutation_window
    offspring_ready(window)
    generation = window.generation
    open_flame_and_wait(win, workdir / "candy.flame", 3)                     # another fractal: new offspring at once
    assert window.generation == generation + 1
    offspring_ready(window)
    generation = window.generation
    win.document.set_view(zoom=1.0)                                         # an edit: new offspring once edits pause
    wait_until(lambda: window.generation == generation + 1, 5000)
    window.hide()
    open_flame_and_wait(win, workdir / "candy.flame", 1)                     # hidden: only noted
    assert window.generation == generation + 1 and not window.ready
    win.show_mutation()
    wait_until(lambda: window.generation == generation + 2)


def test_no_fractal_and_no_second_parent_say_so(win):
    win.show_mutation()
    window = win.mutation_window
    wait_until(lambda: window.grid.message != "")
    assert "Open a fractal" in window.grid.message


def test_options_and_tab_persist(win, tmp_path, qapp):
    settings = QSettings(str(tmp_path / "m.ini"), QSettings.Format.IniFormat)
    first = MutationWindow(win.document, win.render_service, None, settings)
    first.mutate_panel.set_options(M.MutationOptions(strength=0.8, kinds=frozenset({M.AFFINE, M.GRADIENT}), trend="julian",
                                                     keep_count=True))
    first.mutate_panel.options_changed.emit()
    first.breed_panel.mode.setCurrentIndex(first.breed_panel.mode.findData("union"))
    first.tabs.setCurrentIndex(1)
    first.save_state()
    again = MutationWindow(win.document, win.render_service, None, settings)
    options = again.mutate_panel.options()
    assert options.strength == 0.8 and options.kinds == {M.AFFINE, M.GRADIENT} and options.trend == "julian" and options.keep_count
    assert again.breed_panel.options().mode == "union" and again.breeding
    first.close()
    again.close()


def test_the_grid_renderer_ignores_passes_of_an_older_generation(win):
    renderer = GridRenderer(win.render_service, QSize(40, 30))
    got = []
    renderer.image_ready.connect(lambda slot, image: got.append(slot))
    renderer.render({})
    stale = ("grid", id(renderer), renderer.generation, 3)
    renderer.render({})
    image = np.zeros((30, 40, 4), np.uint8)
    win.render_service.pass_done.emit(stale, image, RenderStats("CPU", 1, 1, 0, 0, 0.0, 40, 30))
    win.render_service.pass_done.emit(("grid", id(renderer), renderer.generation, 5), image, RenderStats("CPU", 1, 1, 0, 0, 0.0, 40, 30))
    assert got == [5]


def test_space_in_the_grid_makes_new_offspring(win, workdir):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    open_flame_and_wait(win, workdir / "candy.flame", 0)
    win.show_mutation()
    window = win.mutation_window
    offspring_ready(window)
    generation = window.generation
    QTest.keyClick(window.grid, Qt.Key.Key_Space)
    assert window.generation == generation + 1
    assert "Space" in window.mutate_panel.regenerate_button.toolTip()


def test_the_fractal_library_offers_breed_with_current_fractal(main_window_factory, workdir):
    from fractalchemy.library.items import Kind, LibraryItem
    win = main_window_factory(cheap_renders=True)
    open_flame_and_wait(win, workdir / "candy.flame", 0)
    row = LibraryItem(Kind.ENTRY, workdir / "stuff.flame", 2, "a stuff entry")
    menu = win.fractal_menu.build(row, [row])
    action = next(a for a in menu.actions() if a.text() == "Breed with Current Fractal")
    assert [a.text() for a in menu.actions()][:2] == ["Open", "Breed with Current Fractal"]
    action.trigger()
    window = win.mutation_window
    assert window.breeding and window.isVisible()
    wait_until(lambda: window.breed_panel.parent_b is not None)
    assert window.breed_panel.parent_b.name == load_flame(workdir / "stuff.flame", 2).name
    offspring_ready(window)


def test_the_grid_states_are_named_and_shown(win, workdir):
    from fractalchemy.machines import OffspringState
    win.show_mutation()
    window = win.mutation_window
    wait_until(lambda: window.state is OffspringState.EMPTY)
    assert window.state_label.text() == "No fractal" and "no fractal" in window.state_label.toolTip()
    open_flame_and_wait(win, workdir / "candy.flame", 0)
    offspring_ready(window)
    assert window.state is OffspringState.READY and window.state_label.text() == "Ready"
    window.show_breeding()                                   # the Breed tab without a parent B
    wait_until(lambda: window.state is OffspringState.NEEDS_PARENT)
    assert window.state_label.text() == "Needs parent B" and "second parent" in window.grid.message
    window.use_current_as_parent_b()
    assert window.state is OffspringState.GENERATING
    offspring_ready(window)
    window.hide()
    win.document.set_view(zoom=0.5)                          # an edit while hidden: noted, nothing made
    assert window.state is OffspringState.STALE and not window.ready
    events = [step.event for step in window.offspring_state.history]
    assert events[:3] == ["no_fractal", "changed", "generate"] and events[-1] == "changed"
