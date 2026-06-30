# CHANGELOG

## [0.1.4] — 2026-06-30

### Dodano
- Nowy moduł `app/standardization/`: standaryzacja wokalu względem instrumentalu (vocal standardizer for instrumental).
- Workflow standaryzacji: analiza (`analyze`) i generowanie wyniku (`render`) z trybami `ACCEPT`, `CORRECT`, `TRY AGAIN`.
- Nowy panel w GUI: zakładka "Standaryzacja wokalu" jako główny punkt wejścia.
- Rozszerzenie "Legal Search": nowe pola wyszukiwania (gatunek, licencja) oraz integracja z GUI (`app/gui/gradio/legal_search_panel.py`).
- Dokumentacja techniczna modułu standaryzacji: `docs/VOCAL_STANDARDIZER_PL.md`.
- Mechanizm dwukierunkowej synchronizacji zamknięcia: zamknięcie wszystkich kart przeglądarki automatycznie kończy proces serwera (heartbeat mechanism).
- Ostrzeżenie przed przypadkowym zamknięciem karty przeglądarki (JavaScript `onbeforeunload`) w interfejsie Gradio.

### Zmieniono
- Przebudowano interfejs Gradio w `app/gui/gradio/interface.py` wokół nowego workflow standaryzacji.
- "Diagnostyka" w GUI przemianowana na "Narzędzia / Ustawienia".
- Rozszerzono modele wyszukiwania w `app/search/models.py` o pola `genre` i `license_hint`.
- Zaktualizowano `README.md`: uogólniono workflow (zmiana "bez Cubase" na "bez zewnętrznego DAW"), dodano Melodyne jako przykład wspieranego edytora zewnętrznego.
- Doprecyzowano status integracji z DAW i profesjonalnymi narzędziami edytorskimi.
- Dodano wzmiankę o Melodyne w komentarzach technicznych `app/audio/pitch.py`.
- Poprawiono spójność informacji o roli ASIO w projekcie (fundament pod niską latencję).

## [0.1.3] — 2026-06-29

### Zmieniono
- Zreorganizowano strukturę katalogów: interfejs Gradio przeniesiony do `app/gui/gradio/`, silnik Applio do `app/engines/applio/`.
- Wydzielono logikę Applio do osobnego modułu `app/engines/applio/engine.py`.
- Narzędzie diagnostyczne Applio przeniesione z `tools/applio_probe.py` do `app/engines/applio/probe.py`.

## [0.1.2] — 2026-06-29

### Dodano
- Interfejs graficzny (GUI) oparty na Gradio, dostępny przez flagę `--gui` w `main.py`.
- Skrypt `run-gui.bat` do łatwego uruchamiania interfejsu w systemie Windows.
- Zależność `gradio` w `requirements.txt`.

### Zmieniono
- `main.py` obsługuje teraz tryb GUI oraz ulepszoną walidację argumentów CLI.

## [0.1.1] — 2026-06-29

### Dodano
- Integracja z silnikiem Applio przez API Gradio (`applio_gradio` backend w `VoiceConversionEngine`).
- Narzędzie diagnostyczne `tools/applio_probe.py` do testowania połączenia z serwerem Applio.
- Przykładowy skrypt `run-applio.bat` ułatwiający uruchamianie zewnętrznego serwera Applio.
- Nowa zależność `gradio_client` w `requirements.txt`.

### Zmieniono
- `VoiceConversionEngine` obsługuje teraz dynamiczne przełączanie backendów (rvc_cli, applio_gradio) oraz elastyczne mapowanie parametrów API Applio.
- Ulepszone narzędzie `tools/applio_probe.py` z pełnym raportowaniem specyfikacji API Gradio.

### Decyzje projektowe
- Wybór Applio jako rekomendowanej ścieżki rozwoju zamiast archiwalnego fairseq/RVC.
- Komunikacja z Applio odbywa się przez HTTP/Gradio API, co pozwala na separację środowisk i uniknięcie konfliktów zależności.

## v0.1.0 — 2026-06-28

### Dodano
- Batch processing CLI (`--input-dir`, `--recursive`, `--pattern`, `--batch-limit`, `--continue-on-error`, `--batch-summary-json`) w `main.py` i `app/cli/batch_runner.py`.
- Per-run session folder management (`app/core/session.py`) — każdy render trafia do `data/projects/<timestamp>_<name>/`.
- Centralny logger (`app/utils/logging.py`) — `logs/vms.log` i per-sesyjny `logs/render_*.log`.
- Standardowy format kształtu audio — mono `(samples,)`, stereo `(samples, channels)` — w `app/audio/format.py`.
- Lekki etap czyszczenia audio (`app/audio/cleanup.py`): DC offset removal, fade safety, noise gate, trim silence, gain staging.
- Modularne etapy masteringu (`app/mastering/stages.py`, `meters.py`, `presets.py`).
- Adaptacyjny mastering z profilowaniem per-run.
- Guardrails jakości z fail-safe neutral preset.
- Raporty `before/after/delta` i `guardrails` per-sesja.
- Detekcja tonacji (`app/analysis/key_detector.py`) na bazie chroma CQT.
- Raport pitch z mapowaniem F0 → nuta + odchylenie centowe.
- `DemucsPlugin` — aktywna separacja wokalu przez CLI.
- `ExternalFxBridge` z `strict` mode i biblioteką presetów (`preset_library`).
- Narzędzie `tools/external_fx_chain.py` z presetami `wrapper_cleanup` i `wrapper_broadcast_vocal`.
- API search dla Freesound i Archive.org w `search_sources.py` (`--freesound`, `--archive`, `--download-legal`).
- Walidacja konfiguracji YAML (`app/utils/config.py`).
- `.gitignore` — pełne wykluczenie artefaktów, audio, modeli i cache.
- Placeholder `.gitkeep` w `data/work`, `data/output`, `data/projects`.

### Zmieniono
- `VERSION` → `0.1.0`.
- `README.md` — ujednolicony tytuł, tabela statusu funkcji, opis session folderów i search CLI.
- `CHANGELOG.md` — przepisany pod nowy schemat wersjonowania.

### Decyzje projektowe
- Wersja startowa `0.1.0` — projekt jest teraz spójnym, publicznym repozytorium.
- Ciężkie modele AI (DeepFilterNet, RVC, Seed-VC) pozostają placeholderami z interfejsem gotowym do podpięcia.
- Pitch correction jest na razie nieinwazyjna — raport diagnostyczny, bez modyfikacji audio.
