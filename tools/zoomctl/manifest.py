"""Backup manifest: canonical JSON, content-addressed state digest, writer."""

import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 1


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def state_digest(manifest: dict) -> str:
    digest_input = {
        "identity": manifest["identity"],
        "patch_bank": manifest["patch_bank"],
        "patches": [(p["location"], p["sha256"]) for p in manifest["patches"]],
        "files": [(f["name"], f["sha256"]) for f in manifest["fs"]["files"]],
    }
    return hashlib.sha256(canonical_json(digest_input).encode()).hexdigest()


def write_manifest(manifest: dict, manifests_dir: Path) -> Path:
    manifests_dir = Path(manifests_dir)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    path = manifests_dir / f"{manifest['state_digest']}.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return path
