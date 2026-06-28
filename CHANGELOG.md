# CHANGELOG

ś## v0.1.0 — 2026-06-28

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
