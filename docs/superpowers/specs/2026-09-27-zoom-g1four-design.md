# Zoom G1 Four — Open Firmware Project: Design

Date: 2026-09-27
Status: Approved (design review complete)
Repo: `/Users/andrii/Projects/zoom-g1four`

## Goal

Make it possible to run custom firmware on a Zoom G1 Four, in a software-first
ladder of increasingly invasive phases. "Open source firmware" is treated as the
end goal; phases P0–P4 build the capability and evidence needed to get there
without destroying the device.

## Non-goals (for now)

- Clean-room firmware rewrite during P0–P4 (assessed at P5).
- Any hardware modification unless a gate requires it.
- JTAG bring-up on the TI C6745 (escape hatch only; documented but not planned).

## Validated context

Target device (live-verified this session):

- **Zoom G1 Four** guitar multi-effects pedal, firmware **v2.00**.
- USB `1686:04a1`, product string "ZOOM G Series", full-speed, USB Audio +
  USB MIDI Streaming. Identity reply:
  `F0 7E 00 06 02 52 6E 00 0C 00 32 2E 30 30 F7` (model bytes `0C 00`).
- Same PID/string is shared by G1X Four (`0D 00`), B1 Four (`0E 00`),
  B1X Four (`0F 00`) — model must be discriminated via SysEx identity, never by PID.
- Main board PCB-0993-02, shared with A1/B1 Four.
- **DSP/MCU: TI TMS320C6745DPTP3** (C674x, floating point) — not ARM.
  The connected ST-LINK-V3 is not usable for this target; TI XDS110 would be
  required for JTAG (escape hatch).
- **Flash: MX25L3233F**, 4 MB SPI NOR.
- All control (patches, effects, firmware update) goes over **USB-MIDI SysEx**.
- Firmware update mode: hold both footswitches while plugging in USB. The
  updater pushes `ROM.bin`, `Main.bin`, `FS.bin`, `Preset.bin` over SysEx.
- No signing/encryption observed anywhere in the update path; cross-model
  flashing via patched updaters is proven by the community.
- Effects are TI C6000 ELF binaries (`.ZD2`, `ZDLF` wrapper). Custom DSP code
  already runs on sibling hardware (MS-70CDR).
- Known danger: bad filesystem writes can brick the unit, and official re-flash
  does not restore the filesystem on this model. Recovery requires opening the
  unit. This drives the safety gates below.

Detailed prior art, sources, and URLs: `docs/research/2026-09-27-prior-art.md`.

## Architecture

Repo layout:

```
zoom-g1four/
  README.md                  # project overview, phase status
  docs/
    research/                # findings, sources, prior art
    superpowers/specs/       # this design doc
    recovery.md              # brick recovery playbook (living doc)
  firmware/
    official/                # pristine Zoom updater downloads (never edited)
    extracted/               # canonical ROM/Main/FS/Preset bins + hashes
    repacked/                # modified updaters, named with intent
  flash/                     # full-chip dumps + memory map (phase 2)
  backups/                   # SysEx patch/FS backups from the pedal
  tools/
    zoomctl/                 # CLI: identity, backup, fs read/write, effect upload
    extract_updater/         # updater -> canonical bins pipeline
  effects/
    zd2/                     # custom effect C sources + Dockerized C674x build
  analysis/
    main-bin/                # dis6x/objdump scripts, notes, patched diffs
```

Components (one job each):

| Component | Job | Depends on |
|---|---|---|
| `extract_updater` | fetch+verify official v2.00 zip, unpack app/exe resources, emit canonical bins with SHA256 | known Zoom URLs, 7z/python |
| `zoomctl` | single CLI for all pedal I/O over USB-MIDI SysEx (identity, CRC-checked reads, gated writes); wraps/borrows `zoom-zt2` protocol lib | mido |
| flash playbook | documented CH341A flow for MX25L3233F + map verification vs extracted bins | hardware, P2 only |
| `effects/zd2` | C sources -> TI C6000 CGT (x86 Linux Docker) -> ZDLF-wrapped ELF with correct FXID/target/CRC | TI CGT, RE notes (zoom-zt2#93/#109) |
| `analysis/main-bin` | TI `dis6x` disassembly, string/table mapping, patch diffs | CGT toolchain |

Data flow is always `pedal <-> USB-MIDI SysEx <-> zoomctl <-> repo artifacts`.
Hardware tools only read unless a phase explicitly says write.

## Phase gates

- **P0 Extract** (no device): canonical official bins in repo.
- **P1 Backup** (reads only): identity + all patches + full effect FS backed up
  and CRC-verified. Gate: `zoomctl` cannot perform any write until a verified
  backup manifest exists for the current pedal state.
- **P2 Ground truth** (hardware): 4 MB flash dump, memory map reconciled with
  P0 bins. Hard gate before any `Main.bin` flashing.
- **P3 Custom effect**: self-compiled C674x effect audible on the pedal,
  verified via USB-audio capture.
- **P4 Patched firmware**: modified `Main.bin` (start: version/identity string
  only) boots after updater repack.
- **P5 Assessment**: written go/no-go for clean-room firmware.

## Safety and error handling

- Read-only default: every `zoomctl` command reads unless `--write` is passed;
  `--write` refuses without a valid backup manifest from current pedal state
  (a manifest = JSON in `backups/` listing every artifact, its CRC/SHA256, and
  the pedal identity/version it came from).
- Banned by default: changing effect category IDs (documented FS corruption),
  full-FS rewrites, any operation during unstable USB.
  One mutation per test, always.
- Gate before `Main.bin` flashing: P2 dump exists, verified against extracted
  bins, with a tested restore path (`docs/recovery.md`).
- Every transfer CRC-checked (`~CRC32` over the 7-bit-unpacked block);
  read-back verification after each write; power-cycle test after FS ops.
- Pristine sources fenced: `firmware/official/` is never edited; repacks carry
  intent plus a byte-diff report vs original showing only intended changes.

## Testing and verification

- **P0:** unit tests for extractor (known magics/sizes/offsets); Mac vs Windows
  updater payloads must be byte-identical.
- **P1:** round-trip: backup patch -> modify copy -> upload to scratch slot ->
  read back -> CRC match -> restore original and verify.
- **P3:** static ELF checks (machine = C674x, section addresses), then
  audio-in-the-loop: play test tones through the pedal's USB audio interface,
  capture output on the Mac, assert expected transform (FFT/gain/notch). This
  is the hardware regression loop.
- **P4:** flash build with only the version string changed; success = boots and
  identity SysEx reports the new string; then progressively deeper patches.
- **P5:** assessment doc covering boot chain unknowns, effort estimate, and
  licensing/clean-room notes.

## Milestones

Each milestone = a commit plus a short report in `docs/`.

- **M0** canonical official bins + hashes documented
- **M1** verified full backup of this pedal; write-gate released
- **M2** 4 MB flash dump + memory map
- **M3** first self-compiled effect audible; audio test automated
- **M4** patched `Main.bin` boots
- **M5** full-firmware go/no-go report

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Bricking the unit | P2 dump + recovery playbook before any flash; FS writes gated behind backup |
| TI C6000 CGT hard to get / macOS ARM | x86 Linux Docker via colima; fallback: prebuilt toolchain container |
| ZD2 ABI only partially public | start by modifying a stock ZD2 module (proven per zoom-zt2#109), generalize later |
| Update-mode full read unverified | try early (read-only); chip-off is fallback |
| G1 Four FS unrecoverable by official reflash | never touch FS without backup; `recovery.md` primary reference |

## Open questions

1. Exact update-mode bootloader opcode set / whether flash read exists for this
   generation (one unverified report says a full 8 MB read was achieved).
2. Whether `Main.bin` is checked beyond a checksum by the bootloader.
3. ZD2 runtime ABI for self-compiled modules (only partially mapped publicly).
4. C6745 JTAG pads/pinout on PCB-0993-02 (escape hatch only).
