"""Read-only backup: identity, patches, filesystem, manifest, timings."""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import manifest as manifest_module
from .oracle import compare_names, extract_names_from_path
from .pedal import PedalError
from .transport import TransportError


@dataclass
class BackupResult:
    manifest: dict
    manifest_path: Path
    artifact_dir: Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_name(name: str) -> None:
    if not name or name in (".", "..") or "/" in name or "\\" in name or Path(name).name != name:
        raise PedalError(f"unsafe file name from device: {name!r}")


def run_backup(pedal, out_dir: Path, manifests_dir: Path, oracle_path: Path | None = None) -> BackupResult:
    out_dir = Path(out_dir)
    manifests_dir = Path(manifests_dir)
    started = time.perf_counter()

    identity = pedal.identity()

    backup_error = None
    try:
        pedal.pcmode_on()
        count, patch_size, bank_size = pedal.patch_check()

        patch_total_start = time.perf_counter()
        patches = []
        patch_blobs = {}
        for location in range(1, count + 1):
            read_start = time.perf_counter()
            data = pedal.patch_download(location, bank_size)
            read_seconds = time.perf_counter() - read_start
            patch_blobs[location] = data
            patches.append(
                {
                    "location": location,
                    "sha256": _sha256(data),
                    "size": len(data),
                    "read_seconds": round(read_seconds, 4),
                    "crc32_device_ok": True,
                }
            )
        patch_total_seconds = time.perf_counter() - patch_total_start

        listing_start = time.perf_counter()
        names = []
        name = pedal.file_wild(first=True)
        while name:
            names.append(name)
            name = pedal.file_wild(first=False)
        listing_seconds = time.perf_counter() - listing_start

        for name in names:
            _validate_name(name)

        fs_total_start = time.perf_counter()
        files = []
        file_blobs = {}
        for name in names:
            read_start = time.perf_counter()
            data = pedal.file_download(name)
            pedal.file_close()
            read_seconds = time.perf_counter() - read_start
            file_blobs[name] = data
            files.append(
                {
                    "name": name,
                    "sha256": _sha256(data),
                    "size": len(data),
                    "read_seconds": round(read_seconds, 4),
                    "crc32_device_ok": True,
                }
            )
        fs_total_seconds = time.perf_counter() - fs_total_start
    except BaseException as error:
        backup_error = error
        raise
    finally:
        try:
            pedal.pcmode_off()
        except (PedalError, TransportError):
            if backup_error is None:
                raise

    oracle = {"source": None, "device_only": [], "oracle_only": []}
    if oracle_path is not None and Path(oracle_path).is_file():
        oracle["source"] = str(oracle_path)
        oracle.update(compare_names(set(names), extract_names_from_path(oracle_path)))

    manifest = {
        "schema_version": manifest_module.SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "identity": identity,
        "patch_bank": {"count": count, "patch_size": patch_size, "bank_size": bank_size},
        "patches": patches,
        "fs": {"files": files, "listing_seconds": round(listing_seconds, 4)},
        "oracle": oracle,
        "timings": {
            "patch_total_seconds": round(patch_total_seconds, 4),
            "fs_total_seconds": round(fs_total_seconds, 4),
            "total_seconds": round(time.perf_counter() - started, 4),
        },
    }
    manifest["state_digest"] = manifest_module.state_digest(manifest)

    artifact_dir = out_dir / manifest["state_digest"]
    (artifact_dir / "patches").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "fs").mkdir(parents=True, exist_ok=True)
    for location, data in patch_blobs.items():
        (artifact_dir / "patches" / f"{location:03d}.zptc").write_bytes(data)
    for name, data in file_blobs.items():
        (artifact_dir / "fs" / name).write_bytes(data)

    manifest_path = manifest_module.write_manifest(manifest, manifests_dir)
    return BackupResult(manifest=manifest, manifest_path=manifest_path, artifact_dir=artifact_dir)
