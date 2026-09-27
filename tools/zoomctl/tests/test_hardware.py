"""Read-only tests against a physically connected pedal.

Run with: .venv/bin/python -m pytest -m hardware -v
"""

import pytest

from tools.zoomctl.pedal import ZoomPedal
from tools.zoomctl.transport import MidoTransport


def _pedal_or_skip() -> ZoomPedal:
    ports = MidoTransport.find_zoom_ports()
    if ports is None:
        pytest.skip("no ZOOM G Series MIDI ports found")
    return ZoomPedal(MidoTransport(*ports))


@pytest.mark.hardware
def test_identity_reports_g1_four():
    identity = _pedal_or_skip().identity()
    assert identity["model"] == "G1 Four"
    assert identity["firmware"]


@pytest.mark.hardware
def test_patch_and_first_file_download_verify_crc():
    pedal = _pedal_or_skip()
    pedal.pcmode_on()
    try:
        count, patch_size, bank_size = pedal.patch_check()
        assert count >= 1 and patch_size > 0 and bank_size >= 1
        assert pedal.patch_download(1, bank_size)
        name = pedal.file_wild(first=True)
        assert name
        assert pedal.file_download(name)
        pedal.file_close()
    finally:
        pedal.pcmode_off()
