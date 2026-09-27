from tools.zoomctl.pedal import ZoomPedal
from tools.zoomctl.tests.fake_transport import FakeTransport, sysex
from tools.zoomctl.transport import ZOOM_PORT_PREFIX


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
        [sysex([0x7E, 0x00, 0x06, 0x02, 0x52, 0x6E, 0x00, 0x99, 0x00] + list(b"9.99"))]
    )
    pedal = ZoomPedal(transport)

    identity = pedal.identity()

    assert identity["model"] == "unknown (99 00)"
    assert identity["firmware"] == "9.99"


def test_port_prefix_is_zoom_g():
    assert ZOOM_PORT_PREFIX == "ZOOM G"
