# VocalModelingStudio v0.2.1 — patch 001

Typ paczki: **PATCH**.

Ta paczka zawiera wyłącznie pliki nowe lub zmienione względem:

```text
VocalModelingStudio_v0.2.0_full.zip
```

Każdy plik w tej paczce jest **kompletnym plikiem**, gotowym do skopiowania/zastąpienia w projekcie. To nie są pliki typu `diff`.

## Jak zastosować patch

1. Rozpakuj `VocalModelingStudio_v0.2.0_full.zip` jako bazę projektu.
2. Rozpakuj ten patch.
3. Skopiuj zawartość katalogu `VocalModelingStudio_v0.2.1_patch_001/` do katalogu projektu, zachowując strukturę folderów.
4. Pozwól na zastąpienie plików `README.md`, `CHANGELOG.md`, `requirements.txt`, `pyproject.toml`, `VERSION`.

## Dodane / zmienione pliki

```text
VERSION
CHANGELOG.md
PATCH_NOTES.md
README.md
requirements.txt
pyproject.toml
configs/audio_devices.yaml
configs/realtime.yaml
app/audio_devices/__init__.py
app/audio_devices/device_manager.py
app/audio_devices/latency_profiles.py
app/audio_devices/settings.py
app/realtime/__init__.py
app/realtime/config.py
app/realtime/diagnostics.py
app/realtime/low_latency_stream.py
docs/ASIO4ALL_REALTIME_PL.md
tools/list_audio_devices.py
tools/test_realtime_monitor.py
tests/test_audio_device_settings.py
tests/test_realtime_config.py
```

## Zakres funkcjonalny

- ręczne ładowanie ścieżki audio pozostaje głównym trybem pracy,
- brak integracji z Cubase w tej iteracji,
- dodana warstwa przygotowawcza pod niską latencję i ASIO4ALL,
- dodane narzędzia do listowania urządzeń audio,
- dodany lekki engine monitoringu realtime przez `sounddevice`,
- dodane profile latencji: `safe`, `balanced`, `low`, `realtime_experimental`.

## Uwaga

ASIO4ALL nie jest konfigurowany w pełni „z Pythona”. Program może wybrać urządzenie/host API i ustawić parametry streamu, ale panel ASIO4ALL oraz bufor ASIO zwykle ustawia się w panelu sterownika.
