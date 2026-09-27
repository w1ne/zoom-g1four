"""Integration: scanner counts on the real vendor binaries.

Run with: .venv/bin/python -m pytest -m integration -v
"""

import pytest

from tools.capture.analyze_updater import scan_path
from tools.extract_updater.pipeline import extract_all

EXE_CODE_ONLY = {
    "file_ack_60_05": 1,
    "file_api_60_09": 1,
    "file_delete_60_24": 3,
    "file_list_60_25": 2,
}

MAC_CODE_ONLY = {
    "file_delete_60_24": 2,
    "file_list_60_25": 2,
    "file_read_block_60_22": 1,
}


def _zero_except(counts, nonzero):
    for name, value in counts.items():
        if name in nonzero:
            assert value == nonzero[name], name
        else:
            assert value == 0, name


@pytest.mark.integration
def test_scanner_code_only_counts_on_real_binaries(tmp_path):
    bins = extract_all(tmp_path / "official", tmp_path / "extracted", tmp_path / "work")
    exclude = [bins[name] for name in bins]

    win_exe = next((tmp_path / "work" / "win").rglob("*.exe"))
    win = scan_path(win_exe, exclude_paths=exclude)
    _zero_except(win["signatures"], EXE_CODE_ONLY)

    mac_binary = next((tmp_path / "work" / "mac").rglob("EFX Updater"))
    mac_report = scan_path(mac_binary, exclude_paths=[])
    _zero_except(mac_report["signatures"], MAC_CODE_ONLY)
