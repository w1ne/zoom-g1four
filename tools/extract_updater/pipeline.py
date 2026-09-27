"""Orchestration: fetch pristine packages, extract, cross-check, verify."""

import shutil
from pathlib import Path

from . import constants
from .resources import extract_win_resources, find_mac_resources
from .utils import download, extract_zip, sha256_file


def fetch_all(official_dir: Path) -> dict[str, Path]:
    official_dir = Path(official_dir)
    official_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for key, package in constants.OFFICIAL_PACKAGES.items():
        dest = official_dir / package["filename"]
        if dest.is_file() and sha256_file(dest) == package["sha256"]:
            paths[key] = dest
            continue
        paths[key] = download(package["url"], dest, package["sha256"])
    return paths


def canonicalize(
    mac: dict[str, Path], win: dict[str, Path], report_path: Path | None = None
) -> dict[str, Path]:
    if set(mac) != set(win):
        raise ValueError(f"payload set mismatch: mac={sorted(mac)} win={sorted(win)}")
    for name in sorted(mac):
        mac_hash = sha256_file(mac[name])
        win_hash = sha256_file(win[name])
        if mac_hash != win_hash:
            message = f"platform mismatch for {name}: mac={mac_hash} win={win_hash}"
            if report_path is not None:
                report_path.write_text(message + "\n")
            raise ValueError(message)
    return mac


def write_sha256sums(bins: dict[str, Path], out_path: Path) -> Path:
    out_path = Path(out_path)
    lines = [f"{sha256_file(path)}  {name}\n" for name, path in sorted(bins.items())]
    out_path.write_text("".join(lines), encoding="ascii")
    return out_path


def extract_all(official_dir: Path, out_dir: Path, work_dir: Path) -> dict[str, Path]:
    packages = fetch_all(official_dir)
    mac_root = extract_zip(packages["mac"], work_dir / "mac")
    win_root = extract_zip(packages["win"], work_dir / "win")
    exes = list(win_root.rglob("*.exe"))
    if len(exes) != 1:
        raise FileNotFoundError(
            f"expected exactly one updater EXE under {win_root}, found {len(exes)}"
        )
    mac_bins = find_mac_resources(mac_root)
    win_bins = extract_win_resources(exes[0], work_dir / "win-resources")
    bins = canonicalize(mac_bins, win_bins, report_path=work_dir / "mismatch-report.txt")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    final = {name: out_dir / name for name in bins}
    for name, src in bins.items():
        shutil.copyfile(src, final[name])
    write_sha256sums(final, out_dir / "SHA256SUMS")
    return final


def verify_all(extracted_dir: Path) -> None:
    extracted_dir = Path(extracted_dir)
    for name, meta in constants.PAYLOADS.items():
        path = extracted_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"missing {path}")
        size = path.stat().st_size
        if size != meta["size"]:
            raise ValueError(f"{name}: expected size {meta['size']}, got {size}")
        actual = sha256_file(path)
        if actual != meta["sha256"]:
            raise ValueError(f"{name}: expected sha256 {meta['sha256']}, got {actual}")
    expected = "".join(
        f"{meta['sha256']}  {name}\n" for name, meta in sorted(constants.PAYLOADS.items())
    )
    actual_sums = (extracted_dir / "SHA256SUMS").read_text()
    if actual_sums != expected:
        raise ValueError("SHA256SUMS does not match constants")
    print("verify OK: " + ", ".join(sorted(constants.PAYLOADS)))
