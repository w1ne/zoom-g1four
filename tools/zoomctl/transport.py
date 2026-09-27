"""MIDI transport: mido ports for the pedal, protocol-agnostic interface."""

from typing import Protocol

import mido

ZOOM_PORT_PREFIX = "ZOOM G"


class Transport(Protocol):
    def send(self, message) -> None: ...

    def receive(self): ...


class MidoTransport:
    def __init__(self, input_name: str, output_name: str):
        self._input = mido.open_input(input_name)
        self._output = mido.open_output(output_name)

    @staticmethod
    def find_zoom_ports() -> tuple[str, str] | None:
        inputs = [n for n in mido.get_input_names() if n.startswith(ZOOM_PORT_PREFIX)]
        outputs = [n for n in mido.get_output_names() if n.startswith(ZOOM_PORT_PREFIX)]
        if inputs and outputs:
            return inputs[0], outputs[0]
        return None

    def send(self, message) -> None:
        self._output.send(message)

    def receive(self):
        return self._input.receive()
