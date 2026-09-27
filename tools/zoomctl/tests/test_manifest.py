import json

import pytest

from tools.zoomctl.manifest import canonical_json, state_digest, write_manifest


def _sample_manifest():
    return {
        "schema_version": 1,
        "created_utc": "2026-09-27T12:00:00Z",
        "identity": {"model": "G1 Four", "firmware": "2.00", "reply_hex": "7E 00 06 02"},
        "patch_bank": {"count": 60, "patch_size": 32, "bank_size": 10},
        "patches": [{"location": 1, "sha256": "a" * 64, "size": 32, "read_seconds": 0.1}],
        "fs": {"files": [{"name": "X.ZD2", "sha256": "b" * 64, "size": 10, "read_seconds": 0.2}]},
        "oracle": {"source": None, "device_only": [], "oracle_only": []},
        "timings": {"patch_total_seconds": 0.1, "fs_total_seconds": 0.2, "total_seconds": 0.3},
        "state_digest": "c" * 64,
    }


def test_canonical_json_is_sorted_and_compact():
    assert canonical_json({"b": 1, "a": [2, 3]}) == '{"a":[2,3],"b":1}'


def test_state_digest_is_stable_and_content_addressed():
    manifest = _sample_manifest()
    digest = state_digest(manifest)
    assert digest == state_digest(json.loads(json.dumps(manifest)))
    changed = _sample_manifest()
    changed["patches"][0]["sha256"] = "d" * 64
    assert state_digest(changed) != digest


def test_write_manifest_uses_digest_filename(tmp_path):
    manifest = _sample_manifest()
    manifest["state_digest"] = state_digest(manifest)
    path = write_manifest(manifest, tmp_path)
    assert path == tmp_path / f"{manifest['state_digest']}.json"
    assert json.loads(path.read_text())["schema_version"] == 1


def test_state_digest_ignores_timings_oracle_and_created():
    baseline = state_digest(_sample_manifest())
    changed = _sample_manifest()
    changed["created_utc"] = "2030-01-01T00:00:00Z"
    changed["oracle"] = {"source": "FS.bin", "device_only": ["X"], "oracle_only": []}
    changed["timings"] = {
        "patch_total_seconds": 99,
        "fs_total_seconds": 99,
        "total_seconds": 99,
    }

    assert state_digest(changed) == baseline


def test_write_manifest_rejects_wrong_digest(tmp_path):
    manifest = _sample_manifest()
    manifest["state_digest"] = "deadbeef"

    with pytest.raises(ValueError, match="state digest mismatch"):
        write_manifest(manifest, tmp_path)
