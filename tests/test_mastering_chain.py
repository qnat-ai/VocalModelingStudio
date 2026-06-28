from __future__ import annotations

import numpy as np
import soundfile as sf

from app.mastering.chain import MasteringChain, MasteringSettings


def test_mastering_chain_process_audio_limits_peak():
    sample_rate = 48_000
    time = np.linspace(0.0, 1.0, sample_rate, endpoint=False)
    audio = 1.25 * np.sin(2 * np.pi * 110.0 * time)

    chain = MasteringChain(
        MasteringSettings(
            enable_highpass=True,
            highpass_hz=70.0,
            compressor_threshold_db=-18.0,
            compressor_ratio=2.5,
            limiter_ceiling_db=-1.0,
            makeup_gain_db=0.0,
        )
    )
    processed = chain.process_audio(audio, sample_rate)

    assert processed.shape == audio.shape
    assert float(np.max(np.abs(processed))) <= 10 ** (-1.0 / 20) + 1e-6


def test_mastering_chain_process_file(tmp_path):
    sample_rate = 48_000
    time = np.linspace(0.0, 0.25, int(sample_rate * 0.25), endpoint=False)
    audio = 0.1 * np.sin(2 * np.pi * 220.0 * time)
    input_path = tmp_path / "input.wav"
    output_path = tmp_path / "output.wav"
    sf.write(input_path, audio, sample_rate)

    result = MasteringChain().process(input_path, output_path)

    assert result == output_path
    assert output_path.exists()


def test_mastering_chain_adaptive_profile_is_bounded():
    sample_rate = 48_000
    time = np.linspace(0.0, 1.0, sample_rate, endpoint=False)
    audio = 0.02 * np.sin(2 * np.pi * 180.0 * time)

    settings = MasteringSettings(
        compressor_threshold_db=-18.0,
        compressor_ratio=2.0,
        limiter_ceiling_db=-1.0,
        makeup_gain_db=0.0,
        adaptive_enabled=True,
        adaptive_target_rms_dbfs=-18.0,
        adaptive_min_ratio=1.3,
        adaptive_max_ratio=3.2,
        adaptive_max_makeup_db=5.0,
    )
    chain = MasteringChain(settings)
    processed = chain.process_audio(audio, sample_rate)
    profile = chain.get_last_profile()

    assert processed.shape == audio.shape
    assert profile["adaptive_enabled"] is True
    assert 1.3 <= float(profile["compressor_ratio"]) <= 3.2
    assert 0.0 <= float(profile["makeup_gain_db"]) <= 5.0
    assert float(profile["compressor_threshold_db"]) <= -8.0
    assert float(np.max(np.abs(processed))) <= 10 ** (-1.0 / 20) + 1e-6


def test_mastering_chain_air_and_width_on_stereo():
    sample_rate = 48_000
    time = np.linspace(0.0, 1.0, sample_rate, endpoint=False)
    left = 0.2 * np.sin(2 * np.pi * 200.0 * time)
    right = 0.2 * np.sin(2 * np.pi * 220.0 * time)
    stereo = np.column_stack((left, right))

    chain = MasteringChain(
        MasteringSettings(
            air_amount=0.5,
            air_cutoff_hz=8_000.0,
            stereo_width=1.4,
            limiter_ceiling_db=-1.0,
            adaptive_enabled=False,
        )
    )
    processed = chain.process_audio(stereo, sample_rate)

    assert processed.shape == stereo.shape
    assert float(np.max(np.abs(processed))) <= 1.0 + 1e-6


