# P2 decision table (2026-09-27)

| Experiment | Status | Decision / finding |
|---|---|---|
| E1-alt | done | inconclusive (E1 required); see e1alt-updater-analysis.md |
| E1 | scheduled | operator-assisted same-version reflash; preflight filled in docs/recovery.md |
| E2 | done | see below |
| E3 | done | no read opcode evidenced in code (E1-alt); chip-off is the P3 primary path |
| E4 | done | no pedal USB audio (MIDI-only); external capture required; see below |
| E5 | done | container regeneration verified; see below |
| E6 | done | auto-detectable via identity firmware string (see below) |

## E2 — flasher host

- macOS updater binary: Mach-O x86_64, launches under Rosetta (verified 2026-09-27).
- Launch smoke test: process started and was terminated. First `open` attempt failed with
  `The application cannot be opened for an unexpected reason, error=Error Domain=RBSRequestErrorDomain Code=5 "Launch failed." UserInfo={NSLocalizedFailureReason=Launch failed., NSUnderlyingError=0x... {Error Domain=NSPOSIXErrorDomain Code=111 "Unknown error: 111" UserInfo={NSLocalizedDescription=Launchd job spawn failed}}}`.
  Cause: the unzip step of `tools/extract_updater` drops zip modes, so the extracted
  `Contents/MacOS/EFX Updater` had mode `644` (no execute bit). After `chmod +x` on the
  extracted copy, `open` succeeded; `pgrep -x "EFX Updater"` showed the process
  (PID 38485) which was then `pkill`ed (`pkill exit: 0`, `TERMINATED`). Host is `arm64`
  with `oahd` running, and the signed app is notarized (`spctl`: accepted, Developer ID
  ZOOM CORPORATION), so the run was genuinely under Rosetta.
- Wine: not installed on this machine; the Windows EXE path would need `brew install --cask wine-stable` or a Windows host.
- **Decision:** primary flash host = official macOS updater (Rosetta), pending an actual E1 session; a native SysEx flasher remains the fallback if the GUI updater cannot run or a modified updater is rejected.

## E4 — USB audio routing matrix

Probe: `tools/capture/audio_probe.py` (3 s / 440 Hz tone into an output device while recording an
input device; reports RMS and writes WAV). Device list on the lab Mac, verbatim:

    0 in=0 out=2 USB AUDIO  CODEC
    1 in=2 out=0 USB AUDIO  CODEC
    2 in=2 out=2 FB200 Audio I/O
    3 in=1 out=0 External Microphone
    4 in=0 out=2 External Headphones
    5 in=0 out=2 Mac mini Speakers

**Finding: the G1 Four v2.00 exposes no USB audio streaming interfaces — it is MIDI-only.**

- IORegistry: the `ZOOM G Series` USB device (`1686:04a1`, ZOOM Corporation) has only an
  AudioControl (class 1/subclass 1) and a MIDI Streaming (class 1/subclass 3) interface; there is
  no AudioStreaming (class 1/subclass 2) interface. CoreMIDI lists `ZOOM G Series` in/out;
  CoreAudio lists no ZOOM device.
- The 2-in/2-out class-compliant audio device is a **separate** TI USB-audio codec dongle
  (`08bb:29c0`, "USB AUDIO CODEC", BurrBrown/Texas Instruments vendor string) on the same hub;
  `FB200 Audio I/O` (`cafe:4002`) is another separate gadget. All three enumerate as distinct
  USB devices at distinct bus addresses.
- Zoom's G1 Four manual specifies `USB: USB MIDI`; firmware 2.00 only added looper pre/post and
  the rhythm screen. Community sources agree the G1 Four is not an audio interface. The spec's
  "full-speed, USB Audio + MIDI Streaming" note described the AudioControl-class and
  MIDIStreaming interfaces, not audio streams.

Consequently *physical input -> USB record* and *USB playback -> record* are both impossible on
this pedal; there is no USB routing matrix to measure. Controls measured anyway (played RMS =
0.3536; `ffmpeg volumedetect` mean/max):

| path (indices in -> out) | rate | recorded RMS | mean/max dB | 440 Hz? |
|---|---|---|---|---|
| TI dongle 1 -> 0 (no signal / no loopback at its analog input) | 48000 | 0.0002 | -77.3 / -62.0 | no (peak 0.7 Hz) |
| TI dongle 1 -> 0 | 44100 | 0.0001 | -78.8 / -63.5 | no |
| FB200 2 -> 2 (loopback gadget control) | 44100 | 0.0035 | -49.3 / -44.8 | yes, peak 440.0 Hz, 57% of spectrum in 400–480 Hz |
| Mac mini Speakers 5 -> External Microphone 3 (acoustic control) | 48000 | 0.0068 | -43.4 / -29.4 | yes, peak 440.0 Hz |

The speaker->mic control rules out a macOS microphone-permission problem: the host record path
and a 440 Hz tone are recoverable end-to-end. WAV artifacts (gitignored): `.work/p2/audio/`.

- **Decision per spec rule:** **external audio capture (physical path only)**. No automated USB
  fixture is possible; any P4 audio test must capture the pedal's analog OUTPUT through an
  external USB audio interface (the TI dongle input or FB200 are present). Manual listening
  test is the fallback if the analog capture cannot be wired.

Validation scope: only digital loopback (TI dongle), gadget loopback (FB200), and
acoustic speaker-to-built-in-mic paths were exercised. The analog pedal-output
capture chain has NOT been wired or verified. The RMS values above are
noise-floor/control measurements, not usable thresholds for a bypass-vs-effect
differential.

Spec mapping: with no USB audio at all (not even USB playback loopback), this is
the spec's `else` branch; external capture is chosen because it still produces
recorded evidence, with manual listening as the fallback.

Operator brief for P4 audio tests:
- Cable: pedal OUTPUT (1/4") -> 3.5 mm line-in of a capture interface (TI dongle
  `08bb:29c0` or FB200 `cafe:4002`); the probe records mono channel 0 only.
- Set interface input gain so a played tone peaks well above the control noise
  floor (controls measured RMS 0.0001-0.0068, max -29.4 dB).
- Record a new reference level with the pedal in the chain (bypass vs effect)
  once wired; that differential becomes the P4 fixture tolerance.

- **Effect bypass-vs-on differential:** not measurable over USB (N/A). With external capture it
  needs operator action — a signal source at the pedal INPUT (tone into AUX IN bypasses the
  effects per the manual) and a footswitch/patch toggle for the effect. Not performed here.
- Tooling note: `play_and_record` uses a duplex `sounddevice.playrec` stream. The planned
  `rec()`+`play()` pair never waits for the record stream (`wait()` tracks only the most recent
  stream), so it read uninitialized frames (NaN/full-scale garbage); fixed during E4.

## E5 — zero-change repack round-trip

Tools: `tools/repack_updater/repack_win.py` (PE resource patching in place) and
`tools/repack_updater/repack_mac.py` (resource replacement + ad-hoc re-sign). Unit tests:
`.venv/bin/python -m pytest tools/repack_updater/tests -v` -> `4 passed`. `pefile 2024.8.26`
installed in the venv (already declared under the `recon` extra, installed manually per the
pyproject note). No updater was launched in this task.

### Discovered PE resource layout (matches the P0/plan assumption; no adaptation needed)

The resource type is a **named** top-level entry `BIN` (not a numeric type id); each payload has
a single language entry (LCID 1041), and 7zz renders the same tree as `.rsrc/1041/BIN/<id>`:

| id | file | file offset | size |
|---|---|---|---|
| 129 | Main.bin | 0x4aa28 | 493412 |
| 133 | Preset.bin | 0xc318c | 45056 |
| 136 | FS.bin | 0xce18c | 3137536 |
| 139 | MAIN_INFO.bin | 0x3cc18c | 4096 |
| 142 | ROM.bin | 0x3cd18c | 163840 |

`find_resource_offset` matched via its named-type branch (`type_name == "BIN"`); the RT_RCDATA
id-10 fallback is not exercised on this EXE.

### Windows results

Zero-change repack (all five canonical payloads from `firmware/extracted`), verbatim:

    {'in': '.work/p0/win/G1 FOUR_v2.00_Win_E/ZOOM G1 FOUR System v2.00 Updater.exe', 'out': '.work/p2/repack/zero_change.exe', 'replaced': [129, 133, 136, 139, 142], 'in_sha256': '1dfabfcd45be26738334a8ab5e18a316b5d6beba6dfaa75bd3283771d2dd8a5b', 'out_sha256': '1dfabfcd45be26738334a8ab5e18a316b5d6beba6dfaa75bd3283771d2dd8a5b'}
    ZERO_CHANGE_BYTE_IDENTICAL

One-byte edit (`Main.bin[100] ^= 0xFF` in a copy of the bin dir), verbatim end of the run:
out SHA256 `f18fc4228fcb5f2928d43a63ea1882b9e955b6e225a008f5ac20934fa6056fef` and
`ONE_BYTE_ROUND_TRIP_OK`. `cmp -l` against the original shows exactly 1 differing byte, at file
offset 305804 (`0x4AA2C` = Main.bin resource offset `0x4AA28` + 100), and the resource
re-extracted with 7zz (`.rsrc/1041/BIN/129`) is byte-identical to the patched `Main.bin`.

Limitation: the Windows path patches in place and rejects size-changing payloads (`ValueError`);
a size-changing edit would need the Mac path or a full PE resource rewriter.

### Mac results

Repack of a copy of the official `.app` with the five canonical bins, then ad-hoc re-sign,
verbatim:

    {'app': '.work/p2/repack/Updater.app', 'replaced': ['FS.bin', 'MAIN_INFO.bin', 'Main.bin', 'Preset.bin', 'ROM.bin'], 'verified': True}
    MAC_SIGNED_OK

`codesign --verify --deep --strict` passes; `codesign -dv` reports `Signature=adhoc`,
`Identifier=jp.co.zoom.EFX-Updater`, `TeamIdentifier=not set` — the Developer ID/notarization
chain is gone after editing, as expected. All five resources are byte-identical to
`firmware/extracted` after the repack (`sha256sum -c SHA256SUMS`: all `OK`); the upstream
`_CodeSignature`/`CodeResources` are superseded by the ad-hoc signature. Only signature validity
was checked (the no-launch rule stands); actual launchability of the modified app is untested and
left to P5a.

### Decision

- **No mismatch** in the zero-change round-trip (EXE out SHA == in SHA; Mac payloads
  byte-identical to the originals) and the one-byte edit landed exactly at resource 129 —
  decision rule outcome: **container regeneration verified**; no issue found before P5a.

### Windows/Mac signing note for P5a

Windows signing note for P5a: byte patching invalidates the EXE's Authenticode
signature and leaves the PE checksum stale. Windows ignores the checksum for
user-mode EXEs, but expect SmartScreen/UAC "Unknown publisher" friction when
running a repacked updater. Options if it blocks: recompute the checksum with
`pefile.generate_checksum()` or run the flash from a Windows host/VM with
SmartScreen bypass. Mac side: repack uses ad-hoc signing plus
`codesign --verify --strict`.

## E6 — update-mode descriptors (2026-09-27, operator-assisted)

Normal mode (baseline, `.work/p2/e6/normal.txt`):
- USB `1686:04a1`, product `ZOOM G Series`, `bcdDevice 0x0100`, one config,
  interface 0 = class 1/1 (AudioControl, 0 endpoints), interface 1 = class 1/3
  (MIDIStreaming, 2 endpoints). MIDI ports `ZOOM G Series` in/out.
- Identity: `7E 00 06 02 52 6E 00 0C 00 32 2E 30 30` -> G1 Four, firmware 2.00.

Update mode (both footswitches held while plugging USB; `.work/p2/e6/update.txt`):
- USB descriptors and MIDI ports are IDENTICAL to normal mode (same PID, product
  string, `bcdDevice`, interface layout, 2 endpoints). The device does not
  re-enumerate differently.
- Identity still responds, but reports firmware **1.00** (boot ROM):
  `7E 00 06 02 52 6E 00 0C 00 31 2E 30 30`.

Decision: mode is auto-detectable via the identity firmware string — the value
reports whichever firmware is running (application version vs boot ROM). A
future `zoomctl mode` must compare against the expected application version
(e.g. from the latest verified manifest or `MAIN_INFO.bin`), not a hardcoded
"1.00". Implementation deferred to P3/P4a; recorded here as the expectation.

Note: `system_profiler SPUSBDataType` does not list USB devices in this
environment; `ioreg -p IOUSB -l` was used for descriptors.

## E1 — not yet executed (paused 2026-09-27)

Status: paused by the operator before clicking Execute. Preflight is filled and
committed (`docs/recovery.md`, "E1 preflight"), the updater app launches under
Rosetta (E2), and the side-capture logger is proven working: while the updater
was merely open, `.work/p2/e1/session.log` captured the app's own identity
exchange (`7E 00 06 02 52 6E 00 0C 00 32 2E 30 30`, firmware 2.00).

Resume steps:
1. Enter update mode: unplug, hold both footswitches, plug in, release on
   FIRMWARE UPDATE.
2. Start capture:
   `.venv/bin/python -m tools.capture.midi_log --out .work/p2/e1/session.log`
3. Open the updater app, Rescan if needed, click Execute, wait for Complete!.
4. Stop the logger; unplug/replug; verify `zoomctl identity` still reports
   G1 Four / 2.00.
5. Analyze the captured log with the E1-alt report; fill the E1 row and the
   FS.bin conclusion; append the operation-log entry in `docs/recovery.md`;
   commit.
