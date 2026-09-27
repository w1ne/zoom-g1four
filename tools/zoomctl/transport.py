"""MIDI transport: mido ports for the pedal, protocol-agnostic interface."""

import time
from typing import Protocol

import mido

ZOOM_PORT_PREFIX = "ZOOM G"
RECEIVE_TIMEOUT_SECONDS = 5.0


class TransportError(RuntimeError):
    pass


class Transport(Protocol):
    def send(self, message) -> None: ...

    def receive(self, timeout: float | None = None): ...


class MidoTransport:
    def __init__(self, input_name: str, output_name: str):
        self._input = mido.open_input(input_name)
        self._output = mido.open_output(output_name)

    @staticmethod
    def find_zoom_ports() -> tuple[str, str] | None:
        inputs = [n for n in mido.get_input_names() if n.startswith(ZOOM_PORT_PREFIX)]
        outputs = [n for n in mido.get_output_names() if n.startswith(ZOOM_PORT_PREFIX)]
        if not inputs and not outputs:
            return None
        if len(inputs) != 1 or len(outputs) != 1:
            raise TransportError(
                f"expected exactly one ZOOM MIDI input and output, found in={inputs} out={outputs}"
            )
        return inputs[0], outputs[0]

    def send(self, message) -> None:
        self._output.send(message)

    def receive(self, timeout: float | None = RECEIVE_TIMEOUT_SECONDS):
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            message = self._input.poll()
            if message is not None:
                return message
            if deadline is not None and time.monotonic() >= deadline:
                raise TransportError(
                    "no MIDI reply within "
                    f"{timeout}s; check the pedal connection and that it is powered on"
                )
            time.sleep(0.01)

    def close(self) -> None:
        self._input.close()
        self._output.close()
