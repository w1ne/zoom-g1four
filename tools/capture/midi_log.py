"""Log MIDI messages from a ZOOM port to a timestamped text file.

macOS limitation: CoreMIDI lets several listeners observe a source, so this
records device->host traffic while the vendor updater runs. Host->device
commands are inferred from E1-alt static analysis. Full bidirectional capture
requires a Linux usbmon host (see tools/capture/README.md).

Sysex payloads are logged in full. Channel/other messages log their data bytes
after the status byte; single-byte realtime messages (clock) log type only.
Timestamps come from poll time (write time), quantized by the 10 ms poll loop.
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import mido


def format_message(message, elapsed: float) -> str:
    data = getattr(message, "data", None)
    prefix = f"{elapsed:9.3f} {message.type:12s}"
    if data is None:
        raw = message.bytes()
        if len(raw) <= 1:
            return prefix
        data = raw[1:]
    return prefix + " " + " ".join(f"{byte:02X}" for byte in data)


def record(
    input_name_prefix: str,
    out_path: Path,
    duration: float | None,
    append: bool = False,
) -> int:
    names = [name for name in mido.get_input_names() if name.startswith(input_name_prefix)]
    if not names:
        print(f"no MIDI input starting with {input_name_prefix!r}", file=sys.stderr)
        return 2
    out_path = Path(out_path)
    if out_path.exists() and not append:
        print(f"refusing to overwrite {out_path}; pass --append to append", file=sys.stderr)
        return 3
    out_path.parent.mkdir(parents=True, exist_ok=True)
    port = mido.open_input(names[0])
    started = time.monotonic()
    count = 0
    interrupted = False
    try:
        with open(out_path, "a" if append else "x", encoding="ascii") as log:
            log.write(f"# port: {names[0]}\n")
            log.write(
                f"# started: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
            )
            while duration is None or time.monotonic() - started < duration:
                message = port.poll()
                if message is None:
                    time.sleep(0.01)
                    continue
                log.write(format_message(message, time.monotonic() - started) + "\n")
                log.flush()
                count += 1
    except KeyboardInterrupt:
        interrupted = True
    finally:
        port.close()
    print(f"logged {count} messages to {out_path}")
    return 130 if interrupted else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.capture.midi_log")
    parser.add_argument("--port-prefix", default="ZOOM G")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=None, help="seconds; default until interrupted")
    parser.add_argument("--append", action="store_true", help="append instead of refusing to overwrite")
    args = parser.parse_args(argv)
    return record(args.port_prefix, args.out, args.duration, append=args.append)


if __name__ == "__main__":
    raise SystemExit(main())
