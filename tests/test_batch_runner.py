from __future__ import annotations

from pathlib import Path

import pytest

from app.cli.batch_runner import collect_input_files, run_batch


class _FakePipeline:
    def __init__(self, fail_on: str | None = None) -> None:
        self.fail_on = fail_on

    def run(self, *, input_path, reference_path, export_for_audacity, output_path):
        _ = reference_path, export_for_audacity, output_path
        if self.fail_on and input_path.name == self.fail_on:
            raise RuntimeError("boom")
        return input_path.with_suffix(".processed.wav")


def test_collect_input_files_filters_and_sorts(tmp_path: Path):
    (tmp_path / "b.mp3").write_bytes(b"x")
    (tmp_path / "a.wav").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")

    files = collect_input_files(tmp_path, recursive=False, pattern="*")

    assert [path.name for path in files] == ["a.wav", "b.mp3"]


def test_run_batch_continue_on_error(tmp_path: Path):
    files = [tmp_path / "ok.wav", tmp_path / "bad.wav"]
    for path in files:
        path.write_bytes(b"x")

    results = run_batch(_FakePipeline(fail_on="bad.wav"), files, continue_on_error=True)

    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is False


def test_run_batch_raises_without_continue(tmp_path: Path):
    files = [tmp_path / "bad.wav"]
    files[0].write_bytes(b"x")

    with pytest.raises(RuntimeError):
        run_batch(_FakePipeline(fail_on="bad.wav"), files, continue_on_error=False)

