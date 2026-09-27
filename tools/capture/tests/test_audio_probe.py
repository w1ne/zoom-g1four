import math

from tools.capture import audio_probe


def test_sine_samples_length_and_range():
    samples = audio_probe.sine_samples(frequency=440.0, seconds=0.1, rate=8000)
    assert len(samples) == 800
    assert all(-1.0 <= value <= 1.0 for value in samples)


def test_rms_of_sine_is_amplitude_over_sqrt_two():
    samples = audio_probe.sine_samples(frequency=440.0, seconds=0.5, rate=8000, amplitude=0.5)
    assert math.isclose(audio_probe.rms(samples), 0.5 / math.sqrt(2), rel_tol=0.02)


def test_rms_of_silence_is_zero():
    assert audio_probe.rms([0.0] * 100) == 0.0


def test_write_wav_round_trip(tmp_path):
    import wave

    path = tmp_path / "tone.wav"
    samples = audio_probe.sine_samples(frequency=440.0, seconds=0.05, rate=8000)
    audio_probe.write_wav(path, samples, rate=8000)

    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == 8000
        assert wav.getnchannels() == 1
        assert wav.getnframes() == len(samples)
