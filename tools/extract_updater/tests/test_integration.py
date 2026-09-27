import hashlib

import pytest

from tools.extract_updater import constants
from tools.extract_updater.pipeline import extract_all


@pytest.mark.integration
def test_end_to_end_matches_known_good_hashes(tmp_path):
    bins = extract_all(tmp_path / "official", tmp_path / "extracted", tmp_path / "work")

    for name, meta in constants.PAYLOADS.items():
        assert bins[name].stat().st_size == meta["size"], name
        digest = hashlib.sha256(bins[name].read_bytes()).hexdigest()
        assert digest == meta["sha256"], name

    expected = "".join(
        f"{meta['sha256']}  {name}\n" for name, meta in sorted(constants.PAYLOADS.items())
    )
    assert (tmp_path / "extracted" / "SHA256SUMS").read_text() == expected
