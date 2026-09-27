"""Integration: real-EXE zero-change and one-byte round-trip.

Run with: .venv/bin/python -m pytest -m integration -v
"""

import pytest

from tools.extract_updater.pipeline import extract_all
from tools.repack_updater import repack_win


@pytest.mark.integration
def test_zero_change_and_one_byte_round_trip(tmp_path):
    bins = extract_all(tmp_path / "official", tmp_path / "extracted", tmp_path / "work")
    exe = next((tmp_path / "work" / "win").rglob("*.exe"))

    zero = tmp_path / "zero.exe"
    repack_win.repack(exe, zero, {rid: bins[name] for rid, name in repack_win.BIN_RESOURCE_IDS.items()})
    assert zero.read_bytes() == exe.read_bytes()

    edited_dir = tmp_path / "edited"
    edited_dir.mkdir()
    for name, path in bins.items():
        data = bytearray(path.read_bytes())
        if name == "Main.bin":
            data[100] ^= 0xFF
        (edited_dir / name).write_bytes(bytes(data))

    one = tmp_path / "one.exe"
    repack_win.repack(exe, one, {rid: edited_dir / name for rid, name in repack_win.BIN_RESOURCE_IDS.items()})

    original = exe.read_bytes()
    patched = one.read_bytes()
    assert len(original) == len(patched)
    diffs = [index for index, (before, after) in enumerate(zip(original, patched)) if before != after]
    assert len(diffs) == 1
