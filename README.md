# zoom-g1four

Reverse engineering and open-firmware effort for the **Zoom G1 Four** guitar
multi-effects pedal (and relatives: G1X/B1/B1X/A1 Four, board PCB-0993-02).

Target: eventually run custom/open-source firmware. Strategy: a software-first
ladder — extract the official firmware, back up everything, capture and decide
open questions, get ground truth on the flash, then run self-compiled DSP
effects, then patched firmware, then assess a full replacement.

Read `docs/superpowers/specs/2026-09-27-zoom-g1four-design.md` for the design and
`docs/research/2026-09-27-prior-art.md` for findings and sources.

## Hardware at a glance

| | |
|---|---|
| DSP | TI TMS320C6745DPTP3 (C674x, floating point) |
| Flash | MX25L3233F, 4 MB SPI NOR |
| USB | `1686:04a1` "ZOOM G Series", USB Audio + MIDI (all control via MIDI SysEx) |
| Update mode | hold both footswitches while plugging USB |
| Effects | TI C6000 ELF payloads (`.ZD2`, `ZDLF` wrapper) |

## Phase status

| Phase | Goal | Milestone | Status |
|---|---|---|---|
| P0 | Extract official v2.00 updater into canonical bins | M0 | done (M0) |
| P1 | Read-only patch/FS backup (required before any write) | M1 | done (M1) |
| P2 | Capture USB sessions, decide open questions (E1-alt/E1–E6) | M2 | done (M2) |
| P3 | 4 MB flash dump, memory map, restore verified to the level recorded in recovery.md (opens write gate) | M3 | not started |
| P4a | No-op write, install path, modified stock effect audible | M4a | not started |
| P4b | Self-compiled C674x effect audible | M4b | not started |
| P5a | Zero-change repacked updater boots | M5a | not started |
| P5b | String-patched `Main.bin` boots | M5b | not started |
| P6 | Clean-room firmware go/no-go | M6 | not started |

## Extract official firmware (P0)

Prerequisites: Python >= 3.11, 7-Zip CLI (`brew install sevenzip`).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -q -U pip pytest   # pytest only needed to run tests
.venv/bin/python -m tools.extract_updater fetch     # download official v2.00 packages
.venv/bin/python -m tools.extract_updater extract   # -> firmware/extracted/*.bin + SHA256SUMS
.venv/bin/python -m tools.extract_updater verify    # run after extract
```

Hashes are committed (`firmware/extracted/SHA256SUMS`); the packages and payload
`.bin` files stay gitignored. Details: `docs/research/2026-09-27-p0-recon.md`.

## Back up the pedal (P1, read-only)

Requires the pedal connected via USB and the runtime dependency from
`pyproject.toml` installed once:
`.venv/bin/python -m pip install "mido[ports-rtmidi]"`.
Protocol reference: `docs/research/2026-09-27-p1-protocol.md`.

```bash
.venv/bin/python -m tools.zoomctl ports      # confirm the ZOOM G Series ports
.venv/bin/python -m tools.zoomctl identity   # model + firmware
.venv/bin/python -m tools.zoomctl backup     # patches + filesystem -> backups/
```

Read-only: nothing on the pedal is modified. Artifacts and a manifest land in
`backups/<state_digest>/` and `backups/manifests/<state_digest>.json`
(schema: `backups/manifests/SCHEMA.md`).

## Recon results (P2, M2)

The P2 decision table (E1-alt static analysis, flasher host, audio routing,
repack round-trip, update-mode detection) lives in
`docs/research/2026-09-27-p2-decisions.md`; the E1-alt detail is in
`docs/research/2026-09-27-e1alt-updater-analysis.md`.

## Safety

No device writes before M3. The only exception is the E1 official same-version
reflash in P2, which requires the M1 backup first. Filesystem damage on this
model is not recoverable by official re-flash (unless E1 proves the updater
writes `FS.bin`). See `docs/recovery.md`.
