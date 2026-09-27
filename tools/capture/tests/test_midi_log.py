import mido

from tools.capture import midi_log


def test_format_message_sysex():
    message = mido.Message("sysex", data=[0x52, 0x00, 0x6E, 0x52])
    assert midi_log.format_message(message, 1.2345) == "    1.234 sysex        52 00 6E 52"


def test_format_message_without_data():
    message = mido.Message("clock")
    assert midi_log.format_message(message, 0.0) == "    0.000 clock       "


def test_format_message_note_on_logs_data_bytes():
    message = mido.Message("note_on", note=60, velocity=100)
    assert midi_log.format_message(message, 0.0) == "    0.000 note_on      3C 64"


def test_record_returns_2_when_no_port(monkeypatch, tmp_path):
    monkeypatch.setattr(mido, "get_input_names", lambda: ["Other Device"])
    assert midi_log.record("ZOOM G", tmp_path / "log.txt", duration=0.0) == 2


def test_record_refuses_to_overwrite(monkeypatch, tmp_path):
    out = tmp_path / "log.txt"
    out.write_text("existing")
    monkeypatch.setattr(mido, "get_input_names", lambda: ["ZOOM G Series"])

    assert midi_log.record("ZOOM G", out, duration=0.0) == 3
    assert out.read_text() == "existing"


def test_record_logs_messages(monkeypatch, tmp_path):
    class FakePort:
        def __init__(self):
            self.messages = [mido.Message("sysex", data=[0x52, 0x00, 0x6E, 0x44]), mido.Message("clock")]

        def poll(self):
            return self.messages.pop(0) if self.messages else None

        def close(self):
            pass

    ticks = iter([0.0, 0.1, 0.2, 0.3, 0.4, 10.0, 10.1, 10.2])
    monkeypatch.setattr(midi_log.time, "monotonic", lambda: next(ticks, 100.0))
    monkeypatch.setattr(mido, "get_input_names", lambda: ["ZOOM G Series"])
    monkeypatch.setattr(mido, "open_input", lambda name: FakePort())

    out = tmp_path / "log.txt"
    assert midi_log.record("ZOOM G", out, duration=0.5) == 0

    lines = out.read_text().splitlines()
    assert lines[0] == "# port: ZOOM G Series"
    assert lines[1].startswith("# started: ")
    assert "sysex" in lines[2] and "52 00 6E 44" in lines[2]
    assert "clock" in lines[3]
