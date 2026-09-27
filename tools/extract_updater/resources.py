"""Locate payloads in the unpacked Mac app and extract PE resources from the EXE."""

import shutil
import subprocess
from pathlib import Path

from . import constants


def find_mac_resources(root: Path) -> dict[str, Path]:
    root = Path(root)
    found: dict[str, Path] = {}
    for name in constants.PAYLOADS:
        for candidate in root.rglob(name):
            if candidate.parent.name == "Resources":
                found[name] = candidate
                break
    missing = sorted(set(constants.PAYLOADS) - set(found))
    if missing:
        raise FileNotFoundError(f"missing payloads under {root}: {missing}")
    return found


def find_sevenzip() -> str:
    for candidate in constants.SEVENZIP_CANDIDATES:
        if shutil.which(candidate):
            return candidate
    raise FileNotFoundError("7-Zip not found; install with: brew install sevenzip")


def extract_win_resources(
    exe_path: Path, dest_dir: Path, sevenzip: str | None = None
) -> dict[str, Path]:
    sevenzip = sevenzip or find_sevenzip()
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sevenzip, "x", f"-o{dest_dir}", "-y", str(exe_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    result: dict[str, Path] = {}
    for rid, name in sorted(constants.WIN_BIN_RESOURCE_IDS.items()):
        path = dest_dir / ".rsrc" / "1041" / "BIN" / str(rid)
        if not path.is_file():
            raise FileNotFoundError(f"resource {rid} ({name}) not found under {dest_dir}")
        result[name] = path
    return result
