"""Low-latency monitoring stream.

This is a small realtime preview layer. It deliberately performs only a pass-
through operation inside the callback. Heavy AI processing should run offline or
in a separate buffered worker.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from app.audio_devices.device_manager import AudioDeviceManager
from app.realtime.config import RealtimeConfig, load_realtime_config


@dataclass
class StreamStats:
    callbacks: int = 0
    underflows: int = 0
    overflows: int = 0
    last_status: str = ""


class LowLatencyMonitor:
    """Simple input-to-output monitor using sounddevice.Stream."""

    def __init__(
        self,
        config: RealtimeConfig | None = None,
        *,
        input_device: int | None = None,
        output_device: int | None = None,
    ) -> None:
        self.config = config or load_realtime_config()
        self.input_device = input_device
        self.output_device = output_device
        self.manager = AudioDeviceManager()
        self.sd = self.manager._sd  # sounddevice module; intentionally internal wrapper
        self.stats = StreamStats()
        self._stream = None

    def _callback(self, indata, outdata, frames, time_info, status) -> None:  # noqa: ANN001
        self.stats.callbacks += 1
        if status:
            text = str(status)
            self.stats.last_status = text
            if "input overflow" in text.lower():
                self.stats.overflows += 1
            if "output underflow" in text.lower():
                self.stats.underflows += 1

        # Pass-through with channel safety.
        if indata.shape[1] == outdata.shape[1]:
            outdata[:] = indata
        else:
            mono = np.mean(indata, axis=1, keepdims=True)
            outdata[:] = np.repeat(mono, outdata.shape[1], axis=1)

    def open(self) -> None:
        if self.input_device is None:
            preferred_input = self.manager.preferred_input_device()
            self.input_device = preferred_input.index if preferred_input else None
        if self.output_device is None:
            preferred_output = self.manager.preferred_output_device()
            self.output_device = preferred_output.index if preferred_output else None

        self._stream = self.sd.Stream(
            samplerate=self.config.samplerate,
            blocksize=self.config.blocksize,
            latency=self.config.latency,
            channels=self.config.channels,
            dtype="float32",
            device=(self.input_device, self.output_device),
            callback=self._callback,
        )
        self._stream.start()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def run_for_seconds(self, seconds: float) -> StreamStats:
        """Open the stream, run for N seconds, return stats."""
        self.open()
        try:
            time.sleep(max(0.1, float(seconds)))
        finally:
            self.close()
        return self.stats

    def __enter__(self) -> "LowLatencyMonitor":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.close()
