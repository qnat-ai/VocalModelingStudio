# CHANGELOG

## v0.2.1 — patch 001

### Dodano
- Moduł `app/audio_devices/` do wykrywania i wyboru urządzeń audio.
- Moduł `app/realtime/` jako fundament pod monitoring i przetwarzanie o niskiej latencji.
- Konfiguracje `configs/audio_devices.yaml` i `configs/realtime.yaml`.
- Narzędzie `tools/list_audio_devices.py` do sprawdzania urządzeń widocznych przez `sounddevice`/PortAudio.
- Narzędzie `tools/test_realtime_monitor.py` do ostrożnego testu streamu realtime.
- Dokumentację `docs/ASIO4ALL_REALTIME_PL.md`.
- Testy konfiguracji audio i realtime.

### Zmieniono
- `README.md` opisuje aktualny zakres: ręcznie ładowane audio, bez Cubase, z przygotowaniem pod ASIO4ALL.
- `requirements.txt` zawiera `sounddevice` jako zależność dla realtime I/O.
- `pyproject.toml` podniesiony do wersji 0.2.1.

### Decyzje projektowe
- Ciężkie modele AI nie są uruchamiane w callbacku audio. Callback ma być lekki, żeby unikać dropów i trzasków.
- Tryb realtime traktujemy jako monitoring/preview. Finalne czyszczenie, pitch correction i voice conversion pozostają domyślnie offline.

## v0.2.0 — full

- Pełny snapshot projektu.
- Dodane moduły `plugins`, `analysis`, `ai`, `mastering`, `export`, `search`.
- Dodane szkielety pod Audacity, Cubase, Melodyne, RX, Demucs, DeepFilterNet, RVC, Seed-VC, RMVPE.
- Dodane `VERSION`, `CHANGELOG.md`, `PACKAGING.md`.
