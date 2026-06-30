# Standaryzacja wokalu względem instrumentalu

## Cel modułu

VocalModelingStudio jest lokalnym standaryzatorem wokalu względem instrumentalu.
Program ma automatyzować powtarzalne czynności przy produkcji muzyki i zwracać
przetworzoną ścieżkę wokalną gotową do dalszej pracy w dowolnym DAW.

## Najważniejsza zasada

```text
instrumental = referencja
vocal_processed.wav = główny wynik VMS
preview_mix.wav = tylko odsłuch kontrolny
```

VMS nie modyfikuje instrumentalu destrukcyjnie. Instrumental służy do porównania,
dopasowania poziomu wokalu i wygenerowania kontrolnego podglądu miksu.

## Workflow

```text
ścieżka wokalna
+ opcjonalnie instrumental jako referencja
↓
porównanie poziomów i podstawowych parametrów
↓
propozycja korekty wokalu
↓
ACCEPT / CORRECT / TRY AGAIN
↓
vocal_processed.wav
+ preview_mix.wav tylko do kontroli
+ raport JSON/TXT
```

## Tryby decyzji

- `ACCEPT` — zastosuj automatyczną propozycję VMS.
- `CORRECT` — zastosuj ręcznie wpisany gain wokalu.
- `TRY AGAIN` — zastosuj ostrożniejszą alternatywną korektę.

## Co jest analizowane w pierwszym etapie

- peak,
- RMS,
- headroom,
- clipping,
- crest factor / dynamika,
- proste proporcje pasm: niskie pasmo, obecność 1–4 kHz, sybilanty 5–9 kHz,
- możliwe maskowanie wokalu przez instrumental w paśmie obecności.

To nie jest jeszcze pełny mastering ani pełna analiza psychoakustyczna. Moduł ma
być praktycznym narzędziem automatyzującym powtarzalne decyzje produkcyjne.

## Czego moduł nie robi

- nie tworzy finalnego miksu całego utworu,
- nie publikuje plików na platformy muzyczne,
- nie zastępuje DAW,
- nie modyfikuje instrumentalu jako pliku wynikowego,
- nie zastępuje Applio w obszarze voice conversion.

## Relacja z Applio

Applio pozostaje osobnym backendem dla:

- Voice Changer,
- Voice Conversion,
- Voice Blender.

VMS może przygotować wokal przed Applio i sprawdzić/dopasować wynik po Applio,
ale nie powinien implementować własnego RVC, treningu modeli ani voice blendera.
