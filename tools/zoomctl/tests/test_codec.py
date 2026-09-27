import binascii

from tools.zoomctl.codec import crc32_5, decode_crc32_5, pack_7bit, unpack_7bit


def test_pack_known_vectors():
    assert pack_7bit(b"") == b""
    assert pack_7bit(b"\xff" * 7) == b"\x7f" * 8
    assert pack_7bit(b"\x80" * 7) == b"\x7f" + b"\x00" * 7
    assert pack_7bit(b"\x80\x00") == b"\x40\x00\x00"
    assert pack_7bit(b"\x00\x80") == b"\x20\x00\x00"


def test_pack_unpack_round_trip_all_group_sizes():
    for size in range(0, 40):
        data = bytes((i * 37 + 200) % 256 for i in range(size))
        assert unpack_7bit(pack_7bit(data)) == data


def test_unpack_known_vectors_and_dangling_msb():
    assert unpack_7bit(b"\x7f" + b"\x00" * 7) == b"\x80" * 7
    assert unpack_7bit(b"\x40\x00\x00") == b"\x80\x00"
    assert unpack_7bit(b"\x40\x55\x7f") == b"\xd5\x7f"


def test_crc32_5_known_vector():
    assert crc32_5(b"123456789") == bytes([0x59, 0x0D, 0x2F, 0x20, 0x03])
    assert decode_crc32_5(bytes([0x59, 0x0D, 0x2F, 0x20, 0x03])) == 0x340BC6D9


def test_crc32_5_is_inverted_crc32():
    for data in (b"", b"a", b"123456789", bytes(range(256))):
        value = decode_crc32_5(crc32_5(data))
        assert (value ^ 0xFFFFFFFF) == binascii.crc32(data)
