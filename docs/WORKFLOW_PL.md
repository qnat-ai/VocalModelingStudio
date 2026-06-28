# Workflow praktyczny

## Wariant 1: Python → Audacity → Python

1. Umieść plik w `data/input/`.
2. Uruchom:

```bash
python main.py --input data/input/moj_wokal.wav --audacity-export
```

3. Otwórz plik z `data/work/audacity_in/` w Audacity.
4. Wykonaj czyszczenie, normalizację, kompresję lub makro.
5. Eksportuj wynik do `data/work/audacity_out/`.
6. Użyj wyeksportowanego pliku jako nowego wejścia.

## Wariant 2: Python → RX/Melodyne → Python

1. Python przygotowuje technicznie poprawny WAV.
2. RX: czyszczenie i naprawa nagrania.
3. Melodyne: ręczna korekcja nut.
4. Python: voice conversion / dalsze przetwarzanie.

## Wariant 3: docelowy AI Vocal Studio

Docelowo moduły można rozszerzyć o:

- DeepFilterNet: odszumianie,
- RMVPE: wykrywanie F0,
- Rubber Band / pyworld: korekcja wysokości,
- Seed-VC / RVC: zmiana barwy głosu,
- pedalboard: EQ, compressor, de-esser, limiter.
