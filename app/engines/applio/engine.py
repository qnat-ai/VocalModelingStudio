import logging
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from app.audio.format import ensure_audio_shape

logger = logging.getLogger(__name__)


class ApplioEngine:
    """Backend konwersji głosu korzystający z API Gradio instancji Applio."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    def convert(self, audio: np.ndarray, sr: int, reference_path: Path) -> np.ndarray:
        """Call a locally running Applio instance through its Gradio API."""
        strict = bool(self.config.get("strict", False))
        applio_cfg = self.config.get("applio", {})
        url = str(applio_cfg.get("url", "http://127.0.0.1:7860"))
        api_name = applio_cfg.get("api_name")  # e.g. "/run" — required
        param_map = applio_cfg.get("param_map", {})
        output_key = applio_cfg.get("output_key")

        if not api_name:
            message = (
                "voice_conversion.applio.api_name is not set. Run "
                "`python tools/applio_probe.py --url <applio-url>` against your running "
                "Applio instance, then copy the inference endpoint name into configs/default.yaml."
            )
            if strict:
                raise RuntimeError(message)
            return audio

        try:
            from gradio_client import Client
        except ImportError:
            if strict:
                raise RuntimeError(
                    "gradio_client is not installed. Install it with: pip install gradio_client"
                ) from None
            return audio

        with tempfile.TemporaryDirectory(prefix="vms_applio_") as tmp_dir:
            tmp = Path(tmp_dir)
            input_wav = tmp / "input.wav"
            sf.write(input_wav, ensure_audio_shape(np.asarray(audio)), sr)

            kwargs: dict[str, Any] = {}
            kwargs[param_map.get("input_audio", "input_audio")] = str(input_wav)
            kwargs[param_map.get("reference_audio", "reference_audio")] = str(reference_path)
            for our_key, applio_key in param_map.items():
                if our_key in ("input_audio", "reference_audio"):
                    continue
                if our_key in applio_cfg.get("extra_params", {}):
                    kwargs[applio_key] = applio_cfg["extra_params"][our_key]

            try:
                client = Client(url)
                result = client.predict(api_name=api_name, **kwargs)
            except Exception as exc:
                if strict:
                    raise RuntimeError(f"Applio conversion failed: {exc}") from exc
                return audio

            output_path = self._extract_output_path(result, output_key)
            if output_path is None or not Path(output_path).exists():
                if strict:
                    raise RuntimeError(f"Applio call returned no usable output audio path: {result!r}")
                return audio

            converted, _ = sf.read(output_path, always_2d=False)
            return ensure_audio_shape(np.asarray(converted))

    @staticmethod
    def _extract_output_path(result: Any, output_key: str | int | None) -> str | None:
        if output_key is not None:
            try:
                if isinstance(output_key, int):
                    candidate = result[output_key]
                else:
                    candidate = result[output_key]
            except (KeyError, IndexError, TypeError):
                candidate = None
        else:
            candidate = result

        if isinstance(candidate, dict):
            candidate = candidate.get("path") or candidate.get("name") or candidate.get("value")
        if isinstance(candidate, (tuple, list)) and candidate:
            candidate = candidate[0]
        if isinstance(candidate, str):
            return candidate
        return None
