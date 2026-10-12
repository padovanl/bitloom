from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from textual import on, work
from textual.binding import Binding
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Markdown, OptionList, Select, Static, TextArea
from textual.widgets.option_list import Option

from .toolbar import ToolBar
from .commands import ACTIONS, Action, arguments, invocation
from .models import Profile, Settings


class FindBar(Input):
    """nano-style "Where Is" prompt; Esc returns to the editor."""
    BINDINGS = [("escape", "close", "Cancel")]

    def action_close(self):
        self.display = False
        self.screen.editor().focus()


class NanoEditor:
    """nano keys for editor dialogs: ^O write, ^X exit, ^W where is, ^K cut, ^U uncut, ^G help."""
    EDITOR = "#content"
    NANO_BINDINGS = [
        Binding("ctrl+o", "save", "Write out", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True, show=False),
        Binding("ctrl+x", "nano_exit", "Exit", priority=True),
        Binding("ctrl+w", "where_is", "Where is", priority=True),
        Binding("alt+w", "find_next", "Next", priority=True, show=False),
        Binding("ctrl+k", "cut_line", "Cut line", priority=True),
        Binding("ctrl+u", "uncut", "Uncut", priority=True),
        Binding("ctrl+g", "app.keys", "Help", priority=True),
    ]
    _nano_baseline = None
    _nano_query = ""
    _nano_cut = ""
    _nano_last_cut_row = None
    _nano_exit_armed = False

    def editor(self) -> TextArea:
        return self.query_one(self.EDITOR, TextArea)

    def nano_ready(self):
        self._nano_baseline = self.editor().text
        bar = FindBar(placeholder="Search (Enter finds, Esc cancels)", id="find-bar")
        bar.display = False
        self.query_one(Vertical).mount(bar)

    def nano_saved(self):
        self._nano_baseline = self.editor().text
        self._nano_exit_armed = False

    def action_nano_exit(self):
        if self._nano_baseline is not None and self.editor().text != self._nano_baseline and not self.editor().read_only and not self._nano_exit_armed:
            self._nano_exit_armed = True
            self.notify("Modified buffer not saved: ^O writes it, ^X again discards the changes", severity="warning", timeout=8)
            return
        self.dismiss(None)

    def action_where_is(self):
        bar = self.query_one("#find-bar", FindBar)
        bar.value = self._nano_query
        bar.display = True
        bar.focus()

    def on_input_submitted(self, event):
        # A plain handler name: @on is not collected from non-widget mixins.
        if event.input.id != "find-bar":
            return
        event.stop()
        self._nano_query = event.value
        event.input.display = False
        self.editor().focus()
        self.action_find_next()

    def action_find_next(self):
        query = self._nano_query.casefold()
        if not query:
            self.action_where_is()
            return
        editor = self.editor()
        lines = editor.text.split("\n")
        row, column = editor.selection.end
        order = list(range(row, len(lines))) + list(range(0, row + 1))
        for index, number in enumerate(order):
            start = column if index == 0 else 0
            found = lines[number].casefold().find(query, start)
            if index == len(order) - 1 and number == row and found >= column:
                found = -1 if index else found
            if found >= 0:
                from textual.widgets.text_area import Selection
                editor.selection = Selection((number, found), (number, found + len(query)))
                editor.scroll_cursor_visible()
                if index and number <= row:
                    self.notify("Search wrapped", timeout=2)
                return
        self.notify(f'"{self._nano_query}" not found', severity="warning", timeout=3)

    def action_cut_line(self):
        editor = self.editor()
        if editor.read_only:
            return
        row = editor.cursor_location[0]
        count = editor.document.line_count
        line = editor.document.get_line(row)
        # Consecutive ^K presses accumulate, like nano's cut buffer.
        if self._nano_last_cut_row != row:
            self._nano_cut = ""
        self._nano_cut += line + "\n"
        if row + 1 < count:
            editor.delete((row, 0), (row + 1, 0))
        else:
            editor.delete((row, 0), (row, len(line)))
        editor.move_cursor((min(row, editor.document.line_count - 1), 0))
        self._nano_last_cut_row = row

    def action_uncut(self):
        editor = self.editor()
        if editor.read_only or not self._nano_cut:
            return
        row = editor.cursor_location[0]
        editor.insert(self._nano_cut, (row, 0))
        self._nano_last_cut_row = None


class ActionScreen(ModalScreen):
    DEFAULT_CSS = """
    ActionScreen { align: center middle; background: $background 70%; }
    ActionScreen > Vertical { width: 88; max-height: 90%; border: round $accent; border-title-color: $accent; border-title-style: bold; padding: 1 2; background: $surface; }
    ActionScreen #hint { color: $text-muted; margin-bottom: 1; }
    ActionScreen Input, ActionScreen Select { margin-bottom: 1; }
    ActionScreen #preview { height: auto; max-height: 6; color: $text-muted; margin: 1 0; }
    ActionScreen Horizontal { height: 3; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True), Binding("ctrl+g", "app.keys", "Help", priority=True)]

    def __init__(self, profile: Profile, action_id="build", target=""):
        super().__init__()
        self.profile = profile
        self.initial_action = action_id
        self.target = target

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[dim]Type to filter · [b]↑ ↓[/b] choose · [b]Tab[/b] fields · [b]Enter[/b] queue · [b]Esc[/b] close[/]", id="hint")
            yield Input(placeholder="Filter commands by operation or group…", id="action-search")
            yield Select([(self.option_label(a), a.id) for a in ACTIONS], value=self.initial_action, allow_blank=False, id="action")
            with VerticalScroll(id="fields", can_focus=False):
                for key in ("target", "task", "path", "path2", "variable", "device", "source", "command"):
                    yield Input(value=self.target if key == "target" else "", placeholder=key, id=f"field-{key}")
            yield Static(id="preview", markup=False)
            with Horizontal():
                yield Button("Queue / Run", variant="primary", id="submit")
                yield Button("Close", id="close")

    def on_mount(self):
        self.query_one(Vertical).border_title = "Command center"
        self.update_fields()
        self.query_one("#action-search", Input).focus()

    def on_key(self, event):
        # Arrow keys in the filter choose the operation without leaving the field.
        if event.key in {"up", "down"} and self.focused is self.query_one("#action-search", Input):
            select = self.query_one("#action", Select)
            values = [value for _, value in select._options if value is not Select.BLANK]
            if values:
                index = values.index(select.value) if select.value in values else 0
                select.value = values[(index + (1 if event.key == "down" else -1)) % len(values)]
            event.stop()
            event.prevent_default()

    @on(Input.Submitted)
    def submitted(self, event):
        event.stop()
        if not self.query_one("#submit", Button).disabled:
            self.submit()

    @on(Input.Changed, "#action-search")
    def filter_actions(self, event):
        query = event.value.casefold()
        matches = [a for a in ACTIONS if query in f"{a.group} {a.title} {a.id}".casefold()]
        if not matches:
            return
        select = self.query_one("#action", Select)
        previous = str(select.value)
        select.set_options([(self.option_label(a), a.id) for a in matches])
        select.value = previous if previous in {a.id for a in matches} else matches[0].id

    @on(Select.Changed, "#action")
    def action_changed(self):
        self.update_fields()

    @on(Input.Changed)
    def values_changed(self):
        self.update_preview()

    def option_label(self, action):
        from .commands import availability
        ok, _ = availability(action, getattr(self.app, 'release', None))
        return f"{action.group} / {action.title}" + ("  (not in this release)" if ok is False else "")

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
        submit = self.query_one('#submit', Button)
        submit.disabled = False
        try:
            a = self.selected()
            inv = invocation(self.profile, arguments(a, self.values()))
            text = inv.display
            if a.help:
                text += "\n" + a.help
            from .commands import availability
            from .versions import describe
            release = getattr(self.app, 'release', None)
            ok, reason = availability(a, release)
            if ok is False:
                submit.disabled = True
                text += '\n✖ Not available: ' + reason
            elif a.since or a.until:
                text += '\n✔ Available in ' + describe(release) if ok else '\n? ' + reason
            cap = getattr(self.app, 'capability_cache', {}).get((self.profile.name, self.values().get('target', '')))
            import time
            if cap and time.time() - cap.get('captured', 0) > 30: cap = None
            if a.task and cap and a.task not in cap.get('tasks', []):
                submit.disabled = True
                text += '\nUnavailable in the probed runtime: ' + a.task
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


class ProfilesScreen(NanoEditor, ModalScreen):
    DEFAULT_CSS = """
    ProfilesScreen { align: center middle; }
    ProfilesScreen > Vertical { width: 100; height: 90%; border: round $accent; border-title-color: $accent; border-title-style: bold; padding: 1 2; background: $surface; }
    ProfilesScreen TextArea { height: 1fr; }
    ProfilesScreen Horizontal { height: 3; margin-top: 1; }
    """
    EDITOR = "#json"
    BINDINGS = [("escape", "dismiss", "Close"), *NanoEditor.NANO_BINDINGS]

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

    def compose(self):
        with Vertical():
            yield Label("Modes: host · kas · container · kas-container · wrapper (project launcher script). Edit the JSON; [b]^O[/b] saves, [b]^X[/b] exits, [b]^W[/b] searches, [b]P[/b] on the main screen switches profile.")
            if self.settings.shared:
                yield Label("[dim]Read-only team profiles from include files: " + ", ".join(sorted(self.settings.shared)) + " · clone one to customise it[/]")
            yield TextArea(self.document(), id="json")
            with Horizontal():
                yield Button("Save profiles", variant="primary", id="save")
                yield Button("Clone profile", id="profiles-clone")
                yield Button("Close", id="close")

    @on(Button.Pressed, "#profiles-clone")
    def clone(self):
        from .developer_ui import CloneProfileScreen
        self.app.push_screen(CloneProfileScreen(self.settings), self.clone_result)

    def document(self):
        data = {"active": self.settings.active, "include": self.settings.include, "profiles": [asdict(p) for p in self.settings.own_profiles]}
        return json.dumps(data, indent=2)

    def clone_result(self, result):
        if result:
            self.query_one('#json', TextArea).load_text(self.document())
            self.app.profiles_result(True)

    def on_mount(self):
        self.query_one(Vertical).border_title = "Profiles"
        self.query_one("#json", TextArea).focus()
        self.nano_ready()

    def action_save(self):
        self.save()

    @on(Button.Pressed, "#save")
    def save(self):
        try:
            data = json.loads(self.query_one("#json", TextArea).text)
            profiles = [Profile(**p) for p in data["profiles"]]
            include = data.get("include", [])
            if not isinstance(include, list) or any(not isinstance(i, str) for i in include):
                raise ValueError("include must be an array of file paths")
            for p in profiles:
                p.validate()
            old = self.settings.profiles, self.settings.active, self.settings.include, self.settings.shared
            self.settings.profiles, self.settings.include, self.settings.shared = profiles, include, {}
            self.settings.load_shared()
            names = [p.name for p in self.settings.profiles]
            try:
                if not names or data["active"] not in names:
                    raise ValueError("Active profile must exist (personal or included)")
                if len(set(names)) != len(names):
                    raise ValueError("Profile names must be unique")
                self.settings.active = data["active"]
                self.settings.save()
            except Exception:
                self.settings.profiles, self.settings.active, self.settings.include, self.settings.shared = old
                raise
            self.dismiss(True)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            self.notify(str(exc), severity="error")

    @on(Button.Pressed, "#close")
    def close(self):
        self.dismiss(False)


class FileScreen(NanoEditor, ModalScreen):
    DEFAULT_CSS = """
    FileScreen { align: center middle; }
    FileScreen > Vertical { width: 95%; height: 92%; padding: 0 1; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; }
    FileScreen #file-hint { color: $text-muted; height: 1; }
    FileScreen TextArea { height: 1fr; }
    FileScreen Horizontal { height: 3; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), *NanoEditor.NANO_BINDINGS]

    def __init__(self, path: Path, editable=False):
        super().__init__()
        self.path = path
        self.editable = editable
        self.original = path.read_text(errors="replace") if path.exists() else ""

    def compose(self):
        with Vertical():
            yield Label(("^O write with backup · ^K cut line · ^U uncut · " if self.editable else "Read only · ") + "^W search · ^X exit · ^G help", id="file-hint")
            yield TextArea(self.original[:2_000_000], read_only=not self.editable, id="content", show_line_numbers=True)
            with Horizontal():
                if self.editable:
                    yield Button("Save + backup", variant="primary", id="save")
                yield Button("Close", id="close")

    def on_mount(self):
        self.query_one(Vertical).border_title = str(self.path)
        self.query_one("#content", TextArea).focus()
        self.nano_ready()

    def action_save(self):
        if self.editable:
            self.save()

    @on(Button.Pressed, "#save")
    def save(self):
        from .leases import BuildLease
        lease = BuildLease(self.app.profile)
        try:
            if self.app.runner.active or any(j.status == 'queued' for j in self.app.runner.jobs) or getattr(self.app, 'developer_busy', False):
                raise ValueError('Wait for the build queue and Developer probe before editing metadata')
            lease.acquire()
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
            self.nano_saved()
            self.app.capability_cache.clear()
            self.notify("Saved with backup")
        except (ValueError, OSError) as exc:
            self.notify(str(exc), severity="error")
        finally:
            lease.close()

    @on(Button.Pressed, "#close")
    def close(self):
        self.dismiss(None)


class PruneScreen(ModalScreen):
    DEFAULT_CSS = """
    PruneScreen { align: center middle; }
    PruneScreen > Vertical { width: 85; height: auto; max-height: 85%; padding: 1 2; border: round $warning; border-title-color: $warning; border-title-style: bold; background: $surface; }
    PruneScreen TextArea { height: 14; }
    PruneScreen Horizontal { height: 3; margin-top: 1; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True)]

    def __init__(self, root: Path, entries):
        super().__init__()
        self.root, self.entries = root, entries

    def compose(self):
        from .inspectors import human_size
        with Vertical():
            yield Label(f"{len(self.entries)} files · {human_size(sum(e.size for e in self.entries))}")
            yield Label("Only listed stale files. Locks and .done markers excluded. Stop other builders using this cache first.")
            yield TextArea("\n".join(str(e.path) for e in self.entries[:1000]), read_only=True)
            with Horizontal():
                yield Button("Execute plan", variant="warning", id="execute")
                yield Button("Close", id="close")

    def on_mount(self):
        self.query_one(Vertical).border_title = "Cache prune plan"
        self.query_one("#close", Button).focus()

    @on(Button.Pressed, "#execute")
    def execute(self):
        self.dismiss(True)

    @on(Button.Pressed, "#close")
    def close(self):
        self.dismiss(False)


class RuntimeFileScreen(NanoEditor, ModalScreen):
    """Edit runtime files with optimistic concurrency and a preserved backup."""
    DEFAULT_CSS = FileScreen.DEFAULT_CSS.replace('FileScreen', 'RuntimeFileScreen')
    BINDINGS = [("escape", "dismiss", "Close"), *NanoEditor.NANO_BINDINGS]

    def __init__(self, profile, data, editable=True, line=1):
        super().__init__()
        self.profile, self.data = profile, data
        self.editable, self.line = editable, line

    def compose(self):
        with Vertical():
            yield Label(('^O write with hash check and backup · ^K cut line · ^U uncut · ' if self.editable else 'Read only · ') + '^W search · ^X exit · ^G help', id='file-hint')
            yield TextArea(self.data['text'], id='content', show_line_numbers=True, read_only=not self.editable)
            with Horizontal():
                if self.editable:
                    yield Button('Save + backup', id='save', variant='primary')
                yield Button('Close', id='close')

    def on_mount(self):
        self.query_one(Vertical).border_title = self.data['path']
        editor = self.query_one('#content', TextArea)
        editor.move_cursor((max(0, min(self.line - 1, len(self.data['text'].splitlines()) - 1)), 0))
        editor.scroll_cursor_visible()
        editor.focus()
        self.nano_ready()

    async def action_save(self):
        if self.editable:
            await self.save()

    @on(Button.Pressed, '#save')
    async def save(self):
        from .runtime import request
        from .leases import BuildLease
        lease = BuildLease(self.profile)
        try:
            if self.app.runner.active or any(j.status == 'queued' for j in self.app.runner.jobs) or getattr(self.app, 'developer_busy', False):
                raise ValueError('Wait for queued and running jobs before editing runtime configuration')
            text = self.query_one('#content', TextArea).text
            lease.acquire()
            result = await request(self.profile, 'write', self.data['path'], sha256=self.data['sha256'], text=text)
            import hashlib
            self.data['sha256'] = hashlib.sha256(text.encode()).hexdigest()
            self.nano_saved()
            self.notify('Saved. Backup: ' + result['backup'])
            self.app.scan_project()
            self.app.capability_cache.clear()
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity='error')
        finally:
            lease.close()

    @on(Button.Pressed, '#close')
    def close(self):
        self.dismiss(None)


class ThemeScreen(ModalScreen):
    DEFAULT_CSS = """
    ThemeScreen { align: center middle; }
    ThemeScreen > Vertical { width: 64; height: auto; padding: 1 2; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; }
    ThemeScreen Select { height: 3; margin: 1 0; }
    ThemeScreen Horizontal { height: 3; }
    """
    BINDINGS = [("escape", "cancel", "Cancel"), Binding("ctrl+x", "cancel", "Cancel", priority=True),
                Binding("ctrl+o", "save", "Save", priority=True), Binding("ctrl+s", "save", "Save", priority=True, show=False)]

    def __init__(self):
        super().__init__()
        self.original = None

    def on_mount(self):
        self.query_one(Vertical).border_title = "Themes"
        self.query_one('#theme-choice', Select).focus()

    def action_save(self):
        self.save()

    def compose(self):
        from .themes import THEMES
        self.original = self.app.theme
        with Vertical():
            yield Label('Enter opens the list; the palette previews live. ^O saves it for future sessions; Esc or ^X restores the previous one.')
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


class NewFileScreen(NanoEditor, ModalScreen):
    """Create a file in the selected runtime without replacing existing data."""
    DEFAULT_CSS = """
    NewFileScreen { align: center middle; }
    NewFileScreen > Vertical { width: 95%; height: 90%; border: round $accent; border-title-color: $accent; border-title-style: bold; padding: 0 1; background: $surface; }
    NewFileScreen TextArea { height: 1fr; }
    NewFileScreen Horizontal { height: 3; }
    NewFileScreen Input, NewFileScreen Select { height: 3; }
    """
    EDITOR = '#new-content'
    BINDINGS = [('escape','dismiss','Cancel'), *NanoEditor.NANO_BINDINGS]

    def __init__(self,profile):
        super().__init__()
        self.profile=profile

    def compose(self):
        with Vertical():
            yield Label('Selected profile runtime · missing parent folders are created · ^O create · ^X cancel · ^W search · ^K/^U cut/uncut')
            yield Input(placeholder='Absolute runtime path, e.g. /work/meta-custom/recipes-example/hello/hello_1.0.bb',id='new-path')
            yield Select([('Empty text file','text'),('Private example recipe','recipe'),('Recipe append','append')],value='text',allow_blank=False,id='new-template')
            yield TextArea('',id='new-content',show_line_numbers=True)
            with Horizontal():
                yield Button('Create file',id='create-file',variant='primary')
                yield Button('Cancel',id='cancel-new')

    def on_mount(self):
        self.query_one(Vertical).border_title='New file'
        self.query_one('#new-path',Input).focus()
        self.nano_ready()

    async def action_save(self):
        await self.create()

    @on(Select.Changed,'#new-template')
    def template(self,event):
        samples={'text':'','recipe':'SUMMARY = "My recipe"\nLICENSE = "CLOSED"\nS = "${WORKDIR}"\n\ndo_install() {\n    install -d ${D}${datadir}/${BPN}\n    echo "Hello" > ${D}${datadir}/${BPN}/message.txt\n}\n','append':'# Extend an existing recipe using a matching .bbappend filename.\nSUMMARY:append = " (customized)"\n'}
        if event.value in samples:
            self.query_one('#new-content',TextArea).load_text(samples[event.value])

    @on(Button.Pressed,'#create-file')
    async def create(self):
        from .runtime import request
        from .leases import BuildLease
        lease = BuildLease(self.profile)
        try:
            if self.app.runner.active or any(j.status=='queued' for j in self.app.runner.jobs) or getattr(self.app, 'developer_busy', False):
                raise ValueError('Wait for queued and running jobs before creating metadata')
            path=self.query_one('#new-path',Input).value.strip()
            if not Path(path).is_absolute():
                raise ValueError('Enter an absolute path in the selected runtime')
            lease.acquire()
            result=await request(self.profile,'create',path,text=self.query_one('#new-content',TextArea).text)
            self.app.capability_cache.clear()
            self.dismiss(result)
        except (OSError,ValueError) as exc:
            self.notify(str(exc),severity='error')
        finally:
            lease.close()

    @on(Button.Pressed,'#cancel-new')
    def cancel(self):
        self.dismiss(None)


class KeysScreen(ModalScreen):
    """Keyboard reference generated from the same map that defines the bindings."""
    DEFAULT_CSS = """
    KeysScreen { align: center middle; background: $background 60%; }
    KeysScreen > Vertical { width: 84; height: 90%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    KeysScreen VerticalScroll { height: 1fr; }
    KeysScreen Markdown { background: $surface; margin: 0; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), ("q", "dismiss", "Close"), ("question_mark", "dismiss", "Close"),
                Binding("ctrl+x", "dismiss", "Close", priority=True), Binding("ctrl+g", "dismiss", "Close", priority=True),
                Binding("ctrl+v", "page(1)", "Page down", priority=True), Binding("ctrl+y", "page(-1)", "Page up", priority=True),
                ("j", "scroll(1)", "Down"), ("k", "scroll(-1)", "Up")]

    def compose(self):
        from .keys import reference_markdown
        with Vertical():
            with VerticalScroll(id="keys-scroll"):
                yield Markdown(reference_markdown().split("\n", 2)[2])

    def on_mount(self):
        self.query_one(Vertical).border_title = "Keyboard reference · Esc closes"
        self.query_one("#keys-scroll").focus()

    def action_page(self, step):
        scroll = self.query_one("#keys-scroll")
        scroll.scroll_page_down() if step > 0 else scroll.scroll_page_up()

    def action_scroll(self, step):
        scroll = self.query_one("#keys-scroll")
        scroll.scroll_down() if step > 0 else scroll.scroll_up()


class ProfilePickerScreen(ModalScreen):
    """Fast keyboard profile switcher: arrows/j/k, Enter selects."""
    DEFAULT_CSS = """
    ProfilePickerScreen { align: center middle; background: $background 60%; }
    ProfilePickerScreen > Vertical { width: 76; height: auto; max-height: 80%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    ProfilePickerScreen OptionList { height: auto; max-height: 20; border: none; background: $surface; }
    ProfilePickerScreen #picker-hint { color: $text-muted; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                ("j", "move(1)", "Down"), ("k", "move(-1)", "Up")]

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

    def compose(self):
        from rich.text import Text
        options = []
        width = max((len(p.name) for p in self.settings.profiles), default=0)
        for p in self.settings.profiles:
            label = Text.assemble(("● " if p.name == self.settings.active else "  ", "bold"), (p.name.ljust(width), "bold"),
                                  ("  team" if p.name in self.settings.shared else "", "italic"), ("  " + p.mode, "dim"), ("  " + (p.machine or "") + "  " + str(p.build_path), "dim"), no_wrap=True, overflow="ellipsis")
            options.append(Option(label, id=p.name))
        with Vertical():
            yield Label("↑ ↓ choose · Enter switch · Esc cancel · F4 edits profiles", id="picker-hint")
            yield OptionList(*options, id="picker")

    def on_mount(self):
        self.query_one(Vertical).border_title = "Switch profile"
        picker = self.query_one("#picker", OptionList)
        names = [p.name for p in self.settings.profiles]
        picker.highlighted = names.index(self.settings.active) if self.settings.active in names else 0
        picker.focus()

    def action_move(self, step):
        picker = self.query_one("#picker", OptionList)
        picker.action_cursor_down() if step > 0 else picker.action_cursor_up()

    @on(OptionList.OptionSelected, "#picker")
    def chosen(self, event):
        self.dismiss(event.option.id)


class ConsoleBuildsScreen(ModalScreen):
    """Pick a BitBake console log, including builds started outside Bitloom."""
    DEFAULT_CSS = """
    ConsoleBuildsScreen { align: center middle; background: $background 60%; }
    ConsoleBuildsScreen > Vertical { width: 100; height: auto; max-height: 85%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    ConsoleBuildsScreen OptionList { height: auto; max-height: 24; border: none; background: $surface; }
    ConsoleBuildsScreen #console-hint { color: $text-muted; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                ("j", "move(1)", "Down"), ("k", "move(-1)", "Up")]

    def __init__(self, profile):
        super().__init__()
        self.profile = profile
        self.entries = []

    def compose(self):
        with Vertical():
            yield Label("Every build of this build directory, also from a terminal, script or CI. Enter opens it in Builds.", id="console-hint")
            yield OptionList(id="console-list")

    def on_mount(self):
        self.query_one(Vertical).border_title = "Console builds · " + str(self.profile.build_path / "tmp/log/cooker")
        self.load()

    @work(exclusive=True)
    async def load(self):
        import asyncio
        from datetime import datetime
        from rich.text import Text
        from .inspectors import console_logs, human_size
        self.entries = await asyncio.to_thread(console_logs, self.profile)
        picker = self.query_one("#console-list", OptionList)
        glyphs = {"success": ("✔", self.app.current_theme.success), "failed": ("✖", self.app.current_theme.error),
                  "interrupted": ("⚠", self.app.current_theme.warning)}
        for index, entry in enumerate(self.entries):
            glyph, color = glyphs.get(entry.detail, ("·", self.app.current_theme.foreground))
            picker.add_option(Option(Text.assemble((f"{glyph} {entry.detail:<11}", color), datetime.fromtimestamp(entry.modified).strftime("%Y-%m-%d %H:%M"),
                                                   ("  " + entry.kind, "bold"), ("  " + human_size(entry.size), "dim")), id=str(index)))
        if not self.entries:
            picker.add_option(Option("No console logs yet: BitBake writes tmp/log/cooker/<MACHINE>/*.log for each build", disabled=True))
        else:
            picker.highlighted = 0  # options arrive after mount; Enter must open the newest at once
        picker.focus()

    def action_move(self, step):
        picker = self.query_one("#console-list", OptionList)
        picker.action_cursor_down() if step > 0 else picker.action_cursor_up()

    @on(OptionList.OptionSelected, "#console-list")
    def chosen(self, event):
        self.dismiss(self.entries[int(event.option.id)])


class SbomSettingsScreen(ModalScreen):
    """SBOM, vulnerability and traceability options with explanations and release checks."""
    DEFAULT_CSS = """
    SbomSettingsScreen { align: center middle; background: $background 60%; }
    SbomSettingsScreen > Vertical { width: 96%; height: 92%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    SbomSettingsScreen #sbom-hint { color: $text-muted; height: auto; }
    SbomSettingsScreen #sbom-split { height: 1fr; }
    SbomSettingsScreen #sbom-options { width: 3fr; height: 1fr; }
    SbomSettingsScreen #sbom-side { width: 2fr; height: 1fr; margin-left: 1; }
    SbomSettingsScreen #sbom-info { height: 1fr; background: $surface; border: round $primary-muted; padding: 0 1; }
    SbomSettingsScreen #sbom-preview { height: auto; max-height: 12; border: round $primary-muted; color: $text-muted; padding: 0 1; }
    SbomSettingsScreen #sbom-text { display: none; }
    SbomSettingsScreen Horizontal.buttons { height: 1; margin-top: 1; }
    SbomSettingsScreen Horizontal.buttons Button { margin-right: 1; }
    """
    BINDINGS = [("escape", "close", "Close"), Binding("ctrl+x", "close", "Close", priority=True),
                Binding("ctrl+o", "apply", "Apply", priority=True), Binding("ctrl+s", "apply", "Apply", priority=True, show=False),
                ("space", "toggle", "Toggle"), ("v", "verify", "Verify"), ("j", "move(1)", "Down"), ("k", "move(-1)", "Up")]

    def __init__(self, profile, release):
        super().__init__()
        from .sbom_settings import current
        self.profile, self.release = profile, release
        self.managed, self.elsewhere = current(profile)
        self.values = dict(self.managed)
        self.initial = dict(self.managed)

    def compose(self):
        from textual.widgets import DataTable
        with Vertical():
            yield Label("Enter/Space toggles or edits · v verifies a variable in the runtime (bitbake-getvar) · ^O applies with a backup · Esc closes without changes", id="sbom-hint")
            with Horizontal(id="sbom-split"):
                yield DataTable(id="sbom-options", cursor_type="row")
                with Vertical(id="sbom-side"):
                    yield Markdown(id="sbom-info")
                    yield Static(id="sbom-preview", markup=False)
            yield Input(placeholder="Organisation name (Enter saves, Esc cancels)", id="sbom-text")
            with Horizontal(classes="buttons"):
                yield Button("^O Apply", id="sbom-apply", variant="primary")
                yield Button("v Verify", id="sbom-verify")
                yield Button("Esc Close", id="sbom-close")

    def on_mount(self):
        from .sbom_settings import target
        from .versions import describe
        self.query_one(Vertical).border_title = f"SBOM & CRA settings · {describe(self.release)} · {target(self.profile)}"
        table = self.query_one("#sbom-options")
        for name, width in (("State", 16), ("Option", 44), ("Release", 15)):
            table.add_column(name, width=width)
        table.border_title = "Options"
        self.query_one("#sbom-preview").border_title = "Managed block preview"
        self.refresh_rows()
        table.focus()

    def state(self, option):
        from .sbom_settings import availability
        ok, _ = availability(option, self.release)
        value = self.values.get(option.id)
        if ok is False:
            return "n/a" + (" (set!)" if value or option.id in self.elsewhere else "")
        if value:
            return value if option.kind in {"choice", "text"} else "on"
        if option.id in self.elsewhere:
            return "on (local.conf)" if option.kind != "choice" else self.elsewhere[option.id] + " (local)"
        return "off"

    def refresh_rows(self):
        from rich.text import Text
        from .sbom_settings import OPTIONS, availability
        table = self.query_one("#sbom-options")
        row = table.cursor_row
        table.clear()
        theme = self.app.current_theme
        for option in OPTIONS:
            ok, _ = availability(option, self.release)
            state = self.state(option)
            color = theme.error if ok is False else theme.success if state not in {"off"} else theme.foreground
            span = (option.since or "any") + ("…" + option.until if option.until else "+")
            table.add_row(Text(state, style=color), option.title, Text(span + ("" if option.verified else " ?"), style="dim"), key=option.id)
        table.move_cursor(row=min(row, len(OPTIONS) - 1))
        self.show_info()

    def selected(self):
        from .sbom_settings import OPTIONS
        return OPTIONS[self.query_one("#sbom-options").cursor_row]

    def show_info(self):
        from .sbom_settings import info_markdown, preview
        option = self.selected()
        self.query_one("#sbom-info", Markdown).update(info_markdown(option, self.release, self.state(option)))
        self.query_one("#sbom-preview", Static).update(preview(self.profile, self.values))

    def on_data_table_row_highlighted(self, event):
        self.show_info()

    def on_data_table_row_selected(self, event):
        self.action_toggle()

    def action_move(self, step):
        table = self.query_one("#sbom-options")
        table.action_cursor_down() if step > 0 else table.action_cursor_up()

    def action_toggle(self):
        from .sbom_settings import availability
        option = self.selected()
        ok, reason = availability(option, self.release)
        if ok is False and not self.values.get(option.id):
            self.notify(f"{option.title}: {reason}", severity="warning", timeout=10)
            return
        if option.kind == "text":
            field = self.query_one("#sbom-text", Input)
            field.value = self.values.get(option.id, "")
            field.display = True
            field.focus()
            return
        if option.kind == "choice":
            choices = list(option.choices)
            now = self.values.get(option.id, "")
            self.values[option.id] = choices[(choices.index(now) + 1) % len(choices)] if now in choices else choices[0]
        elif self.values.get(option.id):
            self.values.pop(option.id)
        else:
            self.values[option.id] = "1"
        self.refresh_rows()

    def on_input_submitted(self, event):
        if event.input.id != "sbom-text":
            return
        event.stop()
        option = self.selected()
        if event.value.strip():
            self.values[option.id] = event.value.strip()
        else:
            self.values.pop(option.id, None)
        event.input.display = False
        self.query_one("#sbom-options").focus()
        self.refresh_rows()

    def on_key(self, event):
        field = self.query_one("#sbom-text", Input)
        if event.key == "escape" and field.display:
            field.display = False
            self.query_one("#sbom-options").focus()
            event.stop()
            event.prevent_default()

    def action_close(self):
        if self.values != self.initial:
            self.notify("Changes discarded (^O applies them)", timeout=4)
        self.dismiss(None)

    def action_verify(self):
        option = self.selected()
        name = "INHERIT" if option.kind == "inherit" else option.name + ("_name" if option.kind == "text" else "")
        self.dismiss({"verify": name, "fragment": option.kind == "fragment"})

    def action_apply(self):
        from .sbom_settings import BY_ID, apply, availability, kas_files_with_overlay
        from .leases import BuildLease
        app = self.app
        if app.runner.active or any(j.status == "queued" for j in app.runner.jobs) or getattr(app, "developer_busy", False):
            self.notify("Wait for the build queue before changing build configuration", severity="warning")
            return
        blocked = [BY_ID[k].title for k, v in self.values.items() if v and availability(BY_ID[k], self.release)[0] is False and self.initial.get(k) != v]
        if blocked:
            self.notify("Not available in this release: " + ", ".join(blocked), severity="error", timeout=10)
            return
        lease = BuildLease(self.profile)
        try:
            lease.acquire()
            path, backup = apply(self.profile, self.values)
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="error", timeout=10)
            return
        finally:
            lease.close()
        result = {"path": str(path), "backup": str(backup) if backup else None, "fragments": []}
        fragment = BY_ID["sbom-cve-check"]
        if bool(self.values.get(fragment.id)) != bool(self.initial.get(fragment.id)):
            result["fragments"].append("sbom-cve-enable" if self.values.get(fragment.id) else "sbom-cve-disable")
        if self.profile.mode in {"kas", "kas-container"}:
            result["kas_file"] = kas_files_with_overlay(self.profile)
        self.dismiss(result)

    @on(Button.Pressed, "#sbom-apply")
    def apply_pressed(self):
        self.action_apply()

    @on(Button.Pressed, "#sbom-verify")
    def verify_pressed(self):
        self.action_verify()

    @on(Button.Pressed, "#sbom-close")
    def close_pressed(self):
        self.action_close()


class StudioScreen(ModalScreen):
    """Create a product layer, distribution, machine, image, recipe or append with explained fields."""
    DEFAULT_CSS = """
    StudioScreen { align: center middle; background: $background 60%; }
    StudioScreen > Vertical { width: 98%; height: 96%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    StudioScreen #studio-hint { color: $text-muted; height: 1; }
    StudioScreen #studio-split { height: 1fr; }
    StudioScreen #studio-kinds { width: 30; height: 1fr; border: round $primary-muted; background: $surface; }
    StudioScreen #studio-kinds:focus { border: round $accent; }
    StudioScreen #studio-form { width: 1fr; height: 1fr; margin: 0 1; border: round $primary-muted; padding: 0 1; }
    StudioScreen #studio-form:focus-within { border: round $accent; }
    StudioScreen #studio-preview { width: 1fr; height: 1fr; border: round $primary-muted; }
    StudioScreen .field-label { margin-top: 1; text-style: bold; height: 1; }
    StudioScreen .field-info { color: $text-muted; height: auto; }
    StudioScreen SelectionList { height: auto; max-height: 8; border: none; background: $surface; }
    StudioScreen Input, StudioScreen Select { height: 1; }
    StudioScreen #studio-notes { height: auto; max-height: 3; color: $warning; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                Binding("ctrl+o", "create", "Create", priority=True), Binding("ctrl+s", "create", "Create", priority=True, show=False),
                Binding("ctrl+g", "app.keys", "Help", priority=True)]

    def __init__(self, profile, release, layers):
        super().__init__()
        self.profile, self.release, self.target_layers = profile, release, layers
        self.kind = "distro"
        self.plan = None
        self.ready = False

    def compose(self):
        from textual.containers import VerticalScroll
        from textual.widgets import RichLog
        from .studio import KINDS
        with Vertical():
            yield Label("↑↓ choose what to create · Tab to the form · every field explains itself · ^O creates (never overwrites) · Esc closes", id="studio-hint")
            with Horizontal(id="studio-split"):
                yield OptionList(*[Option(f"{title}", id=kind) for kind, (title, _) in KINDS.items()], id="studio-kinds")
                yield VerticalScroll(id="studio-form")
                yield RichLog(id="studio-preview", wrap=False, markup=False, auto_scroll=False)
            yield Static(id="studio-notes", markup=False)

    def on_mount(self):
        from .versions import describe
        self.query_one(Vertical).border_title = f"Studio · {self.profile.name} · {describe(self.release)}"
        self.query_one("#studio-kinds").border_title = "Create"
        self.query_one("#studio-preview").border_title = "Files to create"
        kinds = self.query_one("#studio-kinds", OptionList)
        kinds.highlighted = list(__import__("bitloom.studio", fromlist=["KINDS"]).KINDS).index(self.kind)
        kinds.focus()
        self.run_worker(self.build_form(), exclusive=True, group="studio-form")
        # Ignore the OptionList's initial highlight; afterwards arrows switch the form.
        self.call_after_refresh(lambda: setattr(self, "ready", True))

    def on_option_list_option_highlighted(self, event):
        if self.ready and event.option_list.id == "studio-kinds" and event.option.id != self.kind:
            self.kind = event.option.id
            self.run_worker(self.build_form(), exclusive=True, group="studio-form")

    def on_option_list_option_selected(self, event):
        if event.option_list.id == "studio-kinds":
            self.call_after_refresh(lambda: self.query_one("#studio-form").focus_next())

    async def build_form(self):
        from textual.widgets import Checkbox, SelectionList
        from .studio import KINDS, fields
        form = self.query_one("#studio-form")
        await form.remove_children()
        title, description = KINDS[self.kind]
        form.border_title = title
        widgets = [Static(description, classes="field-info")]
        for field in fields(self.kind, self.release, self.target_layers):
            widgets.append(Label(field.label + (" *" if field.required else ""), classes="field-label"))
            if field.kind == "choice":
                widgets.append(Select([(c, c) for c in field.choices], value=field.default, allow_blank=False, id="f-" + field.id))
            elif field.kind == "multi":
                chosen = set(field.default.split())
                widgets.append(SelectionList(*[(c, c, c in chosen) for c in field.choices], id="f-" + field.id))
            elif field.kind == "bool":
                widgets.append(Checkbox("enabled", value=field.default == "1", id="f-" + field.id))
            else:
                widgets.append(Input(value=field.default, id="f-" + field.id))
            if field.info:
                widgets.append(Static(field.info, classes="field-info"))
        if self.kind in {"distro", "machine"} and self.profile.mode in {"host", "container"}:
            widgets += [Label("Use for this profile", classes="field-label"),
                        Checkbox("set " + ("DISTRO" if self.kind == "distro" else "MACHINE") + " of " + self.profile.name, value=True, id="f-use")]
        await form.mount_all(widgets)
        self.refresh_preview()

    def values(self):
        from textual.widgets import Checkbox, SelectionList
        result = {}
        for widget in self.query("#studio-form *"):
            ident = (widget.id or "")
            if not ident.startswith("f-"):
                continue
            key = ident[2:]
            if isinstance(widget, SelectionList):
                result[key] = " ".join(widget.selected)
            elif isinstance(widget, Checkbox):
                result[key] = "1" if widget.value else ""
            elif isinstance(widget, Select):
                result[key] = str(widget.value)
            elif isinstance(widget, Input):
                result[key] = widget.value
        return result

    def on_input_changed(self, event):
        self.refresh_preview()

    def on_select_changed(self, event):
        self.refresh_preview()

    def on_selection_list_selected_changed(self, event):
        self.refresh_preview()

    def on_checkbox_changed(self, event):
        self.refresh_preview()

    def refresh_preview(self):
        from rich.text import Text
        from textual.widgets import RichLog
        from .studio import plan
        log = self.query_one("#studio-preview", RichLog)
        log.clear()
        try:
            self.plan = plan(self.kind, self.values(), self.profile, self.release)
        except ValueError as exc:
            self.plan = None
            log.write(Text("✖ " + str(exc), style=self.app.current_theme.error))
            self.query_one("#studio-notes", Static).update("")
            return
        root = self.plan["layer"]
        log.write(Text(("NEW LAYER " if self.plan["new_layer"] else "INTO ") + root, style=f"bold {self.app.current_theme.accent}"))
        for name, text in self.plan["files"].items():
            log.write(Text("\n+++ " + name, style=f"bold {self.app.current_theme.success}"))
            log.write(Text(text))
        log.scroll_home(animate=False)
        self.query_one("#studio-notes", Static).update("  ".join("⚠ " + n for n in self.plan["notes"]))

    def action_create(self):
        from .studio import create
        app = self.app
        if not self.plan:
            self.notify("Fix the highlighted field first", severity="warning")
            return
        if app.runner.active or any(j.status == "queued" for j in app.runner.jobs):
            self.notify("Wait for the build queue before changing metadata", severity="warning")
            return
        try:
            written = create(self.profile, self.plan)
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="error", timeout=10)
            return
        self.dismiss({"plan": self.plan, "written": [str(p) for p in written], "use": self.values().get("use") == "1"})


class SetupScreen(ModalScreen):
    """Guided project setup: scan a directory, pick how it builds, adjust, save and reload."""
    DEFAULT_CSS = """
    SetupScreen { align: center middle; background: $background 60%; }
    SetupScreen > Vertical { width: 98%; height: 96%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    SetupScreen #setup-hint { color: $text-muted; height: auto; }
    SetupScreen #setup-dir-row { height: 1; margin: 1 0; }
    SetupScreen #setup-dir { width: 1fr; }
    SetupScreen #setup-split { height: 1fr; }
    SetupScreen #setup-found { width: 2fr; height: 1fr; border: round $primary-muted; background: $surface; }
    SetupScreen #setup-found:focus { border: round $accent; }
    SetupScreen #setup-form { width: 3fr; height: 1fr; margin-left: 1; border: round $primary-muted; padding: 0 1; }
    SetupScreen #setup-form:focus-within { border: round $accent; }
    SetupScreen .field-label { margin-top: 1; text-style: bold; height: 1; }
    SetupScreen .field-info { color: $text-muted; height: auto; }
    SetupScreen Input, SetupScreen Select { height: 1; }
    SetupScreen #setup-env { height: 4; }
    SetupScreen #setup-checks { height: auto; max-height: 7; }
    SetupScreen Horizontal.buttons { height: 1; margin-top: 1; }
    SetupScreen Horizontal.buttons Button { margin-right: 1; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                Binding("ctrl+o", "save", "Save", priority=True), Binding("ctrl+s", "save", "Save", priority=True, show=False)]
    FIELDS = [("name", "Profile name", "Unique name shown in the profile switcher (P)."),
              ("kas_file", "kas configuration", "kas modes: the YAML file(s), colon-separated, relative to the project."),
              ("init_script", "Init script", "host: oe-init-build-env path relative to the project; empty if you start from an initialised shell."),
              ("build_dir", "Build directory", "host/container: relative to the project or absolute; kas modes use KAS_WORK_DIR/build."),
              ("launcher", "Launcher script", "wrapper: the project script that runs kas, e.g. ./scripts/run.sh."),
              ("machine", "MACHINE", "Optional override; empty keeps the configuration's value."),
              ("distro", "DISTRO", "Optional override."),
              ("targets", "Targets", "Space-separated; the first fills the build target field.")]

    def __init__(self, settings, directory):
        super().__init__()
        self.settings, self.directory = settings, str(directory)
        self.candidates = []

    def compose(self):
        from textual.containers import VerticalScroll
        with Vertical():
            yield Label("Point Bitloom at a project: it finds kas files, init scripts, build directories and launcher scripts. "
                        "Pick a proposal, adjust it, ^O saves and the workspace reloads with the new profile.", id="setup-hint")
            with Horizontal(id="setup-dir-row"):
                yield Input(value=self.directory, placeholder="Project directory (Enter scans)", id="setup-dir")
                yield Button("Scan", id="setup-scan")
            with Horizontal(id="setup-split"):
                yield OptionList(id="setup-found")
                with VerticalScroll(id="setup-form"):
                    yield Label("Runtime", classes="field-label")
                    yield Select([(m, m) for m in ("kas-container", "kas", "host", "container", "wrapper")], value="kas-container", allow_blank=False, id="setup-mode")
                    yield Static("kas-container: kas and Yocto in a container (recommended). kas: kas on the host. host: an initialised Poky/OE-Core checkout. "
                                 "container: your own Docker/Podman image. wrapper: a project script that runs kas.", classes="field-info")
                    for key, label, info in self.FIELDS:
                        yield Label(label, classes="field-label", id="label-" + key)
                        yield Input(id="setup-" + key)
                        yield Static(info, classes="field-info", id="info-" + key)
                    yield Label("Environment (KEY=VALUE per line)", classes="field-label")
                    yield TextArea("", id="setup-env")
                    yield Static("kas-container: KAS_WORK_DIR (separate Linux directory), KAS_CONTAINER_ENGINE. wrapper: the variable that selects the configuration, e.g. YML=boards/board.yml.", classes="field-info")
                    yield Label("Checks", classes="field-label")
                    yield Static(id="setup-checks")
            with Horizontal(classes="buttons"):
                yield Button("^O Save + use", id="setup-save", variant="primary")
                yield Button("Esc Close", id="setup-close")

    def on_mount(self):
        self.query_one(Vertical).border_title = "Set up a project"
        self.query_one("#setup-found").border_title = "Found"
        self.query_one("#setup-form").border_title = "Profile"
        self.scan()

    def scan(self):
        from .setup import detect
        found = self.query_one("#setup-found", OptionList)
        found.clear_options()
        try:
            self.candidates = detect(Path(self.query_one("#setup-dir", Input).value))
        except (OSError, ValueError) as exc:
            self.candidates = []
            found.add_option(Option("✖ " + str(exc), disabled=True))
            return
        if not self.candidates:
            found.add_option(Option("Nothing recognised: fill the form by hand", disabled=True))
            self.fill({"name": "project", "root": self.query_one("#setup-dir", Input).value, "mode": "kas-container"})
            return
        from rich.text import Text
        for index, candidate in enumerate(self.candidates):
            label = Text.assemble((candidate.title, "bold"), "\n", ("  " + " · ".join(candidate.evidence), "dim"))
            found.add_option(Option(label, id=str(index)))
        found.highlighted = 0
        found.focus()
        self.fill(self.candidates[0].profile)

    def fill(self, data):
        self.query_one("#setup-mode", Select).value = data.get("mode", "kas-container")
        for key, _, _ in self.FIELDS:
            value = data.get(key, "")
            if key == "launcher":
                value = " ".join(value or [])
            if key == "targets":
                value = " ".join(value or [])
            self.query_one("#setup-" + key, Input).value = value or ""
        self.query_one("#setup-env", TextArea).load_text("\n".join(f"{k}={v}" for k, v in (data.get("environment") or {}).items()))
        self.refresh_form()

    def profile(self):
        import shlex
        from .models import Profile
        values = {key: self.query_one("#setup-" + key, Input).value.strip() for key, _, _ in self.FIELDS}
        environment = {}
        for line in self.query_one("#setup-env", TextArea).text.splitlines():
            if "=" in line.strip():
                key, value = line.strip().split("=", 1)
                environment[key.strip()] = value.strip()
        data = {"name": values["name"], "root": self.query_one("#setup-dir", Input).value.strip(), "mode": str(self.query_one("#setup-mode", Select).value),
                "kas_file": values["kas_file"] or "kas.yml", "init_script": values["init_script"], "build_dir": values["build_dir"] or "build",
                "machine": values["machine"], "distro": values["distro"], "targets": values["targets"].split() or ["core-image-minimal"],
                "environment": environment}
        if data["mode"] == "wrapper":
            data["launcher"] = shlex.split(values["launcher"])
        return Profile.from_dict(data)

    def refresh_form(self):
        from rich.text import Text
        from .setup import check
        mode = str(self.query_one("#setup-mode", Select).value)
        visible = {"kas_file": mode in {"kas", "kas-container"}, "init_script": mode in {"host", "container"}, "build_dir": mode in {"host", "container"},
                   "launcher": mode == "wrapper"}
        for key, show in visible.items():
            for prefix in ("label-", "setup-", "info-"):
                self.query_one("#" + prefix + key).display = show
        theme = self.app.current_theme
        text = Text()
        try:
            rows = check(self.profile())
        except (ValueError, TypeError) as exc:
            rows = [("ERR", str(exc))]
        for status, message in rows:
            glyph, color = {"OK": ("✔", theme.success), "WARN": ("▲", theme.warning), "ERR": ("✖", theme.error)}[status]
            text.append(f"{glyph} ", style=f"bold {color}").append(message + "\n")
        self.query_one("#setup-checks", Static).update(text)
        self.query_one("#setup-save", Button).disabled = any(status == "ERR" for status, _ in rows)

    def on_option_list_option_highlighted(self, event):
        if event.option_list.id == "setup-found" and event.option.id is not None:
            self.fill(self.candidates[int(event.option.id)].profile)

    def on_option_list_option_selected(self, event):
        if event.option_list.id == "setup-found":
            self.query_one("#setup-name", Input).focus()

    def on_input_changed(self, event):
        if event.input.id and event.input.id.startswith("setup-") and event.input.id != "setup-dir":
            self.refresh_form()

    def on_text_area_changed(self, event):
        self.refresh_form()

    def on_select_changed(self, event):
        self.refresh_form()

    def on_input_submitted(self, event):
        if event.input.id == "setup-dir":
            event.stop()
            self.scan()

    @on(Button.Pressed, "#setup-scan")
    def scan_pressed(self):
        self.scan()

    @on(Button.Pressed, "#setup-close")
    def close_pressed(self):
        self.dismiss(None)

    @on(Button.Pressed, "#setup-save")
    def save_pressed(self):
        self.action_save()

    def action_save(self):
        from .setup import save
        try:
            profile = self.profile()
            if self.query_one("#setup-save", Button).disabled:
                raise ValueError("Fix the checks marked ✖ first")
            save(self.settings, profile)
        except (OSError, ValueError, TypeError) as exc:
            self.notify(str(exc), severity="error", timeout=10)
            return
        self.dismiss(profile.name)


class ProjectsScreen(ModalScreen):
    """Project hub: recent projects, open a folder, create a new project, clone from Git."""
    DEFAULT_CSS = """
    ProjectsScreen { align: center middle; background: $background 60%; }
    ProjectsScreen > Vertical { width: 110; max-width: 96%; height: auto; max-height: 90%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    ProjectsScreen #projects-hint { color: $text-muted; height: auto; margin-bottom: 1; }
    ProjectsScreen OptionList { height: auto; max-height: 18; border: round $primary-muted; background: $surface; }
    ProjectsScreen OptionList:focus { border: round $accent; }
    ProjectsScreen Horizontal { height: 1; margin-top: 1; }
    ProjectsScreen Horizontal Button { margin-right: 1; }
    ProjectsScreen #open-row { display: none; height: 1; }
    ProjectsScreen #open-dir { width: 1fr; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                ("o", "open_folder", "Open folder"), ("n", "choose('new')", "New project"), ("g", "choose('clone')", "Clone"),
                ("j", "move(1)", "Down"), ("k", "move(-1)", "Up")]

    def __init__(self, settings, recent):
        super().__init__()
        self.settings, self.recent = settings, recent
        self.items = []

    def compose(self):
        with Vertical():
            yield Label("Enter opens a recent project (its profile, or the guided setup) · o open a folder · n new project · g clone from Git · Esc close", id="projects-hint")
            yield OptionList(id="projects-list")
            with Horizontal(id="open-row"):
                yield Input(placeholder="Folder to open (Enter scans it)", id="open-dir")
            with Horizontal():
                yield Button("o Open folder", id="projects-open")
                yield Button("n New project", id="projects-new", variant="primary")
                yield Button("g Clone from Git", id="projects-clone")

    def on_mount(self):
        from rich.text import Text
        self.query_one(Vertical).border_title = "Projects"
        seen, picker = set(), self.query_one("#projects-list", OptionList)
        roots = {str(p.root_path): p.name for p in self.settings.profiles}
        for item in self.recent.load() + [{"root": root, "profile": name, "how": "profile"} for root, name in roots.items()]:
            if item["root"] in seen:
                continue
            seen.add(item["root"])
            self.items.append(item)
            profile = roots.get(item["root"])
            folder = Path(item["root"]).name or item["root"]
            active = profile == self.settings.active
            # ● active project, ○ set up (switches profile), + not set up yet (opens the guided setup).
            mark = ("● ", "bold $accent") if active else ("○ ", "") if profile else ("+ ", "dim")
            state = "active" if active else (f"profile {profile}" if profile and profile != folder else "switch") if profile else "not set up"
            label = Text.assemble(mark, (folder, "bold"), ("  " + state, "italic"), ("  " + item["root"], "dim"),
                                  no_wrap=True, overflow="ellipsis")
            picker.add_option(Option(label, id=str(len(self.items) - 1)))
        if self.items:
            picker.highlighted = 0
        picker.focus()

    def action_move(self, step):
        picker = self.query_one("#projects-list", OptionList)
        picker.action_cursor_down() if step > 0 else picker.action_cursor_up()

    def action_open_folder(self):
        self.query_one("#open-row").display = True
        field = self.query_one("#open-dir", Input)
        field.value = field.value or str(Path.home())
        field.focus()

    def action_choose(self, what):
        self.dismiss({what: True})

    @on(OptionList.OptionSelected, "#projects-list")
    def chosen(self, event):
        self.dismiss({"open": self.items[int(event.option.id)]["root"]})

    def on_input_submitted(self, event):
        if event.input.id == "open-dir":
            event.stop()
            self.dismiss({"open": event.value.strip()})

    @on(Button.Pressed, "#projects-open")
    def open_pressed(self):
        self.action_open_folder()

    @on(Button.Pressed, "#projects-new")
    def new_pressed(self):
        self.dismiss({"new": True})

    @on(Button.Pressed, "#projects-clone")
    def clone_pressed(self):
        self.dismiss({"clone": True})


class NewProjectScreen(ModalScreen):
    """Create a new Yocto project folder with a pinned kas configuration."""
    DEFAULT_CSS = """
    NewProjectScreen { align: center middle; background: $background 60%; }
    NewProjectScreen > Vertical { width: 98%; height: 94%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    NewProjectScreen #np-split { height: 1fr; }
    NewProjectScreen #np-form { width: 2fr; height: 1fr; border: round $primary-muted; padding: 0 1; }
    NewProjectScreen #np-form:focus-within { border: round $accent; }
    NewProjectScreen #np-preview { width: 3fr; height: 1fr; margin-left: 1; }
    NewProjectScreen .field-label { margin-top: 1; text-style: bold; height: 1; }
    NewProjectScreen .field-info { color: $text-muted; height: auto; }
    NewProjectScreen Input, NewProjectScreen Select { height: 1; }
    NewProjectScreen #np-hint { color: $text-muted; height: 1; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                Binding("ctrl+o", "create", "Create", priority=True), Binding("ctrl+s", "create", "Create", priority=True, show=False)]

    def compose(self):
        from textual.containers import VerticalScroll
        from textual.widgets import Checkbox, RichLog
        from .projects import IMAGES, MACHINES, RELEASES
        base = Path.home() / "yocto"
        with Vertical():
            yield Label("A few choices give you a buildable project: kas.yml pinned to verified release tags, README, .gitignore and git init. ^O creates, Esc closes.", id="np-hint")
            with Horizontal(id="np-split"):
                with VerticalScroll(id="np-form"):
                    for ident, label, widget, info in [
                        ("name", "Project name", Input(value="my-product", id="np-name"), "Lowercase; also the profile name."),
                        ("dir", "Folder", Input(value=str(base / "my-product"), id="np-dir"), "A new or empty folder."),
                        ("release", "Yocto release", Select([(v["title"], k) for k, v in RELEASES.items()], value="scarthgap", allow_blank=False, id="np-release"),
                         "Both are LTS. Wrynose uses split repositories (no poky), SPDX 3 and sbom-cve-check."),
                        ("machine", "MACHINE", Select([(m, m) for m in MACHINES], value="qemux86-64", allow_blank=False, id="np-machine"), "Start on QEMU; derive your board later in Studio."),
                        ("distro", "DISTRO", Input(value="poky", id="np-distro"), "poky, or the id of your own distribution created later with Studio."),
                        ("target", "Image", Select([(i, i) for i in IMAGES], value="core-image-minimal", allow_blank=False, id="np-target"), "The image built by b."),
                        ("runtime", "Runtime", Select([("kas-container (recommended)", "kas-container"), ("kas on the host", "kas")], value="kas-container", allow_blank=False, id="np-runtime"),
                         "kas-container brings every Yocto host dependency in a container."),
                    ]:
                        yield Label(label, classes="field-label")
                        yield widget
                        yield Static(info, classes="field-info")
                    yield Label("Product layer", classes="field-label")
                    yield Checkbox("create meta-<name> for your recipes, distro and machines", value=True, id="np-layer")
                    yield Label("Copyright owner", classes="field-label")
                    yield Input(value="", placeholder="Your company", id="np-owner")
                yield RichLog(id="np-preview", wrap=False, markup=False, auto_scroll=False)

    def on_mount(self):
        self.query_one(Vertical).border_title = "New project"
        self.query_one("#np-preview").border_title = "Files"
        self.query_one("#np-name", Input).focus()
        self.refresh_preview()

    def plan(self):
        from .projects import new_project_plan
        value = lambda ident: str(getattr(self.query_one("#np-" + ident), "value"))
        return new_project_plan(value("dir"), value("name"), value("release"), value("machine"), value("distro"), value("target"),
                                bool(self.query_one("#np-layer").value), value("owner"))

    def on_input_changed(self, event):
        if event.input.id == "np-name":
            folder = self.query_one("#np-dir", Input)
            parent = Path(folder.value).parent if folder.value else Path.home() / "yocto"
            folder.value = str(parent / event.value)
        self.refresh_preview()

    def on_select_changed(self, event):
        self.refresh_preview()

    def on_checkbox_changed(self, event):
        self.refresh_preview()

    def refresh_preview(self):
        from rich.text import Text
        log = self.query_one("#np-preview")
        log.clear()
        try:
            plan = self.plan()
        except ValueError as exc:
            log.write(Text("✖ " + str(exc), style=self.app.current_theme.error))
            return
        for name in ("kas.yml", "README.md", ".gitignore"):
            log.write(Text("+++ " + name, style=f"bold {self.app.current_theme.success}"))
            log.write(Text(plan["files"][name]))
        if plan["layer"]:
            log.write(Text(f"+++ {plan['layer']}/ (conf/layer.conf, README.md, COPYING.MIT)", style=f"bold {self.app.current_theme.success}"))
        log.scroll_home(animate=False)

    def action_create(self):
        from .projects import create_project
        try:
            plan = self.plan()
            profile = create_project(plan, str(self.query_one("#np-runtime", Select).value))
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="error", timeout=10)
            return
        self.dismiss(profile)


class CloneScreen(ModalScreen):
    """Clone a project from GitHub or any Git server, then set it up."""
    DEFAULT_CSS = """
    CloneScreen { align: center middle; background: $background 60%; }
    CloneScreen > Vertical { width: 100; max-width: 96%; height: auto; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1 1 1; }
    CloneScreen .field-label { margin-top: 1; text-style: bold; height: 1; }
    CloneScreen .field-info { color: $text-muted; height: auto; }
    CloneScreen Input { height: 1; }
    CloneScreen #clone-preview { margin-top: 1; color: $text-muted; height: auto; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                Binding("ctrl+o", "clone", "Clone", priority=True)]

    def compose(self):
        with Vertical():
            yield Label("Repository URL", classes="field-label")
            yield Input(placeholder="https://github.com/org/product.git or git@github.com:org/product.git", id="clone-url")
            yield Static("HTTPS or SSH; your git credentials and SSH agent are used as in a terminal.", classes="field-info")
            yield Label("Destination folder", classes="field-label")
            yield Input(id="clone-dest")
            yield Label("Branch or tag (optional)", classes="field-label")
            yield Input(id="clone-branch")
            yield Static(id="clone-preview", markup=False)

    def on_mount(self):
        self.query_one(Vertical).border_title = "Clone a project · ^O clones, then the guided setup opens"
        self.query_one("#clone-url", Input).focus()

    autofill = ""
    dest_touched = False

    def on_input_changed(self, event):
        from .projects import clone_argv, default_destination
        if event.input.id == "clone-dest" and event.value != self.autofill:
            self.dest_touched = True  # never overwrite a destination the user typed
        if event.input.id == "clone-url" and event.value.strip() and not self.dest_touched:
            self.autofill = default_destination(event.value, Path.home() / "yocto")
            self.query_one("#clone-dest", Input).value = self.autofill
        try:
            import shlex
            text = "$ " + shlex.join(clone_argv(*(self.query_one("#clone-" + k, Input).value for k in ("url", "dest", "branch"))))
        except ValueError as exc:
            text = str(exc)
        self.query_one("#clone-preview", Static).update(text)

    def on_input_submitted(self, event):
        event.stop()
        self.action_clone()

    def action_clone(self):
        from .projects import clone_argv
        values = [self.query_one("#clone-" + k, Input).value for k in ("url", "dest", "branch")]
        try:
            argv = clone_argv(*values)
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return
        self.dismiss({"argv": argv, "dest": argv[-1]})


class VulnerabilitiesScreen(ModalScreen):
    """CVE findings from cve-check, sbom-cve-check and Grype with reviews and scans."""
    DEFAULT_CSS = """
    VulnerabilitiesScreen { align: center middle; background: $background 60%; }
    VulnerabilitiesScreen > Vertical { width: 98%; height: 96%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1; }
    VulnerabilitiesScreen #vuln-tools { height: 1; margin: 1 0; }
    VulnerabilitiesScreen #vuln-tools Select { width: 34; }
    VulnerabilitiesScreen #vuln-status { width: 18; }
    VulnerabilitiesScreen #vuln-min { width: 12; }
    VulnerabilitiesScreen #vuln-filter { width: 1fr; }
    VulnerabilitiesScreen #vuln-summary { height: auto; color: $text-muted; }
    VulnerabilitiesScreen #vuln-split { height: 1fr; }
    VulnerabilitiesScreen #vuln-table { width: 3fr; height: 1fr; }
    VulnerabilitiesScreen #vuln-detail { width: 2fr; height: 1fr; margin-left: 1; border: round $primary-muted; padding: 0 1; }
    VulnerabilitiesScreen Input, VulnerabilitiesScreen Select { height: 1; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                ("r", "review", "Review"), ("g", "grype", "Grype scan"), ("x", "export", "Export CSV"),
                ("slash", "focus_filter", "Filter"), ("j", "move(1)", "Down"), ("k", "move(-1)", "Up")]

    def __init__(self, profile, state):
        super().__init__()
        self.profile, self.state = profile, Path(state)
        self.findings, self.errors, self.shown = [], [], []

    def compose(self):
        from textual.widgets import DataTable
        from .vulns import sources
        options = [("Newest report of each tool", "")] + [(label, label) for label, _ in sources(self.profile, self.state)]
        with Vertical():
            with ToolBar(id="vuln-tools"):
                yield Select(options, value="", allow_blank=False, id="vuln-source")
                yield Select([("Unpatched", "unpatched"), ("All", "all"), ("Reviewed", "reviewed")], value="unpatched", allow_blank=False, id="vuln-status")
                yield Input(placeholder="min CVSS", id="vuln-min", type="number")
                yield Input(placeholder="/ CVE, package or text", id="vuln-filter")
            yield Static(id="vuln-summary", markup=False)
            with Horizontal(id="vuln-split"):
                yield DataTable(id="vuln-table", cursor_type="row")
                yield Static(id="vuln-detail", markup=False)

    def on_mount(self):
        from .versions import describe
        self.query_one(Vertical).border_title = "Vulnerabilities · r review · g scan with Grype · x export CSV · / filter · Esc close"
        table = self.query_one("#vuln-table")
        for name, width in (("Severity", 10), ("CVSS", 5), ("CVE", 18), ("Package", 22), ("Status", 11), ("Review", 16)):
            table.add_column(name, width=width)
        table.border_title = "Findings"
        self.query_one("#vuln-detail").border_title = "Detail"
        self.reload()
        table.focus()

    def reload(self):
        from .vulns import load
        self.findings, self.errors = load(self.profile, self.state, str(self.query_one("#vuln-source", Select).value))
        self.render_rows()

    def render_rows(self):
        from rich.text import Text
        from .vulns import counts, select
        try:
            minimum = float(self.query_one("#vuln-min", Input).value or 0)
        except ValueError:
            minimum = 0.0
        self.shown = select(self.findings, str(self.query_one("#vuln-status", Select).value), minimum, self.query_one("#vuln-filter", Input).value)
        table = self.query_one("#vuln-table")
        table.clear()
        theme = self.app.current_theme
        colors = {"critical": theme.error, "high": theme.error, "medium": theme.warning, "low": theme.foreground}
        for index, finding in enumerate(self.shown[:2000]):
            table.add_row(Text(finding.severity, style=f"bold {colors.get(finding.severity, theme.foreground)}"), f"{finding.score:.1f}" if finding.score else "—",
                          finding.id, f"{finding.package} {finding.version}", finding.status, Text(finding.review or "", style=theme.success), key=str(index))
        c = counts(self.findings)
        if not self.findings and not self.errors:
            summary = ("No CVE report yet. Wrynose: enable sbom-cve-check (Configuration → s) and build the image; older releases: "
                       "INHERIT += \"cve-check\". Or press g to scan the newest SPDX SBOM with Grype.")
        else:
            summary = (f"{c['total']} assessed · {c['unpatched']} unpatched (critical {c.get('unpatched_critical', 0)}, high {c.get('unpatched_high', 0)}, "
                       f"medium {c.get('unpatched_medium', 0)}) · {c['patched']} patched · {c['ignored']} ignored · {c['reviewed']} reviewed · showing {len(self.shown)}")
        self.query_one("#vuln-summary", Static).update(summary + "".join("\n! " + e for e in self.errors))
        self.show_detail()

    def selected(self):
        table = self.query_one("#vuln-table")
        return self.shown[table.cursor_row] if self.shown and table.cursor_row < len(self.shown) else None

    def show_detail(self):
        finding = self.selected()
        detail = self.query_one("#vuln-detail", Static)
        if not finding:
            detail.update("")
            return
        detail.update("\n".join(filter(None, [f"{finding.id} · {finding.severity} {finding.score or ''}", f"{finding.package} {finding.version} · {finding.status}",
                                               f"source: {finding.source}", f"detail: {finding.detail}" if finding.detail else "",
                                               f"vector: {finding.vector}" if finding.vector else "", finding.link, "", finding.summary,
                                               "", f"Reviewed: {finding.review}" if finding.review else "Not reviewed: press r to record an owner, a reason and an expiry."])))

    def on_data_table_row_highlighted(self, event):
        self.show_detail()

    def on_select_changed(self, event):
        self.reload() if event.select.id == "vuln-source" else self.render_rows()

    def on_input_changed(self, event):
        self.render_rows()

    def on_input_submitted(self, event):
        event.stop()
        self.query_one("#vuln-table").focus()

    def action_focus_filter(self):
        self.query_one("#vuln-filter", Input).focus()

    def action_move(self, step):
        table = self.query_one("#vuln-table")
        table.action_cursor_down() if step > 0 else table.action_cursor_up()

    def action_review(self):
        from .developer_ui import DispositionScreen
        finding = self.selected()
        if not finding:
            return
        self.app.push_screen(DispositionScreen(self.state, {"package": finding.package, "id": finding.id, "status": finding.status}), lambda saved: saved and self.reload())

    def action_export(self):
        from .vulns import to_csv
        from datetime import datetime
        destination = self.state / "exports" / f"vulnerabilities-{datetime.now():%Y%m%d-%H%M%S}.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(to_csv(self.shown))
        self.notify(f"Exported {len(self.shown)} rows to {destination}", timeout=8)

    def action_grype(self):
        from datetime import datetime
        from .sbom import sbom_files
        from .vulns import grype_argv
        try:
            sboms = [p for p in sbom_files(self.profile) if p.name.endswith(".spdx.json")]
            if not sboms:
                raise ValueError("No SPDX JSON SBOM in tmp/deploy (SPDX 3 releases write IMAGE.spdx.json)")
            output = self.state / "vulnerability-scans" / f"{sboms[0].name[:-len('.spdx.json')]}-{datetime.now():%Y%m%d-%H%M%S}.grype.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            argv = grype_argv(sboms[0], output)
        except ValueError as exc:
            self.notify(str(exc), severity="warning", timeout=10)
            return
        self.dismiss({"scan": argv, "output": str(output)})


class NotificationsScreen(ModalScreen):
    """Where the build service announces finished jobs: desktop and/or a webhook."""
    DEFAULT_CSS = """
    NotificationsScreen { align: center middle; background: $background 60%; }
    NotificationsScreen > Vertical { width: 96; max-width: 96%; height: auto; max-height: 92%; border: round $accent; border-title-color: $accent; border-title-style: bold; background: $surface; padding: 0 1 1 1; }
    NotificationsScreen .field-label { margin-top: 1; text-style: bold; height: 1; }
    NotificationsScreen .field-info { color: $text-muted; height: auto; }
    NotificationsScreen Input, NotificationsScreen Select { height: 1; }
    NotificationsScreen SelectionList { height: auto; max-height: 5; border: none; background: $surface; }
    NotificationsScreen Horizontal { height: 1; margin-top: 1; }
    NotificationsScreen Horizontal Button { margin-right: 1; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), Binding("ctrl+x", "dismiss", "Close", priority=True),
                Binding("ctrl+o", "save", "Save", priority=True), Binding("ctrl+t", "test", "Test", priority=True)]

    def __init__(self, state):
        super().__init__()
        self.state = Path(state)

    def compose(self):
        from textual.widgets import Checkbox, SelectionList
        from .notify import load
        config = load(self.state)
        with Vertical():
            yield Label("When", classes="field-label")
            yield SelectionList(*[(s, s, s in config["on"]) for s in ("success", "failed", "cancelled")], id="nt-on")
            yield Label("Only for jobs longer than (seconds)", classes="field-label")
            yield Input(str(config["min_seconds"]), id="nt-min", type="integer")
            yield Static("Short commands stay quiet. The terminal bell always rings in an open TUI.", classes="field-info")
            yield Label("Desktop", classes="field-label")
            yield Checkbox("desktop notification (notify-send on Linux, a Windows notification from WSL)", value=config["desktop"], id="nt-desktop")
            yield Label("Webhook", classes="field-label")
            yield Input(config["webhook"], placeholder="https://ntfy.sh/your-topic or a Slack/Teams/Mattermost incoming webhook", id="nt-webhook")
            yield Select([("ntfy (text, title header)", "ntfy"), ("Slack / Teams / Mattermost ({\"text\": …})", "slack"), ("JSON (full job details)", "json")],
                         value=config["format"], allow_blank=False, id="nt-format")
            yield Static("Sent by the build service, so notifications arrive even when no TUI is open. The file is stored with mode 0600.", classes="field-info")
            with Horizontal():
                yield Button("^O Save", id="nt-save", variant="primary")
                yield Button("^T Send test", id="nt-test")
                yield Button("Esc Close", id="nt-close")

    def on_mount(self):
        self.query_one(Vertical).border_title = "Build notifications"
        self.query_one("#nt-on").focus()

    def config(self):
        return {"on": list(self.query_one("#nt-on").selected), "min_seconds": self.query_one("#nt-min", Input).value or 0,
                "desktop": self.query_one("#nt-desktop").value, "webhook": self.query_one("#nt-webhook", Input).value.strip(),
                "format": str(self.query_one("#nt-format", Select).value)}

    def action_save(self):
        from .notify import save
        try:
            save(self.state, self.config())
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="error")
            return
        self.notify("Notifications saved", timeout=4)
        self.dismiss(True)

    def action_test(self):
        from types import SimpleNamespace
        from .notify import save, send
        try:
            save(self.state, self.config())
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="error")
            return
        job = SimpleNamespace(id="test", title="Test notification", status="success", code=0, profile=SimpleNamespace(name="bitloom"),
                              started="2026-01-01T00:00:00+00:00", finished="2026-01-01T00:12:34+00:00", command=["true"],
                              log="", failure_logs=[], action_id="test")
        sent = send(self.state, job, force=True)
        self.app.bell()
        self.notify("Sent: " + (", ".join(sent) or "nothing configured (bell only)"), timeout=6)

    @on(Button.Pressed, "#nt-save")
    def save_pressed(self):
        self.action_save()

    @on(Button.Pressed, "#nt-test")
    def test_pressed(self):
        self.action_test()

    @on(Button.Pressed, "#nt-close")
    def close_pressed(self):
        self.dismiss(None)
