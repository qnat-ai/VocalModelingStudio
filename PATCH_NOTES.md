# PATCH NOTES — VocalModelingStudio 0.1.4 — vocal standardizer for instrumental

## Typ paczki

Patch zbiorczy. Zawiera kompletne nowe/zmienione pliki, nie diffy.
Numer wersji projektu pozostaje bez zmian: `0.1.4`.

## Cel patcha

Ustawienie VMS jako: **standaryzator wokalu względem instrumentalu**.

Najważniejsza zasada:

```text
instrumental = referencja
vocal_processed.wav = główny wynik VMS
preview_mix.wav = tylko odsłuch kontrolny
```

## Pliki w patchu

```text
app/standardization/__init__.py
app/standardization/vocal_standardizer.py
app/gui/gradio/__init__.py
app/gui/gradio/interface.py
app/gui/gradio/legal_search_panel.py
app/search/models.py
docs/VOCAL_STANDARDIZER_PL.md
tests/test_vocal_standardizer.py
tests/test_legal_search_query.py
PATCH_NOTES.md
```

## Zmiany funkcjonalne

- dodano moduł `app/standardization/`,
- dodano workflow: ścieżka wokalna + opcjonalny instrumental jako referencja,
- główny wynik to `vocal_processed.wav`,
- `preview_mix.wav` służy tylko do kontroli odsłuchowej,
- instrumental nie jest zapisywany jako zmodyfikowany wynik,
- dodano tryby decyzji: `ACCEPT`, `CORRECT`, `TRY AGAIN`,
- GUI przebudowane wokół zakładki `Standaryzacja wokalu`,
- `Diagnostyka` przemianowana na `Narzędzia / Ustawienia`,
- Applio pozostaje osobnym backendem `Voice Changer`,
- Legal Search rozszerzony językowo o gatunek i wskazówkę licencji.

## Jak zastosować

Rozpakuj ZIP w głównym katalogu projektu `VocalModelingStudio`, nadpisując istniejące pliki.

## Testy patcha

Po zastosowaniu patcha uruchom:

```bash
pytest tests/test_vocal_standardizer.py tests/test_legal_search_query.py
```
