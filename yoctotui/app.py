from __future__ import annotations

import asyncio
import json
import subprocess
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.text import Text
from rich.syntax import Syntax
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Markdown, ProgressBar, RichLog, Select, Static, TabbedContent, TabPane, Tree

from .commands import invocation
from .inspectors import Entry, cache_candidates, cache_path, diagnostics, human_size, inventory, metadata, prune_cache, search_log, task_logs
from .models import Profile, Settings, read_assignments
from .runner import Job, Runner
from .screens import ActionScreen, FileScreen, ProfilesScreen, PruneScreen
from .store import Store

HELP = """# Bitloom cockpit

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
    TITLE = "Bitloom"
    SUB_TITLE = "Yocto / BitBake workspace"
    CSS = """
    Screen { background: #0b1115; color: #bdcbd2; }
    Header { background: #111b22; color: #84c9c0; }
    #toolbar { height: 1; padding: 0 1; background: #111b22; }
    #profile { width: 22; height: 1; }
    #target { width: 1fr; }
    Button { height: 1; min-width: 8; border: none; background: #16232a; color: #a9c3ce; padding: 0 1; }
    Button:hover, Button:focus { background: #25404b; color: #e0f3f6; }
    Button.-primary { background: #183832; color: #8fdbc3; }
    Button.-warning { background: #382d1b; color: #dfbe77; }
    Input { height: 1; border: none; background: #121e25; padding: 0 1; }
    Select { height: 1; border: none; }
    SelectCurrent { height: 1; border: none; padding: 0 1; background: #172730; }
    #shell { height: 1fr; }
    #rail { width: 22; background: #0d171d; padding: 0 1; border-right: solid #30444e; }
    #brand { height: 3; color: #89d2bd; text-style: bold; padding-top: 1; }
    .rail-label { color: #d2b77b; height: 2; padding-top: 1; }
    #rail Button { width: 1fr; text-align: left; height: 1; margin: 0; padding: 0 1; background: #0d171d; color: #9ab4c0; }
    #rail Button.selected { background: #203e49; color: #d9f3f5; text-style: bold; }
    #rail-context { height: 1fr; color: #738e9d; margin-top: 2; }
    #main { width: 1fr; }
    #overview { height: 3; padding: 0 1; color: #9ab4c0; border-bottom: solid #30444e; }
    #metrics { height: 4; }
    .metric { width: 1fr; padding: 0 1; border-bottom: solid #30444e; border-right: solid #30444e; background: #0b1115; }
    #workspace { height: 1fr; }
    #workspace > ContentTabs { display: none; }
    TabPane { padding: 0 1; }
    .tools { height: 1; margin-bottom: 1; }
    .tools Input { width: 1fr; }
    .tools Button { min-width: 8; }
    DataTable { height: 1fr; border: solid #30444e; background: #0b1115; }
    DataTable > .datatable--header { background: #14242c; color: #89c7d5; text-style: bold; }
    DataTable > .datatable--cursor { background: #203e49; color: #daf1f2; }
    #build-split { height: 1fr; }
    #history-panel { width: 40; padding-right: 1; }
    #history { height: 1fr; }
    #task-monitor { height: 9; border: solid #30444e; color: #97cbbb; padding: 0 1; }
    #stream-panel { width: 1fr; }
    .section-title { height: 2; color: #81bdcf; padding-top: 1; }
    #job-state { height: 2; color: #9eb2c1; }
    #progress { height: 1; margin-bottom: 1; }
    #log { height: 1fr; border: solid #30444e; background: #080f13; }
    #scan-state { height: 2; color: #92a4bd; }
    #cache-days { width: 9; }
    #cache-kind { width: 18; }
    #inspect-kind { width: 19; }
    #analysis-kind { width: 24; }
    #analysis-output { height: 1fr; border: solid #30444e; }
    #health { height: 1fr; }
    #metadata-split { height: 1fr; }
    #layer-tree { width: 26; border: solid #30444e; background: #0d171d; }
    #metadata-table { width: 3fr; }
    #source-preview { width: 2fr; border: solid #30444e; background: #080f13; }
    #active-tasks { height: 4; color: #a6d9c8; }
    #detail { height: 2; color: #92a4bd; }
    #help { height: 1fr; }
    Footer { background: #111b22; }
    Screen.compact #rail { width: 20; }
    Screen.compact #history-panel { width: 34; }
    Screen.compact #toolbar #commands, Screen.compact #toolbar #profiles { display: none; }
    Screen.narrow #rail { display: none; }
    Screen.narrow #workspace > ContentTabs { display: block; }
    Screen.narrow #overview { height: 2; }
    Screen.narrow #metrics { height: 3; }
    Screen.narrow .section-title { height: 1; padding-top: 0; }
    Screen.narrow .tools { margin-bottom: 0; }
    Screen.narrow #progress { margin-bottom: 0; }
    Screen.narrow #build-split { layout: vertical; }
    Screen.narrow #history-panel { width: 1fr; height: 7; padding-right: 0; }
    Screen.narrow #stream-panel { width: 1fr; height: 1fr; }
    Screen.narrow #task-monitor, Screen.narrow #source-preview, Screen.narrow #layer-tree { display: none; }
    """
    BINDINGS = [
        ("f2", "command", "Commands"), ("f3", "refresh", "Refresh"),
        ("f4", "profiles", "Profiles"), ("ctrl+q", "quit", "Exit"),
        ("f5", "stop_job", "Stop"), ("f6", "retry", "Retry"),
        ("ctrl+l", "log_focus", "Logs"),
        ("alt+1", "section('builds')", "Builds"),
        ("alt+2", "section('metadata')", "Metadata"),
        ("alt+3", "section('tasklogs')", "Tasks"),
        ("alt+4", "section('workbench')", "Inspect"),
        ("alt+5", "section('caches')", "Caches"),
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
        self.errors_only = False
        self.follow_log = True
        self.resource_previous = None
        self.resource_time = time.monotonic()
        self.last_line = ""
        self.live_lines: list[str] = []
        self.history_rows: dict[str, dict] = {}
        self.metadata_rows: dict[str, Entry] = {}
        self.file_rows: dict[str, Entry] = {}
        self.inspection_rows: list[tuple[str, str]] = []
        self.config_hints = {}
        self.analysis_text = ""

    def main_query(self, selector, expect_type=None):
        """Keep background updates on the workspace while a modal is open."""
        return self.screen_stack[0].query_one(selector, expect_type)

    @property
    def profile(self):
        return self.settings.profile

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, icon="B")
        with Horizontal(id="toolbar"):
            yield Select([(p.name, p.name) for p in self.settings.profiles], value=self.profile.name, allow_blank=False, id="profile")
            yield Input(placeholder="Build target / recipe", value=self.profile.targets[0] if self.profile.targets else "", id="target")
            yield Button("[ Build ]", variant="primary", id="build")
            yield Button("Commands", id="commands")
            yield Button("Profiles", id="profiles")
        with Horizontal(id="shell"):
            with Vertical(id="rail"):
                yield Static("BITLOOM\nYocto / BitBake", id="brand")
                yield Static("BUILD & DIAGNOSE", classes="rail-label")
                for title, tab in [("Builds / logs", "builds"), ("Task logs", "tasklogs")]:
                    yield Button(title, id=f"nav-{tab}")
                yield Static("DEVELOP & INSPECT", classes="rail-label")
                for title, tab in [("Metadata", "metadata"), ("Environment", "workbench"), ("Artifacts", "artifacts"), ("Analysis", "analysis")]:
                    yield Button(title, id=f"nav-{tab}")
                yield Static("WORKSPACE", classes="rail-label")
                for title, tab in [("Caches", "caches"), ("Configuration", "healthtab"), ("Help", "guide")]:
                    yield Button(title, id=f"nav-{tab}")
                yield Static(id="rail-context")
            with Vertical(id="main"):
                yield Static(id="overview", markup=False)
                with Horizontal(id="metrics"):
                    for ident in ("build-metric", "queue-metric", "resource-metric", "disk-metric"):
                        yield Static(id=ident, classes="metric")
                with TabbedContent(id="workspace"):
                    with TabPane("◈ Builds", id="builds"):
                        with Horizontal(id="build-split"):
                            with Vertical(id="history-panel"):
                                yield Static("RECENT OPERATIONS", classes="section-title")
                                yield DataTable(id="history", cursor_type="row")
                                with Horizontal(classes="tools"):
                                    yield Button("Stop…", variant="warning", id="stop")
                                    yield Button("Retry", id="retry")
                                    yield Button("Export", id="export")
                                yield Static("No observed active tasks", id="task-monitor", markup=False)
                            with Vertical(id="stream-panel"):
                                yield Static("BUILD OUTPUT / DIAGNOSTICS", classes="section-title")
                                yield Static("Select an operation to inspect its output", id="job-state", markup=False)
                                yield ProgressBar(total=100, show_eta=False, id="progress")
                                with Horizontal(classes="tools"):
                                    yield Input(placeholder="Search output · ±3 context lines", id="log-search")
                                    yield Button("Errors", id="errors")
                                    yield Button("Pause", id="log-follow")
                                yield RichLog(id="log", min_width=1, wrap=True, highlight=False, markup=False, max_lines=5000)
                    with TabPane("◇ Layers & recipes", id="metadata"):
                        with Horizontal(classes="tools"):
                            yield Input(placeholder="Search recipe, layer, append, class, kas file…", id="metadata-search")
                            yield Button("Build recipe", id="recipe-build")
                            yield Button("Modify", id="recipe-modify")
                            yield Button("Layer actions", id="layer-actions")
                            yield Button("Rescan", id="rescan")
                        yield Static(id="detail", markup=False)
                        with Horizontal(id="metadata-split"):
                            yield Tree("Workspace metadata", id="layer-tree")
                            yield DataTable(id="metadata-table", cursor_type="row")
                            yield RichLog(id="source-preview", wrap=False, max_lines=200, markup=False)
                    with TabPane("≋ Task logs", id="tasklogs"):
                        with Horizontal(classes="tools"):
                            yield Input(placeholder="Filter task logs by recipe or task…", id="task-search")
                            yield Button("Refresh logs", id="logs-refresh")
                            yield Button("Read selected", id="logs-read")
                            yield Button("Failed task log", id="failed-task-log")
                        yield Static("No active tasks in this TUI session.", id="active-tasks", markup=False)
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
                            yield Button("Rootfs inventory", id="image-contents")
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
                            yield Button("Why this task?", id="dependency-context")
                            yield Button("Timings", id="task-timings")
                        yield DataTable(id="inspect-table", cursor_type="row")
                    with TabPane("Analysis", id="analysis"):
                        with Horizontal(classes="tools"):
                            yield Select([("Search metadata", "metadata"), ("Compare manifests", "manifests"), ("Sstate efficiency", "sstate"), ("Warning groups", "warnings")], value="metadata", allow_blank=False, id="analysis-kind")
                            yield Input(placeholder="Literal metadata search phrase", id="analysis-query")
                            yield Button("Analyze", id="analysis-run")
                            yield Button("Export", id="analysis-export")
                        with Horizontal(classes="tools", id="analysis-paths"):
                            yield Input(placeholder="First manifest / build log path (blank uses selected log)", id="analysis-first")
                            yield Input(placeholder="Second manifest path", id="analysis-second")
                        yield Static("Read-only reports. Manifest paths must be visible on the host; logs are persisted from every runtime.", id="analysis-note", markup=False)
                        yield RichLog(id="analysis-output", min_width=1, wrap=True, markup=False)
                    with TabPane("? Guide", id="guide"):
                        yield Markdown(HELP, id="help")
        yield Footer()

    def on_mount(self):
        columns = {
            "history": ("Operation", "Status", "Elapsed"),
            "metadata-table": ("Name", "Type", "Path / details"),
            "task-table": ("Recipe", "Task", "Size", "Modified"),
            "cache-table": ("File", "Size", "Age", "Path"),
            "artifact-table": ("Artifact", "Type", "Size", "Path"),
            "health": ("Status", "Check", "Details"),
            "inspect-table": ("Variable / task", "Value / dependency"),
        }
        for ident, names in columns.items():
            table = self.main_query(f"#{ident}", DataTable)
            for name in names:
                table.add_column(name, width=16 if ident == "history" and name == "Operation" else None)
        self.main_query("#history", DataTable).border_title = "Persistent history"
        self.main_query("#log", RichLog).border_title = "Live stream"
        self.main_query("#task-monitor", Static).border_title = "Active BitBake tasks"
        self.set_interval(0.2, self.flush_log)
        self.set_interval(2, self.update_telemetry)
        self.analysis_fields()
        self.navigation_changed()
        self.update_telemetry()
        self.refresh_history()
        self.action_refresh()

    def action_command(self, action_id="build", target=None):
        target = target if target is not None else self.main_query("#target", Input).value
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
            self.main_query("#workspace", TabbedContent).active = "builds"
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
            selector = self.main_query("#profile", Select)
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
            self.main_query("#target", Input).value = self.profile.targets[0] if self.profile.targets else ""
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
        self.main_query("#overview", Static).update(
            f"{p.name.upper()}  /  {p.mode.upper()}  ·  MACHINE={p.machine or self.config_hints.get('MACHINE', '?')}  ·  DISTRO={p.distro or self.config_hints.get('DISTRO', '?')}\n"
            f"{p.root_path}  →  {p.build_dir}"
        )
        recent = next((r for r in self.history_rows.values() if r["profile"] == p.name), None)
        status = active.status.upper() if active else recent["status"].upper() if recent else "IDLE"
        title = active.title if active else recent["title"] if recent else "No jobs in this profile"
        color = "#df9a87" if status == "FAILED" else "#a6d9c8"
        metric = Text("BUILD STATUS\n", style="dim", no_wrap=True, overflow="ellipsis")
        metric.append(status + "\n", style=f"bold {color}")
        metric.append(title, style="#bdcbd2")
        self.main_query("#build-metric", Static).update(metric)
        progress = active.progress if active else json.loads(recent["metadata"]).get("progress", [0, 0]) if recent else [0, 0]
        tasks = f"{progress[0]} / {progress[1]}" if progress[1] else "No task count reported"
        self.main_query("#queue-metric", Static).update(Text.from_markup(
            f"[dim]TASKS / QUEUE[/dim]\n[bold #dfbe77]{tasks}[/]\n{queue} queued / {len(active.at_risk) if active else 0} running"))
        self.main_query("#rail-context", Static).update(
            f"RUNTIME\n{p.mode}\n\nPROFILE\n{p.name}\n\nF2  Command center\nF4  Edit profiles"
        )

    def action_section(self, tab):
        self.main_query("#workspace", TabbedContent).active = tab

    def on_resize(self, event):
        self.screen_stack[0].set_class(event.size.width < 130, "compact")
        self.screen_stack[0].set_class(event.size.width < 105, "narrow")

    @on(Button.Pressed, "#rail Button")
    def navigate(self, event):
        self.main_query("#workspace", TabbedContent).active = event.button.id[4:]

    @on(TabbedContent.TabActivated, "#workspace")
    def navigation_changed(self):
        active = self.main_query("#workspace", TabbedContent).active
        for button in self.screen_stack[0].query("#rail Button"):
            button.set_class(button.id == f"nav-{active}", "selected")

    @on(Button.Pressed, "#log-follow")
    def toggle_follow(self):
        self.follow_log = not self.follow_log
        self.main_query("#log-follow", Button).label = "Pause" if self.follow_log else "Resume"
        if self.follow_log:
            self.live_lines.clear()
            self.reload_log()

    def update_telemetry(self):
        # Host resources are explicitly labelled: a remote/container runtime may differ.
        try:
            values = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
            current = (sum(values[:8]), values[3] + values[4])
            cpu = "warming up"
            if self.resource_previous:
                delta = current[0] - self.resource_previous[0]
                usage = 100 * (1 - (current[1] - self.resource_previous[1]) / delta) if delta else 0
                cpu = f"{usage:.0f}% CPU"
            self.resource_previous = current
            mem = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
            ram = 100 * (1 - mem['MemAvailable'] / mem['MemTotal'])
            self.main_query("#resource-metric", Static).update(Text.from_markup(
                f"[dim]HOST RESOURCES[/dim]\n[bold #adc7fa]{cpu} · {ram:.0f}% RAM[/]\n{human_size((mem['MemTotal']-mem['MemAvailable'])*1024)} used"))
        except (OSError, ValueError, KeyError):
            self.main_query("#resource-metric", Static).update("HOST RESOURCES\nUnavailable on this host")
        try:
            disk = shutil.disk_usage(self.profile.root_path)
            self.main_query("#disk-metric", Static).update(Text.from_markup(
                f"[dim]WORKSPACE DISK[/dim]\n[bold #a6e3cb]{human_size(disk.free)} free[/]\n{100*disk.used/disk.total:.0f}% used · host filesystem"))
        except OSError:
            self.main_query("#disk-metric", Static).update("WORKSPACE DISK\nPath unavailable")
        active = self.runner.active
        tasks = list(active.active_recipe_tasks) if active else []
        self.main_query("#task-monitor", Static).update("\n".join(tasks[:7]) if tasks else "No observed active tasks\n\nTasks appear as BitBake reports\nStarted / Succeeded events.")
        self.main_query("#active-tasks", Static).update(
            "LIVE TASKS / CURRENT SESSION\n" + ("  ·  ".join(tasks[:8]) if tasks else "No observed active tasks")
        )
        self.update_overview()

    @on(DataTable.RowHighlighted, "#metadata-table")
    def preview_metadata(self, event):
        entry = self.metadata_rows.get(str(event.row_key.value))
        if entry:
            path = entry.path / "conf/layer.conf" if entry.kind == "layer" else entry.path
            self.read_preview(path)

    @work(exclusive=True, group="preview")
    async def read_preview(self, path):
        def read():
            with path.open(errors="replace") as source:
                return "".join(line for _, line in zip(range(200), source))
        try:
            content = await asyncio.to_thread(read)
        except OSError as exc:
            content = str(exc)
        preview = self.main_query("#source-preview", RichLog)
        preview.border_title = path.name
        preview.clear()
        preview.write(Syntax(content, "yaml" if path.suffix in {".yml", ".yaml"} else "bash", theme="nord", line_numbers=True, word_wrap=False))

    @work(exclusive=True, group="scan")
    async def scan_project(self):
        p = self.profile
        entries, logs, health, artifacts = await asyncio.gather(
            asyncio.to_thread(metadata, p), asyncio.to_thread(task_logs, p),
            asyncio.to_thread(diagnostics, p), asyncio.to_thread(self.find_artifacts, p),
        )
        self.entries, self.logs, self.artifacts = entries, logs, artifacts
        self.config_hints = await asyncio.to_thread(read_assignments, p.build_path / "conf/local.conf")
        self.update_overview()
        self.render_metadata()
        self.render_layer_tree()
        self.render_logs()
        self.render_artifacts()
        table = self.main_query("#health", DataTable)
        table.clear()
        for status, name, detail in health:
            table.add_row(Text(status, style={"OK": "green", "WARN": "yellow", "INFO": "cyan"}[status]), name, detail)
        self.main_query("#detail", Static).update(f"{len(entries)} local metadata entries. BitBake layer commands show evaluated configuration. Enter opens a file.")

    @staticmethod
    def find_artifacts(p):
        result = []
        for sub in ("tmp/deploy", "tmp/log", "tmp/buildstats", "buildhistory"):
            result.extend(inventory(p.build_path / sub, limit=4000))
        return sorted(result, key=lambda e: e.modified, reverse=True)

    def render_layer_tree(self):
        tree = self.main_query("#layer-tree", Tree)
        tree.clear()
        tree.show_root = False
        layers = sorted((e for e in self.entries if e.kind == "layer"), key=lambda e: len(e.path.parts), reverse=True)
        nodes = {str(e.path): tree.root.add(e.name, data=e, expand=False) for e in layers}
        layer_paths = {e.path: e for e in layers}
        other = tree.root.add("Workspace files", expand=True)
        for entry in self.entries:
            if entry.kind == "layer":
                continue
            layer = next((layer_paths[parent] for parent in entry.path.parents if parent in layer_paths), None)
            parent = nodes[str(layer.path)] if layer else other
            parent.add_leaf(entry.name, data=entry)
        if not other.children:
            other.remove()
        tree.root.expand()

    @on(Tree.NodeSelected, "#layer-tree")
    def layer_tree_selected(self, event):
        entry = event.node.data
        if isinstance(entry, Entry):
            self.main_query("#metadata-search", Input).value = str(entry.path) if entry.kind == "layer" else entry.name
            path = entry.path / "conf/layer.conf" if entry.kind == "layer" else entry.path
            self.read_preview(path)

    def render_metadata(self):
        query = self.main_query("#metadata-search", Input).value.casefold()
        table = self.main_query("#metadata-table", DataTable)
        table.clear()
        self.metadata_rows.clear()
        for i, e in enumerate(self.entries):
            if query in f"{e.name} {e.kind} {e.path}".casefold():
                key = f"meta-{i}"
                self.metadata_rows[key] = e
                table.add_row(e.name, e.kind, e.detail or str(e.path), key=key)

    def render_logs(self):
        query = self.main_query("#task-search", Input).value.casefold()
        table = self.main_query("#task-table", DataTable)
        table.clear()
        for i, e in enumerate(self.logs):
            if query in f"{e.name} {e.detail}".casefold():
                key = f"task-{i}"
                self.file_rows[key] = e
                table.add_row(e.detail, e.name, human_size(e.size), datetime.fromtimestamp(e.modified).strftime("%m-%d %H:%M"), key=key)

    def render_artifacts(self):
        query = self.main_query("#artifact-search", Input).value.casefold()
        table = self.main_query("#artifact-table", DataTable)
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
        table = self.main_query("#history", DataTable)
        cursor = table.cursor_row
        table.clear()
        self.history_rows.clear()
        for row in self.store.history():
            self.history_rows[row["id"]] = row
            status = row["status"]
            color = {"success": "green", "failed": "red", "running": "cyan", "queued": "yellow"}.get(status, "white")
            elapsed = "—"
            if status != "queued":
                start = datetime.fromisoformat(row["started"])
                end = datetime.fromisoformat(row["finished"]) if row["finished"] else datetime.now(timezone.utc)
                seconds = max(0, int((end-start).total_seconds()))
                elapsed = f"{seconds//3600:02}:{seconds//60%60:02}:{seconds%60:02}"
            table.add_row(row["title"], Text(status, style=color), elapsed, key=row["id"])
        if table.row_count:
            table.move_cursor(row=min(cursor, table.row_count-1))

    def job_update(self, job: Job, line: str | None):
        if line is not None:
            if job.id == self.selected_job_id and not self.errors_only and not self.main_query("#log-search", Input).value:
                if self.follow_log:
                    self.live_lines.append(line)
            if "ERROR:" in line:
                self.last_line = line
        else:
            self.refresh_history()
            self.update_overview()
            if job.status == "success" and job.action_id == "graph-read" and job.profile.name == self.profile.name:
                self.read_runtime_graph(job.log)
            if job.status == "failed":
                self.notify(f"{job.title} failed — open Errors only and Task logs", severity="error", timeout=8)
                self.scan_project()
            if job.id == self.selected_job_id:
                self.main_query("#job-state", Static).update(f"{job.title} · {job.status} · exit {job.code} · {job.log}")
        if job.id == self.selected_job_id and job.status == "success":
            self.main_query("#progress", ProgressBar).update(total=100, progress=100)
        elif job.id == self.selected_job_id and job.progress[1]:
            self.main_query("#progress", ProgressBar).update(total=job.progress[1], progress=job.progress[0])

    def flush_log(self):
        if self.live_lines and self.follow_log:
            log = self.main_query("#log", RichLog)
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
            progress = json.loads(row["metadata"]).get("progress", [0, 0])
            live = next((j for j in self.runner.jobs if j.id == ident), None)
            if live:
                progress = live.progress
            if row["status"] == "success":
                self.main_query("#progress", ProgressBar).update(total=100, progress=100)
            elif progress[1]:
                self.main_query("#progress", ProgressBar).update(total=progress[1], progress=progress[0])
            else:
                self.main_query("#progress", ProgressBar).update(total=100, progress=0)
            self.main_query("#job-state", Static).update(f"{row['title']} · {row['status']} · {path}")

    @work(exclusive=True, group="logread")
    async def reload_log(self):
        path = self.selected_log
        if not path:
            return
        query = self.main_query("#log-search", Input).value
        try:
            text = await asyncio.to_thread(search_log, path, query, self.errors_only)
        except OSError as exc:
            text = str(exc) if path.exists() else "Waiting for log output…"
        log = self.main_query("#log", RichLog)
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
            self.main_query("#workspace", TabbedContent).active = "builds"
            self.main_query("#job-state", Static).update(str(e.path))
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
        table = self.main_query("#metadata-table", DataTable)
        if not table.row_count:
            return None
        key = str(table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value)
        return self.metadata_rows.get(key)

    def selected_recipe(self):
        e = self.selected_entry()
        if e and e.kind in {"bb", "bbappend"}:
            return e.name.split("_", 1)[0].removesuffix(".bb").removesuffix(".bbappend")
        return self.main_query("#target", Input).value

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
        elif ident == "failed-task-log":
            self.read_failed_task()
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
        elif ident in {"inspect-diff", "buildhistory-report", "download-audit", "build-report", "dependency-context", "image-contents", "task-timings"}:
            self.make_report(ident)
        elif ident in {"logs-read", "artifact-read"}:
            table = self.main_query("#task-table" if ident == "logs-read" else "#artifact-table", DataTable)
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

    def read_failed_task(self):
        row = self.history_rows.get(self.selected_job_id)
        if not row:
            self.notify("Select a failed build in history first")
            return
        metadata = json.loads(row["metadata"])
        paths = metadata.get("failure_logs", [])
        if not paths:
            self.notify("No failure logfile path was reported by this build", severity="warning")
            return
        try:
            profile = Profile(**metadata["profile"])
            for path in paths[:10]:
                job = self.runner.submit(profile, "Failed task log: " + Path(path).name, ["cat", path], "custom")
            self.select_job(job.id, job.log)
            self.main_query("#workspace", TabbedContent).active = "builds"
        except (OSError, ValueError) as exc:
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
        kind = str(self.main_query("#cache-kind", Select).value)
        p = cache_path(self.profile, kind)
        self.main_query("#scan-state", Static).update(f"Scanning {p}…")
        entries = await asyncio.to_thread(inventory, p)
        if kind != str(self.main_query("#cache-kind", Select).value) or p != cache_path(self.profile, kind):
            return
        self.cache_entries = entries
        self.render_cache()
        self.main_query("#scan-state", Static).update(f"{p} · {len(entries)} files · {human_size(sum(e.size for e in entries))} · scan capped at 20,000 files")

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
        table = self.main_query("#cache-table", DataTable)
        query = self.main_query("#cache-search", Input).value.casefold()
        table.clear()
        for e in self.cache_entries:
            if query in str(e.path).casefold():
                table.add_row(e.name, human_size(e.size), f"{int((time.time()-e.modified)/86400)}d", e.detail)

    def prune_plan(self):
        if any(j.status in {"running", "queued", "cancelling"} for j in self.runner.jobs):
            self.notify("Stop or finish queued builds before pruning caches", severity="warning")
            return
        try:
            days = int(self.main_query("#cache-days", Input).value)
            if days < 1:
                raise ValueError("Age must be at least one day")
            entries = cache_candidates(self.cache_entries, days)
            root = cache_path(self.profile, str(self.main_query("#cache-kind", Select).value))
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
            kind = str(self.main_query("#inspect-kind", Select).value)
            if kind == "env":
                jobs = environment_jobs(self.store, self.profile, self.main_query("#target", Input).value)
                if not jobs:
                    raise ValueError("Resolve an environment first, then load its successful output")
                values = await asyncio.to_thread(environment, Path(jobs[0]["log"]))
                self.inspection_rows = sorted(values.items())
            else:
                path = self.profile.build_path / "task-depends.dot"
                if not path.exists() and self.profile.mode != "host":
                    job = self.runner.submit(self.profile, "Read runtime dependency graph", ["cat", "task-depends.dot"], "graph-read")
                    self.select_job(job.id, job.log)
                    self.notify("Reading task-depends.dot through the selected runtime")
                    return
                self.inspection_rows = await asyncio.to_thread(dependencies, path)
            self.render_inspection()
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="warning")

    @work(exclusive=True, group="runtime-graph")
    async def read_runtime_graph(self, path):
        from .reports import dependencies
        try:
            self.inspection_rows = await asyncio.to_thread(dependencies, path)
            self.render_inspection()
            self.notify(f"Loaded {len(self.inspection_rows)} runtime dependency edges")
        except OSError as exc:
            self.notify(str(exc), severity="warning")

    @on(Input.Changed, "#inspect-search")
    def inspection_filter(self):
        self.render_inspection()

    def render_inspection(self):
        query = self.main_query("#inspect-search", Input).value.casefold()
        table = self.main_query("#inspect-table", DataTable)
        table.clear()
        for name, value in self.inspection_rows:
            if query in f"{name} {value}".casefold():
                table.add_row(name, value)

    @work(exclusive=True, group="reports")
    async def make_report(self, ident):
        from .reports import build_history, build_summary, download_audit, environment, environment_jobs, env_diff, dependency_context, image_contents, task_timings
        try:
            if ident == "dependency-context":
                if str(self.main_query("#inspect-kind", Select).value) != "graph":
                    raise ValueError("Load a dependency graph first")
                text = dependency_context(self.inspection_rows, self.main_query("#inspect-search", Input).value.strip())
            elif ident == "image-contents":
                table = self.main_query("#artifact-table", DataTable)
                if not table.row_count:
                    raise ValueError("Select a rootfs tar archive first")
                key = str(table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value)
                text = await asyncio.to_thread(image_contents, self.file_rows[key].path)
            elif ident == "inspect-diff":
                jobs = environment_jobs(self.store, self.profile, self.main_query("#target", Input).value)
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
                text = await asyncio.to_thread(task_timings if ident == "task-timings" else build_summary, self.selected_log)
            dest = self.store.directory / "reports" / f"{ident}.txt"
            dest.parent.mkdir(exist_ok=True)
            dest.write_text(text)
            self.open_file(dest)
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="warning")

    @on(Select.Changed, "#analysis-kind")
    def analysis_fields(self):
        kind = str(self.main_query("#analysis-kind", Select).value)
        self.main_query("#analysis-query", Input).display = kind == "metadata"
        self.main_query("#analysis-paths").display = kind != "metadata"
        self.main_query("#analysis-second", Input).display = kind == "manifests"

    @on(Button.Pressed, "#analysis-run")
    @work(exclusive=True, group="analysis")
    async def run_analysis(self):
        from .analysis import metadata_search, manifest_diff, sstate_report, warning_report
        try:
            kind = str(self.main_query("#analysis-kind", Select).value)
            first = self.main_query("#analysis-first", Input).value.strip()
            second = self.main_query("#analysis-second", Input).value.strip()
            if kind == "metadata":
                text = await asyncio.to_thread(metadata_search, list(self.entries), self.main_query("#analysis-query", Input).value)
            elif kind == "manifests":
                if not first or not second:
                    raise ValueError("Enter both manifest paths, before then after")
                text = await asyncio.to_thread(manifest_diff, Path(first).expanduser(), Path(second).expanduser())
            else:
                path = Path(first).expanduser() if first else self.selected_log
                if path is None:
                    raise ValueError("Select a build log or enter its path")
                text = await asyncio.to_thread(sstate_report if kind == "sstate" else warning_report, path)
            self.analysis_text = text
            output = self.main_query("#analysis-output", RichLog)
            output.clear()
            output.write(Text(text))
            output.scroll_home(animate=False)
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="warning")

    @on(Button.Pressed, "#analysis-export")
    def export_analysis(self):
        if not self.analysis_text:
            self.notify("Run an analysis first", severity="warning")
            return
        destination = self.store.directory / "exports" / f"analysis-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.txt"
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(self.analysis_text)
        self.notify(f"Report exported to {destination}")

    def action_log_focus(self):
        self.main_query("#workspace", TabbedContent).active = "builds"
        self.main_query("#log-search", Input).focus()

    def action_stop_job(self):
        self.stop_build()

    def action_retry(self):
        self.retry_job()

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
        if job.profile.mode in {"kas", "kas-container"} or job.profile.container_name or not job.stop_confirmed:
            self.notify("Shutdown unconfirmed: verify all tasks have stopped before manually queuing clean.", severity="warning", timeout=12)
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
