"""Every explicit state machine of the application, in one place.

Each spec says what its states mean and which events move between them; the owner (named in `owner`) holds a
`Machine` of it and derives its buttons, labels and public properties from the machine's state. `docs/state-machines.md`
is written from these specs by `tools/state_machines.py` (a test keeps it current), together with the inventory of the
implicit machines that were deliberately left as they are, and why.
"""

from __future__ import annotations

from enum import StrEnum

from .core import MachineSpec


# --- background jobs with Start / Pause / Stop (the four render windows) ---------------------------------------------
class JobState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"


J = JobState
JOB = MachineSpec(
    "Render job", JobState, J.IDLE,
    {
        (J.IDLE, "start"): J.RUNNING,
        (J.RUNNING, "pause"): J.PAUSED,
        (J.PAUSED, "resume"): J.RUNNING,
        (J.RUNNING, "stop"): J.STOPPING,
        (J.PAUSED, "stop"): J.STOPPING,
        (J.RUNNING, "finished"): J.IDLE,
        (J.PAUSED, "finished"): J.IDLE,
        (J.STOPPING, "finished"): J.IDLE,
    },
    meanings={
        J.IDLE: "no job: the options can be edited, Start is enabled (when the options are valid)",
        J.RUNNING: "the job's thread is working: Pause and Stop are enabled, the options are locked",
        J.PAUSED: "the job waits between chunks of work: Resume and Stop are enabled",
        J.STOPPING: "Stop was pressed and the job is winding down: nothing else can be done until its thread ends",
    },
    owner="ui/job_window.py: JobWindowBase (Render Image, Render Animation, Render 3D Image, Render Fragment)",
    doc="The life of one background render started from a job window. Pause is not an event of *stopping*: pausing a "
        "cancelled job used to leave its thread waiting for a resume that never came.",
)


# --- a script run in the Script Editor ---------------------------------------------------------------------------------
class ScriptState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    STOPPING = "stopping"
    RERUNNING = "rerunning"
    SUPERSEDED = "superseded"


S = ScriptState
SCRIPT_RUN = MachineSpec(
    "Script run", ScriptState, S.IDLE,
    {
        (S.IDLE, "run"): S.RUNNING,
        (S.RUNNING, "wait"): S.WAITING,
        (S.WAITING, "rendered"): S.RUNNING,
        (S.RUNNING, "stop"): S.STOPPING,
        (S.WAITING, "stop"): S.STOPPING,
        (S.RUNNING, "finished"): S.IDLE,
        (S.WAITING, "finished"): S.IDLE,
        (S.STOPPING, "finished"): S.IDLE,
        (S.IDLE, "rerun"): S.RERUNNING,
        (S.RERUNNING, "finished"): S.IDLE,
        (S.RERUNNING, "stop"): S.STOPPING,
        (S.RERUNNING, "run"): S.SUPERSEDED,
        (S.SUPERSEDED, "finished"): S.IDLE,
        (S.SUPERSEDED, "stop"): S.STOPPING,
    },
    meanings={
        S.IDLE: "no script is running: Run is enabled",
        S.RUNNING: "the script's thread runs against a copy of the fractal: Stop is enabled",
        S.WAITING: "the script called update(wait=True): the main viewport is rendering the intermediate fractal",
        S.STOPPING: "Stop was pressed: the script ends at its next line (or at once when it waits for input)",
        S.RERUNNING: "a live parameter re-run is on the worker (restricted: no prompts, updates or files); Run stays enabled "
                     "and supersedes it, Stop appears only when the re-run is slow",
        S.SUPERSEDED: "Run was pressed during a re-run: the re-run is being stopped and the requested Run starts when its result "
                      "(discarded) arrives",
    },
    owner="ui/script_editor_window.py: ScriptEditorWindow",
    doc="One run from Run to its result. The run ends when the window has *processed* the result, not when the thread "
        "exits, so a second Run cannot start while the first one's result is still on its way.",
)


# --- the Script Editor's live parameters -------------------------------------------------------------------------------
class LiveState(StrEnum):
    OFF = "off"
    READY = "ready"
    PENDING = "pending"
    RERUNNING = "rerunning"
    QUEUED = "queued"
    INERT = "inert"
    DETACHED = "detached"


L = LiveState
_ANY_LIVE = tuple(LiveState)
_LIVE_SESSION = (L.READY, L.PENDING, L.RERUNNING, L.QUEUED)
LIVE_PARAMS = MachineSpec(
    "Live parameters", LiveState, L.OFF,
    {
        **{(s, "declared_live"): L.READY for s in _ANY_LIVE},
        **{(s, "declared_inert"): L.INERT for s in _ANY_LIVE},
        **{(s, "declared_none"): L.OFF for s in _ANY_LIVE},
        **{(s, "run"): L.OFF for s in _ANY_LIVE},
        **{(s, "unload"): L.OFF for s in _ANY_LIVE},
        **{(s, "detach"): L.DETACHED for s in _LIVE_SESSION},
        (L.READY, "changed"): L.PENDING,
        (L.PENDING, "changed"): L.PENDING,
        (L.RERUNNING, "changed"): L.QUEUED,
        (L.QUEUED, "changed"): L.QUEUED,
        (L.OFF, "changed"): L.OFF,
        (L.INERT, "changed"): L.INERT,
        (L.DETACHED, "changed"): L.DETACHED,
        (L.PENDING, "settle"): L.RERUNNING,
        (L.RERUNNING, "finished"): L.READY,
        (L.QUEUED, "finished"): L.RERUNNING,
        (L.RERUNNING, "refused"): L.INERT,
        (L.QUEUED, "refused"): L.INERT,
    },
    meanings={
        L.OFF: "no live session: the controls (if a run declared any) only set the values the next Run uses",
        L.READY: "the last run declared parameters and may re-run: moving a control re-runs it from the pre-run snapshot",
        L.PENDING: "a control moved: the re-run starts once it has been still for a moment (the debounce)",
        L.RERUNNING: "a re-run is on the worker; its result replaces the fractal (same undo step)",
        L.QUEUED: "a control moved during a re-run: one more re-run follows with the latest values",
        L.INERT: "the script has side effects (prompts, messages, update / sleep, files, imports): its controls set the "
                 "values, Run applies them",
        L.DETACHED: "the fractal was changed in another way after the run: re-running from the old snapshot would undo that, "
                    "so the controls wait for the next Run",
    },
    owner="ui/script_live.py: LiveParameters (the Script Editor)",
    doc="Blender's *Adjust Last Operation*, for scripts: a live session belongs to the last run and ends as soon as "
        "anything else changes the fractal. Latest value wins: changes during a re-run queue exactly one more.",
)


# --- the Mutate & Breed window's offspring ---------------------------------------------------------------------------
class OffspringState(StrEnum):
    STALE = "stale"
    EMPTY = "empty"
    NEEDS_PARENT = "needs_parent"
    NEEDS_SCRIPT = "needs_script"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


O = OffspringState
_ANY_OFFSPRING = tuple(OffspringState)
OFFSPRING = MachineSpec(
    "Mutate & Breed offspring", OffspringState, O.STALE,
    {
        **{(s, "generate"): O.GENERATING for s in _ANY_OFFSPRING},
        **{(s, "no_fractal"): O.EMPTY for s in _ANY_OFFSPRING},
        **{(s, "no_second_parent"): O.NEEDS_PARENT for s in _ANY_OFFSPRING},
        **{(s, "no_script"): O.NEEDS_SCRIPT for s in _ANY_OFFSPRING},
        **{(s, "changed"): O.STALE for s in _ANY_OFFSPRING},
        (O.GENERATING, "made"): O.READY,
        (O.GENERATING, "failed"): O.FAILED,
        (O.STALE, "made"): O.STALE,
        (O.STALE, "failed"): O.STALE,
    },
    meanings={
        O.STALE: "the parent or the options changed: new offspring are made once the edits pause (or when the window "
                 "is shown); results still arriving for the old parent are shown meanwhile",
        O.EMPTY: "the main window shows no fractal: there is nothing to mutate",
        O.NEEDS_PARENT: "the Breed tab is showing and there is no second parent (B) yet",
        O.NEEDS_SCRIPT: "the Explore script tab is showing and the Script Editor has no live script with parameters",
        O.GENERATING: "offspring are being made on the thread pool",
        O.READY: "eight offspring are shown: click one (or press its number) to make it the fractal",
        O.FAILED: "making offspring raised an error (shown across the grid)",
    },
    owner="ui/mutation_window.py: MutationWindow",
    doc="What the grid shows. Every regeneration decides between *empty*, *needs_parent* / *needs_script* and *generating*; a change "
        "in the main window or the options makes the grid *stale*. Adopting a cell is not a state: it is one undoable "
        "edit followed by a regeneration.",
)


# --- a fragment tab's program ----------------------------------------------------------------------------------------
class BuildState(StrEnum):
    STALE = "stale"
    BUILT = "built"
    FAILED = "failed"


B = BuildState
BUILD = MachineSpec(
    "Fragment build", BuildState, B.STALE,
    {
        (B.STALE, "edit"): B.STALE,
        (B.BUILT, "edit"): B.STALE,
        (B.FAILED, "edit"): B.FAILED,
        (B.STALE, "built"): B.BUILT,
        (B.BUILT, "built"): B.BUILT,
        (B.FAILED, "built"): B.BUILT,
        (B.STALE, "rejected"): B.FAILED,
        (B.BUILT, "rejected"): B.FAILED,
        (B.FAILED, "rejected"): B.FAILED,
    },
    meanings={
        B.STALE: "the source, a lock or a build option changed since the shown program was built: *Build needed*",
        B.BUILT: "the shown program is the current source",
        B.FAILED: "the last build was rejected (preprocessor, translator or driver): *Build failed*; the previous "
                  "program, if any, keeps rendering",
    },
    owner="ui/fragments/document.py: FragDocument",
    doc="Replaces the two flags `needs_build` / `build_failed_last` (whose fourth combination was impossible); both "
        "remain as properties derived from the state.",
)


# --- animation playback in the Animation window ----------------------------------------------------------------------
class PlaybackState(StrEnum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


P = PlaybackState
PLAYBACK = MachineSpec(
    "Animation playback", PlaybackState, P.STOPPED,
    {
        (P.STOPPED, "play"): P.PLAYING,
        (P.PAUSED, "play"): P.PLAYING,
        (P.PLAYING, "play"): P.PLAYING,          # Play while playing re-anchors the clock at the playhead
        (P.PLAYING, "pause"): P.PAUSED,
        (P.STOPPED, "stop"): P.STOPPED,
        (P.PLAYING, "stop"): P.STOPPED,
        (P.PAUSED, "stop"): P.STOPPED,
        (P.PLAYING, "ended"): P.STOPPED,
    },
    meanings={
        P.STOPPED: "no playback session: Play starts one from the playhead",
        P.PLAYING: "the playhead advances with the wall clock (frames are dropped when the engine is slower)",
        P.PAUSED: "the session holds its place: Play resumes, Stop returns to where playback started",
    },
    owner="ui/animation_playback.py: Playback",
    doc="Replaces `QTimer.isActive()` plus a `_session` flag; `playing` and `in_session` remain as derived properties.",
)


# --- the Fragments render queue --------------------------------------------------------------------------------------
class QueueState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"


Q = QueueState
RENDER_QUEUE = MachineSpec(
    "Render queue", QueueState, Q.IDLE,
    {
        (Q.IDLE, "start"): Q.RUNNING,
        (Q.RUNNING, "start"): Q.RUNNING,
        (Q.STOPPING, "start"): Q.RUNNING,
        (Q.RUNNING, "stop"): Q.STOPPING,
        (Q.RUNNING, "emptied"): Q.IDLE,
        (Q.STOPPING, "drained"): Q.IDLE,
    },
    meanings={
        Q.IDLE: "nothing renders: entries can be added, removed and started",
        Q.RUNNING: "the waiting entries render one after another",
        Q.STOPPING: "Stop was pressed: the current entry is cancelled and the rest stay waiting",
    },
    owner="ui/fragments/render_queue.py: RenderQueueWindow",
    doc="The queue as a whole (each entry has its own waiting / rendering / done / failed / stopped label). Replaces a "
        "`_running` flag whose meaning depended on whether a job object happened to exist.",
)


ALL: tuple[MachineSpec, ...] = (JOB, SCRIPT_RUN, LIVE_PARAMS, OFFSPRING, BUILD, PLAYBACK, RENDER_QUEUE)

__all__ = ["ALL", "JOB", "SCRIPT_RUN", "LIVE_PARAMS", "OFFSPRING", "BUILD", "PLAYBACK", "RENDER_QUEUE", "JobState", "ScriptState",
           "LiveState", "OffspringState", "BuildState", "PlaybackState", "QueueState"]
