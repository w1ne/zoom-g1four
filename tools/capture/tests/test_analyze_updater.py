import json

from tools.capture.analyze_updater import SIGNATURES, STRINGS, main, scan


def test_scan_counts_signatures_and_strings():
    data = (
        bytes([0x52, 0x00, 0x6E, 0x45]) + b"xx" +
        bytes([0x60, 0x20, 0x01]) + b"yy" +
        b"FS.bin" + b"zz" + b"FS.bin"
    )
    report = scan(data)
    assert report["signatures"]["patch_upload_opcode_45"] == 1
    assert report["signatures"]["file_open_write_60_20_01"] == 1
    assert report["signatures"]["file_open_read_60_20_02"] == 0
    assert report["strings"]["FS.bin"] == 2
    assert report["strings"]["Main.bin"] == 0


def test_scan_empty_input_is_all_zero():
    report = scan(b"")
    assert set(report["signatures"]) == set(SIGNATURES)
    assert set(report["strings"]) == set(STRINGS)
    assert all(count == 0 for count in report["signatures"].values())
    assert all(count == 0 for count in report["strings"].values())


def test_signature_table_covers_write_and_read_paths():
    assert "file_open_write_60_20_01" in SIGNATURES
    assert "file_upload_block_60_23" in SIGNATURES
    assert "file_delete_60_24" in SIGNATURES
    assert "file_open_read_60_20_02" in SIGNATURES
    assert "enter_update_mode_01" in SIGNATURES
    assert "file_read_block_60_22" in SIGNATURES
    assert "file_open_other_60_20_00" in SIGNATURES
    assert "file_api_60_27" in SIGNATURES


def test_scan_subtracts_excluded_payload_blobs():
    signature = bytes([0x60, 0x23])
    embedded = signature + b"embedded"
    data = b"code" + signature + b"more" + embedded

    assert scan(data)["signatures"]["file_upload_block_60_23"] == 2
    assert scan(data, [embedded])["signatures"]["file_upload_block_60_23"] == 1


def test_main_json_output(tmp_path, capsys):
    binary = tmp_path / "fake.bin"
    binary.write_bytes(bytes([0x60, 0x23]) + b"FS.bin")

    exit_code = main([str(binary), "--json"])

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["signatures"]["file_upload_block_60_23"] == 1
    assert report["strings"]["FS.bin"] == 1
