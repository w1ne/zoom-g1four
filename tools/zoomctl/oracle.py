"""FS.bin name oracle: cross-check device listing against the extracted image.

Heuristic: FS.bin stores effect files in `ZDLFx` wrappers whose names appear as
plain ASCII with known extensions. This is informational only; a difference does
not fail the backup.
"""

import re
from pathlib import Path

KNOWN_EXTENSIONS = ("ZD2", "ZIC", "ZIR", "ZT2")
NAME_RE = re.compile(
    rb"(?<![A-Z0-9_])[A-Z0-9_]{1,12}\.(?:%s)(?![A-Z0-9_])"
    % b"|".join(extension.encode("ascii") for extension in KNOWN_EXTENSIONS)
)


def extract_names(fs_bin: bytes) -> set[str]:
    return {match.decode("ascii") for match in NAME_RE.findall(fs_bin)}


def extract_names_from_path(path: Path) -> set[str]:
    return extract_names(Path(path).read_bytes())


def compare_names(device_names: set[str], oracle_names: set[str]) -> dict:
    return {
        "device_only": sorted(device_names - oracle_names),
        "oracle_only": sorted(oracle_names - device_names),
    }
