"""Your own section keys: validated, saved, applied to bindings, footer, buttons and the reference."""
import json
import os
import subprocess
import sys

import pytest

from bitloom import keys


@pytest.fixture
def restore():
    saved = {section: list(rows) for section, rows in keys.SECTION_KEYS.items()}
    yield
    keys.SECTION_KEYS.clear()
    keys.SECTION_KEYS.update(saved)


def test_overrides_are_checked_and_applied(restore):
    errors = keys.apply_overrides({"builds": {"Stop": "S", "Retry": "e", "Errors": "j"}, "nowhere": {"x": "y"}, "analysis": {"Nope": "z", "Analyze": "ctrl+a"}})
    table = {(s, label): key for s, label, key, _ in keys.effective_table()}
    assert table[("builds", "Stop")] == "S" and table[("analysis", "Analyze")] == "ctrl+a"
    assert table[("builds", "Retry")] == "r" and table[("builds", "Errors")] == "e"       # refused: keep defaults
    assert any("Retry → e" in e and "already does “Errors”" in e for e in errors)
    assert any("Errors → j" in e and "reserved" in e for e in errors)
    assert any("unknown section “nowhere”" in e for e in errors) and any("no action “Nope”" in e for e in errors)
    assert "| `S` | Stop |" in keys.reference_markdown()
    assert keys.button_hints()["stop"] == "S"


def test_key_names():
    assert keys.check_key("builds", "Stop", "F") == "" and keys.check_key("builds", "Stop", "f11") == ""
    assert "use a letter" in keys.check_key("builds", "Stop", "ctrl+shift+s")
    assert "reserved" in keys.check_key("builds", "Stop", "5")


def test_save_and_reset(tmp_path, monkeypatch, restore):
    path = tmp_path / "keys.json"
    monkeypatch.setenv("BITLOOM_KEYS", str(path))
    keys.save_override("builds", "Stop", "S")
    keys.save_override("caches", "Scan", "z")
    assert json.loads(path.read_text()) == {"builds": {"Stop": "S"}, "caches": {"Scan": "z"}}
    keys.save_override("builds", "Stop", None)
    assert json.loads(path.read_text()) == {"caches": {"Scan": "z"}}
    out = subprocess.run([sys.executable, "-m", "bitloom", "--keys"], capture_output=True, text=True, env={**os.environ, "BITLOOM_KEYS": str(path)})
    assert out.returncode == 0 and "z        (default s)" in out.stdout
    path.write_text('{"builds": {"Stop": "1"}}')
    bad = subprocess.run([sys.executable, "-m", "bitloom", "--keys"], capture_output=True, text=True, env={**os.environ, "BITLOOM_KEYS": str(path)})
    assert bad.returncode == 1 and "reserved" in bad.stdout
