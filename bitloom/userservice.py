"""The build service (and optionally the web dashboard) as systemd user services: running after a reboot or
a logout, without a terminal open — what a shared build server needs.

`bitloom --service-install [--web]` writes ~/.config/systemd/user/<name>.service (and <name>-web.service),
enables and starts them; `--service-uninstall` removes them. Nothing needs root. `loginctl enable-linger`
(asked once, by you) keeps them running when you are not logged in."""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

NAME = re.compile(r"[a-z][a-z0-9-]{0,40}")


def unit_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd/user"


def _quote(value: str) -> str:
    # systemd splits ExecStart like a shell: quote what has spaces or specials.
    return value if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", value) else '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def units(state: Path, config: Path, name: str = "bitloom", web: bool = False, host: str = "127.0.0.1", port: int = 8765) -> dict[str, str]:
    """The unit files: the build service, and the dashboard on top of it."""
    if not NAME.fullmatch(name):
        raise ValueError("Service name: lowercase letters, digits and hyphens")
    python = sys.executable
    # The login PATH, without what does not belong in a service: WSL's Windows folders (BitBake rejects some of
    # them) and editor helper paths that change at every update. Bitloom's own Python comes first.
    keep = [str(Path(python).parent)]
    for entry in os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin").split(os.pathsep):
        if entry and entry not in keep and not entry.startswith("/mnt/") and ".vscode-server" not in entry:
            keep.append(entry)
    common = [f"Environment={_quote('PATH=' + os.pathsep.join(keep))}", f"WorkingDirectory={_quote(str(Path.home()))}"]
    from . import module_command
    run = lambda module, *args: " ".join(_quote(part) for part in module_command(module, *args))
    service = "\n".join(["[Unit]", f"Description=Bitloom build service ({state})", "",
                         "[Service]", "Type=simple", f"ExecStart={run('bitloom.daemon', str(state))}",
                         *common, "Restart=on-failure", "RestartSec=5", "", "[Install]", "WantedBy=default.target", ""])
    result = {f"{name}.service": service}
    if web:
        result[f"{name}-web.service"] = "\n".join([
            "[Unit]", f"Description=Bitloom web dashboard on {host}:{port}", f"Requires={name}.service", f"After={name}.service", "",
            "[Service]", "Type=simple",
            f"ExecStart={run('bitloom', '--web', '--no-browser', '--persistent-token', '--host', host, '--port', str(port), '--config', str(config), '--state', str(state))}",
            *common, "Restart=on-failure", "RestartSec=5", "", "[Install]", "WantedBy=default.target", ""])
    return result


def systemctl(*args: str) -> subprocess.CompletedProcess:
    if not shutil.which("systemctl"):
        raise ValueError("systemctl not found: this system does not use systemd; start the service with bitloom or bitloom --web instead")
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, timeout=60)


def install(state: Path, config: Path, name: str = "bitloom", web: bool = False, host: str = "127.0.0.1", port: int = 8765) -> list[str]:
    """Write, enable and start the units; a service already started by the TUI is stopped first (when idle)."""
    from .daemon import rpc
    probe = systemctl("is-system-running")
    if probe.returncode not in (0, 1) or probe.stdout.strip() in ("offline", ""):
        raise ValueError("The systemd user manager is not running (systemctl --user): on WSL enable systemd in /etc/wsl.conf")
    messages = []
    try:
        status = rpc(state, {"op": "status"})
        if status.get("active") or any(j["status"] == "queued" for j in status.get("jobs", [])):
            raise ValueError("A build is running in the current service: let it finish (or stop it) before installing")
        rpc(state, {"op": "stop"})
        messages.append("stopped the build service started by Bitloom; systemd runs it from now on")
    except OSError:
        pass
    folder = unit_dir()
    folder.mkdir(parents=True, exist_ok=True)
    written = units(state, config, name, web, host, port)
    for unit, text in written.items():
        (folder / unit).write_text(text)
        messages.append(f"wrote {folder / unit}")
    for args in (("daemon-reload",), ("enable", "--now", *written)):
        result = systemctl(*args)
        if result.returncode:
            raise ValueError(f"systemctl --user {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}")
    messages.append("enabled and started " + ", ".join(written))
    if web:
        from .web import persistent_token
        messages.append(f"dashboard: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/#token={persistent_token(state)}")
    linger = subprocess.run(["loginctl", "show-user", os.environ.get("USER", ""), "-p", "Linger"], capture_output=True, text=True) if shutil.which("loginctl") else None
    if linger and "Linger=no" in linger.stdout:
        messages.append("to keep it running when you log out: loginctl enable-linger " + shlex.quote(os.environ.get("USER", "")))
    return messages


def uninstall(name: str = "bitloom") -> list[str]:
    folder = unit_dir()
    present = [u for u in (f"{name}-web.service", f"{name}.service") if (folder / u).exists()]
    if not present:
        return [f"no {name} service installed"]
    systemctl("disable", "--now", *present)
    for unit in present:
        (folder / unit).unlink()
    systemctl("daemon-reload")
    return [f"stopped, disabled and removed {', '.join(present)}"]


def status(name: str = "bitloom") -> list[str]:
    rows = []
    for unit in (f"{name}.service", f"{name}-web.service"):
        if (unit_dir() / unit).exists():
            active = systemctl("is-active", unit).stdout.strip()
            enabled = systemctl("is-enabled", unit).stdout.strip()
            rows.append(f"{unit:<28} {active} · {enabled}")
    return rows or [f"no {name} service installed (bitloom --service-install)"]
