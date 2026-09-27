"""7-bit packing and 5-byte CRC framing for the ZD2 SysEx protocol.

Protocol logic ported from mungewell/zoom-zt2 (MIT), pinned commit
b1f63b0bee6d2d1bc9755958fc8cf15887efbdcf. See THIRD_PARTY_NOTICES.md.

The unpacker ignores a trailing MSB byte that has no payload bytes after it
(callers intentionally over-read one byte past a full 7-byte group).
"""

import binascii


def pack_7bit(data: bytes) -> bytes:
    packet = bytearray()
    group = bytearray(b"\x00")
    for byte in data:
        group[0] = group[0] + ((byte & 0x80) >> len(group))
        group.append(byte & 0x7F)
        if len(group) > 7:
            packet += group
            group = bytearray(b"\x00")
    if len(group) > 1:
        packet += group
    return bytes(packet)


def unpack_7bit(packet: bytes) -> bytes:
    data = bytearray()
    remaining = -1
    high_bits = 0
    for byte in packet:
        if remaining != -1:
            if high_bits & (2 ** remaining):
                data.append(128 + byte)
            else:
                data.append(byte)
            remaining -= 1
        else:
            high_bits = byte
            remaining = 6
    return bytes(data)


def crc32_5(data: bytes) -> bytes:
    value = binascii.crc32(data) ^ 0xFFFFFFFF
    return bytes(
        [(value >> (7 * i)) & 0x7F for i in range(4)] + [(value >> 28) & 0x0F]
    )


def decode_crc32_5(values: bytes) -> int:
    return (
        values[0]
        + (values[1] << 7)
        + (values[2] << 14)
        + (values[3] << 21)
        + ((values[4] & 0x0F) << 28)
    )
