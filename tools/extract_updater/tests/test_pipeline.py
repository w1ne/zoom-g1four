import pytest

from tools.extract_updater import pipeline


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
