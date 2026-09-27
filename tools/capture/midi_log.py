"""Log all MIDI messages from a ZOOM port to a timestamped text file.

macOS limitation: CoreMIDI lets several listeners observe a source, so this
records device->host traffic while the vendor updater runs. Host->device
commands are inferred from E1-alt static analysis. Full bidirectional capture
requires a Linux usbmon host (see tools/capture/README.md).
"""

import argparse
import sys
import time
from pathlib import Path

import mido


def format_message(message, elapsed: float) -> str:
    data = getattr(message, "data", None)
    prefix = f"{elapsed:9.3f} {message.type:12s}"
    if data is None:
        return prefix
    return prefix + " " + " ".join(f"{byte:02X}" for byte in data)


def record(input_name_prefix: str, out_path: Path, duration: float | None) -> int:
    names = [name for name in mido.get_input_names() if name.startswith(input_name_prefix)]
    if not names:
        print(f"no MIDI input starting with {input_name_prefix!r}", file=sys.stderr)
        return 2
    port = mido.open_input(names[0])
    started = time.monotonic()
    count = 0
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="ascii") as log:
        log.write(f"# port: {names[0]}\n")
        while duration is None or time.monotonic() - started < duration:
            message = port.poll()
            if message is None:
                time.sleep(0.01)
                continue
            log.write(format_message(message, time.monotonic() - started) + "\n")
            log.flush()
            count += 1
    port.close()
    print(f"logged {count} messages to {out_path}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.capture.midi_log")
    parser.add_argument("--port-prefix", default="ZOOM G")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=None, help="seconds; default until interrupted")
    args = parser.parse_args(argv)
    return record(args.port_prefix, args.out, args.duration)


if __name__ == "__main__":
    raise SystemExit(main())
