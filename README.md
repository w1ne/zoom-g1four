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
| P1 | Read-only patch/FS backup (required before any write) | M1 | not started |
| P2 | Capture USB sessions, decide open questions (E1-alt/E1–E6) | M2 | not started |
| P3 | 4 MB flash dump, memory map, restore verified to the level recorded in recovery.md (opens write gate) | M3 | not started |
| P4a | No-op write, install path, modified stock effect audible | M4a | not started |
| P4b | Self-compiled C674x effect audible | M4b | not started |
| P5a | Zero-change repacked updater boots | M5a | not started |
| P5b | String-patched `Main.bin` boots | M5b | not started |
| P6 | Clean-room firmware go/no-go | M6 | not started |

## Safety

No device writes before M3. The only exception is the E1 official same-version
reflash in P2, which requires the M1 backup first. Filesystem damage on this
model is not recoverable by official re-flash (unless E1 proves the updater
writes `FS.bin`). See `docs/recovery.md`.
