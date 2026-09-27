import mido
import pytest

from tools.zoomctl.pedal import PedalError, ZoomPedal
from tools.zoomctl.tests.fake_transport import FakeTransport, sysex
from tools.zoomctl.transport import MidoTransport, TransportError, ZOOM_PORT_PREFIX


def test_identity_parses_g1_four_reply():
    transport = FakeTransport(
        [sysex([0x7E, 0x00, 0x06, 0x02, 0x52, 0x6E, 0x00, 0x0C, 0x00] + list(b"2.00"))]
    )
    pedal = ZoomPedal(transport)

    identity = pedal.identity()

    assert list(transport.sent[0].data) == [0x7E, 0x00, 0x06, 0x01]
    assert identity["model_bytes"] == "0C 00"
    assert identity["model"] == "G1 Four"
    assert identity["firmware"] == "2.00"
    assert identity["reply_hex"] == "7E 00 06 02 52 6E 00 0C 00 32 2E 30 30"


def test_identity_unknown_model_still_parses():
    transport = FakeTransport(
        [sysex([0x7E, 0x00, 0x06, 0x02, 0x52, 0x6E, 0x00, 0x7F, 0x00] + list(b"9.99"))]
    )
    pedal = ZoomPedal(transport)

    identity = pedal.identity()

    assert identity["model"] == "unknown (7F 00)"
    assert identity["firmware"] == "9.99"


def test_port_prefix_is_zoom_g():
    assert ZOOM_PORT_PREFIX == "ZOOM G"


def test_find_zoom_ports_returns_none_without_ports(monkeypatch):
    monkeypatch.setattr(mido, "get_input_names", lambda: [])
    monkeypatch.setattr(mido, "get_output_names", lambda: [])

    assert MidoTransport.find_zoom_ports() is None


def test_find_zoom_ports_returns_pair(monkeypatch):
    monkeypatch.setattr(mido, "get_input_names", lambda: ["ZOOM G Series"])
    monkeypatch.setattr(mido, "get_output_names", lambda: ["ZOOM G Series"])

    assert MidoTransport.find_zoom_ports() == ("ZOOM G Series", "ZOOM G Series")


def test_find_zoom_ports_raises_on_ambiguity(monkeypatch):
    monkeypatch.setattr(mido, "get_input_names", lambda: ["ZOOM G Series", "ZOOM G Series 2"])
    monkeypatch.setattr(mido, "get_output_names", lambda: ["ZOOM G Series"])

    with pytest.raises(TransportError, match="exactly one"):
        MidoTransport.find_zoom_ports()


def test_request_rejects_non_sysex_reply():
    pedal = ZoomPedal(FakeTransport([mido.Message("clock")]))

    with pytest.raises(PedalError, match="unexpected MIDI message"):
        pedal.identity()


def test_identity_truncated_reply_raises():
    pedal = ZoomPedal(FakeTransport([sysex([0x7E, 0x00, 0x06, 0x02, 0x52, 0x6E, 0x00, 0x0C])]))

    with pytest.raises(PedalError, match="truncated"):
        pedal.identity()
