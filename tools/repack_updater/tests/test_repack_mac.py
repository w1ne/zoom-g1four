import pytest

from tools.repack_updater import repack_mac


def _fake_app(root):
    resources = root / "Updater.app" / "Contents" / "Resources"
    resources.mkdir(parents=True)
    (resources / "Main.bin").write_bytes(b"original-main")
    (resources / "FS.bin").write_bytes(b"original-fs")
    return root / "Updater.app"


def test_repack_mac_replaces_payloads_and_verifies(tmp_path):
    app = _fake_app(tmp_path)
    new_main = tmp_path / "Main.bin"
    new_main.write_bytes(b"patched-main")

    signed = []
    result = repack_mac.repack(app, {"Main.bin": new_main}, signer=lambda path: signed.append(path), verifier=lambda path: None)

    assert (app / "Contents" / "Resources" / "Main.bin").read_bytes() == b"patched-main"
    assert (app / "Contents" / "Resources" / "FS.bin").read_bytes() == b"original-fs"
    assert signed == [app]
    assert result["verified"] is True


def test_repack_mac_rejects_missing_payload(tmp_path):
    app = _fake_app(tmp_path)
    missing = tmp_path / "Nope.bin"
    missing.write_bytes(b"x")

    with pytest.raises(FileNotFoundError, match="Nope.bin"):
        repack_mac.repack(app, {"Nope.bin": missing}, signer=lambda path: None, verifier=lambda path: None)
