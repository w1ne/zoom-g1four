# Recovery playbook (gate artifact)

Status: draft. Not valid as the M3 gate artifact until the rehearsal record
below is filled. Requires: exact pin confirmed against the original source,
correct voltage, and a tested restore procedure.

## Escalation order

### 1. Official re-flash retry (software, sanctioned)

Enter update mode (hold both footswitches while plugging USB; screen shows
FIRMWARE UPDATE) and run the pristine official updater. Zoom documents failed
updates as retryable. Whether this restores the filesystem depends on whether
the updater sends `FS.bin` to flash — to be proven in the E1 experiment; until
then assume it does not. If the filesystem itself is corrupt, continue to
step 2.

### 2. Filesystem rebuild via SPI pin short (hardware, community-reported [U])

Community reports: shorting the SPI flash data pin to GND through ~100 Ohm
during boot forces a filesystem rebuild. Sources: mungewell/zoom-zt2 issues
#53, #100; reddit r/zoommultistomp "Zoom G1Four stuck up while booting".

Before use, confirm from the original source which pin is meant. Do not infer.
For reference, the MX25L3233F is standard SOP-8: 1 CS#, 2 SO, 3 WP#, 4 GND,
5 SI, 6 SCLK, 7 HOLD#/RESET#, 8 VCC (verify against the datasheet). Never short
VCC or an arbitrary pin; wrong pins can damage the chip.

Preconditions: power off, official re-flash already attempted, unit opened with
ESD care. Success indicator: normal boot with rebuilt filesystem.

### 3. Chip-off reflash (last resort)

1. Desolder the MX25L3233F with hot air. Do not attempt to program it in
   circuit with a clip: the C6745 drives the same bus (contention), and clips
   are unreliable.
2. Write the P3 dump with a CH341A set to 3.3V (verify the adapter/jumper
   before connecting) using flashrom on Linux.
3. Read back and verify the hash against the dump.
4. Reassemble and power on. Success = normal boot.

Requires: verified P3 dump (`flash/`), and that the P3 restore rehearsal was
performed.

## Rules

- `firmware/official/` downloads are never edited.
- No FS write until a manifest with matching live state digest exists.
- No `Main.bin` flashing until M3 (dump + memory map + rehearsal record).
- Record every operation (tool, command, hashes, observed result) in
  `backups/manifests/`; recovery depends on knowing exactly what changed.

## Flashing preflight checklist

Fill and commit this checklist before every flash operation (E1, P5a, P5b).
This is procedural — vendor binaries cannot be technically gated.

- Manifest with matching live state digest exists (`backups/manifests/`).
- For P5a/P5b: M3 dump present in `flash/` with matching hashes.
- Flasher host decided and verified per E2 (`docs/toolchain.md`).
- Exact updater file recorded (path + SHA256), pristine original preserved.
- Rollback path understood: `recovery.md` escalation 1-3, with the expected
  outcome for this specific operation written down.
- Operator present for the whole operation; no other MIDI/USB traffic on the
  pedal's port; power stable.

Operation log (append one entry per flash: date, operation, files+hashes,
result, follow-up):

### E1 preflight (filled 2026-09-27)

- Operation: official v2.00 same-version reflash of the G1 Four via the macOS
  updater (Rosetta), with the device->host MIDI side-capture running.
- Manifest: `backups/manifests/83d9f8a31176623b56373e6aec1b90045914585546836b4ca75f2eb88515c7f1.json` (M1, verified).
- Dump requirement: not applicable (E1 is not a Main.bin flash; the M3 dump is
  required only for P5a/P5b).
- Flasher host: decided in E2 (official macOS updater under Rosetta; launch
  smoke test passed).
- Updater file: `.work/p0/mac/G1 FOUR_v2.00_Mac_E/ZOOM G1 FOUR System v2.00 Updater.app`
  from `firmware/official/G1_FOUR_v2.00_Mac_E.zip`
  (sha256 `f90c831af6a8d43ec480f69d78a6a1c16369ac7902a8a85086aa581720b05010`).
  Pristine zip preserved.
- Rollback: escalation 1 (retry the official reflash); escalations 2/3 below.
- Operator present: yes; no other MIDI/USB traffic on the pedal's port; power
  stable.


## Rehearsal record

Not yet performed. Required before M3 is declared complete. Minimum without a
donor unit: full write + readback verification on the target chip. Full
rehearsal (dump -> erase -> write -> boot) requires a donor unit or board.
