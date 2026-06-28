from __future__ import annotations

from pathlib import Path


def describe_external_workflow(wav_path: Path) -> str:
    return f"""
Plik roboczy: {wav_path}

Sugerowany workflow:
1. Otwórz WAV w Audacity lub RX i usuń szumy/kliki/pogłos.
2. Eksportuj czysty WAV.
3. Załaduj WAV do Cubase.
4. Użyj Melodyne do ręcznej korekcji nut.
5. Wyeksportuj poprawiony wokal jako WAV.
6. Wróć do programu i użyj tego pliku jako wejścia do voice conversion.
""".strip()
