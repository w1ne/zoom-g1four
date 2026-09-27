import mido
import pytest

from tools.capture import midi_log


def test_format_message_sysex():
    message = mido.Message("sysex", data=[0x52, 0x00, 0x6E, 0x52])
    assert midi_log.format_message(message, 1.2345) == "    1.234 sysex        52 00 6E 52"


def test_format_message_without_data():
    message = mido.Message("clock")
    assert midi_log.format_message(message, 0.0) == "    0.000 clock       "


def test_record_returns_2_when_no_port(monkeypatch, tmp_path):
    monkeypatch.setattr(mido, "get_input_names", lambda: ["Other Device"])
    assert midi_log.record("ZOOM G", tmp_path / "log.txt", duration=0.0) == 2


def test_record_logs_messages(monkeypatch, tmp_path):
    class FakePort:
        def __init__(self):
            self.messages = [mido.Message("sysex", data=[0x52, 0x00, 0x6E, 0x44]), mido.Message("clock")]

        def poll(self):
            return self.messages.pop(0) if self.messages else None

        def close(self):
            pass

    monkeypatch.setattr(mido, "get_input_names", lambda: ["ZOOM G Series"])
    monkeypatch.setattr(mido, "open_input", lambda name: FakePort())

    out = tmp_path / "log.txt"
    assert midi_log.record("ZOOM G", out, duration=0.5) == 0

    lines = out.read_text().splitlines()
    assert lines[0] == "# port: ZOOM G Series"
    assert "sysex" in lines[1] and "52 00 6E 44" in lines[1]
    assert "clock" in lines[2]
