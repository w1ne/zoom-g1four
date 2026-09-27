"""E5: replace payloads inside the unpacked Mac updater .app and ad-hoc sign it.

Zero-change round-trip: replacing with the extracted bins must leave the
resource bytes byte-identical (trivially true) and the app launchable after an
ad-hoc signature.
"""

import hashlib
import subprocess
from pathlib import Path


def _codesign(path: Path) -> None:
    subprocess.run(
        ["codesign", "--force", "--deep", "--sign", "-", str(path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repack(app_dir: Path, bins: dict[str, Path], signer=_codesign) -> dict:
    app_dir = Path(app_dir)
    resources = app_dir / "Contents" / "Resources"
    if not resources.is_dir():
        raise FileNotFoundError(f"no Resources directory under {app_dir}")
    expected = {}
    for name, source in bins.items():
        target = resources / name
        if not target.is_file():
            raise FileNotFoundError(f"payload {name} not present in {resources}")
        data = Path(source).read_bytes()
        target.write_bytes(data)
        expected[name] = hashlib.sha256(data).hexdigest()
    signer(app_dir)
    verified = all(_sha256(resources / name) == digest for name, digest in expected.items())
    return {"app": str(app_dir), "replaced": sorted(bins), "verified": verified}
