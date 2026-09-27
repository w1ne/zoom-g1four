"""Read-only ZD2 SysEx protocol client.

Packet formats ported from mungewell/zoom-zt2 (MIT), pinned commit
b1f63b0bee6d2d1bc9755958fc8cf15887efbdcf. See THIRD_PARTY_NOTICES.md.
"""

import mido

from .codec import decode_crc32_5, pack_7bit, unpack_7bit

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
        return self.transport.receive()

    def pcmode_on(self) -> None:
        self._request([0x52, 0x00, 0x6E, 0x52])

    def pcmode_off(self) -> None:
        self._request([0x52, 0x00, 0x6E, 0x53])

    def identity(self) -> dict:
        reply = self._request([0x7E, 0x00, 0x06, 0x01])
        data = list(reply.data)
        if len(data) < 10 or data[0:4] != [0x7E, 0x00, 0x06, 0x02]:
            raise PedalError(f"unexpected identity reply: {data}")
        model = (data[7], data[8])
        version = bytes(data[9:]).decode("ascii", "replace")
        return {
            "reply_hex": " ".join(f"{b:02X}" for b in data),
            "model_bytes": f"{model[0]:02X} {model[1]:02X}",
            "model": MODELS.get(model, f"unknown ({model[0]:02X} {model[1]:02X})"),
            "firmware": version,
        }
