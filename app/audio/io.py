from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import sounddevice as sd
import soundfile as sf

from app.audio.format import ensure_audio_shape


def load_audio(path: Path, sample_rate: int, *, mono: bool = False) -> tuple[np.ndarray, int]:
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku audio: {path}")
    audio, sr = librosa.load(path, sr=sample_rate, mono=mono)
    return ensure_audio_shape(np.asarray(audio)), sr


def save_audio(path: Path, audio: np.ndarray, sample_rate: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, ensure_audio_shape(np.asarray(audio)), sample_rate)
    return path


def list_output_devices() -> list[dict]:
    devices = sd.query_devices()
    return [dict(device) for device in devices if int(device.get("max_output_channels", 0)) > 0]


def select_output_device(preferred_driver: str | None = None, preferred_name: str | None = None) -> int | None:
    devices = list_output_devices()
    if not devices:
        return None

    for device in devices:
        name = str(device.get("name", "")).lower()
        if preferred_driver and preferred_driver.lower() in name:
            return int(device.get("index", 0))
    for device in devices:
        name = str(device.get("name", "")).lower()
        if preferred_name and preferred_name.lower() in name:
            return int(device.get("index", 0))
    return int(devices[0].get("index", 0))


def play_audio(
    audio: np.ndarray,
    sample_rate: int,
    *,
    preferred_driver: str | None = "asio",
    preferred_name: str | None = "asio4all",
    block: bool = True,
) -> int | None:
    device = select_output_device(preferred_driver=preferred_driver, preferred_name=preferred_name)
    playback = ensure_audio_shape(np.asarray(audio))
    sd.play(playback, samplerate=sample_rate, device=device)
    if block:
        sd.wait()
    return device


