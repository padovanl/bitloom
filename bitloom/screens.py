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
            yield Select([(f"{a.group} / {a.title}", a.id) for a in ACTIONS], value=self.initial_action, allow_blank=False, id="action")
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
        submit = self.query_one('#submit', Button)
        submit.disabled = False
        try:
            a = self.selected()
            inv = invocation(self.profile, arguments(a, self.values()))
            text = inv.display
            if a.help:
                text += "\n" + a.help
            required = {'license':'do_create_spdx', 'cve':'do_cve_check', 'ptest':'do_compile_ptest_base', 'testimage':'do_testimage',
                        'kernel-diff':'do_diffconfig', 'kernel-fragments':'do_kernel_configcheck', 'menuconfig':'do_menuconfig'}
            cap = getattr(self.app, 'capability_cache', {}).get((self.profile.name, self.values().get('target', '')))
            import time
            if cap and time.time() - cap.get('captured', 0) > 30: cap = None
            if a.id in required and cap and required[a.id] not in cap.get('tasks', []):
                submit.disabled = True
                text += '\nUnavailable in the probed runtime: ' + required[a.id]
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
        for p in self.settings.profiles:
            label = Text.assemble(("● " if p.name == self.settings.active else "  ", "bold"), (p.name, "bold"),
                                  ("  team" if p.name in self.settings.shared else "", "italic"), ("  " + p.mode, "dim"), ("  " + (p.machine or "") + "  " + str(p.build_path), "dim"))
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
        picker.focus()

    def action_move(self, step):
        picker = self.query_one("#console-list", OptionList)
        picker.action_cursor_down() if step > 0 else picker.action_cursor_up()

    @on(OptionList.OptionSelected, "#console-list")
    def chosen(self, event):
        self.dismiss(self.entries[int(event.option.id)])
