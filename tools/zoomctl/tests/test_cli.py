import pytest

from tools.zoomctl import __main__ as cli
from tools.zoomctl.transport import TransportError


def test_identity_reports_transport_error_cleanly(monkeypatch):
    def fake_open():
        raise TransportError("expected exactly one ZOOM MIDI input and output")

    monkeypatch.setattr(cli, "_open_pedal", fake_open)

    with pytest.raises(SystemExit, match="error: expected exactly one"):
        cli.main(["identity"])


def test_backup_reports_transport_error_cleanly(monkeypatch):
    def fake_open():
        raise TransportError("expected exactly one ZOOM MIDI input and output")

    monkeypatch.setattr(cli, "_open_pedal", fake_open)

    with pytest.raises(SystemExit, match="error: expected exactly one"):
        cli.main(["backup"])
