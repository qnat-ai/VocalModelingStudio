from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import soundfile as sf

from app.models.voice_conversion import VoiceConversionEngine


def _write_wav(path: Path, seconds: float = 0.2, sample_rate: int = 16_000) -> None:
    t = np.linspace(0.0, seconds, int(sample_rate * seconds), endpoint=False)
    audio = 0.1 * np.sin(2 * np.pi * 220.0 * t)
    sf.write(path, audio, sample_rate)


def test_disabled_engine_is_noop():
    engine = VoiceConversionEngine(enabled=False, config={"backend": "applio_gradio"})
    audio = np.zeros(100, dtype=np.float64)
    result = engine.convert(audio, 16_000, reference_path=Path("does_not_matter.wav"))
    assert result is audio


def test_applio_backend_without_api_name_returns_audio_unchanged(tmp_path):
    reference = tmp_path / "reference.wav"
    _write_wav(reference)
    engine = VoiceConversionEngine(
        enabled=True,
        config={"backend": "applio_gradio", "applio": {"url": "http://127.0.0.1:7860"}},
    )
    audio = np.zeros(100, dtype=np.float64)
    result = engine.convert(audio, 16_000, reference_path=reference)
    np.testing.assert_array_equal(result, audio)


def test_applio_backend_without_api_name_raises_in_strict_mode(tmp_path):
    reference = tmp_path / "reference.wav"
    _write_wav(reference)
    engine = VoiceConversionEngine(
        enabled=True,
        config={"backend": "applio_gradio", "strict": True, "applio": {"url": "http://127.0.0.1:7860"}},
    )
    audio = np.zeros(100, dtype=np.float64)
    try:
        engine.convert(audio, 16_000, reference_path=reference)
        raise AssertionError("Expected RuntimeError due to missing api_name in strict mode")
    except RuntimeError as exc:
        assert "api_name" in str(exc)


def _install_fake_gradio_client(monkeypatch, *, predict_return, capture: dict):
    """Install a fake `gradio_client` module into sys.modules.

    VoiceConversionEngine imports gradio_client lazily inside the method
    (`from gradio_client import Client`), so injecting a fake module into
    sys.modules before the call is enough to intercept it without needing
    the real dependency installed.
    """

    class _FakeClient:
        def __init__(self, url):
            capture["url"] = url

        def predict(self, *, api_name, **kwargs):
            capture["api_name"] = api_name
            capture["kwargs"] = kwargs
            # The temp dir holding the input wav is cleaned up as soon as
            # `convert()` returns, so any "did the input file exist" check
            # must happen here, while the call is in flight, not afterwards.
            capture["input_audio_existed_during_call"] = Path(kwargs.get("audio_in", "")).exists()
            return predict_return

    fake_module = types.ModuleType("gradio_client")
    fake_module.Client = _FakeClient
    monkeypatch.setitem(sys.modules, "gradio_client", fake_module)


def test_applio_backend_calls_client_predict_and_reads_output(tmp_path, monkeypatch):
    reference = tmp_path / "reference.wav"
    _write_wav(reference)

    output_wav = tmp_path / "converted_output.wav"
    _write_wav(output_wav, seconds=0.3)

    capture: dict = {}
    _install_fake_gradio_client(monkeypatch, predict_return=(str(output_wav), "some status text"), capture=capture)

    engine = VoiceConversionEngine(
        enabled=True,
        config={
            "backend": "applio_gradio",
            "applio": {
                "url": "http://127.0.0.1:7860",
                "api_name": "/run",
                "output_key": 0,
                "param_map": {
                    "input_audio": "audio_in",
                    "reference_audio": "voice_model",
                },
            },
        },
    )

    audio = np.zeros(1_000, dtype=np.float64)
    result = engine.convert(audio, 16_000, reference_path=reference)

    assert capture["url"] == "http://127.0.0.1:7860"
    assert capture["api_name"] == "/run"
    assert capture["kwargs"]["voice_model"] == str(reference)
    assert capture["input_audio_existed_during_call"] is True
    # Result should be the (re-read) contents of output_wav, not the original silent input.
    assert result.shape[0] > 0
    # Original 'audio' was 1000 samples, 'output_wav' was 4800 samples (0.3s * 16000)
    # result should match output_wav. We don't compare against original 'audio' because shapes differ.
    assert result.shape[0] == 4800


def test_applio_backend_predict_failure_is_swallowed_when_not_strict(tmp_path, monkeypatch):
    reference = tmp_path / "reference.wav"
    _write_wav(reference)

    class _RaisingClient:
        def __init__(self, url):
            pass

        def predict(self, *, api_name, **kwargs):
            raise RuntimeError("simulated network failure")

    fake_module = types.ModuleType("gradio_client")
    fake_module.Client = _RaisingClient
    monkeypatch.setitem(sys.modules, "gradio_client", fake_module)

    engine = VoiceConversionEngine(
        enabled=True,
        config={
            "backend": "applio_gradio",
            "applio": {"url": "http://127.0.0.1:7860", "api_name": "/run"},
        },
    )
    audio = np.zeros(100, dtype=np.float64)
    result = engine.convert(audio, 16_000, reference_path=reference)
    np.testing.assert_array_equal(result, audio)


def test_applio_backend_predict_failure_raises_when_strict(tmp_path, monkeypatch):
    reference = tmp_path / "reference.wav"
    _write_wav(reference)

    class _RaisingClient:
        def __init__(self, url):
            pass

        def predict(self, *, api_name, **kwargs):
            raise RuntimeError("simulated network failure")

    fake_module = types.ModuleType("gradio_client")
    fake_module.Client = _RaisingClient
    monkeypatch.setitem(sys.modules, "gradio_client", fake_module)

    engine = VoiceConversionEngine(
        enabled=True,
        config={
            "backend": "applio_gradio",
            "strict": True,
            "applio": {"url": "http://127.0.0.1:7860", "api_name": "/run"},
        },
    )
    audio = np.zeros(100, dtype=np.float64)
    try:
        engine.convert(audio, 16_000, reference_path=reference)
        raise AssertionError("Expected RuntimeError to propagate in strict mode")
    except RuntimeError as exc:
        assert "simulated network failure" in str(exc)


def test_missing_gradio_client_dependency_is_noop_when_not_strict(tmp_path, monkeypatch):
    reference = tmp_path / "reference.wav"
    _write_wav(reference)
    monkeypatch.setitem(sys.modules, "gradio_client", None)  # simulate ImportError on `from gradio_client import Client`

    engine = VoiceConversionEngine(
        enabled=True,
        config={
            "backend": "applio_gradio",
            "applio": {"url": "http://127.0.0.1:7860", "api_name": "/run"},
        },
    )
    audio = np.zeros(100, dtype=np.float64)
    result = engine.convert(audio, 16_000, reference_path=reference)
    np.testing.assert_array_equal(result, audio)
