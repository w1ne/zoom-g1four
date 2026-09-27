# P2 decision table (2026-09-27)

| Experiment | Status | Decision / finding |
|---|---|---|
| E1-alt | done | inconclusive (E1 required); see e1alt-updater-analysis.md |
| E2 | done | see below |
| E3 | pending | |
| E4 | done | no pedal USB audio (MIDI-only); external capture required; see below |
| E5 | pending | |
| E6 | pending | |

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
