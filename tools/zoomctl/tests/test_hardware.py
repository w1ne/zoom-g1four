"""Read-only tests against a physically connected pedal.

Run with: .venv/bin/python -m pytest -m hardware -v

Isolation: the pedal must not be in use by another MIDI application and no one
should touch it during the run; `MidoTransport.receive` returns the first MIDI
message of any type and the client rejects non-Sysex replies.
"""

import contextlib

import pytest

from tools.zoomctl.pedal import ZoomPedal
from tools.zoomctl.transport import MidoTransport


@pytest.fixture
def pedal():
    ports = MidoTransport.find_zoom_ports()
    if ports is None:
        pytest.skip("no ZOOM G Series MIDI ports found")
    zoom = ZoomPedal(MidoTransport(*ports))
    yield zoom
    zoom.transport.close()


@pytest.mark.hardware
def test_identity_reports_g1_four(pedal):
    identity = pedal.identity()
    assert identity["model"] == "G1 Four"
    assert identity["firmware"]


@pytest.mark.hardware
def test_patch_and_first_file_download_verify_crc(pedal):
    name = None
    try:
        pedal.pcmode_on()
        count, patch_size, bank_size = pedal.patch_check()
        assert count >= 1 and patch_size > 0 and bank_size >= 1
        assert pedal.patch_download(1, bank_size)
        name = pedal.file_wild(first=True)
        assert name
        assert pedal.file_download(name)
    finally:
        if name:
            with contextlib.suppress(Exception):
                pedal.file_close()
        with contextlib.suppress(Exception):
            pedal.pcmode_off()
