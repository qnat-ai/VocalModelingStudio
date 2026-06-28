from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.plugins.demucs.plugin import DemucsPlugin


def test_demucs_plugin_separate_vocals_success(tmp_path, monkeypatch):
    input_path = tmp_path / "input.wav"
    input_path.write_bytes(b"dummy")
    output_dir = tmp_path / "demucs"

    monkeypatch.setattr("shutil.which", lambda _: "demucs")

    def fake_run(command, capture_output, text):
        out_index = command.index("-o") + 1
        demucs_out = Path(command[out_index])
        vocals = demucs_out / "htdemucs" / input_path.stem / "vocals.wav"
        vocals.parent.mkdir(parents=True, exist_ok=True)
        vocals.write_bytes(b"stem")
        return SimpleNamespace(returncode=0, stderr="", stdout="ok")

    monkeypatch.setattr("subprocess.run", fake_run)

    stem = DemucsPlugin().separate_vocals(input_path, output_dir)

    assert stem.name == "vocals.wav"
    assert stem.exists()

