import re

from tools.extract_updater import constants


def test_official_packages_are_https_with_hex_hashes():
    for key, pkg in constants.OFFICIAL_PACKAGES.items():
        assert pkg["url"].startswith("https://"), key
        assert pkg["url"].endswith(pkg["filename"]), key
        assert re.fullmatch(r"[0-9a-f]{64}", pkg["sha256"]), key


def test_payload_sizes_and_hashes_match_recon():
    assert {name: meta["size"] for name, meta in constants.PAYLOADS.items()} == {
        "ROM.bin": 163840,
        "Main.bin": 493412,
        "FS.bin": 3137536,
        "MAIN_INFO.bin": 4096,
        "Preset.bin": 45056,
    }
    for name, meta in constants.PAYLOADS.items():
        assert re.fullmatch(r"[0-9a-f]{64}", meta["sha256"]), name


def test_win_resource_ids_cover_exactly_the_payloads():
    assert set(constants.WIN_BIN_RESOURCE_IDS) == {142, 129, 136, 139, 133}
    assert set(constants.WIN_BIN_RESOURCE_IDS.values()) == set(constants.PAYLOADS)
