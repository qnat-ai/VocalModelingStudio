from app.realtime.config import load_realtime_config


def test_realtime_config_loads_default_profile():
    config = load_realtime_config("configs/realtime.yaml")
    assert config.profile_name == "balanced"
    assert config.samplerate == 48000
    assert config.blocksize == 512
    assert config.allow_heavy_ai_in_callback is False


def test_realtime_config_loads_named_profile():
    config = load_realtime_config("configs/realtime.yaml", profile_name="safe")
    assert config.profile_name == "safe"
    assert config.blocksize == 1024
