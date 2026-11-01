"""MIDI controllers and gamepads driving the sliders: the device reader threads, the coordinator and the mapping dialog.

A `DeviceReader` thread blocks on a device file (`fragments/controllers.py` knows the protocols) and emits `Control`
events; `ControllerCoordinator` keeps the readers, the current document's `ControlMapping` (metadata
`tabs.controllers`) and a *learn* state — choose a slider in the dialog, press *Learn*, move a knob or stick, and the
control is bound — and applies the events to the document at most every `APPLY_MS` (one undo step per burst). The
dialog lists the devices found (*Windows ▸ Controllers…*), the bindings (mode, speed, invert, remove) and the learn
controls. Devices are Linux device files; elsewhere the dialog says none were found.
"""

from __future__ import annotations

import os
import select
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QLabel, QListWidget, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ...fragments.controllers import MODES, Binding, Control, ControlMapping, MidiParser, apply_control, discover_devices, parse_joystick_events

if TYPE_CHECKING:
    from .window import FragmentsWindow

APPLY_MS = 33
MAPPING_KEY = "controllers"


class DeviceReader(QThread):
    """Reads one device file and emits its events.

    Signals:
        control(object): A `Control`.
        failed(str): The device could not be read.
    """
    control = Signal(object)
    failed = Signal(str)

    def __init__(self, kind: str, path: str, parent: QObject | None = None):
        super().__init__(parent)
        self.kind, self.path = kind, path
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:  # noqa: D401 - QThread entry point
        parser = MidiParser()
        leftover = b""
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as exc:
            self.failed.emit(f"{self.path}: {exc}")
            return
        try:
            while not self._stop:
                ready, _w, _x = select.select([fd], [], [], 0.2)
                if not ready:
                    continue
                try:
                    data = os.read(fd, 4096)
                except BlockingIOError:
                    continue
                except OSError as exc:
                    self.failed.emit(f"{self.path}: {exc}")
                    return
                if not data:
                    self.failed.emit(f"{self.path}: disconnected")
                    return
                if self.kind == "joystick":
                    events, leftover = parse_joystick_events(leftover + data)
                else:
                    events = parser.feed(data)
                for event in events:
                    self.control.emit(event)
        finally:
            os.close(fd)


class ControllerCoordinator(QObject):
    """Devices, mapping, learning and applying (see the module docstring).

    Signals:
        learned(str, str): (control key, slider) after a *Learn*.
        activity(object): Every `Control` received (the dialog shows the last one).
    """
    learned = Signal(str, str)
    activity = Signal(object)

    def __init__(self, window: "FragmentsWindow"):
        super().__init__(window)
        self.w = window
        self.readers: dict[str, DeviceReader] = {}
        self._learn_slider: str | None = None
        self._pending: dict[str, Control] = {}
        self._burst = False
        self._last_apply = time.perf_counter()
        self._timer = QTimer(self, interval=APPLY_MS)
        self._timer.timeout.connect(self._apply_pending)

    # --- devices ----------------------------------------------------------------------------------------------------------------
    def start(self, kind: str, path: str) -> bool:
        if path in self.readers:
            return True
        reader = DeviceReader(kind, path, self)
        reader.control.connect(self._on_control)
        reader.failed.connect(lambda message, p=path: self._on_failed(p, message))
        self.readers[path] = reader
        reader.start()
        if not self._timer.isActive():
            self._timer.start()
        self.w.message(f"Listening to {path}")
        return True

    def stop(self, path: str | None = None) -> None:
        for key in list(self.readers) if path is None else [path]:
            reader = self.readers.pop(key, None)
            if reader is not None:
                reader.stop()
                reader.wait(2000)
        if not self.readers:
            self._timer.stop()

    def _on_failed(self, path: str, message: str) -> None:
        self.readers.pop(path, None)
        self.w.log.add("warning", f"Controller: {message}")

    # --- mapping ------------------------------------------------------------------------------------------------------------------
    def mapping(self) -> ControlMapping:
        document = self.w.tabs.document
        return ControlMapping.from_dict(document.metadata.tabs.get(MAPPING_KEY)) if document is not None else ControlMapping()

    def set_mapping(self, mapping: ControlMapping) -> None:
        document = self.w.tabs.document
        if document is not None:
            document.set_tab_metadata(MAPPING_KEY, mapping.to_dict())

    def learn(self, slider: str | None) -> None:
        """The next control event binds to `slider` (None cancels)."""
        self._learn_slider = slider

    @property
    def learning(self) -> bool:
        return self._learn_slider is not None

    # --- events ---------------------------------------------------------------------------------------------------------------------
    def _on_control(self, control: Control) -> None:
        self.activity.emit(control)
        if self._learn_slider is not None and (control.kind != "axis" or abs(control.value) > 0.5):
            mapping = self.mapping()
            mapping.bind(control.key, Binding(self._learn_slider, "relative" if control.kind == "axis" else "absolute"))
            self.set_mapping(mapping)
            slider, self._learn_slider = self._learn_slider, None
            self.learned.emit(control.key, slider)
            return
        self._pending[control.key] = control

    def _apply_pending(self) -> None:
        """Apply the latest event of every control since the last tick (relative bindings keep moving while deflected)."""
        document = self.w.tabs.document
        now = time.perf_counter()
        dt, self._last_apply = now - self._last_apply, now
        if document is None or document.source is None:
            return
        if not self._pending:
            if self._burst:
                self._burst = False
                document.end_merge()                    # the burst of movement is over: the next one is a new undo step
            return
        mapping = self.mapping()
        values = {}
        for key, control in list(self._pending.items()):
            binding = mapping.for_control(control)
            if binding is None:
                self._pending.pop(key, None)
                continue
            new = self._value_for(document, binding, control, dt)
            if new is not None:
                values.update(new)
            if binding.mode == "absolute" or control.kind == "button":
                self._pending.pop(key, None)               # relative axes stay until they return to centre
            elif abs(control.value) < 0.08:
                self._pending.pop(key, None)
        if values:
            self._burst = True
            document.set_values(values, merge_key="controller", interactive=False)

    def _value_for(self, document, binding: Binding, control: Control, dt: float) -> dict | None:
        name = binding.slider[:-1] if binding.slider[-1:].isdigit() else binding.slider
        component = int(binding.slider[-1]) - 1 if binding.slider[-1:].isdigit() else 0
        param = document.state.params.get(name)
        if param is None or document.state.is_locked(name):
            return None
        low, high = getattr(param, "from_", None), getattr(param, "to", None)
        if low is None or high is None:
            return None
        current = document.state.values[name]
        if isinstance(low, (tuple, list)):
            if component >= len(low):
                return None
            parts = list(current)
            parts[component] = apply_control(binding, control, float(parts[component]), float(low[component]), float(high[component]), dt)
            return {name: tuple(parts)}
        new = apply_control(binding, control, float(current), float(low), float(high), dt)
        return {name: int(round(new)) if param.kind == "int" else new}

    def slider_names(self) -> list[str]:
        """Every slider component of the current document (`Power1`, `JuliaC1..3`)."""
        document = self.w.tabs.document
        if document is None or document.source is None:
            return []
        out = []
        for param in document.state.params.values():
            if getattr(param, "from_", None) is None:
                continue
            for c in range(1, param.components + 1):
                out.append(f"{param.name}{c}")
        return out

    def shutdown(self) -> None:
        self.stop()


class ControllerDialog(QDialog):
    """*Windows ▸ Controllers…* (see the module docstring)."""

    def __init__(self, parent: QWidget | None, coordinator: ControllerCoordinator):
        super().__init__(parent)
        self.setWindowTitle("Controllers — MIDI and gamepads")
        self.c = coordinator
        self.devices = QListWidget(self)
        self.start_button = QPushButton("Listen", self)
        self.stop_button = QPushButton("Stop all", self)
        self.refresh_button = QPushButton("Refresh", self)
        self.activity = QLabel("No events yet", self)
        self.slider_combo = QComboBox(self)
        self.learn_button = QPushButton("Learn", self)
        self.learn_button.setCheckable(True)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(("Control", "Slider", "Mode", "Speed", "Invert"))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().hide()
        self.remove_button = QPushButton("Remove binding", self)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        devices_row = QHBoxLayout()
        for button in (self.start_button, self.stop_button, self.refresh_button):
            devices_row.addWidget(button)
        devices_row.addStretch(1)
        learn_row = QHBoxLayout()
        learn_row.addWidget(QLabel("Bind to slider", self))
        learn_row.addWidget(self.slider_combo, 1)
        learn_row.addWidget(self.learn_button)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Devices (Linux: /dev/input/js*, /dev/midi*, /dev/snd/midiC*D*)", self))
        layout.addWidget(self.devices)
        layout.addLayout(devices_row)
        layout.addWidget(self.activity)
        layout.addLayout(learn_row)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.remove_button)
        layout.addWidget(buttons)
        self.resize(640, 520)
        self.refresh_button.clicked.connect(self.refresh_devices)
        self.start_button.clicked.connect(self._listen)
        self.stop_button.clicked.connect(lambda: (self.c.stop(), self.refresh_devices()))
        self.learn_button.toggled.connect(lambda on: self.c.learn(self.slider_combo.currentText() if on else None))
        self.remove_button.clicked.connect(self._remove)
        self.c.learned.connect(self._on_learned)
        self.c.activity.connect(lambda control: self.activity.setText(f"Last event: {control.key} = {control.value:.2f}"))
        self.refresh_devices()
        self.slider_combo.addItems(self.c.slider_names())
        self.refresh_bindings()

    def refresh_devices(self) -> None:
        self.devices.clear()
        found = discover_devices()
        for kind, path in found:
            self.devices.addItem(f"{kind}: {path}" + ("  (listening)" if path in self.c.readers else ""))
        if not found:
            self.devices.addItem("No controller devices found")
        self.start_button.setEnabled(bool(found))

    def _listen(self) -> None:
        row = self.devices.currentRow()
        found = discover_devices()
        if 0 <= row < len(found):
            self.c.start(*found[row])
            self.refresh_devices()

    def refresh_bindings(self) -> None:
        mapping = self.c.mapping()
        self.table.setRowCount(len(mapping.bindings))
        for row, (key, binding) in enumerate(sorted(mapping.bindings.items())):
            self.table.setItem(row, 0, QTableWidgetItem(key))
            self.table.setItem(row, 1, QTableWidgetItem(binding.slider))
            mode = QComboBox(self.table)
            mode.addItems(MODES)
            mode.setCurrentText(binding.mode)
            mode.currentTextChanged.connect(lambda text, k=key: self._edit(k, mode=text))
            self.table.setCellWidget(row, 2, mode)
            speed = QDoubleSpinBox(self.table)
            speed.setRange(0.01, 10.0)
            speed.setSingleStep(0.05)
            speed.setValue(binding.speed)
            speed.valueChanged.connect(lambda value, k=key: self._edit(k, speed=value))
            self.table.setCellWidget(row, 3, speed)
            invert = QCheckBox(self.table)
            invert.setChecked(binding.invert)
            invert.toggled.connect(lambda on, k=key: self._edit(k, invert=on))
            self.table.setCellWidget(row, 4, invert)

    def _edit(self, key: str, **changes) -> None:
        mapping = self.c.mapping()
        binding = mapping.bindings.get(key)
        if binding is None:
            return
        for name, value in changes.items():
            setattr(binding, name, value)
        self.c.set_mapping(mapping)

    def _remove(self) -> None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        if item is not None:
            mapping = self.c.mapping()
            mapping.unbind(item.text())
            self.c.set_mapping(mapping)
            self.refresh_bindings()

    def _on_learned(self, key: str, slider: str) -> None:
        self.learn_button.setChecked(False)
        self.activity.setText(f"Bound {key} → {slider}")
        self.refresh_bindings()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() == Qt.Key.Key_Escape and self.learn_button.isChecked():
            self.learn_button.setChecked(False)
            return
        super().keyPressEvent(event)


__all__ = ["ControllerCoordinator", "ControllerDialog", "DeviceReader", "MAPPING_KEY"]
