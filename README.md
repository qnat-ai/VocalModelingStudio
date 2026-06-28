# Vocal Modeling Studio — v0.2.1 patch 001

Projekt Python/PyCharm do lokalnej edycji partii wokalnych: import ręcznie wskazanej ścieżki audio, analiza, czyszczenie, korekcja wysokości dźwięków, przygotowanie pod voice conversion oraz eksport wyników.

Ta wersja skupia się na **lokalnym workflow bez Cubase** i dodaje fundament pod **niską latencję / ASIO4ALL / sounddevice**.

## Aktualny zakres projektu

Na tym etapie zakładamy:

- ręczne ładowanie pliku WAV/MP3/FLAC,
- lokalną edycję i mastering ścieżki,
- opcjonalne użycie Audacity jako zewnętrznego edytora pomocniczego,
- brak integracji z Cubase,
- brak automatyzacji portali typu Suno/MakeBestMusic,
- przygotowanie do monitoringu realtime przez `sounddevice`,
- optymalizację pod sprzęt przez profile latencji i wybór sterownika/urządzenia audio.

## Szybki start w PyCharm

1. Otwórz folder projektu w PyCharm.
2. Utwórz virtualenv, najlepiej Python 3.11 albo 3.12.
3. Zainstaluj zależności:

```bash
pip install -r requirements.txt
```

4. Włóż plik audio do:

```text
data/input/
```

5. Uruchom pipeline offline:

```bash
python main.py --input data/input/moj_wokal.wav
```

Batch processing (folder wejściowy):

```bash
python main.py --input-dir data/input --pattern "*.wav" --recursive --continue-on-error
python main.py --input-dir data/input --pattern "*.mp3" --batch-limit 20 --batch-summary-json data/work/batch_summary.json
```

## Tryb audio devices / ASIO4ALL

Lista urządzeń audio widocznych przez `sounddevice`:

```bash
python tools/list_audio_devices.py
```

Lista jako JSON:

```bash
python tools/list_audio_devices.py --json
```

Test konfiguracji bez uruchamiania streamu:

```bash
python tools/test_realtime_monitor.py --dry-run
```

Krótki test monitoringu realtime:

```bash
python tools/test_realtime_monitor.py --seconds 5 --profile balanced
```

Raport diagnostyczny jest domyślnie zapisywany do:

```text
logs/audio_diagnostics.txt
```

Dokumentacja:

```text
docs/ASIO4ALL_REALTIME_PL.md
```

## Główna idea realtime

```text
mikrofon / wejście audio
    ↓
sounddevice / PortAudio / ASIO lub WASAPI
    ↓
lekki callback audio
    ↓
monitoring / preview
    ↓
tryb offline dla ciężkich modeli AI
```

Ważne: DeepFilterNet, RMVPE, RVC, Seed-VC i pitch correction nie powinny być na początku wykonywane bezpośrednio w callbacku realtime. Bezpieczniej jest przetwarzać finalnie offline albo w osobnym wątku/buforze.

## ASIO4ALL — założenie

Program może:

- wykryć host API i urządzenia widoczne przez PortAudio,
- wybrać preferowane urządzenie po nazwie, np. `ASIO4ALL`,
- ustawić `samplerate`, `blocksize`, `latency`, `channels`,
- wykonać test streamu.

Program nie zastępuje panelu ASIO4ALL. Ustawienie bufora sterownika, włączenie urządzeń WDM i diagnostyka trzasków zwykle odbywa się w panelu ASIO4ALL.

## Struktura dodana w v0.2.1

```text
app/audio_devices/       # wykrywanie urządzeń, profile latencji, ustawienia
app/realtime/            # engine monitoringu i diagnostyka realtime
configs/audio_devices.yaml
configs/realtime.yaml
tools/list_audio_devices.py
tools/test_realtime_monitor.py
docs/ASIO4ALL_REALTIME_PL.md
```

## Testy

```bash
pytest
```

## Nowe moduły automatyzacji (v0.2.1+)

W projekcie są już aktywne rozszerzenia pod produkcyjny workflow:

- separacja wokalu przez `DemucsPlugin` (CLI),
- detekcja tonacji (`app/analysis/key_detector.py`),
- adaptacyjny mastering z opcjami `air_amount` i `stereo_width`,
- guardrails jakości + fail-safe neutral preset,
- mostek external FX (`app/integration/vst_bridge.py`) pod narzędzia CLI,
- opcjonalny backend `rvc_cli` w `VoiceConversionEngine`,
- API search dla Freesound i Archive.org.

Minimalna konfiguracja (fragment `configs/default.yaml`):

```yaml
processing:
  split_vocals_enabled: false
  key_detection_enabled: true
  voice_conversion_enabled: false
  voice_conversion:
    backend: rvc_cli
    rvc_binary: rvc
    device: cuda

mastering:
  air_amount: 0.0
  stereo_width: 1.0

integration:
  external_fx:
    enabled: false
    command_template: []

quality_guardrails:
  fail_safe_enabled: true
```

## Status funkcji

| Funkcja | Status |
|---|---|
| Import WAV/MP3 | działa |
| Quality report (`before/after/delta/guardrails`) | działa |
| Mastering basic + adaptive + fail-safe | działa |
| Audacity export | działa |
| Realtime diagnostics / monitoring | działa częściowo |
| Pitch correction audio rewrite | placeholder (na razie raport F0 + nuty) |
| Voice conversion (`rvc_cli`) | placeholder / opcjonalny backend |
| DeepFilterNet | placeholder |
| RVC/Seed-VC pełna integracja modeli | placeholder |
| GUI (`app/gui/gradio_app.py`) | placeholder |

## Session folder per run

Każde uruchomienie pipeline tworzy osobną sesję:

```text
data/projects/<timestamp>_<input_name>/
  input/
  work/
  output/
  reports/
  metadata/
  session.yaml
```

To porządkuje wiele wersji wokalu i rozdziela raporty między runami.

## Search CLI (Freesound + Archive.org)

Nowe flagi w `search_sources.py` wspierają API search i opcjonalne pobranie tylko bezpiecznych licencji:

```bash
python search_sources.py --title "vocal one shot" --freesound --freesound-api-key YOUR_TOKEN --limit 5
python search_sources.py --title "public domain vocals" --archive --download-legal
```

Tryb `--download-legal` pobiera wyłącznie wyniki sklasyfikowane jako `safe`.

## Paczkowanie

Ta paczka jest patchem: zawiera kompletne zmienione/dodane pliki, ale nie pełny projekt. Bazą jest:

```text
VocalModelingStudio_v0.2.0_full.zip
```

Szczegóły: `PATCH_NOTES.md`.
