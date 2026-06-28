# Architektura Vocal Modeling Studio

Projekt jest dzielony na niezależne moduły:

1. `audio` — import, eksport, konwersja formatów.
2. `analysis` — F0, tonacja, jakość, formanty.
3. `ai` — korekcja nut i modelowanie barwy.
4. `plugins` — integracje z narzędziami zewnętrznymi.
5. `search` — legalne źródła audio, stemów i metadanych.
6. `mastering` — EQ, kompresja, limiter, de-esser.
7. `gui` — przyszły interfejs Gradio.

Zasada: najpierw pełny snapshot, potem paczki patch z samymi zmianami.
