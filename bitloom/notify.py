"""Tell the developer when a long build ends: desktop notification (Linux, or Windows
from WSL), and an optional webhook (ntfy, Slack/Teams/Mattermost text, or JSON).
The build service sends them, so they arrive even when no TUI is attached."""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

DEFAULTS = {"desktop": True, "webhook": "", "format": "ntfy", "min_seconds": 60, "on": ["success", "failed"]}
FORMATS = ("ntfy", "slack", "json")


def path(state: Path) -> Path:
    return Path(state) / "notifications.json"


def load(state: Path) -> dict:
    try:
        data = json.loads(path(state).read_text())
        return {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save(state: Path, config: dict) -> None:
    config = {**DEFAULTS, **{k: v for k, v in config.items() if k in DEFAULTS}}
    if config["format"] not in FORMATS:
        raise ValueError("format must be ntfy, slack or json")
    if config["webhook"] and not config["webhook"].startswith(("https://", "http://")):
        raise ValueError("The webhook must be an http(s) URL")
    if not isinstance(config["on"], list) or not set(config["on"]) <= {"success", "failed", "cancelled"}:
        raise ValueError("on must list success, failed and/or cancelled")
    config["min_seconds"] = max(0, int(config["min_seconds"]))
    file = path(state)
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2))
    temporary.chmod(0o600)  # the webhook URL may contain a secret
    temporary.replace(file)


def seconds(job) -> float:
    try:
        return (datetime.fromisoformat(job.finished) - datetime.fromisoformat(job.started)).total_seconds()
    except (TypeError, ValueError):
        return 0.0


def message(job) -> tuple[str, str]:
    glyph = {"success": "✔", "failed": "✖", "cancelled": "■"}.get(job.status, "·")
    minutes, rest = divmod(int(seconds(job)), 60)
    title = f"{glyph} Bitloom: {job.title} {job.status}"
    body = f"{job.profile.name} · {minutes}m {rest}s" + (f" · exit {job.code}" if job.code not in (None, 0) else "")
    if job.status == "failed" and getattr(job, "failure_logs", None):
        body += " · " + Path(job.failure_logs[0]).name
    return title, body


def wanted(config: dict, job) -> bool:
    return job.status in config["on"] and seconds(job) >= config["min_seconds"] and job.action_id not in {"vuln-scan"}


def desktop(title: str, body: str) -> str:
    """Best effort, never blocking: notify-send on Linux, a Windows balloon from WSL."""
    if shutil.which("notify-send"):
        subprocess.Popen(["notify-send", "-a", "Bitloom", title, body], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "notify-send"
    if shutil.which("powershell.exe"):
        quote = lambda text: text.replace("'", "''")
        script = ("Add-Type -AssemblyName System.Windows.Forms; $n = New-Object System.Windows.Forms.NotifyIcon; "
                  "$n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true; "
                  f"$n.ShowBalloonTip(8000, '{quote(title)}', '{quote(body)}', [System.Windows.Forms.ToolTipIcon]::None); Start-Sleep -Seconds 9; $n.Dispose()")
        subprocess.Popen(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return "windows"
    return ""


def webhook_request(config: dict, title: str, body: str, job) -> urllib.request.Request:
    if config["format"] == "ntfy":
        priority = "high" if job.status == "failed" else "default"
        return urllib.request.Request(config["webhook"], body.encode(), {"Title": title.encode("ascii", "ignore").decode() or "Bitloom",
                                                                         "Priority": priority, "Tags": "white_check_mark" if job.status == "success" else "x"})
    payload = {"text": f"{title}\n{body}"} if config["format"] == "slack" else {
        "title": title, "body": body, "status": job.status, "job": job.id, "profile": job.profile.name, "command": job.command,
        "exit_code": job.code, "started": job.started, "finished": job.finished, "seconds": seconds(job), "log": str(job.log),
        "failure_logs": getattr(job, "failure_logs", [])}
    return urllib.request.Request(config["webhook"], json.dumps(payload).encode(), {"Content-Type": "application/json"})


def send(state: Path, job, force: bool = False) -> list[str]:
    """Deliver the configured notifications for a finished job; returns what was attempted."""
    config = load(state)
    if not force and not wanted(config, job):
        return []
    title, body = message(job)
    sent = []
    if config["desktop"]:
        method = desktop(title, body)
        if method:
            sent.append(method)
    if config["webhook"]:
        request = webhook_request(config, title, body, job)

        def post():
            try:
                urllib.request.urlopen(request, timeout=10).close()
            except OSError:
                pass  # notifications never affect builds
        threading.Thread(target=post, daemon=True).start()
        sent.append("webhook")
    return sent
