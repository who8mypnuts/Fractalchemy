"""The Mutate & Breed window: explore relatives of the fractal shown in the main window.

*Windows ▸ Mutate & Breed…* (`Ctrl+M`). A 3 × 3 grid (`FlameGrid`) with the current fractal in the centre and eight
offspring around it, made on the thread pool (`fractal/mutation.py`, `fractal/breeding.py`) and rendered small through
the shared render service at thumbnail priority (`GridRenderer`), so the main viewport always comes first.

* **Mutate** tab: eight mutants of the current fractal (strength, what may change, trend, Apophysis's two switches).
* **Breed** tab: eight children of the current fractal (parent A) and a second parent B, which comes from the current
  fractal (*Use current fractal*, then show another one), from a file, from a Fractal Library row dropped on its slot,
  or from a cell's menu.
* **Explore script** tab: eight variations of the Script Editor's live script — its parameters nudged (or drawn anywhere
  in their ranges, or new random numbers only), each run on the fractal as it was before the script (`scripting.explore`,
  restricted). Clicking a cell gives its values to the Parameters tab: the live session re-runs with them, still the
  script's one undo step. (*Make it the fractal* in a cell's menu adopts the flame as a separate step instead.)

**Choosing a cell** (click, or its number 1–9) makes it the main window's fractal as **one undoable edit**: the file
link and the fractal's name are kept, Ctrl+Z goes back, Save overwrites the entry. The grid then regenerates around the
new parent. The Gradient Library follows the new gradient at once and never asks about unsaved gradient edits
(`GradientLink.follow_flame`): they were already applied to the fractal and are in its undo history. A cell's
right-click menu can also *Open as new unsaved fractal* (the same as choosing a fractal in the library), use it as
parent B, or copy its parameters.

The window follows the main window: a different fractal regenerates the grid at once, edits regenerate it once they
pause, and while the window is hidden it only notes that it is stale. Options persist in QSettings (`mutate/…`,
`breed/…`).
"""

from __future__ import annotations

import random
from pathlib import Path

from PySide6.QtCore import QPoint, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QGuiApplication, QShowEvent
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMenu, QScrollArea, QSplitter, QStatusBar, QTabWidget, QWidget

from .. import config
from ..fractal import breeding as B
from ..fractal import mutation as M
from ..fractal.formats import flame_to_text, load_flame, open_dialog_filter
from ..fractal.mutation import Offspring
from ..fractal.scene import Flame
from ..scripting.explore import explore
from ..machines import OFFSPRING, OffspringState
from ..render.service import RenderService
from ..widgets.actions import make_action, populate
from ..widgets.flame_grid import CELLS, CENTRE, FlameGrid
from ..widgets.icons import action_icon, mutation_icon
from ..widgets.windows import bring_to_front
from .background import run_in_background
from .fractal_document import FractalDocument
from .grid_renderer import GridRenderer
from .mutation_panels import BreedPanel, ExplorePanel, MutatePanel
from .undo_labels import show_undo_state

WINDOW_TITLE = "Mutate & Breed"
MUTATE_TAB, BREED_TAB, EXPLORE_TAB = 0, 1, 2
OFFSPRING_CELLS = tuple(i for i in range(CELLS) if i != CENTRE)
SIDE_WIDTH = 300
NO_FRACTAL = "Open a fractal in the main window to mutate it"
OFFSPRING_LABELS = {OffspringState.STALE: "Out of date", OffspringState.EMPTY: "No fractal",
                    OffspringState.NEEDS_PARENT: "Needs parent B", OffspringState.NEEDS_SCRIPT: "Needs a live script",
                    OffspringState.GENERATING: "Making offspring…",
                    OffspringState.READY: "Ready", OffspringState.FAILED: "Failed"}
NO_PARENT_B = ("Choose a second parent (B) on the right: use the current fractal and then show another one, open a file, "
               "or drop a fractal from the Fractal Library")


class MutationWindow(QMainWindow):
    """The Mutate & Breed window (see the module docstring).

    Signals:
        open_requested(object): A `Flame` to show in the main window as a new, unsaved fractal.
    """
    open_requested = Signal(object)

    def __init__(self, document: FractalDocument, service: RenderService, parent: QWidget | None = None,
                 settings: QSettings | None = None):
        """Args:
            document: The main window's document: the parent, and what adopting a cell edits.
            service: The shared render service.
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where the options and the layout persist.
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(mutation_icon())
        self.document = document
        self._settings = settings if settings is not None else QSettings()
        self._rng = random.Random()
        self.grid = FlameGrid(self)
        self.renderer = GridRenderer(service, QSize(*config.MUTATION_CELL_SIZE), self)
        self.parent_renderer = GridRenderer(service, QSize(*config.MUTATION_CELL_SIZE), self)
        self.tabs = QTabWidget(self)
        self.mutate_panel = MutatePanel(self)
        self.breed_panel = BreedPanel(self)
        self.explore_panel = ExplorePanel(self)
        self.script_source = None                           # the Script Editor's LiveParameters (set by the main window)
        self.offspring: dict[int, Offspring] = {}          # grid cell → the mutant / child shown there
        self.variants: dict[int, object] = {}              # grid cell → the explored values (Explore script tab)
        self._generation = 0
        self.offspring_state = OFFSPRING.new(WINDOW_TITLE)   # stale / empty / needs_parent / generating / ready / failed
        self.offspring_state.on_change(lambda _step: self._show_offspring_state())
        self.state_label = QLabel(self)
        self._adopting = False
        self._follow = QTimer(self, singleShot=True, interval=config.EDIT_RENDER_DELAY_MS)
        self._follow.timeout.connect(self._follow_parent)
        self._build()
        self._connect()
        self._load_settings()

    # --- construction ---------------------------------------------------------------------------------------------
    def _build(self) -> None:
        for panel, title, tip in ((self.mutate_panel, "Mutate", "Eight mutants of the current fractal"),
                                  (self.breed_panel, "Breed", "Eight children of the current fractal (A) and a second parent (B)"),
                                  (self.explore_panel, "Explore script", "Eight variations of the Script Editor's live parameters")):
            scroll = QScrollArea(self.tabs)
            scroll.setWidget(panel)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            self.tabs.setTabToolTip(self.tabs.addTab(scroll, title), tip)
        self.tabs.setMinimumWidth(SIDE_WIDTH)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(self.grid)
        self.splitter.addWidget(self.tabs)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.setCentralWidget(self.splitter)
        self.setStatusBar(QStatusBar(self))
        self.statusBar().addPermanentWidget(self.state_label)
        self._show_offspring_state()
        self.regenerate_action = make_action(self, "New offspring", "reload", self.regenerate, "F5",
                                             "Make a new set of mutants / children of the current fractal (Space in the grid)")
        self.undo_action = make_action(self, "Undo", action_icon("undo"), self.document.undo, "Ctrl+Z", "Undo the last change of the fractal")
        self.redo_action = make_action(self, "Redo", action_icon("redo"), self.document.redo, "Ctrl+Shift+Z", "Redo")
        toolbar = self.addToolBar("Mutate & Breed")
        toolbar.setMovable(False)
        populate(toolbar, self.regenerate_action, None, self.undo_action, self.redo_action)
        self.resize(1100, 720)

    def _connect(self) -> None:
        self.grid.chosen.connect(self.adopt)
        self.grid.menu_requested.connect(self._cell_menu)
        self.grid.regenerate_requested.connect(self.regenerate)
        self.renderer.image_ready.connect(self.grid.set_image)
        self.parent_renderer.image_ready.connect(lambda _slot, image: self.breed_panel.show_parent_image(image))
        self.tabs.currentChanged.connect(lambda _index: self._options_changed())
        for panel in (self.mutate_panel, self.breed_panel, self.explore_panel):
            panel.options_changed.connect(self._options_changed)
            panel.regenerate_requested.connect(self.regenerate)
        self.breed_panel.use_current_requested.connect(self.use_current_as_parent_b)
        self.breed_panel.open_requested.connect(self.open_parent_b)
        self.breed_panel.dropped.connect(lambda items: self.load_parent_b(items[0].path, items[0].index))
        doc = self.document
        doc.flame_replaced.connect(self._parent_replaced)
        for signal in (doc.flame_restored, doc.palette_changed, doc.transforms_changed, doc.camera_changed, doc.coloring_changed):
            signal.connect(self._parent_edited)
        doc.xform_changed.connect(lambda *_args: self._parent_edited())
        doc.undo_changed.connect(self._show_undo_state)
        self._show_undo_state(doc.can_undo, doc.can_redo)

    def _show_undo_state(self, can_undo: bool, can_redo: bool) -> None:
        show_undo_state(self.document, self.undo_action, self.redo_action)

    # --- state ------------------------------------------------------------------------------------------------------
    @property
    def breeding(self) -> bool:
        """Whether the Breed tab is the current one."""
        return self.tabs.currentIndex() == BREED_TAB

    @property
    def exploring(self) -> bool:
        """Whether the Explore script tab is the current one."""
        return self.tabs.currentIndex() == EXPLORE_TAB

    def set_script_source(self, source) -> None:
        """The Script Editor's live parameters (`script_live.LiveParameters`): what the Explore tab varies."""
        if source is self.script_source:
            return
        self.script_source = source
        source.changed.connect(self._script_changed)
        self._script_changed()

    def _script_changed(self) -> None:
        source = self.script_source
        if source is None:
            return
        name = source.session.name if source.session is not None else ""
        self.explore_panel.set_script(name, list(source.specs), "" if source.available else source.unavailable_reason())
        if self.exploring and source.live and not self._adopting:
            self._options_changed()

    def show_exploring(self) -> None:
        """Switch to the Explore script tab."""
        self.tabs.setCurrentIndex(EXPLORE_TAB)

    @property
    def generation(self) -> int:
        """Increments with every regeneration (tests wait on the offspring of one)."""
        return self._generation

    @property
    def ready(self) -> bool:
        """Whether the offspring of the latest regeneration have arrived (and nothing has changed since)."""
        return self.offspring_state.state == OffspringState.READY

    @property
    def state(self) -> OffspringState:
        """What the grid shows (see `machines.OFFSPRING`)."""
        return self.offspring_state.state

    def _show_offspring_state(self) -> None:
        self.state_label.setText(OFFSPRING_LABELS[self.offspring_state.state])
        self.state_label.setToolTip(OFFSPRING.meanings[self.offspring_state.state])

    # --- making offspring -------------------------------------------------------------------------------------------
    def regenerate(self) -> None:
        """Make a new set of offspring of the current fractal (on the thread pool) and render the grid."""
        self._follow.stop()
        self._generation += 1
        generation = self._generation
        self.offspring = {}
        parent = self.document.flame
        if parent is None:
            self.renderer.cancel()
            self.grid.clear(NO_FRACTAL)
            self.offspring_state.fire("no_fractal")
            return
        if self.exploring:
            self._regenerate_variations(generation, parent)
            return
        parent_b = self.breed_panel.parent_b
        self.grid.clear(NO_PARENT_B if self.breeding and parent_b is None else "")
        self.grid.set_cell(CENTRE, "Parent A (the current fractal)" if self.breeding else "Parent (the current fractal)",
                           f"{parent.name} — the fractal shown in the main window")
        self.renderer.render({CENTRE: parent})
        if self.breeding and parent_b is None:
            self.offspring_state.fire("no_second_parent")
            return
        self.offspring_state.fire("generate")
        for cell in OFFSPRING_CELLS:
            self.grid.set_cell(cell, "…", busy=True)
        seed = self._rng.getrandbits(32)
        count = min(len(OFFSPRING_CELLS), config.MUTATION_CHILDREN)
        if self.breeding:
            job = (B.children, parent.copy(), parent_b.copy(), count, seed, self.breed_panel.options())
            self.statusBar().showMessage(f"Breeding {parent.name} with {parent_b.name}…")
        else:
            job = (M.mutants, parent.copy(), count, seed, self.mutate_panel.options())
            self.statusBar().showMessage(f"Mutating {parent.name}…")
        run_in_background(*job, on_done=lambda result: self._offspring_made(generation, result),
                          on_error=lambda exc: self._failed(generation, exc))

    def _regenerate_variations(self, generation: int, parent: Flame) -> None:
        """The Explore script tab: eight variations of the live script's values, run on the thread pool."""
        source = self.script_source
        self.variants = {}
        if source is None or not source.available:
            reason = source.unavailable_reason() if source is not None else "Run a script with parameters in the Script Editor"
            self.grid.clear(reason)
            self.offspring_state.fire("no_script")
            return
        session = source.session
        self.grid.clear("")
        self.grid.set_cell(CENTRE, f"{session.name} (as it is)", "The fractal shown in the main window: the script's current values")
        self.renderer.render({CENTRE: parent})
        self.offspring_state.fire("generate")
        for cell in OFFSPRING_CELLS:
            self.grid.set_cell(cell, "…", busy=True)
        count = min(len(OFFSPRING_CELLS), config.MUTATION_CHILDREN)
        self.statusBar().showMessage(f"Exploring the parameters of {session.name}…")
        run_in_background(explore, session.code, session.snapshot, list(source.specs), dict(source.values), session.seed, count,
                          self._rng.getrandbits(32), self.explore_panel.options(), None, lambda f: M.is_stable(f, []),
                          on_done=lambda results: self._variations_made(generation, results),
                          on_error=lambda exc: self._failed(generation, exc))

    def _variations_made(self, generation: int, results: list) -> None:
        if generation != self._generation:
            return
        offspring = {}
        for cell, result in zip(OFFSPRING_CELLS, results):
            self.variants[cell] = result
            notes = list(result.variant.notes) or ["the same values"]
            if result.error:
                self.grid.set_cell(cell, f"✖ {result.error}", result.error)
                continue
            if result.unstable:
                notes.insert(0, "⚠ blows up")
            offspring[cell] = Offspring(result.flame, notes)
            self.grid.set_cell(cell, caption(offspring[cell]), tooltip(offspring[cell]))
            self.renderer.render_slot(cell, result.flame)
        self.offspring = offspring
        self.offspring_state.fire("made")
        self.statusBar().showMessage("Click a variation (or press its number) to give its values to the Parameters tab", 8000)

    def _offspring_made(self, generation: int, offspring: list[Offspring]) -> None:
        if generation != self._generation:
            return                                          # a newer regeneration superseded this one
        self.offspring = dict(zip(OFFSPRING_CELLS, offspring))
        for cell, child in self.offspring.items():
            self.grid.set_cell(cell, caption(child), tooltip(child))
            self.renderer.render_slot(cell, child.flame)
        self.offspring_state.fire("made")                  # from *stale* too: shown until the regeneration replaces them
        what = "children" if self.breeding else "mutants"
        self.statusBar().showMessage(f"{len(offspring)} {what}: click one (or press its number) to make it the fractal; "
                                     "right-click for more", 8000)

    def _failed(self, generation: int, exc: Exception) -> None:
        if generation == self._generation:
            self.offspring_state.fire("failed")
            self.grid.set_message(f"Could not make offspring: {exc}")
            self.statusBar().showMessage(f"Could not make offspring: {exc}")

    # --- choosing -----------------------------------------------------------------------------------------------------
    def adopt(self, cell: int) -> bool:
        """Make the offspring in `cell` the main window's fractal: one undoable edit, file link and name kept. On the
        Explore script tab, give the cell's values to the Parameters tab instead (the live session follows)."""
        if self.exploring and cell in self.variants and cell in self.offspring and self.script_source is not None:
            variant = self.variants[cell].variant
            self.script_source.adopt(variant.values, variant.seed)
            self.statusBar().showMessage(f"Took {cell + 1}: {'; '.join(variant.notes) or 'the same values'} — Ctrl+Z goes back", 10000)
            return True
        return self.adopt_flame(cell)

    def adopt_flame(self, cell: int) -> bool:
        """Make the offspring in `cell` the main window's fractal as a separate undoable edit."""
        child = self.offspring.get(cell)
        if child is None or self.document.flame is None:
            return False
        flame = child.flame.copy()
        flame.name = self.document.flame.name
        self._adopting = True
        try:
            self.document.replace_flame_parameters(flame, "breed" if self.breeding else "mutate" if not self.exploring else "explore")
        finally:
            self._adopting = False
        self.statusBar().showMessage(f"Took {cell + 1}: {'; '.join(child.notes) or 'a copy'} — Ctrl+Z goes back", 10000)
        self.regenerate()
        return True

    def _cell_menu(self, cell: int, pos: QPoint) -> None:
        self.cell_menu(cell).exec(pos)

    def cell_menu(self, cell: int) -> QMenu:
        """The right-click menu of `cell` (the parent's has only the entries that make sense for it)."""
        menu = QMenu(self)
        flame = self.document.flame if cell == CENTRE else (self.offspring[cell].flame if cell in self.offspring else None)
        if flame is None:
            return menu
        if cell != CENTRE and self.exploring and cell in self.variants:
            menu.addAction(f"Use these values ({cell + 1})", lambda: self.adopt(cell))
            menu.addAction("Make it the fractal (a separate step)", lambda: self.adopt_flame(cell))
            menu.addAction("Open as new unsaved fractal", lambda: self.open_requested.emit(flame.copy()))
            menu.addSeparator()
        elif cell != CENTRE:
            menu.addAction(f"Make it the fractal ({cell + 1})", lambda: self.adopt(cell))
            menu.addAction("Open as new unsaved fractal", lambda: self.open_requested.emit(flame.copy()))
            menu.addSeparator()
        menu.addAction("Use as parent B", lambda: self.set_parent_b(flame, "from the grid"))
        menu.addAction("Copy parameters", lambda: QGuiApplication.clipboard().setText(flame_to_text(flame)))
        return menu

    def show_breeding(self) -> None:
        """Switch to the Breed tab."""
        self.tabs.setCurrentIndex(BREED_TAB)

    # --- the second parent --------------------------------------------------------------------------------------------
    def set_parent_b(self, flame: Flame, where: str = "") -> None:
        """Use `flame` as parent B (and regenerate when the Breed tab is showing)."""
        self.breed_panel.set_parent_b(flame, where)
        self.parent_renderer.render({0: flame})
        self.statusBar().showMessage(f"Parent B: {flame.name}", 5000)
        if self.breeding:
            self.regenerate()

    def use_current_as_parent_b(self) -> None:
        """*Use current fractal*: the main window's fractal becomes parent B."""
        if self.document.flame is not None:
            self.set_parent_b(self.document.flame, "the fractal that was shown in the main window")

    def open_parent_b(self) -> None:
        """*Open…*: parent B from a file (its first fractal)."""
        path, _ = QFileDialog.getOpenFileName(self, "Open the second parent", "", open_dialog_filter())
        if path:
            self.load_parent_b(Path(path), 0)

    def load_parent_b(self, path: Path, index: int = 0) -> None:
        """Parent B from fractal `index` of `path` (loaded on the thread pool)."""
        run_in_background(load_flame, path, index,
                          on_done=lambda flame: self.set_parent_b(flame, f"{path.name} #{index + 1}"),
                          on_error=lambda exc: self.statusBar().showMessage(f"Could not open {path.name}: {exc}"))

    # --- following the main window ------------------------------------------------------------------------------------
    def _parent_replaced(self) -> None:
        """A different fractal in the main window: new offspring at once (when visible)."""
        self.offspring_state.fire("changed")
        if self.isVisible():
            self.regenerate()

    def _parent_edited(self) -> None:
        """The fractal was edited elsewhere: regenerate once the edits pause (our own adoptions excepted)."""
        if self._adopting:
            return
        self.offspring_state.fire("changed")
        if self.isVisible():
            self._follow.start()

    def _follow_parent(self) -> None:
        if self.isVisible() and self.offspring_state.state == OffspringState.STALE:
            self.regenerate()

    def _options_changed(self) -> None:
        self._save_options()
        self.offspring_state.fire("changed")
        if self.isVisible():
            self._follow.start()

    # --- window ------------------------------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show the window (restoring it if minimised), raise it and give the grid the keyboard."""
        bring_to_front(self)
        self.grid.setFocus()

    def refresh_formulas(self) -> None:
        """Formulas were added or removed: the trend list follows."""
        self.mutate_panel.populate_trends()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if self.offspring_state.state == OffspringState.STALE:
            QTimer.singleShot(0, self.regenerate)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.save_state()
        self.renderer.cancel()
        self.parent_renderer.cancel()
        super().closeEvent(event)

    def save_state(self) -> None:
        """Remember the layout and the options."""
        self._settings.setValue("mutate/geometry", self.saveGeometry())
        self._settings.setValue("mutate/splitter", self.splitter.saveState())
        self._save_options()

    def _save_options(self) -> None:
        self._settings.setValue("mutate/tab", self.tabs.currentIndex())
        self.mutate_panel.save(self._settings, "mutate")
        self.breed_panel.save(self._settings, "breed")
        self.explore_panel.save(self._settings, "explore")

    def _load_settings(self) -> None:
        geometry, splitter = self._settings.value("mutate/geometry"), self._settings.value("mutate/splitter")
        if geometry is not None:
            self.restoreGeometry(geometry)
        if splitter is not None:
            self.splitter.restoreState(splitter)
        else:
            self.splitter.setSizes([800, SIDE_WIDTH])
        self.mutate_panel.load(self._settings, "mutate")
        self.breed_panel.load(self._settings, "breed")
        self.explore_panel.load(self._settings, "explore")
        try:
            tab = int(self._settings.value("mutate/tab", MUTATE_TAB))
        except (TypeError, ValueError):
            tab = MUTATE_TAB
        self.tabs.blockSignals(True)
        self.tabs.setCurrentIndex(tab if tab in (MUTATE_TAB, BREED_TAB, EXPLORE_TAB) else MUTATE_TAB)
        self.tabs.blockSignals(False)


def caption(child: Offspring) -> str:
    """A cell's caption: the first change made (shortened)."""
    return child.notes[0] if child.notes else "a copy"


def tooltip(child: Offspring) -> str:
    """A cell's tooltip: every change, one per line."""
    return "\n".join([child.flame.name] + [f"• {note}" for note in child.notes])


__all__ = ["MutationWindow", "OFFSPRING_CELLS", "caption", "tooltip"]
