from tools.zoomctl.oracle import compare_names, extract_names, extract_names_from_path


def test_extract_names_finds_known_extensions_only():
    data = (
        b"ZDLFx" + b"ZEN_DRV.ZD2\x00" +
        b"junk README.TXT more" +
        b"AMP.ZIC\x00" + b"ICON.ZIR\x00" + b"FLST_SEQ.ZT2\x00" +
        b"lower.zd2"
    )
    names = extract_names(data)
    assert names == {"ZEN_DRV.ZD2", "AMP.ZIC", "ICON.ZIR", "FLST_SEQ.ZT2"}


def test_extract_names_ignores_non_names():
    assert extract_names(b"\x00\x01\x02 random bytes") == set()


def test_compare_names_reports_both_directions():
    result = compare_names({"A.ZD2", "B.ZD2"}, {"A.ZD2", "C.ZD2"})
    assert result["device_only"] == ["B.ZD2"]
    assert result["oracle_only"] == ["C.ZD2"]


def test_extract_names_respects_token_boundaries():
    data = b"NINE_CHAR.ZD2\x00" + b"X.ZD2X\x00" + b"Y.ZD2\x00"

    assert extract_names(data) == {"NINE_CHAR.ZD2", "Y.ZD2"}


def test_extract_names_from_path_reads_file(tmp_path):
    path = tmp_path / "FS.bin"
    path.write_bytes(b"AMP.ZIC\x00")

    assert extract_names_from_path(path) == {"AMP.ZIC"}
