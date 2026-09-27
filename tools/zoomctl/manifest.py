"""Backup manifest: canonical JSON, content-addressed state digest, writer."""

import hashlib
import json
import os
from pathlib import Path

SCHEMA_VERSION = 1


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def state_digest(manifest: dict) -> str:
    digest_input = {
        "schema_version": manifest["schema_version"],
        "identity": manifest["identity"],
        "patch_bank": manifest["patch_bank"],
        "patches": [(p["location"], p["sha256"]) for p in manifest["patches"]],
        "files": [(f["name"], f["sha256"]) for f in manifest["fs"]["files"]],
    }
    return hashlib.sha256(canonical_json(digest_input).encode()).hexdigest()


def write_manifest(manifest: dict, manifests_dir: Path) -> Path:
    manifests_dir = Path(manifests_dir)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    actual = state_digest(manifest)
    if manifest.get("state_digest") != actual:
        raise ValueError(
            "state digest mismatch: manifest has "
            f"{manifest.get('state_digest')!r}, computed {actual}"
        )
    path = manifests_dir / f"{actual}.json"
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(tmp_path, path)
    return path
