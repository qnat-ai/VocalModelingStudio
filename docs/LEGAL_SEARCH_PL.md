# Legalne wyszukiwanie audio, stemów i partii wokalnych

Ten moduł nie służy do automatycznego pobierania chronionych komercyjnych nagrań.
Jego zadanie to:

1. przeszukać lokalny katalog legalnych źródeł,
2. sprawdzić metadane utworu,
3. wskazać legalne katalogi/datasety,
4. przygotować wynik do dalszej obróbki w pipeline audio.

## Katalog lokalny

Własne lub legalnie pozyskane pliki umieszczaj w:

```text
data/legal_sources/
```

Przykładowo:

```text
data/legal_sources/remix_packs/Artist - Track/vocals.wav
data/legal_sources/datasets/musdb18/track_001/vocals.wav
data/legal_sources/my_recordings/moj_wokal.wav
```

## Uruchomienie

```bash
python search_sources.py --artist "Nazwa wykonawcy" --title "Tytuł"
```

Z metadanymi MusicBrainz:

```bash
python search_sources.py --artist "Nazwa wykonawcy" --title "Tytuł" --online-metadata
```

## Tryby pracy

### 1. Local Mode

Najbezpieczniejszy tryb: program używa plików, które sam dodałeś do katalogu `data/legal_sources/`.

### 2. Metadata Mode

Program szuka informacji o utworze, np. w MusicBrainz. To pomaga ustalić tytuł, wykonawcę, album lub ISRC, ale nie oznacza, że plik audio jest dostępny do pobrania.

### 3. Source Catalog Mode

Program pokazuje miejsca, w których można szukać legalnych materiałów:

- MUSDB18 / MUSDB18-HQ,
- MedleyDB,
- ccMixter,
- Freesound,
- Internet Archive,
- Jamendo.

## Znane utwory komercyjne

Dla znanych utworów najczęściej nie ma legalnie dostępnych stemów lub czystych wokali.
Bezpieczny workflow:

```text
legalnie posiadany plik audio
↓
Demucs / UVR / RX / Audacity
↓
vocal.wav
↓
Melodyne / korekcja pitch
↓
voice conversion / mastering
```

## Licencje

Moduł `license_checker.py` jest konserwatywny. Jeżeli licencja jest nieznana, program nie powinien automatycznie pobierać pliku.

Statusy:

- `safe` — np. CC0, CC-BY, Public Domain;
- `restricted` — np. All Rights Reserved, Non-Commercial;
- `unknown` — brak pewnej informacji.
