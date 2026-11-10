"""The explicit state machines (Qt-free): the primitive, every spec's integrity, the generated docs, and the render
control that a Stop → Pause sequence used to hang."""

import logging
import subprocess
import sys
import threading
from enum import StrEnum
from pathlib import Path

import pytest

from fractalchemy.machines import (ALL, BUILD, JOB, OFFSPRING, PLAYBACK, IllegalTransition, JobState, MachineSpec, is_strict,
                                   set_strict)
from fractalchemy.render.control import RenderControl

ROOT = Path(__file__).resolve().parents[1]


class Light(StrEnum):
    OFF = "off"
    ON = "on"
    BROKEN = "broken"


LIGHT = MachineSpec("Light", Light, Light.OFF, {(Light.OFF, "switch"): Light.ON, (Light.ON, "switch"): Light.OFF,
                                                (Light.ON, "burn"): Light.BROKEN},
                    meanings={Light.OFF: "dark", Light.ON: "lit", Light.BROKEN: "needs a new bulb"})


def test_a_machine_steps_records_and_notifies():
    machine = LIGHT.new("hall")
    seen = []
    machine.on_change(seen.append)
    assert machine.state == Light.OFF == "off" and machine.can("switch") and not machine.can("burn")
    assert machine.fire("switch", "evening") and machine.state is Light.ON
    assert machine.allowed() == ["switch", "burn"] and machine.is_in(Light.ON, Light.BROKEN)
    assert [(s.before, s.event, s.after, s.note) for s in seen] == [(Light.OFF, "switch", Light.ON, "evening")]
    assert list(machine.history) == seen
    assert machine.describe() == "hall: on — lit [accepts: switch, burn]"


def test_illegal_events_raise_in_strict_mode_and_are_refused_otherwise(caplog):
    machine = LIGHT.new("hall")
    assert is_strict()                                          # the test-suite runs strict (conftest)
    with pytest.raises(IllegalTransition, match="'burn' is not allowed in state 'off'"):
        machine.fire("burn")
    set_strict(False)
    try:
        with caplog.at_level(logging.WARNING):
            assert not machine.fire("burn")
        assert machine.state is Light.OFF and "not allowed" in caplog.text
    finally:
        set_strict(True)
    assert not machine.fire_if("burn") and machine.state is Light.OFF   # fire_if: only when allowed, silently


def test_specs_validate_themselves():
    with pytest.raises(ValueError, match="unreachable"):
        MachineSpec("Broken", Light, Light.OFF, {(Light.OFF, "switch"): Light.ON})
    with pytest.raises(ValueError, match="is not a Light"):
        MachineSpec("Wrong", Light, Light.OFF, {(Light.OFF, "switch"): "on-ish", (Light.OFF, "x"): Light.ON,
                                                (Light.ON, "y"): Light.BROKEN})
    assert LIGHT.events() == ["switch", "burn"] and ("on", "burn", "broken") in LIGHT.table()
    assert LIGHT.mermaid().splitlines()[:2] == ["stateDiagram-v2", "    [*] --> off"]


@pytest.mark.parametrize("spec", ALL, ids=lambda s: s.name)
def test_every_application_machine_is_complete(spec):
    assert spec.reachable() == set(spec.states)
    assert set(spec.meanings) == set(spec.states) and all(spec.meanings.values())
    assert spec.owner and spec.doc
    for state in spec.states:                                   # no state is a dead end
        assert any(source == state for (source, _event) in spec.transitions), state


def test_the_render_job_cannot_pause_while_stopping():
    job = JOB.new()
    for event in ("start", "pause", "stop"):
        job.fire(event)
    assert job.state is JobState.STOPPING and job.allowed() == ["finished"]
    assert not job.can("pause") and not job.can("resume")


def test_machine_sequences_of_the_owners():
    build = BUILD.new()
    for event, expected in (("built", "built"), ("edit", "stale"), ("rejected", "failed"), ("edit", "failed"), ("built", "built")):
        build.fire(event)
        assert build.state == expected
    playback = PLAYBACK.new()
    for event, expected in (("play", "playing"), ("pause", "paused"), ("play", "playing"), ("ended", "stopped"), ("stop", "stopped")):
        playback.fire(event)
        assert playback.state == expected
    offspring = OFFSPRING.new()
    for event, expected in (("generate", "generating"), ("changed", "stale"), ("made", "stale"), ("generate", "generating"),
                            ("made", "ready"), ("no_fractal", "empty")):
        offspring.fire(event)
        assert offspring.state == expected


def test_pausing_a_cancelled_render_never_blocks_its_thread():
    """The Stop → Pause hang, at the lowest level: a cancelled control ignores pause, so the thread always gets out."""
    control = RenderControl()
    control.cancel()
    control.pause()
    assert not control.paused
    done = threading.Event()
    threading.Thread(target=lambda: (control.wait_if_paused(), done.set()), daemon=True).start()
    assert done.wait(2.0)


def test_the_state_machine_document_is_current():
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "state_machines.py"), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    text = (ROOT / "docs" / "state-machines.md").read_text(encoding="utf-8")
    assert all(f"### {spec.name}" in text for spec in ALL)
