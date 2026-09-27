from tools.repack_updater import repack_win


def test_bin_resource_ids_cover_the_five_payloads():
    assert set(repack_win.BIN_RESOURCE_IDS) == {142, 129, 136, 139, 133}
    assert repack_win.BIN_RESOURCE_IDS[129] == "Main.bin"


def test_patch_bytes_replaces_range():
    original = bytearray(b"0123456789")
    result = repack_win.patch_bytes(original, offset=2, data=b"XY")
    assert bytes(result) == b"01XY456789"
