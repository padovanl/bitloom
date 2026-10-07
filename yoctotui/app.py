from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Markdown, ProgressBar, RichLog, Select, Static, TabbedContent, TabPane

from .commands import BY_ID, invocation
from .inspectors import Entry, cache_candidates, cache_path, diagnostics, human_size, inventory, metadata, prune_cache, search_log, task_logs
from .models import Profile, Settings
from .runner import Job, Runner
from .screens import ActionScreen, FileScreen, ProfilesScreen, PruneScreen
from .store import Store

HELP = """# YoctoTUI cockpit

**F2** command center · **F3** refresh · **F4** profiles · **Ctrl+P** Textual command palette · **Ctrl+Q** exit

## Workflow
1. Edit profiles (F4): set root, build_dir and runtime. Host auto-discovers oe-init-build-env or poky/oe-init-build-env. kas uses your configuration; containers mount the project at /work.
2. Queue commands (F2). The preview shows exact arguments. Jobs run serially and keep their own profile snapshot.
3. Select a history row to read its log. Search logs with context, isolate errors, and retry failed operations.
4. Browse local recipes/layers and task logs. Enter opens files. Select a recipe then use Build / Modify.

## Configuration
The JSON profile editor supports machine, distro, environment, container_args, downloads and sstate overrides. Paths in containers must live under the mounted root. Runtime paths outside the root need explicit container mounts. Cache inventory paths refer to the host filesystem.

Local configuration editor makes timestamped backups and checks for external changes. Use **bitbake -e** to inspect evaluated variables; local.conf literals are only hints.

## Maintenance
Cache scans are bounded to 20,000 files. Pruning uses age, previews a concrete list, excludes locks/markers and rechecks files before deletion. No attempt is made to determine reachability of shared-state objects. Do not prune a cache used by other builders.

## Compatibility
Commands depend on the selected Yocto release and inherited classes. SPDX, ptest and testimage require configuration. Container images, repositories and kas must be installed separately. No fake successful builds: demo mode supplies a sample workspace only.
"""


class YoctoApp(App):
    TITLE = "YoctoTUI"
    SUB_TITLE = "BUILD · DEVELOP · SHIP"
    CSS = """
    Screen { background: #0b1120; }
    Header { background: #17233a; }
    #toolbar { height: 3; padding: 0 1; background: #101c30; }
    #profile { width: 28; }
    #target { width: 1fr; }
    #toolbar Button { min-width: 10; }
    #overview { height: 5; padding: 1 2; background: #111e32; color: #81e0dc; }
    #workspace { height: 1fr; }
    TabPane { padding: 1; }
    .tools { height: 3; margin-bottom: 1; }
    .tools Input { width: 1fr; }
    .tools Button { min-width: 10; }
    DataTable { height: 1fr; border: round #243d59; }
    #history { height: 11; }
    #job-state { height: 2; }
    #progress { height: 1; }
    #log { height: 1fr; border: round #243d59; background: #070d18; }
    #scan-state { height: 2; color: #92a4bd; }
    #cache-days { width: 12; }
    #cache-kind { width: 20; }
    #health { height: 1fr; }
    #detail { height: 3; color: #92a4bd; }
    #help { height: 1fr; }
    Footer { background: #17233a; }
    """
    BINDINGS = [
        ("f2", "command", "Commands"), ("f3", "refresh", "Refresh"),
        ("f4", "profiles", "Profiles"), ("ctrl+q", "quit", "Exit"),
        ("ctrl+l", "log_focus", "Logs"),
    ]

    def __init__(self, config: Path, state: Path):
        super().__init__()
        self.settings = Settings(config)
        self.store = Store(state)
        self.runner = Runner(self.store, self.job_update)
        self.entries: list[Entry] = []
        self.cache_entries: list[Entry] = []
        self.logs: list[Entry] = []
        self.artifacts: list[Entry] = []
        self.selected_log: Path | None = None
        self.selected_job_id: str | None = None
        self.active_target = ""
        self.errors_only = False
        self.scan_generation = 0
        self.last_line = ""
        self.live_lines: list[str] = []
        self.history_rows: dict[str, dict] = {}
        self.metadata_rows: dict[str, Entry] = {}
        self.file_rows: dict[str, Entry] = {}
        self.inspection_rows: list[tuple[str, str]] = []

    @property
    def profile(self):
        return self.settings.profile

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="toolbar"):
            yield Select([(p.name, p.name) for p in self.settings.profiles], value=self.profile.name, allow_blank=False, id="profile")
            yield Input(placeholder="Build target / recipe", value=self.profile.targets[0] if self.profile.targets else "", id="target")
            yield Button("▶ Build", variant="primary", id="build")
            yield Button("Commands", id="commands")
            yield Button("Profiles", id="profiles")
        yield Static(id="overview", markup=False)
        with TabbedContent(id="workspace"):
            with TabPane("◈ Builds", id="builds"):
                yield DataTable(id="history", cursor_type="row")
                with Horizontal(classes="tools"):
                    yield Button("Stop…", variant="warning", id="stop")
                    yield Button("Retry", id="retry")
                    yield Button("Export log", id="export")
                    yield Input(placeholder="Search selected log (case insensitive, ±3 lines)", id="log-search")
                    yield Button("Errors only", id="errors")
                yield Static("No job selected", id="job-state", markup=False)
                yield ProgressBar(total=100, show_eta=False, id="progress")
                yield RichLog(id="log", wrap=True, highlight=False, markup=False, max_lines=5000)
            with TabPane("◇ Layers & recipes", id="metadata"):
                with Horizontal(classes="tools"):
                    yield Input(placeholder="Search recipe, layer, append, class, kas file…", id="metadata-search")
                    yield Button("Build recipe", id="recipe-build")
                    yield Button("Modify", id="recipe-modify")
                    yield Button("Layer actions", id="layer-actions")
                    yield Button("Rescan", id="rescan")
                yield Static(id="detail", markup=False)
                yield DataTable(id="metadata-table", cursor_type="row")
            with TabPane("≋ Task logs", id="tasklogs"):
                with Horizontal(classes="tools"):
                    yield Input(placeholder="Filter task logs by recipe or task…", id="task-search")
                    yield Button("Refresh logs", id="logs-refresh")
                    yield Button("Read selected", id="logs-read")
                yield DataTable(id="task-table", cursor_type="row")
            with TabPane("▣ Caches & downloads", id="caches"):
                with Horizontal(classes="tools"):
                    yield Select([("Downloads", "downloads"), ("Shared state", "sstate")], value="downloads", allow_blank=False, id="cache-kind")
                    yield Input(placeholder="Filter files", id="cache-search")
                    yield Input(value="30", placeholder="Age days", id="cache-days", type="integer")
                    yield Button("Scan", id="cache-scan")
                    yield Button("Prune plan", variant="warning", id="cache-prune")
                    yield Button("Fetch all", id="fetch-all")
                yield Static("Scan a cache to inspect files, size and age.", id="scan-state", markup=False)
                yield DataTable(id="cache-table", cursor_type="row")
            with TabPane("◉ Artifacts", id="artifacts"):
                with Horizontal(classes="tools"):
                    yield Input(placeholder="Search images, SDK, manifests, licenses, SPDX, buildstats…", id="artifact-search")
                    yield Button("Refresh", id="artifact-refresh")
                    yield Button("Read file", id="artifact-read")
                yield DataTable(id="artifact-table", cursor_type="row")
            with TabPane("⚙ Health & config", id="healthtab"):
                with Horizontal(classes="tools"):
                    yield Button("local.conf", id="local-conf")
                    yield Button("bblayers.conf", id="layers-conf")
                    yield Button("Environment", id="environment")
                    yield Button("Devtool status", id="dev-status")
                    yield Button("Versions", id="versions")
                    yield Button("Refresh", id="health-refresh")
                yield DataTable(id="health", cursor_type="row")
            with TabPane("⌕ Workbench", id="workbench"):
                with Horizontal(classes="tools"):
                    yield Select([("Environment", "env"), ("Dependencies", "graph")], value="env", allow_blank=False, id="inspect-kind")
                    yield Input(placeholder="Filter variable/value or graph node…", id="inspect-search")
                    yield Button("Load", id="inspect-load")
                    yield Button("Resolve env", id="inspect-resolve")
                    yield Button("Env diff", id="inspect-diff")
                with Horizontal(classes="tools"):
                    yield Button("Build history diff", id="buildhistory-report")
                    yield Button("Download audit", id="download-audit")
                    yield Button("Build report", id="build-report")
                    yield Button("Generate graph", id="generate-graph")
                yield DataTable(id="inspect-table", cursor_type="row")
            with TabPane("? Guide", id="guide"):
                yield Markdown(HELP, id="help")
        yield Footer()

    def on_mount(self):
        columns = {
            "history": ("ID", "Profile", "Operation", "Status", "Started", "Exit"),
            "metadata-table": ("Name", "Type", "Path / details"),
            "task-table": ("Recipe", "Task", "Size", "Modified"),
            "cache-table": ("File", "Size", "Age", "Path"),
            "artifact-table": ("Artifact", "Type", "Size", "Path"),
            "health": ("Status", "Check", "Details"),
            "inspect-table": ("Variable / task", "Value / dependency"),
        }
        for ident, names in columns.items():
            self.query_one(f"#{ident}", DataTable).add_columns(*names)
        self.set_interval(0.2, self.flush_log)
        self.refresh_history()
        self.action_refresh()

    def action_command(self, action_id="build", target=None):
        target = target if target is not None else self.query_one("#target", Input).value
        self.push_screen(ActionScreen(self.profile, action_id, target), self.command_result)

    def command_result(self, result):
        if not result:
            return
        action, argv = result
        if action.interactive:
            if any(j.status in {"running", "queued", "cancelling"} for j in self.runner.jobs):
                self.notify("Wait for the active job before opening an interactive command", severity="warning")
                return
            self.run_interactive(argv)
            return
        try:
            job = self.runner.submit(self.profile, action.title, argv, action.id)
            self.select_job(job.id, job.log)
            self.query_one("#workspace", TabbedContent).active = "builds"
        except (ValueError, OSError) as exc:
            self.notify(str(exc), severity="error")

    @work(exclusive=True, group="terminal")
    async def run_interactive(self, argv):
        try:
            inv = invocation(self.profile, argv)
            # Add a tty for container shell commands when the terminal is available.
            if self.profile.mode == "container":
                i = inv.argv.index("-i")
                inv.argv[i] = "-it"
            with self.suspend():
                result = await asyncio.to_thread(subprocess.run, inv.argv, cwd=inv.cwd, env=inv.env)
            self.notify(f"Interactive command exited: {result.returncode}")
        except Exception as exc:
            self.notify(str(exc), severity="error")

    def action_profiles(self):
        self.push_screen(ProfilesScreen(self.settings), self.profiles_result)

    def profiles_result(self, saved):
        if saved:
            selector = self.query_one("#profile", Select)
            selector.set_options([(p.name, p.name) for p in self.settings.profiles])
            selector.value = self.settings.active
            self.action_refresh()

    @on(Select.Changed, "#profile")
    def profile_changed(self, event):
        if event.value is Select.BLANK:
            return
        self.settings.active = str(event.value)
        if self.is_mounted:
            self.settings.save()
            self.query_one("#target", Input).value = self.profile.targets[0] if self.profile.targets else ""
            self.cache_entries = []
            self.inspection_rows = []
            self.render_cache()
            self.render_inspection()
            self.action_refresh()

    def action_refresh(self):
        self.update_overview()
        self.scan_project()
        self.refresh_history()

    def update_overview(self):
        p = self.profile
        active = self.runner.active
        queue = sum(j.status == "queued" for j in self.runner.jobs)
        self.query_one("#overview", Static).update(
            f"YOCTO CONTROL ROOM  /  {p.name.upper()}  /  {p.mode.upper()}\n"
            f"{p.root_path}  →  {p.build_dir}\n"
            f"Machine: {p.machine or 'from configuration'}   Distro: {p.distro or 'from configuration'}   "
            f"Active: {active.title if active else 'idle'}   Queued: {queue}"
        )

    @work(exclusive=True, group="scan")
    async def scan_project(self):
        p = self.profile
        entries, logs, health, artifacts = await asyncio.gather(
            asyncio.to_thread(metadata, p), asyncio.to_thread(task_logs, p),
            asyncio.to_thread(diagnostics, p), asyncio.to_thread(self.find_artifacts, p),
        )
        self.entries, self.logs, self.artifacts = entries, logs, artifacts
        self.render_metadata()
        self.render_logs()
        self.render_artifacts()
        table = self.query_one("#health", DataTable)
        table.clear()
        for status, name, detail in health:
            table.add_row(Text(status, style={"OK": "green", "WARN": "yellow", "INFO": "cyan"}[status]), name, detail)
        self.query_one("#detail", Static).update(f"{len(entries)} local metadata entries. BitBake layer commands show evaluated configuration. Enter opens a file.")

    @staticmethod
    def find_artifacts(p):
        result = []
        for sub in ("tmp/deploy", "tmp/log", "tmp/buildstats", "buildhistory"):
            result.extend(inventory(p.build_path / sub, limit=4000))
        return sorted(result, key=lambda e: e.modified, reverse=True)

    def render_metadata(self):
        query = self.query_one("#metadata-search", Input).value.casefold()
        table = self.query_one("#metadata-table", DataTable)
        table.clear()
        self.metadata_rows.clear()
        for i, e in enumerate(self.entries):
            if query in f"{e.name} {e.kind} {e.path}".casefold():
                key = f"meta-{i}"
                self.metadata_rows[key] = e
                table.add_row(e.name, e.kind, e.detail or str(e.path), key=key)

    def render_logs(self):
        query = self.query_one("#task-search", Input).value.casefold()
        table = self.query_one("#task-table", DataTable)
        table.clear()
        for i, e in enumerate(self.logs):
            if query in f"{e.name} {e.detail}".casefold():
                key = f"task-{i}"
                self.file_rows[key] = e
                table.add_row(e.detail, e.name, human_size(e.size), datetime.fromtimestamp(e.modified).strftime("%m-%d %H:%M"), key=key)

    def render_artifacts(self):
        query = self.query_one("#artifact-search", Input).value.casefold()
        table = self.query_one("#artifact-table", DataTable)
        table.clear()
        for i, e in enumerate(self.artifacts):
            if query in str(e.path).casefold():
                key = f"artifact-{i}"
                self.file_rows[key] = e
                table.add_row(e.name, e.kind, human_size(e.size), str(e.path), key=key)

    @on(Input.Changed, "#metadata-search")
    def metadata_filter(self):
        self.render_metadata()

    @on(Input.Changed, "#task-search")
    def task_filter(self):
        self.render_logs()

    @on(Input.Changed, "#artifact-search")
    def artifact_filter(self):
        self.render_artifacts()

    def refresh_history(self):
        table = self.query_one("#history", DataTable)
        cursor = table.cursor_row
        table.clear()
        self.history_rows.clear()
        for row in self.store.history():
            self.history_rows[row["id"]] = row
            status = row["status"]
            color = {"success": "green", "failed": "red", "running": "cyan", "queued": "yellow"}.get(status, "white")
            table.add_row(row["id"][:8], row["profile"], row["title"], Text(status, style=color), row["started"][11:19], str(row["code"] if row["code"] is not None else "—"), key=row["id"])
        if table.row_count:
            table.move_cursor(row=min(cursor, table.row_count-1))

    def job_update(self, job: Job, line: str | None):
        if line is not None:
            if job.id == self.selected_job_id and not self.errors_only and not self.query_one("#log-search", Input).value:
                self.live_lines.append(line)
            if "ERROR:" in line:
                self.last_line = line
        else:
            self.refresh_history()
            self.update_overview()
            if job.status == "failed":
                self.notify(f"{job.title} failed — open Errors only and Task logs", severity="error", timeout=8)
                self.scan_project()
            if job.id == self.selected_job_id:
                self.query_one("#job-state", Static).update(f"{job.title} · {job.status} · exit {job.code} · {job.log}")
        if job.id == self.selected_job_id and job.progress[1]:
            self.query_one("#progress", ProgressBar).update(total=job.progress[1], progress=job.progress[0])

    def flush_log(self):
        if self.live_lines:
            log = self.query_one("#log", RichLog)
            for line in self.live_lines:
                style = "red" if "ERROR:" in line else "yellow" if "WARNING:" in line else None
                log.write(Text(line, style=style))
            self.live_lines.clear()

    def select_job(self, ident, path):
        self.selected_job_id = ident
        self.selected_log = Path(path)
        self.live_lines.clear()
        self.reload_log()
        row = self.history_rows.get(ident)
        if row:
            self.query_one("#job-state", Static).update(f"{row['title']} · {row['status']} · {path}")

    @work(exclusive=True, group="logread")
    async def reload_log(self):
        path = self.selected_log
        if not path:
            return
        query = self.query_one("#log-search", Input).value
        try:
            text = await asyncio.to_thread(search_log, path, query, self.errors_only)
        except OSError as exc:
            text = str(exc) if path.exists() else "Waiting for log output…"
        log = self.query_one("#log", RichLog)
        log.clear()
        for line in text.splitlines():
            log.write(Text(line, style="red" if "ERROR:" in line else None))

    @on(Input.Changed, "#log-search")
    def log_filter(self):
        self.reload_log()

    @on(DataTable.RowSelected)
    def row_selected(self, event):
        key = str(event.row_key.value)
        ident = event.data_table.id
        if ident == "history":
            row = self.history_rows[key]
            self.select_job(key, row["log"])
        elif ident == "metadata-table":
            e = self.metadata_rows[key]
            p = e.path / "conf/layer.conf" if e.kind == "layer" else e.path
            self.open_file(p, editable=True)
        elif ident == "task-table":
            e = self.file_rows[key]
            self.selected_job_id = None
            self.selected_log = e.path
            self.query_one("#workspace", TabbedContent).active = "builds"
            self.query_one("#job-state", Static).update(str(e.path))
            self.reload_log()
        elif ident == "artifact-table":
            self.open_file(self.file_rows[key].path)

    def open_file(self, path, editable=False):
        try:
            if path.exists():
                if path.stat().st_size > 2_000_000:
                    self.notify("File exceeds 2 MB. Use an external viewer or log search.", severity="warning")
                    return
                if b"\x00" in path.open("rb").read(8192):
                    self.notify(f"Binary artifact: {path}", timeout=8)
                    return
            self.push_screen(FileScreen(path, editable))
        except OSError as exc:
            self.notify(str(exc), severity="error")

    def selected_entry(self):
        table = self.query_one("#metadata-table", DataTable)
        if not table.row_count:
            return None
        key = str(table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value)
        return self.metadata_rows.get(key)

    def selected_recipe(self):
        e = self.selected_entry()
        if e and e.kind in {"bb", "bbappend"}:
            return e.name.split("_", 1)[0].removesuffix(".bb").removesuffix(".bbappend")
        return self.query_one("#target", Input).value

    @on(Button.Pressed)
    def button_pressed(self, event):
        ident = event.button.id
        commands = {"build": "build", "commands": "build", "layer-actions": "layers", "environment": "environment", "dev-status": "dev-status", "fetch-all": "fetch-all", "inspect-resolve": "environment", "generate-graph": "graph"}
        if ident in commands:
            self.action_command(commands[ident])
        elif ident == "profiles":
            self.action_profiles()
        elif ident in {"rescan", "logs-refresh", "artifact-refresh", "health-refresh"}:
            self.action_refresh()
        elif ident in {"recipe-build", "recipe-modify"}:
            self.action_command("build" if ident == "recipe-build" else "dev-modify", self.selected_recipe())
        elif ident == "errors":
            self.errors_only = not self.errors_only
            event.button.label = "All lines" if self.errors_only else "Errors only"
            self.reload_log()
        elif ident == "stop":
            self.stop_build()
        elif ident == "retry":
            self.retry_job()
        elif ident == "export":
            self.export_log()
        elif ident == "cache-scan":
            self.scan_cache()
        elif ident == "cache-prune":
            self.prune_plan()
        elif ident == "local-conf":
            self.open_file(self.profile.build_path / "conf/local.conf", True)
        elif ident == "layers-conf":
            self.open_file(self.profile.build_path / "conf/bblayers.conf", True)
        elif ident == "versions":
            self.version_report()
        elif ident == "inspect-load":
            self.load_inspection()
        elif ident in {"inspect-diff", "buildhistory-report", "download-audit", "build-report"}:
            self.make_report(ident)
        elif ident in {"logs-read", "artifact-read"}:
            table = self.query_one("#task-table" if ident == "logs-read" else "#artifact-table", DataTable)
            if table.row_count:
                key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                table.post_message(DataTable.RowSelected(table, table.cursor_row, key))

    def retry_job(self):
        row = self.history_rows.get(self.selected_job_id)
        if not row:
            return
        try:
            data = json.loads(row["metadata"])
            p = Profile(**data["profile"])
            job = self.runner.submit(p, row["title"], json.loads(row["argv"]), data.get("action", "custom"))
            self.select_job(job.id, job.log)
        except Exception as exc:
            self.notify(str(exc), severity="error")

    @work(exclusive=True, group="export")
    async def export_log(self):
        if not self.selected_log or not self.selected_log.exists():
            return
        import shutil
        dest = self.store.directory / "exports" / self.selected_log.name
        dest.parent.mkdir(exist_ok=True)
        await asyncio.to_thread(shutil.copyfile, self.selected_log, dest)
        self.notify(f"Exported: {dest}", timeout=8)

    @work(exclusive=True, group="cache")
    async def scan_cache(self):
        kind = str(self.query_one("#cache-kind", Select).value)
        p = cache_path(self.profile, kind)
        self.query_one("#scan-state", Static).update(f"Scanning {p}…")
        entries = await asyncio.to_thread(inventory, p)
        if kind != str(self.query_one("#cache-kind", Select).value):
            return
        self.cache_entries = entries
        self.render_cache()
        self.query_one("#scan-state", Static).update(f"{p} · {len(entries)} files · {human_size(sum(e.size for e in entries))} · scan capped at 20,000 files")

    @on(Select.Changed, "#cache-kind")
    def cache_kind_changed(self):
        self.cache_entries = []
        if self.is_mounted:
            self.scan_cache()

    @on(Input.Changed, "#cache-search")
    def cache_filter(self):
        self.render_cache()

    def render_cache(self):
        import time
        table = self.query_one("#cache-table", DataTable)
        query = self.query_one("#cache-search", Input).value.casefold()
        table.clear()
        for e in self.cache_entries:
            if query in str(e.path).casefold():
                table.add_row(e.name, human_size(e.size), f"{int((time.time()-e.modified)/86400)}d", e.detail)

    def prune_plan(self):
        if any(j.status in {"running", "queued", "cancelling"} for j in self.runner.jobs):
            self.notify("Stop or finish queued builds before pruning caches", severity="warning")
            return
        try:
            days = int(self.query_one("#cache-days", Input).value)
            if days < 1:
                raise ValueError("Age must be at least one day")
            entries = cache_candidates(self.cache_entries, days)
            root = cache_path(self.profile, str(self.query_one("#cache-kind", Select).value))
            self.push_screen(PruneScreen(root, entries), lambda execute: self.execute_prune(root, entries) if execute else None)
        except ValueError as exc:
            self.notify(str(exc), severity="error")

    @work(exclusive=True, group="prune")
    async def execute_prune(self, root, entries):
        if self.runner.active:
            self.notify("A build started. Prune cancelled", severity="warning")
            return
        removed, freed = await asyncio.to_thread(prune_cache, root, entries)
        self.notify(f"Removed {removed} files, freed {human_size(freed)}")
        self.scan_cache()

    @work(exclusive=True, group="versions")
    async def version_report(self):
        from .versions import release_report
        text = await asyncio.to_thread(release_report, self.profile)
        dest = self.store.directory / "versions.txt"
        dest.write_text(text)
        self.open_file(dest)

    @work(exclusive=True, group="inspection")
    async def load_inspection(self):
        from .reports import dependencies, environment, environment_jobs
        try:
            kind = str(self.query_one("#inspect-kind", Select).value)
            if kind == "env":
                jobs = environment_jobs(self.store, self.profile, self.query_one("#target", Input).value)
                if not jobs:
                    raise ValueError("Resolve an environment first, then load its successful output")
                values = await asyncio.to_thread(environment, Path(jobs[0]["log"]))
                self.inspection_rows = sorted(values.items())
            else:
                path = self.profile.build_path / "task-depends.dot"
                self.inspection_rows = await asyncio.to_thread(dependencies, path)
            self.render_inspection()
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="warning")

    @on(Input.Changed, "#inspect-search")
    def inspection_filter(self):
        self.render_inspection()

    def render_inspection(self):
        query = self.query_one("#inspect-search", Input).value.casefold()
        table = self.query_one("#inspect-table", DataTable)
        table.clear()
        for name, value in self.inspection_rows:
            if query in f"{name} {value}".casefold():
                table.add_row(name, value)

    @work(exclusive=True, group="reports")
    async def make_report(self, ident):
        from .reports import build_history, build_summary, download_audit, environment, environment_jobs, env_diff
        try:
            if ident == "inspect-diff":
                jobs = environment_jobs(self.store, self.profile, self.query_one("#target", Input).value)
                if len(jobs) < 2:
                    raise ValueError("Capture two successful environments for the same recipe/profile first")
                first, second = await asyncio.gather(asyncio.to_thread(environment, Path(jobs[1]["log"])), asyncio.to_thread(environment, Path(jobs[0]["log"])))
                text = env_diff(first, second)
            elif ident == "buildhistory-report":
                text = await asyncio.to_thread(build_history, self.profile)
            elif ident == "download-audit":
                root = cache_path(self.profile, "downloads")
                entries = await asyncio.to_thread(inventory, root)
                text = download_audit(root, entries)
            else:
                if not self.selected_log:
                    raise ValueError("Select a build log first")
                text = await asyncio.to_thread(build_summary, self.selected_log)
            dest = self.store.directory / "reports" / f"{ident}.txt"
            dest.parent.mkdir(exist_ok=True)
            dest.write_text(text)
            self.open_file(dest)
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="warning")

    def action_log_focus(self):
        self.query_one("#workspace", TabbedContent).active = "builds"
        self.query_one("#log-search", Input).focus()

    def stop_build(self):
        from .stop import StopScreen
        job = next((j for j in self.runner.jobs if j.id == self.selected_job_id and j.status in {"running", "queued", "cancelling"}), self.runner.active)
        if not job:
            self.notify("No running or queued job selected")
            return
        self.push_screen(StopScreen(job), lambda choice: self.apply_stop(job, choice))

    @work(group="stop")
    async def apply_stop(self, job, choice):
        if choice == "graceful":
            await self.runner.graceful_stop(job)
        elif choice == "force":
            await self.runner.cancel(job)
            self.recovery_screen(job)
        elif choice == "finish":
            self.notify("Build will finish. No interruption requested.")

    def recovery_screen(self, job):
        from .stop import RecoveryScreen
        recipes = sorted(job.at_risk)
        if job.profile.mode in {"kas", "kas-container"} or job.profile.container_name:
            self.notify("External runtime: verify all tasks have stopped before manually queuing clean.", severity="warning", timeout=12)
            return
        if recipes:
            self.push_screen(RecoveryScreen(recipes), lambda chosen: self.recover(job, chosen))
        else:
            self.notify("No active recipe could be identified. Inspect task logs before retry.", severity="warning")

    def recover(self, job, recipes):
        for recipe in recipes or []:
            self.runner.submit(job.profile, f"Recover {recipe}: clean", ["bitbake", "-c", "clean", recipe], "clean")

    @work(group="exit", exclusive=True)
    async def action_quit(self):
        if self.runner.active:
            self.notify("Stopping active job and preserving history…", timeout=15)
        await self.runner.shutdown()
        self.store.close()
        self.exit()
