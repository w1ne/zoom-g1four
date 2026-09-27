# Zoom G1 Four — Open Firmware Project: Design

Date: 2026-09-27
Status: Revised after adversarial review; provisional pending P0.5 findings
Repo: `/Users/andrii/Projects/zoom-g1four`
Supersedes: initial design of the same date (commits 493ebcf, 03ddc81)

## Goal

Make it possible to run custom firmware on a Zoom G1 Four through a software-first
ladder of phases. "Open source firmware" is the end goal; phases P0–P4 build the
capability and evidence needed to get there without destroying the device.

## Non-goals (for now)

- Clean-room firmware rewrite during P0–P4 (assessed at P5).
- JTAG bring-up on the TI C6745 (escape hatch only, no plan).
- Hardware modification except where a phase explicitly requires it (P2).

## Validated context

Target device (live-verified this session):

- **Zoom G1 Four**, firmware **v2.00**. USB `1686:04a1`, "ZOOM G Series",
  full-speed, USB Audio + MIDI Streaming. Identity reply:
  `F0 7E 00 06 02 52 6E 00 0C 00 32 2E 30 30 F7` (model bytes `0C 00`). [V]
- Same PID/string shared by G1X Four (`0D 00`), B1 Four (`0E 00`), B1X Four
  (`0F 00`), GCE-3 (`10 00`). Model is discriminated via SysEx identity, never
  by PID. [V]
- Main board PCB-0993-02, shared with A1/B1 Four. **DSP: TI TMS320C6745DPTP3**
  (C674x). **Flash: MX25L3233F**, 4 MB SPI NOR. [V for the dump thread /
  single-source; codec "AC3101i" unverified]
- All control (patches, effects, firmware update) is **USB-MIDI SysEx**. [V]
- Effects are `ZDLF`-wrapped **TI C6000 ELF** binaries for the C6745. [V]
- Custom DSP code compiled with TI C6000 tools runs on sibling MS-70CDR. [V]
- The connected ST-LINK-V3 cannot debug this target (C674x is not ARM; would
  need TI XDS110). JTAG pinout on this PCB is undocumented. [V]
- Community claims on the critical path, currently unverified (tagged [U]):
  - whether the official updater writes `FS.bin` to flash or skips the
    filesystem on this model;
  - whether update mode supports a flash **read** command (one report of a full
    8 MB read — treat as rumor);
  - whether the pedal's USB audio loops playback through the effect chain in a
    way usable for automated tests;
  - the exact ZD2 runtime ABI for self-compiled modules.

Detailed prior art, sources, and URLs: `docs/research/2026-09-27-prior-art.md`.

## Architecture

Repo layout:

```
zoom-g1four/
  README.md                      # overview, phase status
  pyproject.toml                 # python tooling, pinned deps
  docs/
    research/                    # findings, decision table, captured sessions
    toolchain.md                 # pinned CGT/container/host details
    recovery.md                  # actionable recovery playbook (gate artifact)
    superpowers/specs/           # this design doc
  firmware/
    official/                    # pristine Zoom downloads (immutable)
    extracted/                   # canonical bins + SHA256SUMS
    repacked/                    # modified updaters + byte-diff reports
  flash/                         # full-chip dumps, memory map, README
  backups/
    manifests/                   # JSON manifests + SCHEMA.md
    <state-digest>/              # artifacts (patches, FS files) per manifest
  tools/
    zoomctl/                     # CLI: identity, mode, backup, gated writes
    extract_updater/             # updater -> canonical bins
    repack_updater/              # bins -> updater container + diffs
    zd2wrap/                     # ELF -> ZDLF wrapper with CRCs (P3b)
    capture/                     # USB capture scripts/notes per host
  effects/
    zd2/                         # effect sources, ABI.md, Dockerfile.build
  analysis/
    main-bin/                    # dis6x/objdump scripts, notes, patch diffs
```

Components (one job each):

| Component | Job | Depends on |
|---|---|---|
| `extract_updater` | parse updater container (32-byte table, 4096-byte blocks), emit all five bins + SHA256SUMS, golden tests | Zoom URLs, python |
| `repack_updater` | rebuild updater from bins, emit byte-diff report; zero-change round-trip must be byte-identical | `extract_updater` parser |
| `zoomctl` | all pedal I/O over USB-MIDI SysEx: identity, mode detection, read-only backup, gated writes | mido (verified working) |
| `tools/capture` | documented USB capture procedures for supported hosts | Linux/Windows capture host |
| flash procedure | chip-off MX25L3233F dump/restore with CH341A 3.3V + flashrom on Linux | hardware, P2 |
| `zd2wrap` | wrap/unwrap ZDLF, CRC computation, metadata | stock ZD2 corpus |
| `effects/zd2` | C sources -> pinned TI C6000 CGT in pinned x86_64 container -> ELF | myTI account, Docker/colima |
| `analysis/main-bin` | dis6x/objdump mapping, patch diffs | CGT toolchain |

Data flow is always `pedal <-> USB-MIDI SysEx <-> zoomctl <-> repo artifacts`.
Hardware tools only read unless a phase explicitly says write.

## Phases and gates

**P0 — Extract (software, no device).**
Fetch official v2.00 packages, verify hash, implement the container parser
(reference: Zoom-Firmware-Editor documentation), emit `ROM.bin`, `Main.bin`,
`FS.bin`, `Preset.bin`, `MAIN_INFO.bin` + `SHA256SUMS`. Windows vs Mac payloads
must match; mismatch = abort, write diff report, investigate before proceeding.
Parser round-trip (extract -> repack) must be byte-identical. `FS.bin` file list
becomes the completeness oracle for the P1a backup. Deliverable: **M0**.

**P0.5 — Capture and Decide (recon).**
Runs before any write (sole exception below) and before detailed P2–P4
planning. All results go into a decision table in `docs/research/`.

- **E1 Update-session capture.** On a capture-capable host (Linux VM with USB
  passthrough, Windows + USBPcap, or other Linux box), run the official v2.00
  updater once, same version. This is the *only* device write allowed before
  M2, because it is the vendor recovery procedure itself and is documented as
  retryable. Capture full traffic; analyze opcode sequence, whether `FS.bin`
  bytes are transferred and to which address, update-mode descriptors/identity,
  and whether any read opcode exists.
- **E2 Updater portability.** Confirm which hosts can execute the official
  Mac/Windows updater; decide the P4 flashing environment (vendor updater,
  Wine, or native flasher built from E1 captures).
- **E3 Read-path probe.** Test only opcodes evidenced by E1. No blind opcode
  scanning in update mode.
- **E4 Audio routing matrix.** In normal mode (no writes), measure: physical
  input -> USB record (expected FX path), USB playback -> record (loopback?),
  sample rates, channel mapping, latency. Decide the P3 test fixture and
  tolerances.
- **E5 Zero-change repack round-trip.** Host-side: repack extracted bins,
  assert byte-identical to original updater.
- **E6 Mode detection.** Record identity/descriptors in normal vs update mode;
  define `zoomctl mode` expectations.

Exit criteria: decision table complete; every [U] claim that gates a milestone
is either verified or has a scheduled experiment with a decision rule.
Deliverable: **M0.5**.

**P1a — Backup (read-only).**
`zoomctl backup`: identity + firmware version; all user patches; full FS listing
and every FS file read back with `~CRC`; artifacts + manifest per
`backups/manifests/SCHEMA.md` with SHA256s. Cross-check against the `FS.bin`
oracle; report differences. Measure and record backup/restore transfer times
over full-speed SysEx. Deliverable: **M1**.

**P2 — Ground truth.**
Primary: chip-off dump of the MX25L3233F (desolder, CH341A at 3.3V, flashrom on
Linux; read, hash, re-read verify). Alternative only if E1/E3 proved a read
opcode: update-mode read via `zoomctl`. Reconcile the 4 MB image against P0 bins
and document the memory map in `flash/README.md`. Tested restore path required:
rehearse dump -> erase -> write -> boot on a donor unit or board if available;
without a donor, the minimum is a full write + readback verification on the
target chip plus the documented recovery escalation in `docs/recovery.md`.
Deliverable: **M2 — write gate opens here.**

**P3a — Install-path validation and stock-module effect.**
First FS write is a no-op: write identical bytes to an existing user file,
read back, CRC match, power-cycle. Then determine the allowed install path for
custom effects without category-ID changes (backup first, one mutation per
test). Then modify a stock ZD2 module (parameter/coefficient) and make it
audibly different over the E4 audio fixture. Deliverable: **M3a**.

**P3b — Self-compiled effect.**
Pin the TI C6000 CGT release and x86_64 build container in
`docs/toolchain.md` (license notes included; redistribution only if permitted).
Prove toolchain with a minimal C674x ELF (`readelf`: `EM_TI_C6000`, expected
sections/addresses). Reverse the ZD2 runtime ABI (entry points, per-instance
state, audio buffers, loader symbols) and document in `effects/zd2/ABI.md`.
Build `zd2wrap` with unit tests (wrapping an unwrapped stock module must
reproduce the original bytes). First effect: fixed gain or notch with a known
transfer function. Deliverable: **M3b**.

**P4a — Zero-change repack flash.**
Flash a repacked updater with byte-identical payloads using the E2 environment;
it must boot. Proves container regeneration and the flashing host end-to-end.
Deliverable: **M4a**.

**P4b — Minimal patch.**
Patch only the version/identity string; flash; success = boots and identity
SysEx reports the new string. If the update is rejected, stop and reverse
`MAIN_INFO.bin` (role hypothesis: integrity data) before any further patching.
Deeper Main.bin experiments are a separate future spec. Deliverable: **M4b**.

**P5 — Assessment.**
Boot-chain unknowns, effort estimate, licensing/clean-room notes, go/no-go for
a clean-room firmware. Deliverable: **M5**.

## Safety and error handling

- No device writes before M2. Sole exception: E1 official same-version reflash.
- Write gate: `zoomctl --write` requires a manifest whose **live state digest**
  matches the device at write time. Digest = identity + firmware version + FS
  listing with per-file `~CRC` + patch CRCs. Computed live; mismatch = refuse.
  This is honest *accident prevention*, not security — a determined operator can
  bypass it.
- Banned by default: category-ID changes (documented FS corruption), full-FS
  rewrites, blind opcode scanning in update mode, clip-programming an
  in-circuit flash, any operation while the USB link shows errors (defined as:
  errors observed during the preceding read of the same device).
- One mutation per test. Read-back verification after every write. Power-cycle
  test after FS writes.
- CRC implementation is unit-tested with golden vectors and cross-checked
  against a stock ZD2 module read before any write depends on it.
- `firmware/official/` is immutable. Every repack carries a byte-diff report
  showing only intended changes.
- `docs/recovery.md` must be actionable (exact pin, voltage, host, preconditions)
  and its rehearsal record filled before M2 is declared complete.

## Testing and verification

- **P0:** golden tests (sizes, magics, known strings), parser round-trip,
  Mac/Windows payload equality, mismatch abort policy.
- **P0.5:** E1 capture analysis; E4 routing matrix; E5 byte-identical repack;
  decision table reviewed.
- **P1a:** re-read random FS files and compare CRCs; manifest schema validation;
  transfer-time measurement.
- **P3a:** no-op write verification; then audible test via E4 fixture.
- **P3b:** static ELF checks; `zd2wrap` round-trip tests; audio-in-the-loop with
  defined tone, fixture effect, and tolerances.
- **P4a:** boots with byte-identical payloads.
- **P4b:** boots and identity reports patched version string.

## Milestones

| Milestone | Meaning |
|---|---|
| M0 | canonical bins + SHA256SUMS committed |
| M0.5 | decision table recorded (E1–E6) |
| M1 | read-only backup verified |
| M2 | full-chip dump + memory map + tested restore path; write gate opens |
| M3a | modified stock effect audible |
| M3b | self-compiled effect audible |
| M4a | zero-change repack boots |
| M4b | string-patched Main.bin boots |
| M5 | clean-room go/no-go report |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Bricking the unit before any backup exists | all writes gated until M2; E1 is the only pre-M2 write and is the vendor recovery step |
| Recovery path is fiction until rehearsed | rehearsal record in `docs/recovery.md` required for M2; donor unit/board purchase recommended |
| [U] community claims on the critical path | P0.5 experiments with decision rules; nothing gates a milestone on an unverified claim |
| macOS/ARM tooling friction (updaters, flashrom, x86 colima, CGT) | E2 host decision; native flasher fallback; pinned container |
| TI CGT license/redistribution | pinned release, license notes in `docs/toolchain.md`; container redistributed only if permitted |
| FS corruption from writes | backups + live digest gate + no-op first write + one mutation per test |
| Update-mode read rumor false | hardware chip-off is the primary path; read probe is capture-driven only |
| MAIN_INFO.bin integrity check blocks Main patches | P4b decision rule: reverse MAIN_INFO first if rejected |

## Tooling and environment

- macOS (this machine): control tooling, python/mido (verified), capture is
  *not* available here — capture host must be Linux/Windows (VM with USB
  passthrough or separate machine).
- Linux x86_64: flashrom for CH341A; pinned container for TI CGT.
- Shopping list: CH341A (3.3V-safe) + SOIC-8 adapter and hot-air/desoldering
  capability; donor G1 Four or main board (recommended for restore rehearsal);
  audio loop adapters; TI myTI account for CGT.
- Estimated effort (solo): P0+P1a ~ days; P0.5 ~ days; P2 ~ a weekend plus
  parts shipping; P3a ~ days; P3b ~ weeks; P4 ~ weeks; P5 ~ days.

## Open questions

Each resolves through a named experiment or is explicitly out of scope.

1. Does the updater write `FS.bin`? -> E1.
2. Update-mode read opcode? -> E1, E3; if absent, hardware dump (P2 primary).
3. Role of `MAIN_INFO.bin` / integrity checks -> P4b decision rule.
4. ZD2 runtime ABI -> P3b (`ABI.md`).
5. USB audio routing usable for tests -> E4.
6. C6745 JTAG pinout -> escape hatch, not planned.
