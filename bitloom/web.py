"""Local web dashboard backed by the same reconnectable build service as the TUI.

Standard library only. Listens on loopback by default; every API call needs the
session token (sent as X-Bitloom-Token, which also blocks cross-site form posts)
and the Host header must name this server, which defeats DNS rebinding.
"""
from __future__ import annotations

import hmac
import json
import secrets
import shutil
import sqlite3
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .commands import ACTIONS, BY_ID, arguments, invocation
from .inspectors import console_logs, diagnostics, human_size, metadata, search_log, task_logs
from .models import Profile, Settings, read_assignments

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
MAX_CHUNK = 512 * 1024


def history(state: Path, limit=200) -> list[dict]:
    path = Path(state).resolve() / "history.sqlite3"
    if not path.exists():
        return []
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in db.execute("SELECT * FROM jobs ORDER BY started DESC LIMIT ?", (limit,))]
    finally:
        db.close()
    result = []
    for row in rows:
        data = json.loads(row.pop("metadata") or "{}")
        row["argv"] = json.loads(row["argv"])
        row["progress"] = data.get("progress", [0, 0])
        row["setscene"] = data.get("setscene", [0, 0])
        row["action"] = data.get("action", "custom")
        row["failure_logs"] = data.get("failure_logs", [])
        result.append(row)
    return result


def host_metrics(root: Path) -> dict:
    result = {}
    try:
        mem = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()}
        result["ram_used"] = (mem["MemTotal"] - mem["MemAvailable"]) * 1024
        result["ram_total"] = mem["MemTotal"] * 1024
        result["load"] = Path("/proc/loadavg").read_text().split()[:3]
    except (OSError, ValueError, KeyError, IndexError):
        pass
    try:
        disk = shutil.disk_usage(root if root.exists() else Path.cwd())
        result.update(disk_free=disk.free, disk_total=disk.total, disk_used=disk.used)
    except OSError:
        pass
    return result


def job_report(path: Path) -> dict:
    """Toaster-style build detail from the stored log: summary, sstate reuse, warnings, timings."""
    from .analysis import sstate_report, warning_report
    from .reports import build_summary, task_timings
    return {name: function(path) for name, function in
            (("summary", build_summary), ("sstate", sstate_report), ("warnings", warning_report), ("timings", task_timings))}


class Dashboard:
    def __init__(self, config: Path, state: Path, token: str | None = None):
        self.config, self.state = Path(config), Path(state).resolve()
        self.token = token or secrets.token_urlsafe(24)
        self.cpu_sample = None
        self.cpu_history: list[float] = []

    def cpu(self):
        """Host CPU utilisation between two polls (labelled host: a container runtime may differ)."""
        try:
            values = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
        except (OSError, ValueError, IndexError):
            return None
        sample = (sum(values[:8]), values[3] + values[4])
        previous, self.cpu_sample = self.cpu_sample, sample
        if previous and sample[0] > previous[0]:
            usage = 100 * (1 - (sample[1] - previous[1]) / (sample[0] - previous[0]))
            self.cpu_history = (self.cpu_history + [round(usage, 1)])[-60:]
            return round(usage, 1)
        return None

    # Service access is isolated here so tests can substitute it.
    def rpc(self, payload):
        from .daemon import ensure_service, rpc
        ensure_service(self.state)
        return rpc(self.state, payload)

    def settings(self) -> Settings:
        return Settings(self.config)

    def profile(self, name=None):
        settings = self.settings()
        if not name:
            return settings.profile
        profile = next((p for p in settings.profiles if p.name == name), None)
        if profile is None:
            raise ValueError("Unknown profile: " + name)
        return profile

    def job_row(self, ident):
        row = next((r for r in history(self.state, 500) if r["id"] == ident), None)
        if row is None:
            raise LookupError("Unknown job")
        return row

    # --- API -----------------------------------------------------------------
    def state_payload(self):
        settings = self.settings()
        profile = settings.profile
        try:
            service = self.rpc({"op": "status"})
            from . import __version__
            service = {"pid": service["pid"], "active": service["active"], "version": service.get("version", "unknown"),
                       "outdated": service.get("version", "unknown") != __version__,
                       "jobs": {j["id"]: {"status": j["status"], "progress": j["progress"], "setscene": j.get("setscene", [0, 0]),
                                          "tasks": sorted(j["active_recipe_tasks"])} for j in service["jobs"]}}
        except (OSError, ValueError) as exc:
            service = {"error": str(exc), "jobs": {}}
        rows = history(self.state)
        for row in rows:
            live = service["jobs"].get(row["id"])
            if live:
                row.update(status=live["status"], progress=live["progress"], setscene=live["setscene"], tasks=live["tasks"])
        from .versions import describe, detect_release
        hints = {p.name: read_assignments(p.build_path / "conf/local.conf") for p in settings.profiles}
        return {
            "active": settings.active,
            "profiles": [{"name": p.name, "mode": p.mode, "machine": p.machine or hints[p.name].get("MACHINE", ""),
                          "distro": p.distro or hints[p.name].get("DISTRO", ""), "root": str(p.root_path),
                          "build": str(p.build_path), "targets": p.targets, "release": describe(detect_release(p)),
                          "shared": p.name in settings.shared} for p in settings.profiles],
            "service": {k: v for k, v in service.items() if k != "jobs"},
            "history": rows,
            "host": {**host_metrics(profile.root_path), "cpu": self.cpu(), "cpu_history": self.cpu_history},
        }

    def actions(self):
        return [{"id": a.id, "group": a.group, "title": a.title, "inputs": list(a.inputs), "help": a.help,
                 "interactive": a.interactive, "since": a.since, "until": a.until} for a in ACTIONS]

    def release_check(self, action, profile):
        from .commands import availability
        from .versions import detect_release
        return availability(action, detect_release(profile))

    def preview(self, body):
        action = BY_ID.get(body.get("action", ""))
        if action is None:
            raise ValueError("Unknown operation")
        profile = self.profile(body.get("profile"))
        argv = arguments(action, body.get("values", {}))
        ok, reason = self.release_check(action, profile)
        if ok is False:
            raise ValueError("Not available: " + reason)
        return {"command": invocation(profile, argv).display, "help": action.help + (("\n" + reason) if reason else "")}

    def submit(self, body):
        action = BY_ID.get(body.get("action", ""))
        if action is None:
            raise ValueError("Unknown operation")
        if action.interactive:
            raise ValueError("Interactive terminal operations run from the TUI")
        profile = self.profile(body.get("profile"))
        argv = arguments(action, body.get("values", {}))
        ok, reason = self.release_check(action, profile)
        if ok is False:
            raise ValueError("Not available: " + reason)
        invocation(profile, argv)
        from dataclasses import asdict
        result = self.rpc({"op": "submit", "profile": asdict(profile), "title": action.title + (" · " + argv[-1] if action.inputs else ""),
                           "command": argv, "action_id": action.id})
        return {"id": result["job"]["id"]}

    def stop(self, ident, body):
        mode = body.get("mode", "force")
        if mode not in {"graceful", "force"}:
            raise ValueError("mode must be graceful or force")
        result = self.rpc({"op": "graceful" if mode == "graceful" else "cancel", "id": ident})
        return {"status": result["job"]["status"]}

    def retry(self, ident):
        row = self.job_row(ident)
        if row["status"] in {"running", "queued", "cancelling"}:
            raise ValueError("Operation is still active")
        path = Path(self.state) / "history.sqlite3"
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            data = json.loads(db.execute("SELECT metadata FROM jobs WHERE id=?", (ident,)).fetchone()[0])
        finally:
            db.close()
        result = self.rpc({"op": "submit", "profile": data["profile"], "title": row["title"], "command": row["argv"],
                           "action_id": data.get("action", "custom")})
        return {"id": result["job"]["id"]}

    def log(self, ident, query):
        path = Path(self.job_row(ident)["log"])
        if not path.exists():
            return {"text": "", "offset": 0, "size": 0}
        text_query, errors = query.get("q", [""])[0], query.get("errors", ["0"])[0] == "1"
        if text_query or errors:
            return {"text": search_log(path, text_query, errors), "offset": 0, "size": path.stat().st_size, "filtered": True}
        size = path.stat().st_size
        offset = int(query.get("offset", ["-1"])[0])
        if offset < 0 or offset > size:
            offset = max(0, size - MAX_CHUNK)
        with path.open("rb") as stream:
            stream.seek(offset)
            chunk = stream.read(MAX_CHUNK)
        # Return complete lines only; the service may be writing the last one.
        end = chunk.rfind(b"\n") + 1
        if not end and len(chunk) == MAX_CHUNK:
            end = len(chunk)
        chunk = chunk[:end]
        return {"text": chunk.decode(errors="replace"), "offset": offset + len(chunk), "size": size}

    def report(self, ident):
        path = Path(self.job_row(ident)["log"])
        if not path.exists():
            raise LookupError("Log not available yet")
        return job_report(path)

    def console(self, query):
        profile = self.profile(query.get("profile", [""])[0])
        return {"rows": [{"name": e.name, "machine": e.kind, "status": e.detail, "size": e.size, "modified": e.modified, "path": str(e.path)}
                         for e in console_logs(profile)]}

    def console_entry(self, query):
        profile = self.profile(query.get("profile", [""])[0])
        wanted = query.get("path", [""])[0]
        # Only logs found under tmp/log/cooker of a configured profile are served.
        entry = next((e for e in console_logs(profile) if str(e.path) == wanted), None)
        if entry is None:
            raise LookupError("Console log not found in the build directory")
        return entry.path

    def console_log(self, query):
        path = self.console_entry(query)
        text_query, errors = query.get("q", [""])[0], query.get("errors", ["0"])[0] == "1"
        return {"text": search_log(path, text_query, errors), "filtered": bool(text_query or errors)}

    def console_report(self, query):
        return job_report(self.console_entry(query))

    def compliance(self, query):
        from .sbom import DEADLINES, analyse, cra_checks, sbom_files
        from .sbom_settings import OPTIONS, availability, current
        from .versions import INFO, describe, detect_release
        profile = self.profile(query.get("profile", [""])[0])
        series = detect_release(profile)
        sboms = []
        for path in sbom_files(profile)[:3]:
            try:
                sboms.append(analyse(path))
            except (OSError, ValueError) as exc:
                sboms.append({"file": str(path), "error": str(exc)})
        managed, elsewhere = current(profile)
        options = []
        for option in OPTIONS:
            ok, reason = availability(option, series)
            options.append({"id": option.id, "title": option.title, "name": option.name, "kind": option.kind, "info": option.info, "cra": option.cra,
                            "available": ok, "reason": reason, "value": managed.get(option.id) or elsewhere.get(option.id) or "",
                            "since": option.since, "until": option.until, "verified": option.verified})
        support = INFO.get(series)
        return {"release": describe(series), "series": series, "support_until": support[1].isoformat() if support else None, "lts": bool(support and support[2]),
                "sboms": sboms, "checks": [{"status": s, "item": i, "detail": d} for s, i, d in cra_checks(profile, self.state)],
                "timeline": [{"date": when.isoformat(), "text": text} for when, text in DEADLINES], "options": options}

    def studio_fields(self, query):
        from dataclasses import asdict
        from .studio import KINDS, fields, product_layers
        from .versions import detect_release
        profile = self.profile(query.get("profile", [""])[0])
        kind = query.get("kind", ["distro"])[0]
        if kind not in KINDS:
            raise ValueError("Unknown kind")
        layers = product_layers(metadata(profile), profile)
        return {"kinds": [{"id": k, "title": t, "description": d} for k, (t, d) in KINDS.items()],
                "fields": [asdict(f) for f in fields(kind, detect_release(profile), layers)], "mode": profile.mode}

    def studio_plan(self, body):
        from .studio import plan
        from .versions import detect_release
        profile = self.profile(body.get("profile"))
        values = body.get("values", {})
        if not isinstance(values, dict) or any(not isinstance(v, str) for v in values.values()):
            raise ValueError("values must be strings")
        return profile, plan(body.get("kind", ""), values, profile, detect_release(profile))

    def studio_preview(self, body):
        return self.studio_plan(body)[1]

    def studio_create(self, body):
        from .studio import create, register
        profile, result = self.studio_plan(body)
        written = create(profile, result)
        settings = self.settings()
        profile = next(p for p in settings.profiles if p.name == profile.name)

        def submit(job_profile, title, argv, action):
            from dataclasses import asdict
            self.rpc({"op": "submit", "profile": asdict(job_profile), "title": title, "command": argv, "action_id": action})
        messages, target = register(settings, profile, result, body.get("use") is True, submit)
        return {"written": [str(p) for p in written], "messages": messages, "target": target}

    def projects(self):
        from .projects import IMAGES, MACHINES, RELEASES, Recent
        settings = self.settings()
        roots = {str(p.root_path): p.name for p in settings.profiles}
        items, seen = [], set()
        for item in Recent(self.state).load() + [{"root": root, "profile": name, "how": "profile"} for root, name in roots.items()]:
            if item["root"] not in seen:
                seen.add(item["root"])
                items.append({**item, "profile": roots.get(item["root"], "")})
        return {"recent": items, "releases": {k: v["title"] for k, v in RELEASES.items()}, "machines": list(MACHINES), "images": list(IMAGES),
                "home": str(Path.home())}

    def project_plan(self, body):
        from .projects import new_project_plan
        values = {k: str(body.get(k, "")) for k in ("dir", "name", "release", "machine", "distro", "target", "owner")}
        return new_project_plan(values["dir"], values["name"], values["release"], values["machine"], values["distro"], values["target"],
                                body.get("layer") is True, values["owner"])

    def project_create(self, body):
        from .projects import Recent, create_project
        from .setup import save
        plan = self.project_plan(body)
        runtime = body.get("runtime", "kas-container")
        if runtime not in {"kas", "kas-container"}:
            raise ValueError("runtime must be kas or kas-container")
        profile = create_project(plan, runtime)
        save(self.settings(), profile)
        Recent(self.state).add(profile.root_path, profile.name, "created")
        return {"active": profile.name, "root": str(profile.root_path)}

    def project_clone(self, body):
        from dataclasses import asdict
        from .projects import clone_argv
        argv = clone_argv(str(body.get("url", "")), str(body.get("dest", "")), str(body.get("branch", "")))
        destination = Path(argv[-1])
        destination.parent.mkdir(parents=True, exist_ok=True)
        helper = Profile(name="git-clone", root=str(destination.parent), build_dir=str(destination.parent))
        result = self.rpc({"op": "submit", "profile": asdict(helper), "title": "Clone " + destination.name, "command": argv, "action_id": "project-clone"})
        return {"id": result["job"]["id"], "dest": str(destination)}

    def vulnerabilities(self, query):
        from dataclasses import asdict
        from .vulns import counts, load, scanners, select, sources
        profile = self.profile(query.get("profile", [""])[0])
        findings, errors = load(profile, self.state, query.get("source", [""])[0])
        try:
            minimum = float(query.get("min", ["0"])[0] or 0)
        except ValueError:
            minimum = 0.0
        shown = select(findings, query.get("status", ["unpatched"])[0], minimum, query.get("q", [""])[0])
        return {"sources": [label for label, _ in sources(profile, self.state)], "counts": counts(findings), "errors": errors,
                "findings": [asdict(f) for f in shown[:500]], "shown": len(shown), "scanners": {k: bool(v) for k, v in scanners().items()}}

    def vulnerability_scan(self, body):
        from dataclasses import asdict
        from datetime import datetime
        from .sbom import sbom_files
        from .vulns import grype_argv
        profile = self.profile(body.get("profile"))
        sboms = [p for p in sbom_files(profile) if p.name.endswith(".spdx.json")]
        if not sboms:
            raise ValueError("No SPDX JSON SBOM in tmp/deploy")
        output = self.state / "vulnerability-scans" / f"{sboms[0].name[:-len('.spdx.json')]}-{datetime.now():%Y%m%d-%H%M%S}.grype.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        helper = Profile(name="vulnerability-scan", root=str(self.state), build_dir=str(self.state))
        result = self.rpc({"op": "submit", "profile": asdict(helper), "title": "Grype scan " + output.name, "command": grype_argv(sboms[0], output), "action_id": "vuln-scan"})
        return {"id": result["job"]["id"]}

    def setup_scan(self, query):
        from .setup import candidate_json, detect
        directory = query.get("dir", [""])[0] or str(self.profile().root_path)
        return {"dir": str(Path(directory).expanduser().resolve()), "candidates": [candidate_json(c) for c in detect(Path(directory))]}

    def setup_profile(self, body):
        from .models import Profile
        data = body.get("profile")
        if not isinstance(data, dict):
            raise ValueError("profile must be an object")
        return Profile.from_dict(data)

    def setup_check(self, body):
        from .setup import check
        try:
            rows = check(self.setup_profile(body))
        except (TypeError, ValueError) as exc:
            rows = [("ERR", str(exc))]
        return {"checks": [{"status": s, "message": m} for s, m in rows]}

    def setup_save(self, body):
        from .setup import check, save
        profile = self.setup_profile(body)
        if any(status == "ERR" for status, _ in check(profile)):
            raise ValueError("Fix the checks marked ✖ first")
        save(self.settings(), profile)
        from .projects import Recent
        Recent(self.state).add(profile.root_path, profile.name, "set up")
        return {"active": profile.name}

    def health(self, query):
        profile = self.profile(query.get("profile", [""])[0])
        return {"checks": [{"status": s, "name": n, "detail": d} for s, n, d in diagnostics(profile)]}

    def metadata(self, query):
        profile = self.profile(query.get("profile", [""])[0])
        needle = query.get("q", [""])[0].casefold()
        rows = [{"name": e.name, "kind": e.kind, "path": str(e.path), "detail": e.detail} for e in metadata(profile)
                if needle in f"{e.name} {e.kind} {e.path}".casefold()]
        return {"total": len(rows), "rows": rows[:500]}

    def task_logs(self, query):
        profile = self.profile(query.get("profile", [""])[0])
        needle = query.get("q", [""])[0].casefold()
        rows = [{"recipe": e.detail, "task": e.name, "size": human_size(e.size), "modified": e.modified, "path": str(e.path)}
                for e in task_logs(profile) if needle in f"{e.name} {e.detail}".casefold()]
        return {"total": len(rows), "rows": rows[:500]}

    def task_log(self, query):
        profile = self.profile(query.get("profile", [""])[0])
        wanted = query.get("path", [""])[0]
        # Only files the task-log index found may be read through the dashboard.
        entry = next((e for e in task_logs(profile) if str(e.path) == wanted), None)
        if entry is None:
            raise LookupError("Task log not found in the indexed build directory")
        return {"path": wanted, "text": search_log(entry.path, query.get("q", [""])[0], query.get("errors", ["0"])[0] == "1")}


def make_handler(dashboard: Dashboard, allowed_hosts: set[str] | None):
    from .webpage import PAGE

    class Handler(BaseHTTPRequestHandler):
        server_version = "Bitloom"
        sys_version = ""

        def log_message(self, format, *args):  # Keep the terminal quiet; the TUI may share it.
            pass

        def send(self, status, body: bytes, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            if content_type.startswith("text/html"):
                self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def json(self, status, payload):
            self.send(status, json.dumps(payload).encode())

        def guard(self) -> bool:
            host = (self.headers.get("Host") or "").lower()
            if allowed_hosts is not None and host not in allowed_hosts:
                self.json(HTTPStatus.MISDIRECTED_REQUEST, {"error": "Unexpected Host header"})
                return False
            return True

        def authorized(self) -> bool:
            supplied = self.headers.get("X-Bitloom-Token", "")
            if not hmac.compare_digest(supplied.encode(), dashboard.token.encode()):
                self.json(HTTPStatus.UNAUTHORIZED, {"error": "Missing or invalid session token; open the URL printed by bitloom --web"})
                return False
            return True

        def body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > 64 * 1024:
                raise ValueError("Request too large")
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
            return data

        def dispatch(self, method):
            if not self.guard():
                return
            url = urlparse(self.path)
            parts = [p for p in url.path.split("/") if p]
            if method == "GET" and not parts:
                self.send(HTTPStatus.OK, PAGE.encode(), "text/html; charset=utf-8")
                return
            if not parts or parts[0] != "api":
                self.json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            if not self.authorized():
                return
            query = parse_qs(url.query)
            try:
                route = (method, *parts[1:])
                if route == ("GET", "state"):
                    payload = dashboard.state_payload()
                elif route == ("GET", "actions"):
                    payload = dashboard.actions()
                elif route == ("GET", "health"):
                    payload = dashboard.health(query)
                elif route == ("GET", "metadata"):
                    payload = dashboard.metadata(query)
                elif route == ("GET", "tasklogs"):
                    payload = dashboard.task_logs(query)
                elif route == ("GET", "tasklog"):
                    payload = dashboard.task_log(query)
                elif route == ("GET", "compliance"):
                    payload = dashboard.compliance(query)
                elif route == ("GET", "studio", "fields"):
                    payload = dashboard.studio_fields(query)
                elif route == ("POST", "studio", "preview"):
                    payload = dashboard.studio_preview(self.body())
                elif route == ("POST", "studio", "create"):
                    payload = dashboard.studio_create(self.body())
                elif route == ("GET", "vulnerabilities"):
                    payload = dashboard.vulnerabilities(query)
                elif route == ("POST", "vulnerabilities", "scan"):
                    payload = dashboard.vulnerability_scan(self.body())
                elif route == ("GET", "projects"):
                    payload = dashboard.projects()
                elif route == ("POST", "projects", "preview"):
                    payload = dashboard.project_plan(self.body())
                elif route == ("POST", "projects", "create"):
                    payload = dashboard.project_create(self.body())
                elif route == ("POST", "projects", "clone"):
                    payload = dashboard.project_clone(self.body())
                elif route == ("GET", "setup", "scan"):
                    payload = dashboard.setup_scan(query)
                elif route == ("POST", "setup", "check"):
                    payload = dashboard.setup_check(self.body())
                elif route == ("POST", "setup", "save"):
                    payload = dashboard.setup_save(self.body())
                elif route == ("GET", "console"):
                    payload = dashboard.console(query)
                elif route == ("GET", "console", "log"):
                    payload = dashboard.console_log(query)
                elif route == ("GET", "console", "report"):
                    payload = dashboard.console_report(query)
                elif route == ("POST", "preview"):
                    payload = dashboard.preview(self.body())
                elif route == ("POST", "jobs"):
                    payload = dashboard.submit(self.body())
                elif len(route) == 4 and route[:2] == ("GET", "jobs") and route[3] == "log":
                    payload = dashboard.log(route[2], query)
                elif len(route) == 4 and route[:2] == ("GET", "jobs") and route[3] == "report":
                    payload = dashboard.report(route[2])
                elif len(route) == 4 and route[:2] == ("POST", "jobs") and route[3] == "stop":
                    payload = dashboard.stop(route[2], self.body())
                elif len(route) == 4 and route[:2] == ("POST", "jobs") and route[3] == "retry":
                    payload = dashboard.retry(route[2])
                else:
                    self.json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                    return
                self.json(HTTPStatus.OK, payload)
            except LookupError as exc:
                self.json(HTTPStatus.NOT_FOUND, {"error": str(exc).strip("'\"")})
            except (ValueError, TypeError, OSError) as exc:
                self.json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def do_GET(self):
            self.dispatch("GET")

        def do_POST(self):
            self.dispatch("POST")

    return Handler


def create_server(dashboard: Dashboard, host="127.0.0.1", port=8765) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), None)
    actual = server.server_address[1]
    # Loopback servers accept only their own Host names (DNS rebinding defence);
    # an explicit non-loopback bind is reached by arbitrary names and relies on the token.
    allowed = None
    if host in LOOPBACK:
        allowed = {f"{name}:{actual}" for name in LOOPBACK if ":" not in name} | {f"[::1]:{actual}"}
    server.RequestHandlerClass = make_handler(dashboard, allowed)
    return server


def serve(config: Path, state: Path, host="127.0.0.1", port=8765, open_browser=True):
    dashboard = Dashboard(config, state)
    dashboard.rpc({"op": "status"})  # Start or attach to the build service before announcing the URL.
    server = create_server(dashboard, host, port)
    shown = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{shown}:{server.server_address[1]}/#token={dashboard.token}"
    print(f"Bitloom web dashboard: {url}")
    print(f"State: {dashboard.state} · builds run in the shared service; Ctrl+C stops the web server only.")
    if host not in LOOPBACK:
        print("WARNING: listening beyond loopback. Anyone with the URL can queue builds; prefer an SSH tunnel.")
    if open_browser:
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
