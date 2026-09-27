# Zoom G1 Four — Open Firmware Project: Design

Date: 2026-09-27
Status: Revision 2 — adversarial review + verification fixes applied; provisional
pending P2 findings
Repo: `/Users/andrii/Projects/zoom-g1four`
Supersedes: Revision 1 (commits 493ebcf, 03ddc81) and revision 2 draft (fe090b9).
Phase numbers were renumbered for strict dependency order.

## Goal

Make it possible to run custom firmware on a Zoom G1 Four through a software-first
ladder of phases. "Open source firmware" is the end goal; phases P0–P5 build the
capability and evidence needed to get there without destroying the device.

## Non-goals (for now)

- Clean-room firmware rewrite during P0–P5 (assessed at P6).
- JTAG bring-up on the TI C6745 (escape hatch only, no plan).
- Hardware modification except where a phase explicitly requires it (P3).

## Validated context

Target device (live-verified this session):

- **Zoom G1 Four**, firmware **v2.00**. USB `1686:04a1`, "ZOOM G Series",
  full-speed; interfaces are AudioControl + MIDI Streaming only — the device
  exposes **no USB audio streaming** (confirmed by E4, 2026-09-27). Identity
  reply: `F0 7E 00 06 02 52 6E 00 0C 00 32 2E 30 30 F7` (model bytes `0C 00`). [V]
- Same PID/string shared by G1X Four (`0D 00`), B1 Four (`0E 00`), B1X Four
  (`0F 00`), GCE-3 (`10 00`). Model is discriminated via SysEx identity, never
  by PID. [V]
- Main board PCB-0993-02, shared with A1/B1 Four. **DSP: TI TMS320C6745DPTP3**
  (C674x). **Flash: MX25L3233F**, 4 MB SPI NOR. [U — one primary dump thread]
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
  - ~~whether the pedal's USB audio loops playback through the effect chain~~
    resolved by E4: no USB audio exists; audio verification requires external
    analog capture (or manual listening);
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
    zd2wrap/                     # ELF -> ZDLF wrapper with CRCs (P4b)
    capture/                     # USB capture scripts/notes per host
  effects/
    zd2/                         # effect sources, ABI.md, Dockerfile.build
  analysis/
    main-bin/                    # dis6x/objdump scripts, notes, patch diffs
```

Components (one job each):

| Component | Job | Depends on |
|---|---|---|
| `extract_updater` | download/extract all five payloads from both official platforms, verify byte-equality + known-good hashes, emit bins + SHA256SUMS (payloads gitignored, hashes committed) | Zoom URLs, python, 7zz |
| `repack_updater` | rebuild updater from bins, emit byte-diff report; zero-change round-trip must be byte-identical | `extract_updater` parser |
| `zoomctl` | all pedal I/O over USB-MIDI SysEx: identity, mode detection, read-only backup, gated writes | mido (verified working) |
| `tools/capture` | documented USB capture procedures for supported hosts | Linux/Windows capture host |
| flash procedure | chip-off MX25L3233F dump/restore with CH341A 3.3V + flashrom on Linux | hardware, P3 |
| `zd2wrap` | wrap/unwrap ZDLF, CRC computation, metadata | stock ZD2 corpus |
| `effects/zd2` | C sources -> pinned TI C6000 CGT in pinned x86_64 container -> ELF | myTI account, Docker/colima |
| `analysis/main-bin` | dis6x/objdump mapping, patch diffs | CGT toolchain |

Data flow is always `pedal <-> USB-MIDI SysEx <-> zoomctl <-> repo artifacts`.
Hardware tools only read unless a phase explicitly says write.

## Phases and gates

**P0 — Extract (software, no device).**
Fetch official v2.00 packages, verify hash, extract all five bins from both
platforms and confirm they are byte-identical (recon 2026-09-27: the Mac app
ships them as plain resources; the Windows EXE stores the same payloads as PE
resources, extractable with 7zz). Emit `ROM.bin`, `Main.bin`, `FS.bin`,
`Preset.bin`, `MAIN_INFO.bin` + `SHA256SUMS`. Any mismatch = abort, write a
diff report, investigate before proceeding. The extract/repack container
round-trip (E5) is required before P5a, not for M0. `FS.bin` file list becomes
the completeness oracle for the P1 backup. Deliverable: **M0**.

**P1 — Backup (read-only, no device writes).**
`zoomctl backup`: identity + firmware version; all user patches; full FS listing
and every FS file read back with `~CRC`; artifacts + manifest per
`backups/manifests/SCHEMA.md` with SHA256s. Cross-check against the `FS.bin`
oracle; report differences. Measure and record backup/restore transfer times
over full-speed SysEx. Deliverable: **M1**. This must complete before any write
of any kind, including E1.

**P2 — Capture and Decide (recon).**
Runs after M1. E1 is the only write permitted before M3 and must pass the
flashing preflight checklist in `docs/recovery.md`. All results go into a
decision table in `docs/research/`. Decision rules are part of each experiment.

- **E1-alt Static updater analysis (no device).** Disassemble/strings the
  official updater binary to determine which payloads it sends and in what
  order. If this resolves the `FS.bin` question, E1 may be skipped.
- **E1 Update-session capture (write; only allowed write before M3).** On a
  capture-capable host (Linux VM with USB passthrough, Windows + USBPcap, or
  other Linux box), run the official v2.00 updater once, same version, with the
  M1 manifest present. Zoom documents failed *updates* as retryable, but this
  update does not restore the filesystem unless E1 proves it writes `FS.bin`.
  Capture full traffic; analyze opcode sequence, payload transfer addresses,
  update-mode descriptors/identity, and read opcodes.
  *Decision rule:* if the updater transfers `FS.bin` -> record in
  `docs/recovery.md` that official reflash restores factory FS (upgrades step 1
  of recovery) and that updates wipe user patches; if not -> backups are
  load-bearing and restore is only via our tools or chip-off.
- **E2 Flasher-host decision.** Check whether the official macOS app launches
  and enumerates the pedal; check Windows VM/Wine USB-MIDI passthrough with a
  smoke test. *Decision rule:* macOS app works -> primary flasher; else
  Windows/Wine works -> secondary; else build a native flasher from E1 captures
  (kept as fallback in all cases). Record in `docs/toolchain.md`.
- **E3 Read-path probe.** Only opcodes evidenced by E1/E1-alt. *Decision rule:*
  if no read opcode is evidenced, no probe is attempted; P3 primary path is
  chip-off.
- **E4 Audio routing matrix (no writes).** Measure: physical input -> USB
  record (expected FX path), USB playback -> record (loopback?), sample rates,
  channel mapping, latency. *Decision rule:* if physical-in -> USB-record
  carries the effect chain (confirmed by bypass-vs-effect differential) ->
  automated FFT fixture; elif only playback loopback works -> capture the
  pedal's analog output through an external USB audio interface with manual
  routing; else -> manual listening test, M4a audible check is
  operator-verified with recorded audio kept as evidence. *Outcome
  (2026-09-27):* no USB audio streaming exists at all, so the else/external
  branch applies — P4 audio checks use external analog capture with the
  operator brief in the P2 decision table.
- **E5 Zero-change repack round-trip.** Host-side: repack extracted bins,
  assert byte-identical to original updater. *Decision rule:* mismatch -> fix
  the container parser before P5a.
- **E6 Mode detection.** Record identity/descriptors in normal vs update mode.
  *Decision rule:* if modes present distinct detectable identity/descriptors ->
  `zoomctl mode` auto-detects; else `zoomctl` requires an explicit `--mode`
  flag and refuses ambiguous operations.

Exit criteria: decision table complete; every [U] claim that gates a milestone
is either verified or has a scheduled experiment with a decision rule.
Deliverable: **M2**.

**P3 — Ground truth.**
Primary: chip-off dump of the MX25L3233F (desolder, CH341A at 3.3V, flashrom on
Linux; read, hash, re-read verify). Alternative only if E1/E3 proved a read
opcode: update-mode read via `zoomctl`. Reconcile the 4 MB image against P0 bins
and document the memory map in `flash/README.md`. Restore path verified at the
level recorded in `docs/recovery.md`: full write + readback verification on the
target chip, or dump -> erase -> write -> boot if a donor unit is available.
Deliverable: **M3 — write gate opens here.**

**P4a — Install-path validation and stock-module effect.**
The first zoomctl-initiated FS write is a no-op: write identical bytes to an
existing user file, read back, CRC match, power-cycle. (If E1 already performed
an official filesystem write, that is separately recorded in the decision
table.) Then determine the allowed install path for custom effects without
category-ID changes (backup first, one mutation per test). Then modify a stock
ZD2 module (parameter/coefficient) and make it audibly different via the
E4-determined method. Deliverable: **M4a**.

**P4b — Self-compiled effect.**
Pin the TI C6000 CGT release and x86_64 build container in
`docs/toolchain.md` (license notes included; redistribution only if permitted).
Prove toolchain with a minimal C674x ELF (`readelf`: `EM_TI_C6000`, expected
sections/addresses). Reverse the ZD2 runtime ABI (entry points, per-instance
state, audio buffers, loader symbols) and document in `effects/zd2/ABI.md`.
Build `zd2wrap` with unit tests (wrapping an unwrapped stock module must
reproduce the original bytes). First effect: fixed gain or notch with a known
transfer function. Deliverable: **M4b**.

**P5a — Zero-change repack flash.**
Flash a repacked updater with byte-identical payloads using the E2 environment;
it must boot. Proves container regeneration and the flashing host end-to-end.
Deliverable: **M5a**.

**P5b — Minimal patch.**
Patch only the version/identity string; flash; success = boots and identity
SysEx reports the new string. If the update is rejected, stop and reverse
`MAIN_INFO.bin` (role hypothesis: integrity data) before any further patching.
Deeper Main.bin experiments are a separate future spec. Deliverable: **M5b**.

**P6 — Assessment.**
Boot-chain unknowns, effort estimate, licensing/clean-room notes, go/no-go for
a clean-room firmware. Deliverable: **M6**.

## Safety and error handling

- No device writes before M3, except E1 (allowed only after M1, M1 manifest
  present, decision rule recorded).
- Writes fall in two classes with different enforcement:
  - **zoomctl-mediated FS/file writes:** technically gated. `zoomctl --write`
    requires a manifest whose live state digest matches the device at write
    time. Digest = identity + firmware version + FS listing with per-file
    `~CRC` + patch CRCs. Computed live; mismatch = refuse.
  - **Flashing operations (E1, P5a, P5b) via vendor/repacked updater or native
    flasher:** procedurally gated. A preflight checklist in `docs/recovery.md`
    (manifest present, dump present where required, host decided, rollback
    understood) must be filled and committed before each flash. This cannot be
    technically enforced on vendor binaries; it is honest accident prevention,
    not security.
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
- `docs/recovery.md` must be actionable (exact pin, voltage, host,
  preconditions) and its rehearsal record filled before M3 is declared
  complete.

## Testing and verification

- **P0:** golden tests (sizes, hashes), Mac/Windows payload byte-equality,
  mismatch abort + report policy, published hashes cross-checked; network
  integration test; magic/string observations documented in the recon notes
  (informational, not machine-checked).
- **P1:** re-read random FS files and compare CRCs; manifest schema validation;
  transfer-time measurement.
- **P2:** E1-alt/E1 analysis; E4 routing matrix; E5 byte-identical repack;
  decision table reviewed.
- **P4a:** no-op write verification; then audible test via the E4-determined
  method (automated fixture, external capture, or operator-verified listening).
- **P4b:** static ELF checks; `zd2wrap` round-trip tests; audio-in-the-loop with
  defined tone, fixture effect, and tolerances, or the E4 fallback method with
  recorded audio as evidence.
- **P5a:** boots with byte-identical payloads.
- **P5b:** boots and identity reports patched version string.

## Milestones

| Milestone | Meaning |
|---|---|
| M0 | canonical bins extracted and verified; SHA256SUMS committed (bins gitignored) |
| M1 | read-only backup verified (required before any write, including E1) |
| M2 | decision table recorded (E1-alt/E1–E6) |
| M3 | full-chip dump + memory map + restore path verified at the level recorded in recovery.md; write gate opens |
| M4a | modified stock effect audible |
| M4b | self-compiled effect audible |
| M5a | zero-change repack boots |
| M5b | string-patched Main.bin boots |
| M6 | clean-room go/no-go report |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Bricking the unit before any backup exists | M1 backup completes before any write; E1 is the first write and is vendor-sanctioned |
| E1 itself may wipe the filesystem | E1 runs only after M1; E1 decision rule records the FS consequence; user patches exist in backups |
| Recovery path is fiction until rehearsed | rehearsal record in `docs/recovery.md` required for M3; donor unit/board purchase recommended |
| [U] community claims on the critical path | P2 experiments with decision rules; nothing gates a milestone on an unverified claim |
| macOS/ARM tooling friction (updaters, flashrom, x86 colima, CGT) | E2 host decision with native-flasher fallback; pinned container |
| TI CGT license/redistribution | pinned release, license notes in `docs/toolchain.md`; container redistributed only if permitted |
| FS corruption from writes | backups + live digest gate + no-op first write + one mutation per test |
| Update-mode read rumor false | hardware chip-off is the primary path; read probe is capture-driven only |
| MAIN_INFO.bin integrity check blocks Main patches | P5b decision rule: reverse MAIN_INFO first if rejected |

## Tooling and environment

- macOS (this machine): control tooling, python/mido (verified), capture is
  *not* available here — capture host must be Linux/Windows (VM with USB
  passthrough or separate machine).
- Linux x86_64: flashrom for CH341A; pinned container for TI CGT.
- Shopping list: CH341A (3.3V-safe) + SOIC-8 adapter and hot-air/desoldering
  capability; donor G1 Four or main board (recommended for restore rehearsal);
  audio loop adapters; TI myTI account for CGT.
- Estimated effort (solo): P0+P1 ~ days; P2 ~ days; P3 ~ a weekend plus parts
  shipping; P4a ~ days; P4b ~ weeks; P5 ~ weeks; P6 ~ days.

## Open questions

Each resolves through a named experiment or is explicitly out of scope.

1. Does the updater write `FS.bin`? -> E1-alt, E1; decision rule recorded.
2. Update-mode read opcode? -> E1, E3; if absent, hardware dump (P3 primary).
3. Role of `MAIN_INFO.bin` / integrity checks -> P5b decision rule.
4. ZD2 runtime ABI -> P4b (`ABI.md`).
5. USB audio routing usable for tests -> resolved by E4: no USB audio
   streaming; external analog capture (operator-wired) with manual listening as
   fallback.
6. C6745 JTAG pinout -> escape hatch, not planned.
