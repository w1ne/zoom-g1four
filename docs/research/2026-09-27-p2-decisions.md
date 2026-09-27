# P2 decision table (2026-09-27)

| Experiment | Status | Decision / finding |
|---|---|---|
| E1-alt | done | inconclusive (E1 required); see e1alt-updater-analysis.md |
| E2 | done | see below |
| E3 | pending | |
| E4 | pending | |
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
