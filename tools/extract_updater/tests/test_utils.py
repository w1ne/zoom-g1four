import hashlib

import pytest

from tools.extract_updater.utils import download, extract_zip, sha256_file


def test_sha256_file_matches_hashlib(tmp_path):
    path = tmp_path / "blob.bin"
    path.write_bytes(b"zoom" * 1000)
    assert sha256_file(path) == hashlib.sha256(b"zoom" * 1000).hexdigest()


def test_download_verifies_expected_hash(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"payload")
    expected = hashlib.sha256(b"payload").hexdigest()
    dest = tmp_path / "downloads" / "payload.bin"

    result = download(source.as_uri(), dest, expected)

    assert result == dest
    assert dest.read_bytes() == b"payload"


def test_download_rejects_wrong_hash(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"payload")
    dest = tmp_path / "downloads" / "payload.bin"

    with pytest.raises(ValueError, match="sha256 mismatch"):
        download(source.as_uri(), dest, "0" * 64)

    assert not dest.exists()


def test_extract_zip_rejects_path_traversal(tmp_path):
    import zipfile

    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../evil.txt", "boom")

    with pytest.raises(ValueError, match="unsafe path"):
        extract_zip(evil, tmp_path / "out")


def test_extract_zip_extracts_nested_tree(tmp_path):
    import zipfile

    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("dir/", "")
        zf.writestr("dir/file.bin", b"data")

    out = extract_zip(good, tmp_path / "out")

    assert (out / "dir" / "file.bin").read_bytes() == b"data"


def test_extract_zip_rejects_absolute_path(tmp_path):
    import zipfile

    absolute = tmp_path / "absolute.zip"
    with zipfile.ZipFile(absolute, "w") as zf:
        zf.writestr("/etc/passwd", "boom")

    with pytest.raises(ValueError, match="unsafe path"):
        extract_zip(absolute, tmp_path / "out")


def test_extract_zip_writes_symlink_entry_as_regular_file(tmp_path):
    import stat
    import zipfile

    link_zip = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("link")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(link_zip, "w") as zf:
        zf.writestr(info, "../../outside")

    out = extract_zip(link_zip, tmp_path / "out")

    link = out / "link"
    assert not link.is_symlink()
    assert link.read_bytes() == b"../../outside"


def test_download_failure_leaves_no_residue(tmp_path):
    import urllib.error

    dest_dir = tmp_path / "downloads"
    with pytest.raises(urllib.error.URLError):
        download((tmp_path / "missing.bin").as_uri(), dest_dir / "x.bin", "0" * 64)

    assert list(dest_dir.iterdir()) == []
