from app.audio_devices.latency_profiles import get_latency_profile, list_latency_profiles
from app.audio_devices.settings import load_audio_device_settings


def test_latency_profiles_are_available():
    names = {profile.name for profile in list_latency_profiles()}
    assert {"safe", "balanced", "low", "realtime_experimental"}.issubset(names)
    assert get_latency_profile("balanced").blocksize == 512


def test_audio_device_settings_load_from_yaml():
    settings = load_audio_device_settings("configs/audio_devices.yaml")
    assert settings.samplerate == 48000
    assert settings.channels == 1
    assert "ASIO" in settings.preferred_hostapi_keywords
