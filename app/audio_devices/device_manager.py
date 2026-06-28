"""Audio device discovery and selection.

This module wraps `sounddevice` in a way that keeps the rest of the project
importable even when sounddevice or PortAudio/ASIO support is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .settings import AudioDeviceSettings, load_audio_device_settings


class SoundDeviceUnavailableError(RuntimeError):
    """Raised when sounddevice cannot be imported or used."""


@dataclass(frozen=True)
class AudioHostApi:
    index: int
    name: str
    device_count: int
    default_input_device: int
    default_output_device: int


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    hostapi: int
    hostapi_name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    default_low_input_latency: float | None = None
    default_low_output_latency: float | None = None
    default_high_input_latency: float | None = None
    default_high_output_latency: float | None = None

    @property
    def can_input(self) -> bool:
        return self.max_input_channels > 0

    @property
    def can_output(self) -> bool:
        return self.max_output_channels > 0


class AudioDeviceManager:
    """Discover and select audio devices through sounddevice/PortAudio."""

    def __init__(self, settings: AudioDeviceSettings | None = None) -> None:
        self.settings = settings or load_audio_device_settings()
        self._sd = self._import_sounddevice()

    @staticmethod
    def _import_sounddevice() -> Any:
        try:
            import sounddevice as sd  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on local machine
            raise SoundDeviceUnavailableError(
                "sounddevice is not available. Install it with: pip install sounddevice"
            ) from exc
        return sd

    def query_hostapis(self) -> list[AudioHostApi]:
        """Return host APIs visible to PortAudio."""
        hostapis = self._sd.query_hostapis()
        result: list[AudioHostApi] = []
        for index, api in enumerate(hostapis):
            result.append(
                AudioHostApi(
                    index=index,
                    name=str(api.get("name", "")),
                    device_count=int(api.get("deviceCount", 0)),
                    default_input_device=int(api.get("defaultInputDevice", -1)),
                    default_output_device=int(api.get("defaultOutputDevice", -1)),
                )
            )
        return result

    def query_devices(self) -> list[AudioDevice]:
        """Return all devices visible to sounddevice."""
        raw_devices = self._sd.query_devices()
        hostapis = self.query_hostapis()
        hostapi_names = {api.index: api.name for api in hostapis}
        devices: list[AudioDevice] = []

        for index, dev in enumerate(raw_devices):
            hostapi_index = int(dev.get("hostapi", -1))
            devices.append(
                AudioDevice(
                    index=index,
                    name=str(dev.get("name", "")),
                    hostapi=hostapi_index,
                    hostapi_name=hostapi_names.get(hostapi_index, "unknown"),
                    max_input_channels=int(dev.get("max_input_channels", 0)),
                    max_output_channels=int(dev.get("max_output_channels", 0)),
                    default_samplerate=float(dev.get("default_samplerate", 0.0)),
                    default_low_input_latency=_optional_float(dev.get("default_low_input_latency")),
                    default_low_output_latency=_optional_float(dev.get("default_low_output_latency")),
                    default_high_input_latency=_optional_float(dev.get("default_high_input_latency")),
                    default_high_output_latency=_optional_float(dev.get("default_high_output_latency")),
                )
            )
        return devices

    def find_device(
        self,
        *,
        role: str,
        preferred_keywords: Iterable[str] | None = None,
        hostapi_keywords: Iterable[str] | None = None,
    ) -> AudioDevice | None:
        """Find a preferred input or output device.

        Args:
            role: `input` or `output`.
            preferred_keywords: substrings expected in device name.
            hostapi_keywords: substrings expected in host API name.
        """
        if role not in {"input", "output"}:
            raise ValueError("role must be 'input' or 'output'")

        preferred_keywords = list(preferred_keywords or [])
        hostapi_keywords = list(hostapi_keywords or self.settings.preferred_hostapi_keywords)
        all_devices = self.query_devices()
        if role == "input":
            devices = [device for device in all_devices if device.can_input]
        else:
            devices = [device for device in all_devices if device.can_output]

        def score(device: AudioDevice) -> int:
            value = 0
            value += _keyword_score(device.name, preferred_keywords) * 10
            value += _keyword_score(device.hostapi_name, hostapi_keywords) * 5
            value += _keyword_score(device.hostapi_name, self.settings.fallback_hostapi_keywords)
            return value

        if not devices:
            return None
        ranked = sorted(devices, key=score, reverse=True)
        best = ranked[0]
        return best if score(best) > 0 else ranked[0]

    def preferred_input_device(self) -> AudioDevice | None:
        return self.find_device(role="input", preferred_keywords=self.settings.preferred_input_keywords)

    def preferred_output_device(self) -> AudioDevice | None:
        return self.find_device(role="output", preferred_keywords=self.settings.preferred_output_keywords)

    def check_stream_settings(
        self,
        *,
        samplerate: int,
        channels: int,
        input_device: int | None = None,
        output_device: int | None = None,
    ) -> dict[str, str]:
        """Check input/output stream settings through sounddevice.

        Returns a status dictionary instead of raising, so CLI tools can show a
        readable diagnostic.
        """
        status: dict[str, str] = {}
        try:
            self._sd.check_input_settings(device=input_device, samplerate=samplerate, channels=channels)
            status["input"] = "ok"
        except Exception as exc:  # pragma: no cover - hardware dependent
            status["input"] = f"error: {exc}"

        try:
            self._sd.check_output_settings(device=output_device, samplerate=samplerate, channels=channels)
            status["output"] = "ok"
        except Exception as exc:  # pragma: no cover - hardware dependent
            status["output"] = f"error: {exc}"

        return status


def _keyword_score(text: str, keywords: Iterable[str]) -> int:
    text_lower = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in text_lower)


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
