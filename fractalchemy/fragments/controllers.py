"""Sliders driven by a MIDI controller or a gamepad: the device protocols and the mapping, Qt-free.

No library is needed: on Linux a joystick is `/dev/input/js*` (the kernel's joystick API — 8-byte events of time,
value, type, number) and a MIDI port is `/dev/midi*` or `/dev/snd/midiC*D*` (raw MIDI bytes; control changes are
`0xBn cc value`). `parse_joystick_events` and `MidiParser` turn the bytes into `Control` events; a `ControlMapping`
binds a control (`axis 2`, `cc 74`, `button 1`) to a slider component (`Power1`) either **absolutely** — a knob at
0..127 or a trigger at −1..1 spans the slider's range — or **relatively** — a stick's deflection moves the value at
a speed, so it rests where you leave it. The mapping lives in the `.fafrag` metadata (`tabs.controllers`); the
window's `controller_input.py` reads the devices on a thread and applies the values.
"""

from __future__ import annotations

import glob
import struct
from dataclasses import asdict, dataclass, field

JS_EVENT = struct.Struct("IhBB")          # time ms, value, type, number
JS_EVENT_BUTTON, JS_EVENT_AXIS, JS_EVENT_INIT = 0x01, 0x02, 0x80
MODES = ("absolute", "relative")
KINDS = ("axis", "button", "cc")


@dataclass(frozen=True)
class Control:
    """One event from a device.

    Attributes:
        kind: `axis` (−1..1), `button` (0 / 1) or `cc` (0..1 from 0..127).
        number: The axis / button / controller number.
        value: Normalised as above.
        channel: The MIDI channel (0 for joysticks).
    """
    kind: str
    number: int
    value: float
    channel: int = 0

    @property
    def key(self) -> str:
        return f"{self.kind} {self.number}"


def parse_joystick_events(data: bytes) -> tuple[list[Control], bytes]:
    """Every complete joystick event in `data` (the kernel's `struct js_event`) and the leftover bytes."""
    out = []
    count = len(data) // JS_EVENT.size
    for i in range(count):
        _time, value, kind, number = JS_EVENT.unpack_from(data, i * JS_EVENT.size)
        kind &= ~JS_EVENT_INIT
        if kind == JS_EVENT_AXIS:
            out.append(Control("axis", number, max(-1.0, min(1.0, value / 32767.0))))
        elif kind == JS_EVENT_BUTTON:
            out.append(Control("button", number, 1.0 if value else 0.0))
    return out, data[count * JS_EVENT.size:]


class MidiParser:
    """Raw MIDI bytes → control-change events (running status handled; other messages skipped)."""

    def __init__(self):
        self._status = 0
        self._pending: list[int] = []

    def feed(self, data: bytes) -> list[Control]:
        out = []
        for byte in data:
            if byte >= 0xF8:
                continue                                   # real-time messages never interrupt a running message
            if byte & 0x80:
                self._status, self._pending = byte, []
                continue
            self._pending.append(byte)
            message = self._status & 0xF0
            if message == 0xB0 and len(self._pending) == 2:
                cc, value = self._pending
                out.append(Control("cc", cc, value / 127.0, self._status & 0x0F))
                self._pending = []
            elif message in (0x80, 0x90, 0xA0, 0xE0) and len(self._pending) == 2:
                self._pending = []
            elif message in (0xC0, 0xD0) and len(self._pending) == 1:
                self._pending = []
            elif message == 0xF0:
                self._pending = []
        return out


def discover_devices() -> list[tuple[str, str]]:
    """`(kind, path)` of the joystick and raw MIDI device files present (Linux; empty elsewhere)."""
    found = [("joystick", path) for path in sorted(glob.glob("/dev/input/js*"))]
    found += [("midi", path) for path in sorted(glob.glob("/dev/midi*")) + sorted(glob.glob("/dev/snd/midiC*D*"))]
    return found


@dataclass
class Binding:
    """What a control drives.

    Attributes:
        slider: The slider component (`Power1`, `JuliaC2`).
        mode: `absolute` (the control's position spans the range) or `relative` (deflection moves the value).
        speed: Relative mode: ranges per second at full deflection.
        invert: Reverse the direction.
    """
    slider: str
    mode: str = "absolute"
    speed: float = 0.25
    invert: bool = False


@dataclass
class ControlMapping:
    """Control key (`axis 2`, `cc 74`) → binding; persisted as a plain dict."""
    bindings: dict[str, Binding] = field(default_factory=dict)

    def bind(self, control_key: str, binding: Binding) -> None:
        self.bindings[control_key] = binding

    def unbind(self, control_key: str) -> None:
        self.bindings.pop(control_key, None)

    def for_control(self, control: Control) -> Binding | None:
        return self.bindings.get(control.key)

    def to_dict(self) -> dict:
        return {key: asdict(binding) for key, binding in self.bindings.items()}

    @classmethod
    def from_dict(cls, data: dict | None) -> "ControlMapping":
        mapping = cls()
        for key, value in (data or {}).items():
            if isinstance(value, dict) and value.get("slider"):
                mode = value.get("mode", "absolute")
                mapping.bindings[str(key)] = Binding(str(value["slider"]), mode if mode in MODES else "absolute",
                                                     float(value.get("speed", 0.25)), bool(value.get("invert", False)))
        return mapping


def apply_control(binding: Binding, control: Control, current: float, low: float, high: float, dt: float) -> float:
    """The slider's new value for `control` (`dt`: seconds since the last relative step)."""
    value = control.value
    if binding.invert:
        value = -value if control.kind == "axis" else 1.0 - value
    span = high - low
    if binding.mode == "absolute":
        fraction = (value + 1.0) / 2.0 if control.kind == "axis" else value
        return low + max(0.0, min(1.0, fraction)) * span
    deflection = value if control.kind == "axis" else value * 2.0 - 1.0
    if abs(deflection) < 0.08:
        return current                                     # the stick's dead zone
    return max(min(low, high), min(max(low, high), current + deflection * binding.speed * span * dt))


__all__ = ["Control", "Binding", "ControlMapping", "MidiParser", "parse_joystick_events", "discover_devices", "apply_control", "MODES", "KINDS"]
