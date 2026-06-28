# ASIO4ALL i realtime audio w VocalModelingStudio

## Cel

Na tym etapie projekt nie próbuje zastąpić DAW. Celem jest:

- ręcznie załadować ścieżkę audio,
- testować lokalne przetwarzanie i monitoring,
- przygotować pipeline pod niższą latencję,
- uniknąć ciągłego przechodzenia między narzędziami,
- nie integrować Cubase w obecnej fazie.

## Co może zrobić Python

Python + `sounddevice` może:

- wyświetlić urządzenia audio widoczne dla PortAudio,
- wybrać urządzenie wejściowe/wyjściowe,
- ustawić `samplerate`, `blocksize`, `channels`, `latency`,
- uruchomić stream input → output,
- wykrywać część błędów typu overflow/underflow.

## Czego Python zwykle nie zrobi za ASIO4ALL

Python zwykle nie ustawi za Ciebie całego panelu ASIO4ALL. W panelu ASIO4ALL nadal ustawiasz:

- aktywne urządzenia WDM,
- ASIO Buffer Size,
- ewentualne kompensacje latencji,
- tryb zaawansowany,
- zachowanie resamplingu 44.1/48 kHz.

## Ważne ograniczenie `sounddevice` na Windows

Standardowa instalacja `sounddevice` z `pip` może zawierać PortAudio DLL bez obsługi ASIO. Jeżeli `python tools/list_audio_devices.py` nie pokazuje host API typu ASIO/ASIO4ALL, to problemem może być właśnie brak ASIO w bibliotece PortAudio używanej przez `sounddevice`.

W takim przypadku są 3 praktyczne ścieżki:

1. użyć WASAPI jako fallback,
2. podmienić bibliotekę PortAudio na build z ASIO,
3. używać ASIO w DAW, a w Pythonie testować tylko WASAPI/DirectSound.

## Zalecany start na laptopie

Zacznij od profilu:

```bash
python tools/test_realtime_monitor.py --dry-run --profile balanced
```

Potem krótki test:

```bash
python tools/test_realtime_monitor.py --seconds 5 --profile balanced
```

Po każdym uruchomieniu narzędzie zapisuje raport do `logs/audio_diagnostics.txt`.
Jeżeli chcesz inną ścieżkę, użyj np. `--save-report logs/moj_test.txt`.

Jeżeli są trzaski/dropy:

```bash
python tools/test_realtime_monitor.py --seconds 5 --profile safe
```

Jeżeli działa stabilnie, możesz próbować:

```bash
python tools/test_realtime_monitor.py --seconds 5 --profile low
```

## Profile

```text
safe                   48 kHz, blocksize 1024
balanced               48 kHz, blocksize 512
low                    48 kHz, blocksize 256
realtime_experimental  48 kHz, blocksize 128
```

## Zasada bezpieczeństwa dla AI

Nie wkładaj ciężkich modeli AI bezpośrednio do callbacku audio:

```text
źle:
callback audio → RVC / Seed-VC / DeepFilterNet / RMVPE
```

Lepszy schemat:

```text
callback audio → lekki bufor / monitoring
osobny worker → AI preview lub offline processing
```

Finalna jakość powinna być renderowana offline. Realtime na tym etapie służy głównie do monitoringu, testu latencji i szybkiego preview.

## Co dalej

Następne sensowne kroki:

1. dodać `offline_vocal_editing_workflow.yaml`,
2. dodać `preview_queue` dla quasi-realtime,
3. dodać prosty noise gate / gain / limiter w callbacku,
4. dodać pomiar dropów i zapis raportu do `logs/audio_diagnostics.txt`.
