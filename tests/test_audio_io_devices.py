from __future__ import annotations

from app.audio.io import select_output_device


def test_select_output_device_prefers_asio(monkeypatch):
    fake_devices = [
        {"index": 0, "name": "Speakers (Realtek)", "max_output_channels": 2},
        {"index": 3, "name": "ASIO4ALL v2", "max_output_channels": 2},
    ]

    monkeypatch.setattr("sounddevice.query_devices", lambda: fake_devices)

    selected = select_output_device(preferred_driver="asio", preferred_name="asio4all")

    assert selected == 3

