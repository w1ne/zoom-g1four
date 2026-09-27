# P0 — Official Firmware Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the canonical, hash-verified official G1 FOUR v2.00 payload set (`ROM.bin`, `Main.bin`, `FS.bin`, `MAIN_INFO.bin`, `Preset.bin`) in `firmware/extracted/` with a committed `SHA256SUMS`, extracted identically from both the Mac and Windows official packages.

**Architecture:** Four small Python modules under `tools/extract_updater/` (constants, utils, resources, pipeline) plus a `__main__` CLI. Constants hold every measured fact (URLs, package hashes, payload hashes/sizes, PE resource ID map) so the pipeline is pure verification, never invention. Unit tests use tiny fixtures and monkeypatching; one `integration`-marked test downloads the real packages and asserts byte-level equality across platforms.

**Tech Stack:** Python 3.11+ (system 3.14 present), stdlib only (`hashlib`, `urllib`, `zipfile`, `subprocess`), pytest, 7-Zip CLI (`7zz` via `brew install sevenzip`, already installed), git.

**Spec:** `docs/superpowers/specs/2026-09-27-zoom-g1four-design.md` (P0, M0). The extract/repack container round-trip (spec E5) is explicitly NOT in this plan; it is required before P5a.

---

## Recon facts recorded 2026-09-27 (do not re-derive)

- Mac package URL: `https://zoomcorp.com/documents/57/G1_FOUR_v2.00_Mac_E.zip`
  sha256 `f90c831af6a8d43ec480f69d78a6a1c16369ac7902a8a85086aa581720b05010`
  (~5.0 MB zip, 22 files; `G1 FOUR_v2.00_Mac_E/ZOOM G1 FOUR System v2.00 Updater.app/Contents/Resources/` contains the five bins as plain files)
- Windows package URL: `https://zoomcorp.com/documents/51/G1_FOUR_v2.00_Win_E.zip`
  sha256 `f94adce31934635141bedfbf832e974aa4260363aa14c1145bab681c5dd12131`
  (single 4,193,320-byte PE32 GUI exe `ZOOM G1 FOUR System v2.00 Updater.exe`)
- PE resources under `.rsrc/1041/BIN/` map to Mac payloads by identical sha256:
  `142` = `ROM.bin`, `129` = `Main.bin`, `136` = `FS.bin`, `139` = `MAIN_INFO.bin`, `133` = `Preset.bin`
- Payload hashes/sizes (measured):
  - `ROM.bin` 163840 bytes `5ee756a5dee51b4e790a6e6f6b6c0a8a1ea531c245a13124e8a5897530b01622`
  - `Main.bin` 493412 bytes `43060686fce75e175a217194ab1be3aeffe0be7d59f9d3df4181d41b9d3cc5a7`
  - `FS.bin` 3137536 bytes `7dd2821c02414d548b900b31586a1b42ccf1a4a4bd1e69208cb427211606f8aa`
  - `MAIN_INFO.bin` 4096 bytes `8d18a37537a469106dd87335f9899599c632cc32cb4cdad2bfdd5121b4022f38`
  - `Preset.bin` 45056 bytes `969e95657c0a92de94680447734c621bbc479ec5a1c4b63bb4ce0eaea33d3a29`
- Container magics observed (for later phases, not needed here): `ROM.bin`/`Main.bin` start with ASCII `TIPAcYSX`; `FS.bin` starts `55 AA 00 01`; `FS.bin` contains `ZDLFx` effect wrappers.

## File structure

```
pyproject.toml                                   # pytest config, project metadata
.venv/                                           # local venv (gitignored)
.work/                                           # scratch extraction area (gitignored)
firmware/official/                               # downloaded zips (gitignored)
firmware/extracted/                              # canonical bins (gitignored) + SHA256SUMS (committed)
tools/__init__.py
tools/extract_updater/__init__.py
tools/extract_updater/constants.py               # all measured facts
tools/extract_updater/utils.py                   # sha256, download, zip extraction
tools/extract_updater/resources.py               # mac resource finder, PE resource extractor
tools/extract_updater/pipeline.py                # fetch/extract/verify orchestration
tools/extract_updater/__main__.py                # CLI
tools/extract_updater/tests/test_package.py
tools/extract_updater/tests/test_constants.py
tools/extract_updater/tests/test_utils.py
tools/extract_updater/tests/test_resources.py
tools/extract_updater/tests/test_pipeline.py
tools/extract_updater/tests/test_integration.py  # network test, -m integration
docs/research/2026-09-27-p0-recon.md             # verified extraction facts
```

---

### Task 1: Repo tooling scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `tools/__init__.py`
- Create: `tools/extract_updater/__init__.py`
- Create: `tools/extract_updater/tests/test_package.py`
- Modify: `.gitignore` (add `.work/`)

- [ ] **Step 1: Write the failing test**

`tools/extract_updater/tests/test_package.py`:

```python
def test_package_imports():
    import tools.extract_updater  # noqa: F401
```

- [ ] **Step 2: Create venv and install pytest**

Run:
```bash
cd /Users/andrii/Projects/zoom-g1four
python3 -m venv .venv
.venv/bin/python -m pip install -q -U pip pytest
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_package.py -v`
Expected: collection error / `ModuleNotFoundError: No module named 'tools'` (pyproject with `pythonpath` does not exist yet, packages do not exist yet)

- [ ] **Step 4: Create pyproject and package files**

`pyproject.toml`:

```toml
[project]
name = "zoom-g1four"
version = "0.1.0"
description = "Reverse engineering and open-firmware effort for the Zoom G1 Four"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tools"]
addopts = "-m 'not integration'"
markers = [
    "integration: end-to-end tests that download vendor packages (run with -m integration)",
]
```

`tools/__init__.py`: empty file.
`tools/extract_updater/__init__.py`: empty file.

Append to `.gitignore` (after the `.venv/` line):

```
.work/
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_package.py -v`
Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tools .gitignore
git commit -m "chore: scaffold extract_updater package and pytest config"
```

---

### Task 2: Constants with golden facts

**Files:**
- Create: `tools/extract_updater/constants.py`
- Create: `tools/extract_updater/tests/test_constants.py`

- [ ] **Step 1: Write the failing test**

`tools/extract_updater/tests/test_constants.py`:

```python
import re

from tools.extract_updater import constants


def test_official_packages_are_https_with_hex_hashes():
    for key, pkg in constants.OFFICIAL_PACKAGES.items():
        assert pkg["url"].startswith("https://"), key
        assert pkg["url"].endswith(pkg["filename"]), key
        assert re.fullmatch(r"[0-9a-f]{64}", pkg["sha256"]), key


def test_payload_sizes_and_hashes_match_recon():
    assert {name: meta["size"] for name, meta in constants.PAYLOADS.items()} == {
        "ROM.bin": 163840,
        "Main.bin": 493412,
        "FS.bin": 3137536,
        "MAIN_INFO.bin": 4096,
        "Preset.bin": 45056,
    }
    for name, meta in constants.PAYLOADS.items():
        assert re.fullmatch(r"[0-9a-f]{64}", meta["sha256"]), name


def test_win_resource_ids_cover_exactly_the_payloads():
    assert set(constants.WIN_BIN_RESOURCE_IDS) == {142, 129, 136, 139, 133}
    assert set(constants.WIN_BIN_RESOURCE_IDS.values()) == set(constants.PAYLOADS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_constants.py -v`
Expected: `ModuleNotFoundError: No module named 'tools.extract_updater.constants'`

- [ ] **Step 3: Write the implementation**

`tools/extract_updater/constants.py`:

```python
"""Immutable facts about the official G1 FOUR v2.00 packages.

All hashes were measured on 2026-09-27 from the files served at these URLs.
Do not edit without re-verifying against a fresh download.
"""

OFFICIAL_PACKAGES = {
    "mac": {
        "filename": "G1_FOUR_v2.00_Mac_E.zip",
        "url": "https://zoomcorp.com/documents/57/G1_FOUR_v2.00_Mac_E.zip",
        "sha256": "f90c831af6a8d43ec480f69d78a6a1c16369ac7902a8a85086aa581720b05010",
    },
    "win": {
        "filename": "G1_FOUR_v2.00_Win_E.zip",
        "url": "https://zoomcorp.com/documents/51/G1_FOUR_v2.00_Win_E.zip",
        "sha256": "f94adce31934635141bedfbf832e974aa4260363aa14c1145bab681c5dd12131",
    },
}

PAYLOADS = {
    "ROM.bin": {
        "size": 163840,
        "sha256": "5ee756a5dee51b4e790a6e6f6b6c0a8a1ea531c245a13124e8a5897530b01622",
    },
    "Main.bin": {
        "size": 493412,
        "sha256": "43060686fce75e175a217194ab1be3aeffe0be7d59f9d3df4181d41b9d3cc5a7",
    },
    "FS.bin": {
        "size": 3137536,
        "sha256": "7dd2821c02414d548b900b31586a1b42ccf1a4a4bd1e69208cb427211606f8aa",
    },
    "MAIN_INFO.bin": {
        "size": 4096,
        "sha256": "8d18a37537a469106dd87335f9899599c632cc32cb4cdad2bfdd5121b4022f38",
    },
    "Preset.bin": {
        "size": 45056,
        "sha256": "969e95657c0a92de94680447734c621bbc479ec5a1c4b63bb4ce0eaea33d3a29",
    },
}

# PE resource ids under .rsrc/1041/BIN/ inside the Windows updater EXE.
WIN_BIN_RESOURCE_IDS = {
    142: "ROM.bin",
    129: "Main.bin",
    136: "FS.bin",
    139: "MAIN_INFO.bin",
    133: "Preset.bin",
}

SEVENZIP_CANDIDATES = ("7zz", "7z")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_constants.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add tools/extract_updater/constants.py tools/extract_updater/tests/test_constants.py
git commit -m "feat: record official package and payload facts as constants"
```

---

### Task 3: Hashing and download utilities

**Files:**
- Create: `tools/extract_updater/utils.py`
- Create: `tools/extract_updater/tests/test_utils.py`

- [ ] **Step 1: Write the failing tests**

`tools/extract_updater/tests/test_utils.py`:

```python
import hashlib

import pytest

from tools.extract_updater.utils import download, extract_zip, sha256_file


def test_sha256_file_matches_hashlib(tmp_path):
    path = tmp_path / "blob.bin"
    path.write_bytes(b"zoom" * 1000)
    assert sha256_file(path) == hashlib.sha256(b"zoom" * 1000).hexdigest()


def test_download_verifies_expected_hash(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"payload")
    expected = hashlib.sha256(b"payload").hexdigest()
    dest = tmp_path / "downloads" / "payload.bin"

    result = download(source.as_uri(), dest, expected)

    assert result == dest
    assert dest.read_bytes() == b"payload"


def test_download_rejects_wrong_hash(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"payload")
    dest = tmp_path / "downloads" / "payload.bin"

    with pytest.raises(ValueError, match="sha256 mismatch"):
        download(source.as_uri(), dest, "0" * 64)

    assert not dest.exists()


def test_extract_zip_rejects_path_traversal(tmp_path):
    import zipfile

    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../evil.txt", "boom")

    with pytest.raises(ValueError, match="unsafe path"):
        extract_zip(evil, tmp_path / "out")


def test_extract_zip_extracts_nested_tree(tmp_path):
    import zipfile

    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("dir/", "")
        zf.writestr("dir/file.bin", b"data")

    out = extract_zip(good, tmp_path / "out")

    assert (out / "dir" / "file.bin").read_bytes() == b"data"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_utils.py -v`
Expected: `ModuleNotFoundError: No module named 'tools.extract_updater.utils'`

- [ ] **Step 3: Write the implementation**

`tools/extract_updater/utils.py`:

```python
"""Generic file utilities: streaming sha256, verified downloads, safe unzip."""

import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path, expected_sha256: str) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
        with urllib.request.urlopen(url) as response:
            shutil.copyfileobj(response, tmp)
        tmp_path = Path(tmp.name)
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
    return dest_dir
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_utils.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add tools/extract_updater/utils.py tools/extract_updater/tests/test_utils.py
git commit -m "feat: add verified download and safe zip extraction utilities"
```

---

### Task 4: Resource finders (Mac app + Windows PE)

**Files:**
- Create: `tools/extract_updater/resources.py`
- Create: `tools/extract_updater/tests/test_resources.py`

- [ ] **Step 1: Write the failing tests**

`tools/extract_updater/tests/test_resources.py`:

```python
import subprocess
from pathlib import Path

import pytest

from tools.extract_updater import constants, resources


def _make_mac_tree(root: Path) -> Path:
    res = root / "pkg" / "Updater.app" / "Contents" / "Resources"
    res.mkdir(parents=True)
    for name in constants.PAYLOADS:
        (res / name).write_bytes(b"x")
    return root


def test_find_mac_resources_returns_all_payloads(tmp_path):
    root = _make_mac_tree(tmp_path)
    found = resources.find_mac_resources(root)
    assert set(found) == set(constants.PAYLOADS)
    assert found["Main.bin"].parent.name == "Resources"


def test_find_mac_resources_reports_missing(tmp_path):
    root = _make_mac_tree(tmp_path)
    (root / "pkg" / "Updater.app" / "Contents" / "Resources" / "FS.bin").unlink()
    with pytest.raises(FileNotFoundError, match="FS.bin"):
        resources.find_mac_resources(root)


def test_find_sevenzip_reports_install_hint(monkeypatch):
    monkeypatch.setattr(resources.shutil, "which", lambda name: None)
    with pytest.raises(FileNotFoundError, match="brew install sevenzip"):
        resources.find_sevenzip()


def test_extract_win_resources_maps_ids_to_names(tmp_path, monkeypatch):
    exe = tmp_path / "updater.exe"
    exe.write_bytes(b"MZ")
    dest = tmp_path / "out"

    def fake_run(cmd, check, stdout, stderr):
        out_dir = Path(cmd[2][2:])
        for rid in constants.WIN_BIN_RESOURCE_IDS:
            target = out_dir / ".rsrc" / "1041" / "BIN" / str(rid)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f"resource-{rid}".encode())
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(resources.subprocess, "run", fake_run)

    result = resources.extract_win_resources(exe, dest, sevenzip="7zz")

    assert set(result) == set(constants.PAYLOADS)
    assert result["ROM.bin"].read_bytes() == b"resource-142"


def test_extract_win_resources_reports_missing_resource(tmp_path, monkeypatch):
    exe = tmp_path / "updater.exe"
    exe.write_bytes(b"MZ")

    def fake_run(cmd, check, stdout, stderr):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(resources.subprocess, "run", fake_run)

    with pytest.raises(FileNotFoundError, match="resource 129"):
        resources.extract_win_resources(exe, tmp_path / "out", sevenzip="7zz")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_resources.py -v`
Expected: `ModuleNotFoundError: No module named 'tools.extract_updater.resources'`

- [ ] **Step 3: Write the implementation**

`tools/extract_updater/resources.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_resources.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add tools/extract_updater/resources.py tools/extract_updater/tests/test_resources.py
git commit -m "feat: mac resource finder and PE resource extraction"
```

---

### Task 5: Pipeline — fetch, cross-check, canonical output

**Files:**
- Create: `tools/extract_updater/pipeline.py`
- Create: `tools/extract_updater/tests/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

`tools/extract_updater/tests/test_pipeline.py`:

```python
import pytest

from tools.extract_updater import pipeline


def _bins(tmp_path, name_to_bytes):
    out = {}
    for name, data in name_to_bytes.items():
        path = tmp_path / name
        path.write_bytes(data)
        out[name] = path
    return out


def test_write_sha256sums_sorted_gnu_format(tmp_path):
    bins = _bins(tmp_path, {"b.bin": b"bee", "a.bin": b"aye"})
    out = pipeline.write_sha256sums(bins, tmp_path / "SHA256SUMS")
    lines = out.read_text().splitlines()
    assert lines[0].startswith(pipeline.sha256_file(bins["a.bin"]))
    assert lines[0].endswith("  a.bin")
    assert lines[1].endswith("  b.bin")


def test_canonicalize_accepts_identical_payloads(tmp_path):
    mac = _bins(tmp_path, {"Main.bin": b"same"})
    win_dir = tmp_path / "win"
    win_dir.mkdir()
    win = {}
    for name in mac:
        path = win_dir / name
        path.write_bytes(b"same")
        win[name] = path

    result = pipeline.canonicalize(mac, win)

    assert result == mac


def test_canonicalize_writes_report_and_raises_on_mismatch(tmp_path):
    mac = _bins(tmp_path, {"Main.bin": b"mac"})
    win_dir = tmp_path / "win"
    win_dir.mkdir()
    win_path = win_dir / "Main.bin"
    win_path.write_bytes(b"win")
    report = tmp_path / "mismatch-report.txt"

    with pytest.raises(ValueError, match="platform mismatch for Main.bin"):
        pipeline.canonicalize(mac, {"Main.bin": win_path}, report_path=report)

    text = report.read_text()
    assert "Main.bin" in text
    assert pipeline.sha256_file(mac["Main.bin"]) in text
    assert pipeline.sha256_file(win_path) in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_pipeline.py -v`
Expected: `ModuleNotFoundError: No module named 'tools.extract_updater.pipeline'`

- [ ] **Step 3: Write the implementation**

`tools/extract_updater/pipeline.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_pipeline.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add tools/extract_updater/pipeline.py tools/extract_updater/tests/test_pipeline.py
git commit -m "feat: extraction pipeline with cross-platform mismatch abort"
```

---

### Task 6: CLI entry point

**Files:**
- Create: `tools/extract_updater/__main__.py`

- [ ] **Step 1: Write the command and check it fails**

Run: `.venv/bin/python -m tools.extract_updater verify`
Expected: `No module named tools.extract_updater.__main__`

- [ ] **Step 2: Write the implementation**

`tools/extract_updater/__main__.py`:

```python
"""CLI: python -m tools.extract_updater {fetch,extract,verify}"""

import argparse
from pathlib import Path

from .pipeline import extract_all, fetch_all, verify_all
from .utils import sha256_file


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.extract_updater")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="download the pristine official packages")
    sub.add_parser("extract", help="extract canonical bins + SHA256SUMS")
    sub.add_parser("verify", help="verify extracted artifacts against known-good hashes")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]
    official = repo / "firmware" / "official"
    extracted = repo / "firmware" / "extracted"
    work = repo / ".work" / "p0"

    if args.command == "fetch":
        for key, path in fetch_all(official).items():
            print(f"{key}: {path} {sha256_file(path)}")
    elif args.command == "extract":
        bins = extract_all(official, extracted, work)
        for name, path in sorted(bins.items()):
            print(f"{name}: {path.stat().st_size} bytes {sha256_file(path)}")
        print(f"wrote {extracted / 'SHA256SUMS'}")
    elif args.command == "verify":
        verify_all(extracted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run CLI end-to-end for real**

Run:
```bash
.venv/bin/python -m tools.extract_updater fetch
.venv/bin/python -m tools.extract_updater extract
.venv/bin/python -m tools.extract_updater verify
```
Expected: `fetch` downloads two zips; `extract` prints five payload lines with the exact sizes/hashes from the recon table and writes `firmware/extracted/SHA256SUMS`; `verify` prints `verify OK: FS.bin, MAIN_INFO.bin, Main.bin, Preset.bin, ROM.bin`

- [ ] **Step 4: Commit**

```bash
git add tools/extract_updater/__main__.py
git commit -m "feat: extract_updater CLI (fetch/extract/verify)"
```

---

### Task 7: Integration test against the real packages

**Files:**
- Create: `tools/extract_updater/tests/test_integration.py`

- [ ] **Step 1: Write the test**

`tools/extract_updater/tests/test_integration.py`:

```python
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
```

- [ ] **Step 2: Run the test**

Run: `.venv/bin/python -m pytest tools/extract_updater/tests/test_integration.py -m integration -v`
Expected: `1 passed` (downloads ~9.2 MB on first run)

- [ ] **Step 3: Run the full default suite**

Run: `.venv/bin/python -m pytest -v`
Expected: all non-integration tests pass; integration test deselected

- [ ] **Step 4: Commit**

```bash
git add tools/extract_updater/tests/test_integration.py
git commit -m "test: end-to-end integration against official packages"
```

---

### Task 8: Commit the canonical artifacts and documentation

**Files:**
- Modify: `.gitignore` (allow `firmware/extracted/SHA256SUMS` to be committed)
- Create: `docs/research/2026-09-27-p0-recon.md`
- Modify: `README.md` (phase table P0 row)

- [ ] **Step 1: Allow SHA256SUMS to be committed**

In `.gitignore`, replace:

```
firmware/extracted/*
```

with:

```
firmware/extracted/*
!firmware/extracted/SHA256SUMS
```

- [ ] **Step 2: Write the recon document**

`docs/research/2026-09-27-p0-recon.md`:

```markdown
# P0 extraction recon (2026-09-27)

Verified by downloading and extracting both official v2.00 packages.

## Packages

| Package | SHA256 |
|---|---|
| G1_FOUR_v2.00_Mac_E.zip | f90c831af6a8d43ec480f69d78a6a1c16369ac7902a8a85086aa581720b05010 |
| G1_FOUR_v2.00_Win_E.zip | f94adce31934635141bedfbf832e974aa4260363aa14c1145bab681c5dd12131 |

## Payloads (byte-identical across platforms)

| File | Size | SHA256 | Windows PE resource id |
|---|---|---|---|
| ROM.bin | 163840 | 5ee756a5dee51b4e790a6e6f6b6c0a8a1ea531c245a13124e8a5897530b01622 | 142 |
| Main.bin | 493412 | 43060686fce75e175a217194ab1be3aeffe0be7d59f9d3df4181d41b9d3cc5a7 | 129 |
| FS.bin | 3137536 | 7dd2821c02414d548b900b31586a1b42ccf1a4a4bd1e69208cb427211606f8aa | 136 |
| MAIN_INFO.bin | 4096 | 8d18a37537a469106dd87335f9899599c632cc32cb4cdad2bfdd5121b4022f38 | 139 |
| Preset.bin | 45056 | 969e95657c0a92de94680447734c621bbc479ec5a1c4b63bb4ce0eaea33d3a29 | 133 |

## Structural observations for later phases

- `ROM.bin` and `Main.bin` begin with ASCII `TIPAcYSX` followed by repeating
  `YSX` markers (container format; not needed for P0).
- `FS.bin` begins `55 AA 00 01 04 00 FF 00` and contains `ZDLFx` effect wrappers
  (81 `ZDLF` string hits; e.g. `ZEN_DRV.ZD2`, wrapper versions 1.20/1.30, a JSON
  snippet with `"pedal":false`).
- `MAIN_INFO.bin` is 0xFF-filled then contains `2.00` and `Zoom Corporation`
  (role hypothesis: integrity/version metadata; see spec P5b decision rule).
- `ROM.bin` contains strings `UsbTask`, `UsbTestMidi_Task`, `@ZOOM G Series`
  (update-mode USB layer lives in ROM).
- Mac app `Contents/MacOS/EFX Updater` (320,224 bytes) is the updater client
  binary; `zoom-zt2` community reports modified updater resources changing
  model identity (issue #18).
```

- [ ] **Step 3: Update README phase table**

In `README.md`, change the P0 row status from `not started` to `done (M0)`:

```
| P0 | Extract official v2.00 updater into canonical bins | M0 | done (M0) |
```

- [ ] **Step 4: Verify the final state**

Run:
```bash
.venv/bin/python -m tools.extract_updater verify
git status --short
```
Expected: `verify OK: ...`; `git status` shows `firmware/extracted/SHA256SUMS` as untracked-but-not-ignored, plus the modified README/.gitignore/docs files

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md docs/research/2026-09-27-p0-recon.md firmware/extracted/SHA256SUMS
git commit -m "docs: P0 recon results, artifact hashes, README status"
```

---

## Self-review notes

- Spec coverage: P0 requires fetch+hash verify, all five bins, cross-platform byte equality, mismatch abort + diff report, SHA256SUMS, golden tests, and FS.bin as P1 oracle. Tasks 1–8 cover all of these. Container parser/repack round-trip is E5 (spec P2/P5a), intentionally out of scope here.
- No placeholders: every step contains runnable code or exact commands.
- Type consistency: `sha256_file`, `download`, `extract_zip`, `find_mac_resources`, `find_sevenzip`, `extract_win_resources`, `fetch_all`, `canonicalize`, `write_sha256sums`, `extract_all`, `verify_all` are used with identical signatures across tasks and tests.

---

## Post-implementation follow-ups (recorded 2026-09-27)

- Integration test re-downloads ~9 MB each run; consider honoring an env var
  pointing at `firmware/official` to reuse already-verified packages.
- CLI could wrap known failures (HTTP errors, 7z errors, missing artifacts)
  into concise stderr messages instead of raw tracebacks.
- Spec was aligned after implementation to reflect the hash-only artifact
  policy (bins gitignored) and the reality that no custom container parser is
  needed for extraction.
