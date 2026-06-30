# Vocal Modeling Studio — 0.1.4

> Pipeline lokalny, monitoring realtime, ASIO4ALL, sounddevice, batch processing, GUI Gradio, integracja Applio.

Projekt Python/PyCharm do lokalnej edycji wokalu: import ścieżki audio, analiza, cleanup, korekcja wysokości i eksport wyników.

Ta wersja skupia się na **pipeline lokalnym bez zewnętrznego DAW (np. Cubase)** i dodaje fundament pod **niską latencję / ASIO4ALL / sounddevice**.

## Zakres

Na tym etapie zakładamy:

- ręczne ładowanie pliku WAV/MP3/FLAC,
- lokalną edycję i mastering ścieżki,
- opcjonalne użycie zewnętrznego edytora (Audacity, Melodyne) jako narzędzia pomocniczego,
- brak bezpośredniej integracji z DAW (np. Cubase) — programy te działają niezależnie,
- brak automatyzacji portali typu Suno/MakeBestMusic,
- przygotowanie do monitoringu realtime przez `sounddevice`,
- optymalizację pod sprzęt przez profile latencji i wybór sterownika/urządzenia audio.

## Start

1. Otwórz folder projektu w PyCharm.
2. Skonfiguruj interpreter Python 3.11.
3. Zainstaluj zależności:

    ```bash
    pip install -r requirements.txt
    ```

4. Uruchom interfejs graficzny (zalecane):

    ```bash
    .\run-gui.bat
    ```

    Lub przez CLI:

    ```bash
    python main.py --gui
    ```

5. Uruchom klasyczny tryb CLI (offline):

    ```bash
    python main.py --input data/input/moj_wokal.wav
    ```

6. Szybki dependency check (zalecane po aktualizacji):

    ```bash
    python main.py --check-deps
    ```

   Batch processing (folder wejściowy):

    ```bash
    python main.py --input-dir data/input --pattern "*.wav" --recursive --continue-on-error
     python main.py --input-dir data/input --pattern "*.mp3" --batch-limit 20 --batch-summary-json data/work/batch_summary.json
     ```

## Audio devices / ASIO4ALL

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

## Realtime

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

Ważne: DeepFilterNet, RMVPE, RVC, Seed-VC i pitch correction lepiej uruchamiać offline albo w osobnym wątku/buforze.

## ASIO4ALL

Program może:

- wykryć host API i urządzenia widoczne przez PortAudio,
- wybrać preferowane urządzenie po nazwie, np. `ASIO4ALL`,
- ustawić `samplerate`, `blocksize`, `latency`, `channels`,
- wykonać test streamu.

Program nie zastępuje panelu ASIO4ALL. Ustawienie bufora sterownika, włączenie urządzeń WDM i diagnostyka trzasków zwykle odbywa się w panelu ASIO4ALL.

## Struktura

```text
app/audio_devices/       # wykrywanie urządzeń, profile latencji, ustawienia
app/realtime/            # engine monitoringu i diagnostyka realtime
app/mastering/           # modularne etapy masteringu (stages, meters, presets)
app/standardization/     # standaryzacja wokalu względem instrumentalu
app/gui/gradio/          # interfejs użytkownika Gradio
app/engines/applio/      # integracja z silnikiem konwersji Applio (Klient API)
app/core/session.py      # per-run session folder management
app/cli/batch_runner.py  # batch processing helpers
app/utils/logging.py     # centralny logger
configs/audio_devices.yaml
configs/realtime.yaml
configs/default.yaml
run-gui.bat              # szybki start GUI
run-applio.bat           # pomocniczy skrypt startowy dla serwera Applio
tools/list_audio_devices.py
tools/test_realtime_monitor.py
tools/external_fx_chain.py
docs/ASIO4ALL_REALTIME_PL.md
docs/VOCAL_STANDARDIZER_PL.md
     ```

## Standaryzacja wokalu

VMS v0.1.4 wprowadza tryb standaryzacji wokalu względem podkładu instrumentalnego.

1. Wgraj ścieżkę wokalną i opcjonalnie instrumental (jako referencję).
2. Wybierz **PORÓWNAJ / ZAPROPONUJ** — VMS przeanalizuje poziomy i zasugeruje optymalny gain.
3. Wybierz akcję:
   - **ACCEPT**: zastosuj propozycję i wygeneruj `vocal_processed.wav`.
   - **CORRECT**: wprowadź ręczną korektę i wygeneruj wynik.
   - **TRY AGAIN**: zresetuj i spróbuj innej analizy.

Głównym wynikiem jest dopasowana ścieżka wokalna. `preview_mix.wav` służy tylko do odsłuchu.
Dokumentacja: `docs/VOCAL_STANDARDIZER_PL.md`.

## Applio / Voice Conversion

Projekt wykorzystuje zewnętrzny silnik **Applio** do konwersji głosu.

1. Upewnij się, że Applio jest zainstalowane i działa (domyślnie na http://127.0.0.1:6969).
2. Sprawdź dostępne punkty końcowe API za pomocą narzędzia:
   ```bash
   python app/engines/applio/probe.py --url http://127.0.0.1:6969
   ```
3. Skonfiguruj `api_name` oraz `param_map` w `configs/default.yaml` zgodnie z wynikiem powyższego narzędzia.

## Host i backend

- Wybrany host do pipeline-u zewnętrznego: **REAPER** (najlepszy kompromis automatyzacja/jakość/stabilność).
- Backend FX w VMS: **FFmpeg** przez `ExternalFxBridge` (`ffmpeg_vocal_polish` w `configs/default.yaml`).
- Integracje z `iZotope RX`, `Acon`, `Waves`, `Melodyne` są odłożone na później.

## Testy

```bash
pytest
```

## Moduły

W projekcie są już aktywne rozszerzenia pod produkcyjny pipeline:

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
```

