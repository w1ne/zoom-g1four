"""Read-only ZD2 SysEx protocol client.

Packet formats ported from mungewell/zoom-zt2 (MIT), pinned commit
b1f63b0bee6d2d1bc9755958fc8cf15887efbdcf. See THIRD_PARTY_NOTICES.md.
"""

import binascii

import mido

from .codec import decode_crc32_5, unpack_7bit

MODELS = {
    (0x0C, 0x00): "G1 Four",
    (0x0D, 0x00): "G1X Four",
    (0x0E, 0x00): "B1 Four",
    (0x0F, 0x00): "B1X Four",
    (0x10, 0x00): "GCE-3",
    (0x23, 0x00): "MS-50G+",
}


class PedalError(RuntimeError):
    pass


class ZoomPedal:
    def __init__(self, transport):
        self.transport = transport

    def _request(self, data) -> mido.Message:
        self.transport.send(mido.Message("sysex", data=list(data)))
        reply = self.transport.receive()
        if not isinstance(reply, mido.Message) or reply.type != "sysex":
            raise PedalError(f"unexpected MIDI message from pedal: {reply}")
        return reply

    def pcmode_on(self) -> None:
        self._request([0x52, 0x00, 0x6E, 0x52])

    def pcmode_off(self) -> None:
        self._request([0x52, 0x00, 0x6E, 0x53])

    def identity(self) -> dict:
        reply = self._request([0x7E, 0x00, 0x06, 0x01])
        data = list(reply.data)
        if data[0:4] != [0x7E, 0x00, 0x06, 0x02]:
            raise PedalError(f"unexpected identity reply: {data}")
        if len(data) < 9:
            raise PedalError(f"truncated identity reply: {data}")
        model = (data[7], data[8])
        version = bytes(data[9:]).decode("ascii", "replace")
        return {
            "reply_hex": " ".join(f"{b:02X}" for b in data),
            "model_bytes": f"{model[0]:02X} {model[1]:02X}",
            "model": MODELS.get(model, f"unknown ({model[0]:02X} {model[1]:02X})"),
            "firmware": version,
        }

    def patch_check(self) -> tuple[int, int, int]:
        reply = self._request([0x52, 0x00, 0x6E, 0x44])
        packet = list(reply.data)
        if len(packet) < 12:
            raise PedalError(f"truncated patch info reply: {packet}")
        count = packet[5] * 128 + packet[4]
        patch_size = packet[7] * 128 + packet[6]
        bank_size = packet[11] * 128 + packet[10]
        return count, patch_size, bank_size

    def patch_download(self, location: int, bsize: int) -> bytes:
        bank = (location - 1) // bsize
        loc = location - bank * bsize - 1
        reply = self._request(
            [
                0x52, 0x00, 0x6E, 0x46, 0x00, 0x00,
                bank & 0x7F, (bank >> 7) & 0x7F,
                loc & 0x7F, (loc >> 7) & 0x7F,
            ]
        )
        packet = list(reply.data)
        if len(packet) < 12:
            raise PedalError(f"truncated patch reply for patch {location}: {len(packet)} bytes")
        length = packet[11] * 128 + packet[10]
        if length == 0:
            return b""
        expected = 12 + length + (length + 6) // 7 + 5
        if len(packet) < expected:
            raise PedalError(
                f"truncated patch reply for patch {location}: {len(packet)} < {expected}"
            )
        block = unpack_7bit(bytes(packet[12:12 + length + length // 7 + 1]))
        checksum = decode_crc32_5(bytes(packet[-5:]))
        if (checksum ^ 0xFFFFFFFF) != binascii.crc32(block):
            raise PedalError(f"checksum mismatch for patch {location}")
        return block

    def _filename_request(self, header: list[int], name: str) -> mido.Message:
        data = header + [ord(ch) for ch in name] + [0x00]
        return self._request(data)

    def file_check(self, name: str) -> bool:
        self._filename_request([0x52, 0x00, 0x6E, 0x60, 0x25, 0x00, 0x00], name)
        response = self._request([0x52, 0x00, 0x6E, 0x60, 0x05, 0x00])
        self._request([0x52, 0x00, 0x6E, 0x60, 0x27])
        if len(response.data) < 5:
            raise PedalError(f"truncated file check reply for {name}: {list(response.data)}")
        return bytes(response.data[-5:]) == b"\x00" * 5

    def file_wild(self, first: bool) -> str:
        header = [0x52, 0x00, 0x6E, 0x60, 0x25 if first else 0x26, 0x00, 0x00]
        reply = self._filename_request(header, "*")
        data = list(reply.data)
        if len(data) > 4 and data[4] == 4:
            for end in range(14, min(27, len(data))):
                if data[end] == 0:
                    return bytes(data[14:end]).decode("utf-8")
        return ""

    def file_download(self, name: str) -> bytes:
        header = [0x52, 0x00, 0x6E, 0x60, 0x20, 0x02] + [0x00] * 9
        self._filename_request(header, name)
        collected = bytearray()
        while True:
            self._request([0x52, 0x00, 0x6E, 0x60, 0x05, 0x00])
            self._request([0x52, 0x00, 0x6E, 0x60, 0x22, 0x14, 0x2F, 0x60, 0x00, 0x0C, 0x00, 0x04, 0x00, 0x00, 0x00])
            reply = self._request([0x52, 0x00, 0x6E, 0x60, 0x05, 0x00])
            packet = list(reply.data)
            if len(packet) < 10:
                raise PedalError(f"truncated file reply for {name}: {len(packet)} bytes")
            length = packet[9] * 128 + packet[8]
            if packet[4] != 4 or length == 0:
                break
            expected = 10 + length + (length + 6) // 7 + 5
            if len(packet) < expected:
                raise PedalError(
                    f"truncated file reply for {name}: {len(packet)} < {expected}"
                )
            block = unpack_7bit(bytes(packet[10:10 + length + length // 7 + 1]))
            checksum = decode_crc32_5(bytes(packet[-5:]))
            if (checksum ^ 0xFFFFFFFF) != binascii.crc32(block):
                raise PedalError(f"checksum mismatch for file {name}")
            collected += block
        return bytes(collected)

    def file_close(self) -> None:
        self._request([0x52, 0x00, 0x6E, 0x60, 0x21, 0x40, 0x00, 0x00, 0x00, 0x00])
        self._request([0x52, 0x00, 0x6E, 0x60, 0x09])
