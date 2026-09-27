# Capture tooling

## MIDI side-capture (macOS)

`midi_log.py` records device->host MIDI traffic from the ZOOM port while the
vendor updater runs (CoreMIDI allows multiple listeners). Host->device commands
are not observable this way; they are inferred from `analyze_updater.py` static
analysis. Usage:

    .venv/bin/python -m tools.capture.midi_log --out .work/p2/e1/session.log

Logs refuse to overwrite by default (`--append` to append). Sysex payloads are
complete; channel messages log their data bytes; realtime single-byte messages
log the type only. Timestamps are poll-time (10 ms quantization).

## Full bidirectional capture (Linux host, optional)

On a Linux host with the pedal attached:

    sudo modprobe usbmon
    lsusb                       # identify the bus
    sudo tshark -i usbmon1 -w capture.pcapng

Run the official updater while capturing, then analyze with Wireshark. This
captures both directions including the updater's commands.

## E1-alt static analysis

`analyze_updater.py` scans updater binaries for protocol signatures and payload
names; results are recorded in
`docs/research/2026-09-27-e1alt-updater-analysis.md`.
