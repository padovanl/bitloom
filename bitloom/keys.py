"""Keyboard map: one source for bindings, the footer, the ? overlay and the docs."""
from __future__ import annotations

from textual.binding import Binding

# (pane id, number key, rail title, icon, group)
SECTIONS = [
    ("builds", "1", "Builds", "◈", "BUILD"),
    ("metadata", "2", "Recipes", "◇", "BUILD"),
    ("tasklogs", "3", "Task logs", "≋", "BUILD"),
    ("workbench", "4", "Environment", "≡", "INSPECT"),
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
        ("x", "press('export')", "Export", "export"), ("i", "build_summary", "Summary", ""), ("d", "press('compare-runs')", "Compare", "compare-runs"),
        ("f", "press('failed-task-log')", "Failed log", ""), ("c", "console_builds", "Console builds", "console-builds"),
    ],
    "metadata": [
        ("b", "press('recipe-build')", "Build", "recipe-build"), ("m", "press('recipe-modify')", "Modify", "recipe-modify"),
        ("l", "press('layer-actions')", "Layers", "layer-actions"), ("n", "press('new-file')", "New file", "new-file"),
        ("o", "open_metadata", "Open", ""), ("t", "focus('#layer-tree')", "Tree", ""), ("c", "press('studio')", "Studio", "studio"),
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
        ("w", "press('work-usage')", "tmp/work usage", "work-usage"),
    ],
    "artifacts": [
        ("o", "press('artifact-read')", "Open", "artifact-read"), ("i", "press('image-contents')", "Rootfs", "image-contents"),
        ("m", "press('image-matrix')", "Image matrix", "image-matrix"), ("s", "press('sbom-report')", "SBOM quality", "sbom-report"),
        ("v", "press('vulnerabilities')", "Vulnerabilities", "vulnerabilities"),
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
        ("w", "press('projects')", "Projects", "projects"), ("o", "press('notifications')", "Notifications", "notifications"),
        ("s", "press('sbom-settings')", "SBOM settings", "sbom-settings"), ("c", "press('cra-report')", "CRA readiness", "cra-report"),
        ("l", "press('local-conf')", "local.conf", "local-conf"), ("y", "press('layers-conf')", "bblayers", "layers-conf"),
        ("e", "press('environment')", "bitbake -e", "environment"), ("d", "press('dev-status')", "devtool", "dev-status"),
        ("v", "press('versions')", "Versions", "versions"), ("n", "press('network-check')", "Network", "network-check"),
    ],
    "guide": [("c", "customize_keys", "Customise keys", "")],
}

# --- your own keys ------------------------------------------------------------------------------------------
# ~/.config/bitloom/keys.json: {"builds": {"Stop": "S", "Retry": "ctrl+r"}, "analysis": {"Analyze": "enter"}}
# Section keys can be changed; the global ones below are reserved so every section keeps working.
import json as _json
import os as _os
import re as _re
from pathlib import Path as _Path

DEFAULT_KEYS = {section: [row[0] for row in rows] for section, rows in SECTION_KEYS.items()}
RESERVED = {*"0123456789", "j", "k", "P", "slash", "question_mark", "escape", "enter", "tab", "space", "left_square_bracket", "right_square_bracket",
            "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
            *(f"f{n}" for n in range(1, 11)), *(f"ctrl+{c}" for c in "qxgwyvlpkoc"), *(f"alt+{n}" for n in "0123456789")}
KEY_NAME = _re.compile(r"^(?:[a-zA-Z]|(?:ctrl|alt)\+[a-z]|f1[12])$")


def keys_file() -> _Path:
    custom = _os.environ.get("BITLOOM_KEYS", "")
    if custom:
        return _Path(custom)
    return _Path(_os.environ.get("XDG_CONFIG_HOME", _Path.home() / ".config")) / "bitloom/keys.json"


def check_key(section: str, label: str, key: str, keys: dict | None = None) -> str:
    """Why this key cannot do that, or "" when it can."""
    rows = SECTION_KEYS.get(section)
    if rows is None:
        return f"unknown section {section}"
    if not any(row[2].lower() == label.lower() for row in rows):
        return f"{SECTION_TITLES.get(section, section)} has no action “{label}” ({', '.join(row[2] for row in rows)})"
    if key in RESERVED:
        return f"“{key}” is reserved for a key that works everywhere"
    if not KEY_NAME.match(key):
        return f"“{key}”: use a letter (s, S for Shift+s), ctrl+<letter>, alt+<letter>, f11 or f12"
    current = keys if keys is not None else {row[2].lower(): row[0] for row in rows}
    clash = next((other for other, bound in current.items() if bound == key and other != label.lower()), None)
    if clash:
        return f"“{key}” already does “{next(row[2] for row in rows if row[2].lower() == clash)}” in {SECTION_TITLES.get(section, section)}"
    return ""


def load_overrides(path: _Path | None = None) -> tuple[dict, list[str]]:
    path = path or keys_file()
    if _os.environ.get("BITLOOM_KEYS") == "default" or not path.is_file():
        return {}, []
    try:
        data = _json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return {}, [f"{path}: not valid JSON ({exc}); default keys used"]
    if not isinstance(data, dict) or not all(isinstance(v, dict) for v in data.values()):
        return {}, [f"{path}: expected {{\"section\": {{\"Action\": \"key\"}}}}; default keys used"]
    return data, []


def apply_overrides(data: dict) -> list[str]:
    """Change the section keys in place (bindings, footer, buttons and ? follow); refuse what would break a key."""
    errors = []
    for section, changes in data.items():
        rows = SECTION_KEYS.get(section)
        if rows is None:
            errors.append(f"unknown section “{section}” ({', '.join(SECTION_KEYS)})")
            continue
        keys = {row[2].lower(): row[0] for row in rows}
        for label, key in changes.items():
            reason = check_key(section, str(label), str(key), {**keys})
            if reason:
                errors.append(f"{section}: {label} → {key}: {reason}")
                continue
            keys[str(label).lower()] = str(key)
        SECTION_KEYS[section] = [(keys[row[2].lower()], *row[1:]) for row in rows]
    return errors


def save_override(section: str, label: str, key: str | None, path: _Path | None = None) -> None:
    """Set (or with None, reset) one key in the keys file."""
    path = path or keys_file()
    data, _ = load_overrides(path)
    changes = data.setdefault(section, {})
    canonical = next(row[2] for row in SECTION_KEYS[section] if row[2].lower() == label.lower())
    changes.pop(canonical, None)
    default = DEFAULT_KEYS[section][[row[2] for row in SECTION_KEYS[section]].index(canonical)]
    if key and key != default:
        changes[canonical] = key
    if not changes:
        data.pop(section)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(data, indent=2, sort_keys=True) + "\n")


OVERRIDE_ERRORS = apply_overrides(load_overrides()[0]) + load_overrides()[1]


def effective_table() -> list[tuple[str, str, str, str]]:
    """(section, action, key, default key) for every section key, as Bitloom uses them now."""
    return [(section, row[2], row[0], DEFAULT_KEYS[section][i]) for section, rows in SECTION_KEYS.items() for i, row in enumerate(rows)]


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
    ("↓ (in the target field)", "List the image recipes found in the project; type to filter, Enter picks. → accepts the inline suggestion. Same in the web dashboard."),
    ("b", "Build the target (outside Recipes)"),
    ("P", "Switch profile"),
    ("F2", "Command center (every operation, filtered as you type)"),
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
    ("Ctrl+A", "Guided setup: save every product of a launcher script as its own profile"),
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


FOOTER_KEYS = 6  # per section; the rest stay on the buttons and in the keyboard reference (?)


def section_bindings() -> list[Binding]:
    bindings = []
    for keys in SECTION_KEYS.values():
        for index, (key, action, label, _) in enumerate(keys):
            bindings.append(Binding(key, action, label, show=index < FOOTER_KEYS))
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
    lines += ["", "## Your own keys", "",
              "Every key in the section tables above can be changed. In the TUI open **Help (`0`) → `c`** (or Ctrl+P → *Customise keys*), "
              "select an action, press `Enter`, then the new key: a letter (Shift for capitals), Ctrl or Alt with a letter, F11 or F12. "
              "`r` resets one, `R` resets all. Bitloom refuses a key that another action of the same section already uses, and the keys that "
              "work everywhere (numbers, `j`/`k`, `/`, `?`, `[`/`]`, `P`, F1–F10, the nano Ctrl keys). The new keys apply from the next start "
              "(Ctrl+Q detaches; builds keep running); buttons, the footer and `?` show them.", "",
              "They are saved in `~/.config/bitloom/keys.json` (or the file named by `BITLOOM_KEYS`), which you can also edit or share:", "",
              "```json", '{"builds": {"Stop": "S", "Retry": "ctrl+r"}, "analysis": {"Analyze": "A"}}', "```", "",
              "`bitloom --keys` prints the keys in use and why any were refused (exit status 1 when one was); the TUI says it at start.", "",
              "![Customise keys: Stop moved to S, a reserved key refused](assets/custom-keys.png)"]
    return "\n".join(lines) + "\n"
