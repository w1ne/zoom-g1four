import mido
import pytest

from tools.zoomctl.codec import crc32_5, pack_7bit
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


def test_patch_check_decodes_counts():
    reply = sysex([0x52, 0x00, 0x6E, 0x44, 60, 0, 0x20, 0x00, 0, 0, 10, 0])
    transport = FakeTransport([reply])
    pedal = ZoomPedal(transport)

    count, psize, bsize = pedal.patch_check()

    assert (count, psize, bsize) == (60, 32, 10)
    assert list(transport.sent[0].data) == [0x52, 0x00, 0x6E, 0x44]


def test_patch_download_returns_data_and_verifies_crc():
    data = b"ZPTC-patch-payload"
    packet = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0]
    packet += [len(data) & 0x7F, (len(data) >> 7) & 0x7F]
    packet += list(pack_7bit(data)) + list(crc32_5(data))
    transport = FakeTransport([sysex(packet)])
    pedal = ZoomPedal(transport)

    result = pedal.patch_download(location=1, bsize=10)

    assert result == data
    assert list(transport.sent[0].data) == [0x52, 0x00, 0x6E, 0x46, 0x00, 0x00, 0, 0, 0, 0]


def test_patch_download_bank_and_location_math():
    packet = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0, 0, 0] + list(crc32_5(b""))
    transport = FakeTransport([sysex(packet)])
    pedal = ZoomPedal(transport)

    result = pedal.patch_download(location=23, bsize=10)

    assert result == b""
    assert list(transport.sent[0].data) == [0x52, 0x00, 0x6E, 0x46, 0x00, 0x00, 2, 0, 2, 0]


def test_patch_download_raises_on_bad_crc():
    data = b"payload"
    packet = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0]
    packet += [len(data) & 0x7F, (len(data) >> 7) & 0x7F]
    packet += list(pack_7bit(data)) + [0x01, 0x02, 0x03, 0x04, 0x05]
    transport = FakeTransport([sysex(packet)])
    pedal = ZoomPedal(transport)

    with pytest.raises(PedalError, match="checksum"):
        pedal.patch_download(location=1, bsize=10)


def test_patch_check_decodes_14bit_values():
    reply = sysex([0x52, 0x00, 0x6E, 0x44, 44, 2, 0x48, 1, 0, 0, 100, 0])
    pedal = ZoomPedal(FakeTransport([reply]))

    assert pedal.patch_check() == (300, 200, 100)


def test_patch_check_truncated_reply_raises():
    pedal = ZoomPedal(FakeTransport([sysex([0x52, 0x00, 0x6E, 0x44, 1, 0])]))

    with pytest.raises(PedalError, match="truncated patch info reply"):
        pedal.patch_check()


def test_patch_download_handles_200_byte_patch():
    data = bytes((i * 7) % 256 for i in range(200))
    packet = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0]
    packet += [len(data) & 0x7F, (len(data) >> 7) & 0x7F]
    packet += list(pack_7bit(data)) + list(crc32_5(data))
    pedal = ZoomPedal(FakeTransport([sysex(packet)]))

    assert pedal.patch_download(location=1, bsize=10) == data


def test_patch_download_truncated_reply_raises():
    data = b"0123456789abcdef"
    packet = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0]
    packet += [len(data) & 0x7F, (len(data) >> 7) & 0x7F]
    packet += list(pack_7bit(data))[:3]
    pedal = ZoomPedal(FakeTransport([sysex(packet)]))

    with pytest.raises(PedalError, match="truncated patch reply"):
        pedal.patch_download(location=1, bsize=10)


def _file_list_reply(name: str):
    return sysex([0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                 + list(name.encode()) + [0])


def test_file_wild_returns_name_then_empty_at_end():
    transport = FakeTransport([_file_list_reply("ZEN_DRV.ZD2"), sysex([0x52, 0x00, 0x6E, 0x60, 0x05])])
    pedal = ZoomPedal(transport)

    assert pedal.file_wild(first=True) == "ZEN_DRV.ZD2"
    assert pedal.file_wild(first=False) == ""
    assert list(transport.sent[0].data[:7]) == [0x52, 0x00, 0x6E, 0x60, 0x25, 0x00, 0x00]
    assert list(transport.sent[1].data[:7]) == [0x52, 0x00, 0x6E, 0x60, 0x26, 0x00, 0x00]
    assert list(transport.sent[0].data[7:]) == [ord("*"), 0]


def test_file_check_true_when_last_five_bytes_zero():
    transport = FakeTransport([
        sysex([0x52, 0x00, 0x6E, 0x60, 0x25]),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0]),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x27]),
    ])
    pedal = ZoomPedal(transport)

    assert pedal.file_check("FLST_SEQ.ZT2") is True


def test_file_check_false_when_last_five_bytes_nonzero():
    transport = FakeTransport([
        sysex([0x52, 0x00, 0x6E, 0x60, 0x25]),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x04, 1, 2, 3, 4, 5]),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x27]),
    ])
    pedal = ZoomPedal(transport)

    assert pedal.file_check("MISSING.ZD2") is False


def test_file_check_truncated_reply_raises():
    transport = FakeTransport([
        sysex([0x52, 0x00, 0x6E, 0x60, 0x25]),
        sysex([0x52, 0x00, 0x6E, 0x60]),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x27]),
    ])
    pedal = ZoomPedal(transport)

    with pytest.raises(PedalError, match="truncated file check reply"):
        pedal.file_check("X.ZD2")


def test_file_download_reads_blocks_until_empty_and_closes():
    data = b"effect-binary"
    block = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0]
    block += [len(data) & 0x7F, (len(data) >> 7) & 0x7F]
    block += list(pack_7bit(data)) + list(crc32_5(data))
    end = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0]
    ack = [0x52, 0x00, 0x6E, 0x60, 0x05]
    transport = FakeTransport([
        sysex([0x52, 0x00, 0x6E, 0x60, 0x20]),  # open
        sysex(ack), sysex([0x52, 0x00, 0x6E, 0x60, 0x22]), sysex(block),
        sysex(ack), sysex([0x52, 0x00, 0x6E, 0x60, 0x22]), sysex(end),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x21]),  # close
        sysex([0x52, 0x00, 0x6E, 0x60, 0x09]),
    ])
    pedal = ZoomPedal(transport)

    result = pedal.file_download("X.ZD2")

    assert result == data
    assert list(transport.sent[0].data) == [0x52, 0x00, 0x6E, 0x60, 0x20, 0x02, 0, 0, 0, 0, 0, 0, 0, 0, 0, ord("X"), ord("."), ord("Z"), ord("D"), ord("2"), 0]


def test_file_download_truncated_block_raises():
    data = b"0123456789abcdef"
    block = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0]
    block += [len(data) & 0x7F, (len(data) >> 7) & 0x7F]
    block += list(pack_7bit(data))[:3]
    ack = [0x52, 0x00, 0x6E, 0x60, 0x05]
    transport = FakeTransport([
        sysex([0x52, 0x00, 0x6E, 0x60, 0x20]),
        sysex(ack), sysex([0x52, 0x00, 0x6E, 0x60, 0x22]), sysex(block),
    ])
    pedal = ZoomPedal(transport)

    with pytest.raises(PedalError, match="truncated file reply"):
        pedal.file_download("X.ZD2")
