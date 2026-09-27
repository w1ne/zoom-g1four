import subprocess
from pathlib import Path

import pytest

from tools.extract_updater import constants, resources


def _make_mac_tree(root: Path) -> Path:
    res = root / "pkg" / "Updater.app" / "Contents" / "Resources"
    res.mkdir(parents=True)
    for name in constants.PAYLOADS:
        (res / name).write_bytes(b"x")
    return root


def test_find_mac_resources_returns_all_payloads(tmp_path):
    root = _make_mac_tree(tmp_path)
    found = resources.find_mac_resources(root)
    assert set(found) == set(constants.PAYLOADS)
    assert found["Main.bin"].parent.name == "Resources"


def test_find_mac_resources_reports_missing(tmp_path):
    root = _make_mac_tree(tmp_path)
    (root / "pkg" / "Updater.app" / "Contents" / "Resources" / "FS.bin").unlink()
    with pytest.raises(FileNotFoundError, match="FS.bin"):
        resources.find_mac_resources(root)


def test_find_sevenzip_reports_install_hint(monkeypatch):
    monkeypatch.setattr(resources.shutil, "which", lambda name: None)
    with pytest.raises(FileNotFoundError, match="brew install sevenzip"):
        resources.find_sevenzip()


def test_extract_win_resources_maps_ids_to_names(tmp_path, monkeypatch):
    exe = tmp_path / "updater.exe"
    exe.write_bytes(b"MZ")
    dest = tmp_path / "out"

    def fake_run(cmd, check, stdout, stderr):
        out_dir = Path(cmd[2][2:])
        for rid in constants.WIN_BIN_RESOURCE_IDS:
            target = out_dir / ".rsrc" / "1041" / "BIN" / str(rid)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f"resource-{rid}".encode())
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(resources.subprocess, "run", fake_run)

    result = resources.extract_win_resources(exe, dest, sevenzip="7zz")

    assert set(result) == set(constants.PAYLOADS)
    assert result["ROM.bin"].read_bytes() == b"resource-142"


def test_extract_win_resources_reports_missing_resource(tmp_path, monkeypatch):
    exe = tmp_path / "updater.exe"
    exe.write_bytes(b"MZ")

    def fake_run(cmd, check, stdout, stderr):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(resources.subprocess, "run", fake_run)

    with pytest.raises(FileNotFoundError, match="resource 129"):
        resources.extract_win_resources(exe, tmp_path / "out", sevenzip="7zz")
