"""Immutable facts about the official G1 FOUR v2.00 packages.

All hashes were measured on 2026-09-27 from the files served at these URLs.
Do not edit without re-verifying against a fresh download.
"""

OFFICIAL_PACKAGES = {
    "mac": {
        "filename": "G1_FOUR_v2.00_Mac_E.zip",
        "url": "https://zoomcorp.com/documents/57/G1_FOUR_v2.00_Mac_E.zip",
        "sha256": "f90c831af6a8d43ec480f69d78a6a1c16369ac7902a8a85086aa581720b05010",
    },
    "win": {
        "filename": "G1_FOUR_v2.00_Win_E.zip",
        "url": "https://zoomcorp.com/documents/51/G1_FOUR_v2.00_Win_E.zip",
        "sha256": "f94adce31934635141bedfbf832e974aa4260363aa14c1145bab681c5dd12131",
    },
}

PAYLOADS = {
    "ROM.bin": {
        "size": 163840,
        "sha256": "5ee756a5dee51b4e790a6e6f6b6c0a8a1ea531c245a13124e8a5897530b01622",
    },
    "Main.bin": {
        "size": 493412,
        "sha256": "43060686fce75e175a217194ab1be3aeffe0be7d59f9d3df4181d41b9d3cc5a7",
    },
    "FS.bin": {
        "size": 3137536,
        "sha256": "7dd2821c02414d548b900b31586a1b42ccf1a4a4bd1e69208cb427211606f8aa",
    },
    "MAIN_INFO.bin": {
        "size": 4096,
        "sha256": "8d18a37537a469106dd87335f9899599c632cc32cb4cdad2bfdd5121b4022f38",
    },
    "Preset.bin": {
        "size": 45056,
        "sha256": "969e95657c0a92de94680447734c621bbc479ec5a1c4b63bb4ce0eaea33d3a29",
    },
}

# PE resource ids under .rsrc/1041/BIN/ inside the Windows updater EXE.
WIN_BIN_RESOURCE_IDS = {
    142: "ROM.bin",
    129: "Main.bin",
    136: "FS.bin",
    139: "MAIN_INFO.bin",
    133: "Preset.bin",
}

SEVENZIP_CANDIDATES = ("7zz", "7z")

# Resource directory layout produced by `7zz x` for the Windows updater EXE.
WIN_RESOURCE_BIN_DIR_PARTS = (".rsrc", "1041", "BIN")
