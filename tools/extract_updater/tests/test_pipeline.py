import hashlib
from pathlib import Path

import pytest

from tools.extract_updater import constants, pipeline


def _bins(tmp_path, name_to_bytes):
    out = {}
    for name, data in name_to_bytes.items():
        path = tmp_path / name
        path.write_bytes(data)
        out[name] = path
    return out


def test_write_sha256sums_sorted_gnu_format(tmp_path):
    bins = _bins(tmp_path, {"b.bin": b"bee", "a.bin": b"aye"})
    out = pipeline.write_sha256sums(bins, tmp_path / "SHA256SUMS")
    lines = out.read_text().splitlines()
    assert lines[0].startswith(pipeline.sha256_file(bins["a.bin"]))
    assert lines[0].endswith("  a.bin")
    assert lines[1].endswith("  b.bin")


def test_canonicalize_accepts_identical_payloads(tmp_path):
    mac = _bins(tmp_path, {"Main.bin": b"same"})
    win_dir = tmp_path / "win"
    win_dir.mkdir()
    win = {}
    for name in mac:
        path = win_dir / name
        path.write_bytes(b"same")
        win[name] = path

    result = pipeline.canonicalize(mac, win)

    assert result == mac


def test_canonicalize_writes_report_and_raises_on_mismatch(tmp_path):
    mac = _bins(tmp_path, {"Main.bin": b"mac"})
    win_dir = tmp_path / "win"
    win_dir.mkdir()
    win_path = win_dir / "Main.bin"
    win_path.write_bytes(b"win")
    report = tmp_path / "mismatch-report.txt"

    with pytest.raises(ValueError, match="platform mismatch for Main.bin"):
        pipeline.canonicalize(mac, {"Main.bin": win_path}, report_path=report)

    text = report.read_text()
    assert "Main.bin" in text
    assert pipeline.sha256_file(mac["Main.bin"]) in text
    assert pipeline.sha256_file(win_path) in text


def test_canonicalize_rejects_payload_set_mismatch(tmp_path):
    mac = _bins(tmp_path, {"Main.bin": b"a"})

    with pytest.raises(ValueError, match="payload set mismatch"):
        pipeline.canonicalize(mac, {})


def test_fetch_all_redownloads_when_local_hash_wrong(tmp_path, monkeypatch):
    official = tmp_path / "official"
    official.mkdir()
    for pkg in constants.OFFICIAL_PACKAGES.values():
        (official / pkg["filename"]).write_bytes(b"stale")
    calls = []

    def fake_download(url, dest, expected_sha256):
        calls.append((url, Path(dest), expected_sha256))
        Path(dest).write_bytes(b"fresh")
        return Path(dest)

    monkeypatch.setattr(pipeline, "download", fake_download)

    result = pipeline.fetch_all(official)

    assert len(calls) == 2
    assert set(result) == {"mac", "win"}


def test_fetch_all_reuses_local_file_with_matching_hash(tmp_path, monkeypatch):
    official = tmp_path / "official"
    official.mkdir()
    for pkg in constants.OFFICIAL_PACKAGES.values():
        (official / pkg["filename"]).write_bytes(b"good")

    def fake_sha256(path):
        name = Path(path).name
        if name == constants.OFFICIAL_PACKAGES["mac"]["filename"]:
            return constants.OFFICIAL_PACKAGES["mac"]["sha256"]
        return constants.OFFICIAL_PACKAGES["win"]["sha256"]

    def fail_download(*args, **kwargs):
        raise AssertionError("download must not be called for verified local files")

    monkeypatch.setattr(pipeline, "sha256_file", fake_sha256)
    monkeypatch.setattr(pipeline, "download", fail_download)

    result = pipeline.fetch_all(official)

    assert set(result) == {"mac", "win"}


def _one_payload(tmp_path, data=b"data", name="X.bin"):
    path = tmp_path / name
    path.write_bytes(data)
    return {name: {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}}, path


def test_verify_all_passes_with_matching_artifacts(tmp_path, monkeypatch):
    payloads, path = _one_payload(tmp_path)
    monkeypatch.setattr(pipeline.constants, "PAYLOADS", payloads)
    pipeline.write_sha256sums({name: path for name in payloads}, tmp_path / "SHA256SUMS")

    assert pipeline.verify_all(tmp_path) is None


def test_verify_all_rejects_missing_file(tmp_path, monkeypatch):
    payloads, path = _one_payload(tmp_path)
    monkeypatch.setattr(pipeline.constants, "PAYLOADS", payloads)
    pipeline.write_sha256sums({name: path for name in payloads}, tmp_path / "SHA256SUMS")
    path.unlink()

    with pytest.raises(FileNotFoundError, match="missing"):
        pipeline.verify_all(tmp_path)


def test_verify_all_rejects_wrong_size(tmp_path, monkeypatch):
    payloads, path = _one_payload(tmp_path)
    payloads["X.bin"]["size"] = 99
    monkeypatch.setattr(pipeline.constants, "PAYLOADS", payloads)
    pipeline.write_sha256sums({name: path for name in payloads}, tmp_path / "SHA256SUMS")

    with pytest.raises(ValueError, match="expected size 99"):
        pipeline.verify_all(tmp_path)


def test_verify_all_rejects_wrong_hash(tmp_path, monkeypatch):
    payloads, path = _one_payload(tmp_path)
    payloads["X.bin"]["sha256"] = "0" * 64
    monkeypatch.setattr(pipeline.constants, "PAYLOADS", payloads)
    pipeline.write_sha256sums({name: path for name in payloads}, tmp_path / "SHA256SUMS")

    with pytest.raises(ValueError, match="expected sha256"):
        pipeline.verify_all(tmp_path)


def test_verify_all_rejects_sha256sums_mismatch(tmp_path, monkeypatch):
    payloads, path = _one_payload(tmp_path)
    monkeypatch.setattr(pipeline.constants, "PAYLOADS", payloads)
    (tmp_path / "SHA256SUMS").write_text("f" * 64 + "  X.bin\n")

    with pytest.raises(ValueError, match="SHA256SUMS does not match constants"):
        pipeline.verify_all(tmp_path)


def test_extract_all_rejects_incomplete_payload_set(tmp_path, monkeypatch):
    mac_bin = tmp_path / "mac.bin"
    mac_bin.write_bytes(b"same")
    win_bin = tmp_path / "win.bin"
    win_bin.write_bytes(b"same")

    def fake_extract_zip(pkg, dest):
        dest.mkdir(parents=True, exist_ok=True)
        if dest.name == "win":
            (dest / "updater.exe").write_bytes(b"MZ")
        return dest

    monkeypatch.setattr(pipeline, "fetch_all", lambda official: {"mac": mac_bin, "win": win_bin})
    monkeypatch.setattr(pipeline, "extract_zip", fake_extract_zip)
    monkeypatch.setattr(pipeline, "find_mac_resources", lambda root: {"X.bin": mac_bin})
    monkeypatch.setattr(pipeline, "extract_win_resources", lambda exe, dest, **kw: {"X.bin": win_bin})

    with pytest.raises(ValueError, match="payload set incomplete"):
        pipeline.extract_all(tmp_path / "official", tmp_path / "extracted", tmp_path / "work")
