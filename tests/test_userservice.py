"""The build service and the dashboard as systemd user services, with a dashboard URL that survives restarts."""
import os
import stat
import sys

import pytest

from bitloom import userservice
from bitloom.web import persistent_token


def test_units(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/mnt/c/WINDOWS/system32:/home/u/.vscode-server/bin/x:/bin")
    files = userservice.units(tmp_path / "my state", tmp_path / "profiles.json", "bitloom", web=True, host="0.0.0.0", port=9000)
    service, web = files["bitloom.service"], files["bitloom-web.service"]
    assert f'-m bitloom.daemon "{tmp_path / "my state"}"' in service and "Restart=on-failure" in service and "WantedBy=default.target" in service
    path_line = next(line for line in service.splitlines() if line.startswith("Environment="))
    assert str(os.path.dirname(sys.executable)) in path_line and "WINDOWS" not in path_line and ".vscode-server" not in path_line and "/usr/bin" in path_line
    assert "Requires=bitloom.service" in web and "--web --no-browser --persistent-token --host 0.0.0.0 --port 9000" in web
    assert list(userservice.units(tmp_path, tmp_path / "p.json", "ci-box")) == ["ci-box.service"]
    with pytest.raises(ValueError, match="Service name"):
        userservice.units(tmp_path, tmp_path, "Bad Name")


def test_persistent_token(tmp_path):
    first = persistent_token(tmp_path / "state")
    assert len(first) >= 24 and persistent_token(tmp_path / "state") == first
    assert stat.S_IMODE((tmp_path / "state/web.token").stat().st_mode) == 0o600


def test_uninstall_when_nothing_is_installed(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert userservice.uninstall("bitloom") == ["no bitloom service installed"]
