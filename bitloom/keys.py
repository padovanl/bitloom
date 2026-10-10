"""Keyboard map: one source for bindings, the footer, the ? overlay and the docs."""
from __future__ import annotations

from textual.binding import Binding

# (pane id, number key, rail title, icon, group)
SECTIONS = [
    ("builds", "1", "Builds", "◈", "BUILD"),
    ("metadata", "2", "Recipes", "◇", "BUILD"),
    ("tasklogs", "3", "Task logs", "≋", "BUILD"),
    ("workbench", "4", "Environment", "⌕", "INSPECT"),
    ("caches", "5", "Caches", "▣", "INSPECT"),
    ("artifacts", "6", "Artifacts", "◉", "INSPECT"),
    ("analysis", "7", "Analysis", "∑", "INSPECT"),
    ("developer", "8", "Developer", "⚒", "DEVELOP"),
    ("healthtab", "9", "Configuration", "⚙", "WORKSPACE"),
    ("guide", "0", "Help", "?", "WORKSPACE"),
]
SECTION_TITLES = {ident: title for ident, _, title, _, _ in SECTIONS}

# Widget focused when a section opens, and the filter field that / focuses.
PRIMARY = {
    "builds": "#history", "metadata": "#metadata-table", "tasklogs": "#task-table",
    "workbench": "#inspect-table", "caches": "#cache-table", "artifacts": "#artifact-table",
    "analysis": "#analysis-output", "developer": "#dev-rows", "healthtab": "#health", "guide": "#help",
}
FILTERS = {
    "builds": "#log-search", "metadata": "#metadata-search", "tasklogs": "#task-search",
    "workbench": "#inspect-search", "caches": "#cache-search", "artifacts": "#artifact-search",
    "analysis": "#analysis-query", "developer": "#dev-recipe",
}

# Single-key actions per section: (key, action, footer label, button id or "").
# The button id lets each on-screen button show the same key as a hint.
SECTION_KEYS: dict[str, list[tuple[str, str, str, str]]] = {
    "builds": [
        ("s", "press('stop')", "Stop", "stop"), ("r", "press('retry')", "Retry", "retry"),
        ("e", "press('errors')", "Errors", "errors"), ("p", "press('log-follow')", "Pause", "log-follow"),
        ("x", "press('export')", "Export", "export"), ("i", "build_summary", "Summary", ""),
        ("f", "press('failed-task-log')", "Failed log", ""), ("c", "console_builds", "Console builds", "console-builds"),
    ],
    "metadata": [
        ("b", "press('recipe-build')", "Build", "recipe-build"), ("m", "press('recipe-modify')", "Modify", "recipe-modify"),
        ("l", "press('layer-actions')", "Layers", "layer-actions"), ("n", "press('new-file')", "New file", "new-file"),
        ("o", "open_metadata", "Open", ""), ("t", "focus('#layer-tree')", "Tree", ""),
    ],
    "tasklogs": [
        ("o", "press('logs-read')", "Open", "logs-read"), ("f", "press('failed-task-log')", "Failed log", "failed-task-log"),
    ],
    "workbench": [
        ("t", "toggle_select('#inspect-kind')", "Env/graph", ""), ("l", "press('inspect-load')", "Load", "inspect-load"),
        ("r", "press('inspect-resolve')", "Resolve", "inspect-resolve"), ("d", "press('inspect-diff')", "Diff", "inspect-diff"),
        ("g", "press('generate-graph')", "Graph", "generate-graph"), ("w", "press('dependency-context')", "Why", "dependency-context"),
        ("h", "press('buildhistory-report')", "History", "buildhistory-report"), ("a", "press('download-audit')", "Audit", "download-audit"),
        ("o", "press('build-report')", "Report", "build-report"), ("m", "press('task-timings')", "Timings", "task-timings"),
    ],
    "caches": [
        ("s", "press('cache-scan')", "Scan", "cache-scan"), ("t", "toggle_select('#cache-kind')", "DL/sstate", ""),
        ("p", "press('cache-prune')", "Prune plan", "cache-prune"), ("a", "press('fetch-all')", "Fetch all", "fetch-all"),
    ],
    "artifacts": [
        ("o", "press('artifact-read')", "Open", "artifact-read"), ("i", "press('image-contents')", "Rootfs", "image-contents"),
        ("m", "press('image-matrix')", "Image matrix", "image-matrix"),
    ],
    "analysis": [
        ("t", "open_select('#analysis-kind')", "Type", ""), ("a", "press('analysis-run')", "Analyze", "analysis-run"),
        ("x", "press('analysis-export')", "Export", "analysis-export"),
    ],
    "developer": [
        ("v", "open_select('#dev-view')", "View", ""), ("i", "press('dev-inspect')", "Inspect", "dev-inspect"),
        ("o", "press('dev-open')", "Open", "dev-open"), ("u", "open_select('#dev-operation')", "Operation", ""),
        ("r", "press('dev-execute')", "Run", "dev-execute"), ("c", "press('dev-capture')", "Capture", "dev-capture"),
        ("d", "press('dev-compare')", "Compare", "dev-compare"), ("n", "press('dev-scaffold')", "New layer", "dev-scaffold"),
        ("l", "press('dev-clone')", "Clone", "dev-clone"), ("h", "press('dev-devices')", "Devices", "dev-devices"),
    ],
    "healthtab": [
        ("l", "press('local-conf')", "local.conf", "local-conf"), ("y", "press('layers-conf')", "bblayers", "layers-conf"),
        ("e", "press('environment')", "bitbake -e", "environment"), ("d", "press('dev-status')", "devtool", "dev-status"),
        ("v", "press('versions')", "Versions", "versions"), ("n", "press('network-check')", "Network", "network-check"),
    ],
    "guide": [],
}

# Keys available everywhere on the main screen.
GLOBAL_KEYS = [
    ("1…9, 0", "Jump to a section (also Alt+number)"),
    ("[ / ]  F8 / F9", "Previous / next section"),
    ("Tab / Shift+Tab", "Move focus between fields, tables and logs"),
    ("/  or  Ctrl+W", "Focus the filter or search field of this section (nano: Where Is)"),
    ("Esc", "Leave a field and return to the section list"),
    ("Enter", "Open / select the highlighted row; run from a field"),
    ("↑ ↓  j / k", "Move down / up in tables, trees and logs"),
    ("Ctrl+Y / Ctrl+V", "Page up / page down (nano)"),
    ("t", "Edit the build target (when no section uses t)"),
    ("b", "Build the target (outside Recipes)"),
    ("P", "Switch profile"),
    ("F2", "Command center (all 69 operations)"),
    ("F3", "Refresh metadata, logs and diagnostics"),
    ("F4", "Edit profiles"),
    ("F5 / F6", "Stop / retry the selected job"),
    ("F7", "Themes"),
    ("F10", "Developer workbench"),
    ("Ctrl+L", "Search the build log"),
    ("Ctrl+P", "Command palette: sections, actions, operations"),
    ("?  F1  Ctrl+G", "This keyboard reference (nano: Get Help)"),
    ("Ctrl+Q / Ctrl+X", "Detach (service keeps running) / exit"),
]
DIALOG_KEYS = [
    ("Esc / Ctrl+X", "Close or cancel the dialog; in editors ^X asks before discarding changes"),
    ("Ctrl+O", "Write out: save files and profiles, confirm forms (Ctrl+S also works)"),
    ("Ctrl+W / Alt+W", "Editors: where is (search) / find next"),
    ("Ctrl+K / Ctrl+U", "Editors: cut the current line / uncut (paste)"),
    ("Ctrl+G", "Keyboard reference"),
    ("Enter", "Command center: queue the selected operation"),
    ("↑ / ↓", "Command center filter: choose the operation"),
    ("f / g / k", "Interruption dialog: finish, graceful stop, force"),
]


def sectional_actions() -> set[str]:
    """Action names that only run from the section that binds them."""
    from textual.actions import parse
    return {parse(bound)[1] for keys in SECTION_KEYS.values() for _, bound, _, _ in keys}


def section_bindings() -> list[Binding]:
    bindings = []
    for keys in SECTION_KEYS.values():
        for key, action, label, _ in keys:
            bindings.append(Binding(key, action, label))
    return bindings


def button_hints() -> dict[str, str]:
    return {button: key for keys in SECTION_KEYS.values() for key, _, _, button in keys if button}


def reference_markdown() -> str:
    lines = ["# Keyboard reference", "", "Bitloom is fully usable without a mouse. Section keys work while a table, tree or log has focus; typing in a field never triggers them.", "", "## Everywhere", "", "| Key | Action |", "| --- | --- |"]
    lines += [f"| `{key}` | {text} |" for key, text in GLOBAL_KEYS]
    for ident, number, title, _, _ in SECTIONS:
        keys = SECTION_KEYS.get(ident, [])
        if not keys:
            continue
        lines += ["", f"## {number} · {title}", "", "| Key | Action |", "| --- | --- |"]
        lines += [f"| `{key}` | {label} |" for key, _, label, _ in keys]
    lines += ["", "## Dialogs", "", "| Key | Action |", "| --- | --- |"]
    lines += [f"| `{key}` | {text} |" for key, text in DIALOG_KEYS]
    return "\n".join(lines) + "\n"
