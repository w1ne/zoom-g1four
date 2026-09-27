import pytest

from tools.repack_updater import repack_win


def test_bin_resource_ids_cover_the_five_payloads():
    assert set(repack_win.BIN_RESOURCE_IDS) == {142, 129, 136, 139, 133}
    assert repack_win.BIN_RESOURCE_IDS[129] == "Main.bin"


def test_patch_bytes_replaces_range():
    original = bytearray(b"0123456789")
    result = repack_win.patch_bytes(original, offset=2, data=b"XY")
    assert bytes(result) == b"01XY456789"


def test_patch_bytes_rejects_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        repack_win.patch_bytes(bytearray(b"abc"), 5, b"XY")


def test_repack_rejects_size_change(tmp_path, monkeypatch):
    exe = tmp_path / "fake.exe"
    exe.write_bytes(b"0123456789")
    payload = tmp_path / "Main.bin"
    payload.write_bytes(b"toolong")

    class FakePE:
        def close(self):
            pass

    monkeypatch.setattr(repack_win.pefile, "PE", lambda data: FakePE())
    monkeypatch.setattr(repack_win, "find_resource_offset", lambda pe, resource_id: (0, 3))

    with pytest.raises(ValueError, match="size mismatch"):
        repack_win.repack(exe, tmp_path / "out.exe", {129: payload})
