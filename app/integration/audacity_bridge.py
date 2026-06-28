from __future__ import annotations

from pathlib import Path
import shutil


class AudacityBridge:
    """Integracja plikowa z Audacity.

    Najprostszy i stabilny workflow:
    - Python eksportuje WAV do katalogu audacity_in,
    - użytkownik otwiera go w Audacity,
    - wykonuje makro lub ręczną obróbkę,
    - eksportuje wynik do audacity_out,
    - pipeline może kontynuować pracę na pliku po Audacity.
    """

    def __init__(self, in_dir: Path, out_dir: Path) -> None:
        self.in_dir = in_dir
        self.out_dir = out_dir
        self.in_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def export_for_audacity(self, wav_path: Path) -> Path:
        target = self.in_dir / wav_path.name
        shutil.copy2(wav_path, target)
        return target

    def expected_output_path(self, wav_path: Path) -> Path:
        return self.out_dir / wav_path.name
