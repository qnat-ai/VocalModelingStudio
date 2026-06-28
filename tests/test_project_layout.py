from pathlib import Path


def test_core_layout_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "app" / "plugins").exists()
    assert (root / "docs" / "ARCHITECTURE_PL.md").exists()
    assert (root / "VERSION").exists()
