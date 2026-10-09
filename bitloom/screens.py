from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from .commands import ACTIONS, Action, arguments, invocation
from .models import Profile, Settings


class ActionScreen(ModalScreen):
    DEFAULT_CSS = """
    ActionScreen { align: center middle; background: $background 70%; }
    ActionScreen > Vertical { width: 88; max-height: 90%; border: round $accent; padding: 1 2; background: $surface; }
    ActionScreen Input, ActionScreen Select { margin-bottom: 1; }
    ActionScreen #preview { height: auto; max-height: 6; color: $text-muted; margin: 1 0; }
    ActionScreen Horizontal { height: 3; }
    """
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, profile: Profile, action_id="build", target=""):
        super().__init__()
        self.profile = profile
        self.initial_action = action_id
        self.target = target

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold cyan]COMMAND CENTER[/]  ·  queue a Yocto operation")
            yield Input(placeholder="Filter commands by operation or group…", id="action-search")
            yield Select([(f"{a.group} / {a.title}", a.id) for a in ACTIONS], value=self.initial_action, allow_blank=False, id="action")
            with VerticalScroll(id="fields"):
                for key in ("target", "task", "path", "path2", "variable", "device", "source", "command"):
                    yield Input(value=self.target if key == "target" else "", placeholder=key, id=f"field-{key}")
            yield Static(id="preview", markup=False)
            with Horizontal():
                yield Button("Queue / Run", variant="primary", id="submit")
                yield Button("Close", id="close")

    def on_mount(self):
        self.update_fields()

    @on(Input.Changed, "#action-search")
    def filter_actions(self, event):
        query = event.value.casefold()
        matches = [a for a in ACTIONS if query in f"{a.group} {a.title} {a.id}".casefold()]
        if not matches:
            return
        select = self.query_one("#action", Select)
        previous = str(select.value)
        select.set_options([(f"{a.group} / {a.title}", a.id) for a in matches])
        select.value = previous if previous in {a.id for a in matches} else matches[0].id

    @on(Select.Changed, "#action")
    def action_changed(self):
        self.update_fields()

    @on(Input.Changed)
    def values_changed(self):
        self.update_preview()

    def selected(self) -> Action:
        from .commands import BY_ID
        value = str(self.query_one("#action", Select).value)
        return BY_ID.get(value, BY_ID[self.initial_action])

    def values(self):
        return {key: self.query_one(f"#field-{key}", Input).value for key in self.selected().inputs}

    def update_fields(self):
        action = self.selected()
        for field in self.query("#fields Input"):
            field.display = field.id.removeprefix("field-") in action.inputs
        self.update_preview()

    def update_preview(self):
        try:
            a = self.selected()
            inv = invocation(self.profile, arguments(a, self.values()))
            text = inv.display
            if a.help:
                text += "\n" + a.help
        except ValueError as exc:
            text = str(exc)
        self.query_one("#preview", Static).update(text)

    @on(Button.Pressed, "#submit")
    def submit(self):
        try:
            action = self.selected()
            argv = arguments(action, self.values())
            invocation(self.profile, argv)
            self.dismiss((action, argv))
        except ValueError as exc:
            self.notify(str(exc), severity="error")

    @on(Button.Pressed, "#close")
    def close(self):
        self.dismiss(None)


class ProfilesScreen(ModalScreen):
    DEFAULT_CSS = """
    ProfilesScreen { align: center middle; }
    ProfilesScreen > Vertical { width: 100; height: 90%; border: round $accent; padding: 1 2; background: $surface; }
    ProfilesScreen TextArea { height: 1fr; }
    ProfilesScreen Horizontal { height: 3; margin-top: 1; }
    """
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

    def compose(self):
        with Vertical():
            yield Label("[bold cyan]PROFILES[/]  ·  host / kas / container / kas-container")
            yield Label("Edit JSON. Duplicate a profile with a new name; choose it with the top selector.")
            yield TextArea(json.dumps({"active": self.settings.active, "profiles": [asdict(p) for p in self.settings.profiles]}, indent=2), id="json")
            with Horizontal():
                yield Button("Save profiles", variant="primary", id="save")
                yield Button("Close", id="close")

    @on(Button.Pressed, "#save")
    def save(self):
        try:
            data = json.loads(self.query_one("#json", TextArea).text)
            profiles = [Profile(**p) for p in data["profiles"]]
            if not profiles or data["active"] not in {p.name for p in profiles}:
                raise ValueError("Active profile must exist")
            if len({p.name for p in profiles}) != len(profiles):
                raise ValueError("Profile names must be unique")
            for p in profiles:
                p.validate()
            old_profiles, old_active = self.settings.profiles, self.settings.active
            self.settings.profiles, self.settings.active = profiles, data["active"]
            try:
                self.settings.save()
            except Exception:
                self.settings.profiles, self.settings.active = old_profiles, old_active
                raise
            self.dismiss(True)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            self.notify(str(exc), severity="error")

    @on(Button.Pressed, "#close")
    def close(self):
        self.dismiss(False)


class FileScreen(ModalScreen):
    DEFAULT_CSS = """
    FileScreen { align: center middle; }
    FileScreen > Vertical { width: 95%; height: 92%; padding: 1; border: round $accent; background: $surface; }
    FileScreen TextArea { height: 1fr; }
    FileScreen Horizontal { height: 3; }
    """
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, path: Path, editable=False):
        super().__init__()
        self.path = path
        self.editable = editable
        self.original = path.read_text(errors="replace") if path.exists() else ""

    def compose(self):
        with Vertical():
            yield Label(str(self.path), markup=False)
            yield TextArea(self.original[:2_000_000], read_only=not self.editable, id="content", show_line_numbers=True)
            with Horizontal():
                if self.editable:
                    yield Button("Save + backup", variant="primary", id="save")
                yield Button("Close", id="close")

    @on(Button.Pressed, "#save")
    def save(self):
        try:
            import datetime
            text = self.query_one("#content", TextArea).text
            if self.path.exists() and self.path.read_text(errors="replace") != self.original:
                raise ValueError("File changed externally. Reopen before saving.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                self.path.with_name(self.path.name + ".bak-" + stamp).write_text(self.original)
            temp = self.path.with_name(self.path.name + ".bitloom-tmp")
            temp.write_text(text)
            if self.path.exists():
                temp.chmod(self.path.stat().st_mode)
            temp.replace(self.path)
            self.original = text
            self.notify("Saved with backup")
        except (ValueError, OSError) as exc:
            self.notify(str(exc), severity="error")

    @on(Button.Pressed, "#close")
    def close(self):
        self.dismiss(None)


class PruneScreen(ModalScreen):
    DEFAULT_CSS = """
    PruneScreen { align: center middle; }
    PruneScreen > Vertical { width: 85; height: auto; max-height: 85%; padding: 1 2; border: round $warning; background: $surface; }
    PruneScreen TextArea { height: 14; }
    PruneScreen Horizontal { height: 3; margin-top: 1; }
    """
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, root: Path, entries):
        super().__init__()
        self.root, self.entries = root, entries

    def compose(self):
        from .inspectors import human_size
        with Vertical():
            yield Label("[bold yellow]CACHE PRUNE PLAN[/]")
            yield Label(f"{len(self.entries)} files · {human_size(sum(e.size for e in self.entries))}")
            yield Label("Only listed stale files. Locks and .done markers excluded. Stop other builders using this cache first.")
            yield TextArea("\n".join(str(e.path) for e in self.entries[:1000]), read_only=True)
            with Horizontal():
                yield Button("Execute plan", variant="warning", id="execute")
                yield Button("Close", id="close")

    @on(Button.Pressed, "#execute")
    def execute(self):
        self.dismiss(True)

    @on(Button.Pressed, "#close")
    def close(self):
        self.dismiss(False)


class RuntimeFileScreen(ModalScreen):
    """Edit runtime files with optimistic concurrency and a preserved backup."""
    DEFAULT_CSS = FileScreen.DEFAULT_CSS.replace('FileScreen', 'RuntimeFileScreen')
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, profile, data):
        super().__init__()
        self.profile, self.data = profile, data

    def compose(self):
        with Vertical():
            yield Label(self.data['path'], markup=False)
            yield TextArea(self.data['text'], id='content', show_line_numbers=True)
            with Horizontal():
                yield Button('Save + backup', id='save', variant='primary')
                yield Button('Close', id='close')

    @on(Button.Pressed, '#save')
    async def save(self):
        from .runtime import request
        try:
            if self.app.runner.active or any(j.status == 'queued' for j in self.app.runner.jobs):
                raise ValueError('Wait for queued and running jobs before editing runtime configuration')
            text = self.query_one('#content', TextArea).text
            result = await request(self.profile, 'write', self.data['path'], sha256=self.data['sha256'], text=text)
            import hashlib
            self.data['sha256'] = hashlib.sha256(text.encode()).hexdigest()
            self.notify('Saved. Backup: ' + result['backup'])
            self.app.scan_project()
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity='error')

    @on(Button.Pressed, '#close')
    def close(self):
        self.dismiss(None)


class ThemeScreen(ModalScreen):
    DEFAULT_CSS = """
    ThemeScreen { align: center middle; }
    ThemeScreen > Vertical { width: 64; height: auto; padding: 1 2; border: solid $accent; background: $surface; }
    ThemeScreen Select { height: 3; margin: 1 0; }
    ThemeScreen Horizontal { height: 3; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self):
        super().__init__()
        self.original = None

    def compose(self):
        from .themes import THEMES
        self.original = self.app.theme
        with Vertical():
            yield Label('BITLOOM THEMES')
            yield Label('Preview a palette. Save keeps it for future sessions.')
            choices = [(name, name) for name in THEMES]
            if self.original not in THEMES:
                choices.insert(0, (self.original, self.original))
            yield Select(choices, value=self.original, allow_blank=False, id='theme-choice')
            yield Label('Build status, warnings and errors retain semantic colors.')
            with Horizontal():
                yield Button('Save theme', id='theme-save', variant='primary')
                yield Button('Cancel', id='theme-cancel')

    @on(Select.Changed, '#theme-choice')
    def preview(self, event):
        if isinstance(event.value, str):
            self.app.theme = event.value
            self.app.refresh_theme_colors()

    @on(Button.Pressed, '#theme-save')
    def save(self):
        try:
            self.app.save_theme()
            self.dismiss(True)
        except OSError as exc:
            self.notify(str(exc), severity='error')

    @on(Button.Pressed, '#theme-cancel')
    def action_cancel(self):
        self.app.theme = self.original
        self.app.refresh_theme_colors()
        self.dismiss(False)


class NewFileScreen(ModalScreen):
    """Create a file in the selected runtime without replacing existing data."""
    DEFAULT_CSS = """
    NewFileScreen { align: center middle; }
    NewFileScreen > Vertical { width: 95%; height: 90%; border: solid $accent; padding: 1; background: $surface; }
    NewFileScreen TextArea { height: 1fr; }
    NewFileScreen Horizontal { height: 3; }
    NewFileScreen Input, NewFileScreen Select { height: 3; }
    """
    BINDINGS = [('escape','dismiss','Cancel')]

    def __init__(self,profile):
        super().__init__()
        self.profile=profile

    def compose(self):
        with Vertical():
            yield Label('NEW FILE · selected profile runtime · missing parent folders are created')
            yield Input(placeholder='Absolute runtime path, e.g. /work/meta-custom/recipes-example/hello/hello_1.0.bb',id='new-path')
            yield Select([('Empty text file','text'),('Private example recipe','recipe'),('Recipe append','append')],value='text',allow_blank=False,id='new-template')
            yield TextArea('',id='new-content',show_line_numbers=True)
            with Horizontal():
                yield Button('Create file',id='create-file',variant='primary')
                yield Button('Cancel',id='cancel-new')

    @on(Select.Changed,'#new-template')
    def template(self,event):
        samples={'text':'','recipe':'SUMMARY = "My recipe"\nLICENSE = "CLOSED"\nS = "${WORKDIR}"\n\ndo_install() {\n    install -d ${D}${datadir}/${BPN}\n    echo "Hello" > ${D}${datadir}/${BPN}/message.txt\n}\n','append':'# Extend an existing recipe using a matching .bbappend filename.\nSUMMARY:append = " (customized)"\n'}
        if event.value in samples:
            self.query_one('#new-content',TextArea).load_text(samples[event.value])

    @on(Button.Pressed,'#create-file')
    async def create(self):
        from .runtime import request
        try:
            if self.app.runner.active or any(j.status=='queued' for j in self.app.runner.jobs):
                raise ValueError('Wait for queued and running jobs before creating metadata')
            path=self.query_one('#new-path',Input).value.strip()
            if not Path(path).is_absolute():
                raise ValueError('Enter an absolute path in the selected runtime')
            result=await request(self.profile,'create',path,text=self.query_one('#new-content',TextArea).text)
            self.dismiss(result)
        except (OSError,ValueError) as exc:
            self.notify(str(exc),severity='error')

    @on(Button.Pressed,'#cancel-new')
    def cancel(self):
        self.dismiss(None)
