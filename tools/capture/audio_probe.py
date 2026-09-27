"""E4: probe the pedal's USB audio routing.

Plays a test tone into a chosen output device while recording from a chosen
input device, then reports RMS levels so we can decide whether an automated
audio fixture is possible (spec E4 decision rule).
"""

import argparse
import math
import sys
import wave
from pathlib import Path


def sine_samples(frequency: float, seconds: float, rate: int, amplitude: float = 0.5) -> list[float]:
    total = int(rate * seconds)
    return [amplitude * math.sin(2 * math.pi * frequency * index / rate) for index in range(total)]


def rms(samples) -> float:
    values = list(samples)
    if not values:
        return 0.0
    return math.sqrt(sum(value * value for value in values) / len(values))


def write_wav(path: Path, samples, rate: int) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        frames = bytearray()
        for value in samples:
            clamped = max(-1.0, min(1.0, value))
            frames += int(clamped * 32767).to_bytes(2, "little", signed=True)
        wav.writeframes(bytes(frames))
    return path


def list_devices() -> list[tuple[int, str, int, int]]:
    import sounddevice

    devices = []
    for index, device in enumerate(sounddevice.query_devices()):
        devices.append((index, device["name"], device["max_input_channels"], device["max_output_channels"]))
    return devices


def play_and_record(out_index: int, in_index: int, rate: int, seconds: float, wav_path: Path) -> dict:
    import sounddevice

    tone = sine_samples(frequency=440.0, seconds=seconds, rate=rate)
    recording = sounddevice.playrec(tone, samplerate=rate, channels=1, device=(in_index, out_index))
    sounddevice.wait()
    recorded = [float(value) for frame in recording for value in frame]
    write_wav(wav_path, recorded, rate=rate)
    return {"played_rms": rms(tone), "recorded_rms": rms(recorded)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.capture.audio_probe")
    parser.add_argument("--list", action="store_true", help="list audio devices and exit")
    parser.add_argument("--out-index", type=int)
    parser.add_argument("--in-index", type=int)
    parser.add_argument("--rate", type=int, default=44100)
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--wav", type=Path, default=Path(".work/p2/audio/recorded.wav"))
    args = parser.parse_args(argv)

    if args.list:
        for index, name, inputs, outputs in list_devices():
            print(f"{index:3d} in={inputs} out={outputs} {name}")
        return 0

    if args.out_index is None or args.in_index is None:
        parser.error("--out-index and --in-index are required unless --list is used")

    try:
        result = play_and_record(args.out_index, args.in_index, args.rate, args.seconds, args.wav)
    except Exception as error:
        print(
            f"error: {error} (check --list for valid device indices; a busy device also fails)",
            file=sys.stderr,
        )
        return 1
    print(f"played_rms={result['played_rms']:.4f} recorded_rms={result['recorded_rms']:.4f} wav={args.wav}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
