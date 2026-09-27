# zoom-g1four

Reverse engineering and open-firmware effort for the **Zoom G1 Four** guitar
multi-effects pedal (and relatives: G1X/B1/B1X/A1 Four, board PCB-0993-02).

Target: eventually run custom/open-source firmware. Strategy: a software-first
ladder — back up everything, extract the official firmware, get ground truth on
the flash, then run self-compiled DSP effects, then patched firmware, then
assess a full replacement.

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

| Phase | Goal | Status |
|---|---|---|
| P0 | Extract official v2.00 updater into canonical bins | not started |
| P1 | Full patch/FS backup over SysEx (write gate) | not started |
| P2 | 4 MB flash dump + memory map | not started |
| P3 | Self-compiled C674x effect running on pedal | not started |
| P4 | Patched `Main.bin` boots | not started |
| P5 | Clean-room firmware go/no-go | not started |

## Safety

Never write to the pedal without a verified backup manifest. Filesystem damage
on this model is not recoverable by official re-flash. See `docs/recovery.md`.
