"""Generic file utilities: streaming sha256, verified downloads, safe unzip."""

import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# zoomcorp.com WAF returns HTTP 403 for urllib's default User-Agent.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path, expected_sha256: str) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(dir=dest.parent, delete=False)
    tmp_path = Path(tmp.name)
    try:
        with tmp:
            request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                shutil.copyfileobj(response, tmp)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    actual = sha256_file(tmp_path)
    if actual != expected_sha256:
        tmp_path.unlink(missing_ok=True)
        raise ValueError(
            f"sha256 mismatch for {url}: expected {expected_sha256}, got {actual}"
        )
    tmp_path.replace(dest)
    return dest


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    dest_dir = Path(dest_dir)
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            target = (dest_dir / info.filename).resolve()
            if not target.is_relative_to(dest_dir):
                raise ValueError(f"unsafe path in zip: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                target.chmod(mode)
    return dest_dir
