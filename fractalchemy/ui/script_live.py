"""Live parameters: the Script Editor's controls for a script's `param()` declarations, and the re-runs they drive.

A helper of `ScriptEditorWindow` (it holds the window as `w`). After a run that declared parameters it keeps a
*session*: the code that ran (frozen — edits in the editor do not change what the controls drive until the next Run),
the fractal as it was before the run (the snapshot), the run's undo token, its seed and the declarations. Moving a
control re-runs that code on the snapshot with the new values, restricted (no prompts, messages, `update()`, `sleep()`
or files — `api.LiveRefused`), and the result replaces the fractal through `apply_script` with the *same* token: the
whole session is the one undo step the run recorded. The lifecycle is `machines.LIVE_PARAMS`:

* a control moves → *pending*; `config.SCRIPT_LIVE_DEBOUNCE_MS` later (at once on a slider release) → *re-running*;
  more changes meanwhile → *queued* (exactly one more re-run, with the latest values);
* a re-run that refuses a side effect makes the session *inert*; a script with side effects in plain sight (imports,
  `open()` …) is inert from the start: its controls still set the values the next Run uses;
* any other change of the fractal (an Inspector slider, Undo, another fractal) *detaches* the session (Blender's
  *Adjust Last Operation*): re-running from the old snapshot would silently undo that change;
* re-runs slower than `config.SCRIPT_LIVE_SLOW_MS` switch the controls to *apply on release*.

The values the user changed (*touched*) persist with the draft (`script/parameters`) and feed every Run; untouched
parameters take whatever default the code declares. The class also serves the Mutate & Breed window's *Explore script*
tab and the Parameters tab's *Animate…* (`ScriptExploreSource`).
"""

from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QTextCursor

from .. import config
from ..fractal.scene import Flame
from ..machines import LIVE_PARAMS, LiveState
from ..scripting.parameters import ParamSpec, bake_defaults, coerce, live_blockers
from ..scripting.runner import ScriptResult

if TYPE_CHECKING:
    from .script_editor_window import ScriptEditorWindow

LIVE_RESTRICTION = "while its controls update live"
VALUES_KEY = "script/parameters"
ORIGIN_EDITOR = "editor"


class LiveSession:
    """What a live session re-runs: the frozen code, the snapshot, the undo token, the seed, the declarations."""

    def __init__(self, code: str, snapshot: Flame | None, token: object, seed: int, name: str, origin: str):
        self.code = code
        self.snapshot = snapshot
        self.token = token
        self.seed = seed
        self.name = name
        self.origin = origin
        self.specs: list[ParamSpec] = []
        self.slow = False


class LiveParameters(QObject):
    """The live-parameter coordinator (see the module docstring).

    Signals:
        changed(): The declarations, values or state changed (the Mutate & Breed window's Explore tab listens).
    """
    changed = Signal()

    def __init__(self, window: "ScriptEditorWindow"):
        super().__init__(window)
        self.w = window
        self.tab = window.drawer.parameters
        self.machine = LIVE_PARAMS.new("Script Editor")
        self.machine.on_change(lambda _step: self._show_state())
        self.session: LiveSession | None = None
        self.specs: list[ParamSpec] = []             # the rows shown (from the last run that declared any)
        self.values: dict[str, Any] = {}
        self.touched: set[str] = set()
        self.keep_seed = False
        self.reason = ""
        self._applying = False
        self._buffer = ""
        self._debounce = QTimer(self, singleShot=True, interval=config.SCRIPT_LIVE_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._settle)
        self._busy = QTimer(self, singleShot=True, interval=config.SCRIPT_LIVE_BUSY_MS)
        self._busy.timeout.connect(self._show_busy)
        self._load_values()
        self._connect()
        self._show_state()

    def _connect(self) -> None:
        tab = self.tab
        tab.value_changed.connect(self.set_value)
        tab.reset_requested.connect(self.reset)
        tab.bake_requested.connect(self.bake)
        tab.reseed_requested.connect(self.reseed)
        tab.keep_seed_toggled.connect(self._set_keep_seed)
        tab.goto_line.connect(lambda line: self.w.editor.goto_line(line))
        tab.insert_example.connect(lambda: self.w.editor.insert_snippet(self.w.example_param_line()))
        self.w.document.edited.connect(self._on_document_edited)

    # --- state ----------------------------------------------------------------------------------------------------------
    @property
    def state(self) -> LiveState:
        return self.machine.state

    @property
    def live(self) -> bool:
        """True while moving a control re-runs the script."""
        return self.machine.state in (LiveState.READY, LiveState.PENDING, LiveState.RERUNNING, LiveState.QUEUED)

    def _show_state(self) -> None:
        self.tab.set_state(self.machine.state, self._reason_text())
        self.changed.emit()

    def _reason_text(self) -> str:
        state = self.machine.state
        if state == LiveState.INERT:
            return f"{self.reason} — the controls set the values, Run applies them"
        if state == LiveState.DETACHED:
            return "the fractal was changed after the run: press Run to apply the script again with these values"
        if state in (LiveState.READY, LiveState.PENDING) and self.session is not None and self.session.slow:
            return "slow script: changes apply when you let go of a control"
        return ""

    def _show_busy(self) -> None:
        self._busy_shown = True
        self.tab.set_busy(True)
        self.w.show_run_state()

    @property
    def busy(self) -> bool:
        """A re-run has been on the worker for longer than `SCRIPT_LIVE_BUSY_MS` (Stop and "Updating…" show)."""
        return self._rerunning and self._busy_shown

    _rerunning = False
    _busy_shown = False

    # --- values ---------------------------------------------------------------------------------------------------------
    def values_for_run(self) -> dict[str, Any]:
        """The values a Run passes to `param()`: the ones the user changed."""
        return {name: self.values[name] for name in self.touched if name in self.values}

    def set_value(self, name: str, value: Any, final: bool = True) -> None:
        """A control moved (or a caller sets a value): remember it and, while live, re-run."""
        spec = next((s for s in self.specs if s.name == name), None)
        if spec is None:
            return
        value = coerce(spec, value)
        self.values[name] = value
        if value == spec.default:
            self.touched.discard(name)
        else:
            self.touched.add(name)
        self._save_values()
        self.tab.set_specs(self.specs, self.values, self.touched)
        self._request_rerun(final)

    def set_values(self, values: dict[str, Any], seed: int | None = None) -> None:
        """Set several values at once (and the seed) and re-run once — the explorer grid's *adopt*."""
        for spec in self.specs:
            if spec.name in values:
                self.values[spec.name] = coerce(spec, values[spec.name])
                if self.values[spec.name] == spec.default:
                    self.touched.discard(spec.name)
                else:
                    self.touched.add(spec.name)
        if seed is not None and self.session is not None:
            self.session.seed = seed
            self.tab.set_seed(seed, self.keep_seed)
        self._save_values()
        self.tab.set_specs(self.specs, self.values, self.touched)
        self._request_rerun(True)

    def _request_rerun(self, final: bool) -> None:
        self.machine.fire_if("changed")
        if self.machine.state != LiveState.PENDING:
            return
        if self.session is not None and self.session.slow and not final:
            return                                          # slow scripts: only a release re-runs
        self._debounce.start(0 if final and self.session is not None and self.session.slow else config.SCRIPT_LIVE_DEBOUNCE_MS)

    def reset(self, name: str | None) -> None:
        """Back to the declared default (one parameter, or all)."""
        for spec in self.specs:
            if name is None or spec.name == name:
                self.values[spec.name] = spec.default
                self.touched.discard(spec.name)
        self._save_values()
        self.tab.set_specs(self.specs, self.values, self.touched)
        self._request_rerun(True)

    def reseed(self) -> None:
        """New random numbers for the session (and a re-run)."""
        if self.session is not None:
            self.session.seed = random.getrandbits(32)
            self.tab.set_seed(self.session.seed, self.keep_seed)
            self._request_rerun(True)

    def _set_keep_seed(self, keep: bool) -> None:
        self.keep_seed = keep

    def seed_for_run(self) -> int:
        """The seed of the next Run: the session's with *Keep seed on Run*, else a new one."""
        if self.keep_seed and self.session is not None:
            return self.session.seed
        return random.getrandbits(32)

    # --- the run / re-run life ---------------------------------------------------------------------------------------------
    def on_run_started(self, code: str, snapshot: Flame | None, token: object, seed: int, name: str, origin: str) -> None:
        """A full Run began: the old session ends; this run's result decides the next one."""
        self._debounce.stop()
        self.machine.fire("run")
        self.session = LiveSession(code, snapshot, token, seed, name, origin)
        self.tab.set_error("")
        self.tab.set_seed(seed, self.keep_seed)
        self.refresh_code_changed()

    def on_run_finished(self, result: ScriptResult) -> None:
        """A full Run's result: show its declarations and decide whether the session is live."""
        session = self.session
        if session is None:
            return
        if result.declarations:
            self._adopt_specs(list(result.declarations), result.values)
        if not result.ok:
            self.machine.fire("declared_none")
            self.tab.set_state(self.machine.state, "the last run failed: fix the script and run it again")
            return
        if not result.declarations:
            if self.specs:
                self.specs = []
                self.tab.set_specs([], {}, set())
            self.machine.fire("declared_none")
            return
        blockers = live_blockers(session.code)
        blocked = sorted(result.effects & {"prompt", "message", "update", "sleep", "write"})
        if blockers:
            self.reason = f"not live: {blockers[0]}"
            self.machine.fire("declared_inert")
        elif blocked:
            self.reason = f"not live: the script {', '.join(_EFFECT_WORDS[e] for e in blocked)}"
            self.machine.fire("declared_inert")
        else:
            self.reason = ""
            self.machine.fire("declared_live")
        session.slow = result.seconds * 1000 > config.SCRIPT_LIVE_SLOW_MS
        self._show_state()
        if self.w.auto_show_parameters():                    # the first time a script declares parameters
            self.w.show_tab("parameters")

    def _adopt_specs(self, specs: list[ParamSpec], used: dict[str, Any]) -> None:
        """The declarations of a run: keep touched values that still fit, take the run's values for the rest."""
        self.specs = specs
        for spec in specs:
            if spec.name in self.touched and spec.name in self.values:
                self.values[spec.name] = coerce(spec, self.values[spec.name])
            else:
                self.values[spec.name] = used.get(spec.name, spec.default)
                self.touched.discard(spec.name)
        self.tab.set_specs(specs, self.values, self.touched)

    def _settle(self) -> None:
        session = self.session
        if session is None or not self.machine.fire_if("settle"):
            return
        self._start_rerun()

    def _start_rerun(self) -> None:
        session = self.session
        self._buffer = ""
        self._rerunning = True
        self._busy.start()
        self.w.start_rerun(session.code, session.snapshot, session.seed, dict(self.values), LIVE_RESTRICTION)

    def collect_output(self, text: str) -> None:
        """`print` output of a re-run (shown in the output's live section when the re-run ends)."""
        self._buffer += text

    def on_rerun_finished(self, result: ScriptResult) -> None:
        """A re-run's result: apply it (same undo step) unless the session moved on meanwhile."""
        self._rerunning = False
        self._busy_shown = False
        self._busy.stop()
        self.tab.set_busy(False)
        if self.machine.state not in (LiveState.RERUNNING, LiveState.QUEUED) or self.session is None:
            return                                         # detached, or a Run superseded it: the result is stale
        session = self.session
        if result.refused:
            self.reason = f"not live: {result.refused}"
            self.machine.fire("refused")
            self.w.output.replace_live_section(self._buffer, f"↻ Not applied: {result.refused}", "info")
            return
        summary = " · ".join(f"{name} = {_show(self.values.get(name))}" for name in (s.name for s in self.specs))
        if result.ok and not result.user_stopped:
            if result.declarations and list(result.declarations) != self.specs:
                self._adopt_specs(list(result.declarations), result.values)
            if result.flame is not None:
                self._applying = True
                try:
                    self.w.document.apply_script(result.flame, session.token, label=self.w.run_label(session.name), interactive=True)
                finally:
                    self._applying = False
            self.tab.set_error("")
            self.w.output.replace_live_section(self._buffer, f"↻ Live: {summary} — {result.seconds * 1000:.0f} ms", "info")
            session.slow = session.slow or result.seconds * 1000 > config.SCRIPT_LIVE_SLOW_MS
        elif result.error is not None:
            error = result.error
            self.tab.set_error(f"{summary} → {error}; the fractal shows the last good values")
            self.w.output.replace_live_section(self._buffer, f"✖ {error}", "error", error.line)
        self.machine.fire("finished")
        self._show_state()
        if self.machine.state == LiveState.RERUNNING:      # a change arrived meanwhile: one more, with the latest values
            self._start_rerun()

    def _on_document_edited(self, kind: str) -> None:
        """Anything but our own re-runs changed the fractal: the session can no longer re-run from its snapshot."""
        if self._applying or not self.live:
            return
        was_running = self.machine.state in (LiveState.RERUNNING, LiveState.QUEUED)
        self._debounce.stop()
        self.machine.fire("detach")
        if was_running:
            self.w.stop()

    def unload(self) -> None:
        """Another script was loaded: forget the session, the rows and the values."""
        self._debounce.stop()
        self.machine.fire("unload")
        self.session = None
        self.specs, self.values, self.touched = [], {}, set()
        self._save_values()
        self.tab.set_specs([], {}, set())
        self.tab.set_error("")
        self.tab.set_code_changed(False)

    def stop_requested(self) -> None:
        """Stop during a re-run: the session stays (the next change re-runs again)."""
        self._debounce.stop()

    def superseded(self) -> None:
        """A Run was pressed during a re-run."""
        self._debounce.stop()

    # --- the code -------------------------------------------------------------------------------------------------------
    def refresh_code_changed(self) -> None:
        session = self.session
        changed = (session is not None and session.origin == ORIGIN_EDITOR and bool(self.specs)
                   and self.w.editor.text() != session.code)
        self.tab.set_code_changed(changed)

    def bake(self) -> list[str]:
        """*Set as defaults in script*: write the changed values into the `param()` calls (one editor undo step)."""
        values = self.values_for_run()
        if not values:
            return []
        code = self.w.editor.text()
        new_code, skipped = bake_defaults(code, values)
        if new_code != code:
            cursor = self.w.editor.textCursor()
            cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(new_code)
            cursor.endEditBlock()
        for spec in list(self.specs):
            if spec.name in values and spec.name not in skipped:
                self.specs[self.specs.index(spec)] = _with_default(spec, values[spec.name])
                self.touched.discard(spec.name)
        if self.session is not None and self.session.origin == ORIGIN_EDITOR:
            self.session.code = new_code if self.session.code == code else self.session.code
        self._save_values()
        self.tab.set_specs(self.specs, self.values, self.touched)
        self.refresh_code_changed()
        return skipped

    # --- persistence ----------------------------------------------------------------------------------------------------
    def _save_values(self) -> None:
        data = {name: self.values[name] for name in self.touched if name in self.values}
        self.w.settings.setValue(VALUES_KEY, json.dumps(data))

    def _load_values(self) -> None:
        try:
            data = json.loads(self.w.settings.value(VALUES_KEY, "{}") or "{}")
        except (TypeError, ValueError):
            data = {}
        if isinstance(data, dict):
            self.values = dict(data)
            self.touched = set(data)

    # --- the explorer grid and animation (ScriptExploreSource) -----------------------------------------------------------
    @property
    def available(self) -> bool:
        """Whether the explorer can vary this session (it is live and declares something)."""
        return self.session is not None and self.live and bool(self.specs)

    def unavailable_reason(self) -> str:
        if self.session is None or not self.specs:
            return "Run a script that declares parameters (param(…)) in the Script Editor"
        if self.machine.state == LiveState.INERT:
            return f"The script's parameters are {self.reason}"
        if self.machine.state == LiveState.DETACHED:
            return "The fractal changed after the script ran: run it again in the Script Editor"
        return "The script is not live"

    def adopt(self, values: dict[str, Any], seed: int | None) -> None:
        """Take a grid cell's values (and seed): the Parameters tab shows them and the fractal follows."""
        if self.available:
            self.set_values(values, seed)


_EFFECT_WORDS = {"prompt": "asks questions", "message": "shows messages", "update": "calls update()", "sleep": "calls sleep()",
                 "write": "writes files"}


def _show(value) -> str:
    return f"{value:.4g}" if isinstance(value, float) else repr(value) if isinstance(value, str) else str(value)


def _with_default(spec: ParamSpec, default: Any) -> ParamSpec:
    from dataclasses import replace
    return replace(spec, default=default)


__all__ = ["LiveParameters", "LiveSession", "LIVE_RESTRICTION"]
