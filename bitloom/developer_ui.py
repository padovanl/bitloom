"""Keyboard-driven developer workbench and bounded workflow dialogs."""
from __future__ import annotations

import asyncio
import copy
import json
import os
import shutil
import shlex
import uuid
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, RichLog, Select, Static, TextArea, TabbedContent

from .toolbar import ToolBar
from . import developer as dev
from .developer_agent import report
from .models import Profile


class FormScreen(ModalScreen):
    DEFAULT_CSS = '''
    FormScreen { align: center middle; }
    FormScreen > Vertical { width: 90; max-width: 95%; height: 90%; background: $surface; border: round $accent; padding: 0 1; }
    FormScreen VerticalScroll { height: 1fr; }
    FormScreen Label { height: auto; }
    FormScreen Input, FormScreen Select { height: 3; margin-bottom: 1; }
    FormScreen Horizontal { height: 3; }
    FormScreen TextArea { height: 1fr; }
    '''
    BINDINGS = [('escape', 'dismiss', 'Close'), Binding('ctrl+x', 'dismiss', 'Close', priority=True),
                Binding('ctrl+o', 'primary', 'Confirm', priority=True), Binding('ctrl+g', 'app.keys', 'Help', priority=True)]

    def action_primary(self):
        """^O runs the main enabled button (Clone, Preview/Create, Record, Save)."""
        buttons = [b for b in self.query(Button) if not b.disabled and b.display and b.id and not b.id.endswith(('close', 'back'))]
        primary = next((b for b in buttons if b.variant == 'primary'), buttons[0] if buttons else None)
        if primary:
            primary.press()

    def idle(self):
        if self.app.runner.active or any(j.status in {'queued', 'cancelling'} for j in self.app.runner.jobs) or self.app.developer_busy:
            raise ValueError('Wait for the build queue and Developer probe before changing runtime files')


class CloneProfileScreen(FormScreen):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    def compose(self):
        p = self.settings.profile
        with Vertical():
            yield Label('CLONE PROFILE · separate build directory, same source configuration')
            with VerticalScroll():
                for name, label, value in [('name', 'New name', p.name + '-copy'), ('build', 'New absolute build directory', str(p.build_path) + '-copy'),
                                            ('machine', 'Machine override', p.machine), ('distro', 'Distro override', p.distro)]:
                    yield Label(label)
                    yield Input(value=value, id='clone-' + name)
                yield Label('kas clones keep the source work directory and use a separate KAS_BUILD_DIR. Direct containers keep the build inside their mounted root.')
            with Horizontal():
                yield Button('Clone + select', id='clone-save', variant='primary')
                yield Button('Cancel', id='clone-close')

    @on(Button.Pressed, '#clone-save')
    @work(group='clone-profile', exclusive=True)
    async def save(self):
        try:
            args = [self.query_one('#clone-' + key, Input).value.strip() for key in ('name', 'build', 'machine', 'distro')]
            profile = dev.clone_profile(self.settings, *args)
            if profile.mode == 'kas-container':
                try:
                    await dev.prepare_kas_work(profile)
                except (ValueError, OSError) as exc:
                    self.notify('Clone saved; runtime preparation unavailable: ' + str(exc), severity='warning', timeout=15)
            self.dismiss(profile.name)
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity='error')

    @on(Button.Pressed, '#clone-close')
    def close(self):
        self.dismiss(None)


class ScaffoldScreen(FormScreen):
    def __init__(self, profile):
        super().__init__()
        self.profile = copy.deepcopy(profile)
        self.plan = None

    def compose(self):
        with Vertical():
            yield Label('NEW LAYER + RECIPE · licensed source fixture · preview before creating')
            with VerticalScroll(id='scaffold-fields'):
                for key, label, value in [('path', 'New absolute runtime layer directory', '/work/meta-bitloom-dev' if self.profile.mode != 'host' else str(self.profile.root_path / 'meta-bitloom-dev')),
                    ('name', 'Recipe name', 'bitloom-hello'), ('collection', 'Layer collection', 'bitloomdev'),
                    ('owner', 'MIT copyright owner', 'Your Company'), ('series', 'Compatible Yocto series (space-separated)', 'scarthgap'),
                    ('overlay', 'New kas YAML in the host project (kas profiles only)', 'kas-bitloom-dev.yml')]:
                    yield Label(label)
                    yield Input(value=value, id='scaffold-' + key)
                yield Label('Build system')
                yield Select([(s.title(), s) for s in ('cmake', 'meson', 'make', 'python', 'rust')], value='cmake', allow_blank=False, id='scaffold-system')
            yield TextArea('', read_only=True, id='scaffold-preview')
            with Horizontal():
                yield Button('Preview', id='scaffold-review')
                yield Button('Create + register', id='scaffold-create', variant='primary', disabled=True)
                yield Button('Fields', id='scaffold-back')
                yield Button('Cancel', id='scaffold-close')

    def on_mount(self):
        self.query_one('#scaffold-preview').display = False

    def spec(self):
        result = {key: self.query_one('#scaffold-' + key, Input).value.strip() for key in ('path', 'name', 'collection', 'owner', 'series', 'overlay')}
        result['system'] = str(self.query_one('#scaffold-system', Select).value)
        return result

    @on(Button.Pressed, '#scaffold-review')
    def preview(self):
        try:
            spec = self.spec()
            if not Path(spec['path']).is_absolute():
                raise ValueError('Layer path must be absolute in the selected runtime')
            files = dev.scaffold_plan(spec['name'], spec['collection'], spec['system'], spec['owner'], spec['series'])
            overlay = dev.kas_overlay(self.profile, spec['path'], spec['name'], spec['overlay'])
            if overlay and (Path(spec['overlay']).is_absolute() or '..' in Path(spec['overlay']).parts or not spec['overlay'].endswith(('.yml', '.yaml'))):
                raise ValueError('Choose a new YAML path relative to the host project root')
            text = '\n'.join('+++ ' + name + '\n' + body for name, body in files.items())
            text += '\nHOST KAS OVERLAY\n' + (overlay or 'Host/direct container: bitbake-layers add-layer ' + spec['path'])
            self.plan = (spec, files, overlay)
            self.query_one('#scaffold-preview', TextArea).load_text(text)
            self.query_one('#scaffold-preview').display = True
            self.query_one('#scaffold-fields').display = False
            self.query_one('#scaffold-create', Button).disabled = False
        except ValueError as exc:
            self.notify(str(exc), severity='error')

    @on(Button.Pressed, '#scaffold-back')
    def back(self):
        self.query_one('#scaffold-fields').display = True
        self.query_one('#scaffold-preview').display = False
        self.query_one('#scaffold-create', Button).disabled = True

    @on(Button.Pressed, '#scaffold-create')
    @work(group='scaffold', exclusive=True)
    async def create(self):
        overlay_path = None
        try:
            self.idle()
            if not self.plan or self.plan[0] != self.spec():
                raise ValueError('Preview the current fields before creating')
            spec, files, overlay = self.plan
            if overlay:
                overlay_path = self.profile.root_path / spec['overlay']
                if overlay_path.exists() or overlay_path.is_symlink():
                    raise ValueError('kas overlay already exists; choose a new filename')
            self.app.developer_busy = True
            result = await dev.inspect(self.profile, 'scaffold', spec['path'], files=files)
            if overlay:
                overlay_path.parent.mkdir(parents=True, exist_ok=True)
                with overlay_path.open('x') as stream:
                    stream.write(overlay)
                # Preserve the base profile; its clone selects the new composition.
                p = copy.deepcopy(self.profile)
                p.name = self.profile.name + '-' + spec['name']
                counter = 2
                while p.name in {v.name for v in self.app.settings.profiles}:
                    p.name = self.profile.name + '-' + spec['name'] + '-' + str(counter)
                    counter += 1
                p.kas_file = spec['overlay']
                self.app.settings.profiles.append(p)
                self.app.settings.active = p.name
                self.app.settings.save()
                result['text'] += '\nCreated host kas overlay: ' + str(overlay_path) + '\nSelected profile: ' + p.name + '\nRun kas build/Parse to evaluate registration.'
            else:
                self.app.runner.submit(self.profile, 'Register generated layer', ['bitbake-layers', 'add-layer', spec['path']], 'layer-add')
            self.dismiss(result)
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity='error', timeout=15)
        finally:
            self.app.developer_busy = False

    @on(Button.Pressed, '#scaffold-close')
    def close(self):
        self.dismiss(None)


class DevicesScreen(FormScreen):
    def on_mount(self):
        self.query_one('#devices-json', TextArea).focus()

    def __init__(self, directory):
        super().__init__()
        self.path = Path(directory) / 'devices.json'

    def compose(self):
        sample = {'devices': [{'name': 'my-board', 'ssh': 'root@192.168.7.2', 'labgrid_place': '',
                    'console_argv': ['picocom', '-b', '115200', '/dev/ttyUSB0'],
                    'test_argv': ['ssh', '-o', 'BatchMode=yes', '{device}', 'uname -a']}]}
        with Vertical():
            yield Label('DEVICE PROFILES · real equipment only · arguments are arrays')
            yield Label('Placeholders: {device}, {artifact}, {recipe}, {place}. An empty labgrid_place uses SSH/custom console. Save does not contact a device.')
            yield TextArea(self.path.read_text() if self.path.exists() else json.dumps(sample, indent=2), id='devices-json')
            with Horizontal():
                yield Button('Save devices', id='devices-save', variant='primary')
                yield Button('Close', id='devices-close')

    @on(Button.Pressed, '#devices-save')
    def save(self):
        temporary = self.path.with_suffix('.tmp')
        try:
            text = self.query_one('#devices-json', TextArea).text
            json.loads(text)
            temporary.write_text(text)
            temporary.chmod(0o600)
            dev.load_devices(temporary)
            temporary.replace(self.path)
            self.dismiss(True)
        except (OSError, ValueError, TypeError) as exc:
            temporary.unlink(missing_ok=True)
            self.notify(str(exc), severity='error')

    @on(Button.Pressed, '#devices-close')
    def close(self):
        self.dismiss(False)


class DispositionScreen(FormScreen):
    def __init__(self, directory, issue):
        super().__init__()
        self.path = Path(directory) / 'security-reviews.json'
        self.issue = issue

    def compose(self):
        with Vertical():
            yield Label('REVIEW · ' + self.issue['package'] + ' · ' + self.issue['id'])
            with VerticalScroll():
                for key, label in [('owner', 'Review owner'), ('reason', 'Reason / evidence reference'), ('expiry', 'Expiry (YYYY-MM-DD)')]:
                    yield Label(label)
                    yield Input(id='review-' + key)
                yield Label('This records a disposition; it does not mark the upstream vulnerability patched or change its report.')
            with Horizontal():
                yield Button('Record review', id='review-save', variant='primary')
                yield Button('Cancel', id='review-close')

    @on(Button.Pressed, '#review-save')
    def save(self):
        try:
            dev.security_disposition(self.path, self.issue, *[self.query_one('#review-' + key, Input).value for key in ('owner', 'reason', 'expiry')])
            self.dismiss(True)
        except (ValueError, OSError) as exc:
            self.notify(str(exc), severity='error')

    @on(Button.Pressed, '#review-close')
    def close(self):
        self.dismiss(False)


class DeveloperPanel(Vertical):
    DEFAULT_CSS = '''
    DeveloperPanel { height: 1fr; }
    DeveloperPanel .dev-tools { height: 1; margin-bottom: 1; }
    DeveloperPanel .dev-tools Input { width: 1fr; }
    DeveloperPanel #dev-view { width: 26; }
    DeveloperPanel #dev-operation { width: 24; }
    DeveloperPanel #dev-state { height: 2; color: $text-muted; }
    DeveloperPanel #dev-split { height: 1fr; }
    DeveloperPanel #dev-rows { width: 45%; }
    DeveloperPanel #dev-detail { width: 55%; height: 1fr; margin-left: 1; }
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = None
        self.report_profile = None
        self.report_view = None
        self.report_job = None
        self.stale = False
        self.busy = False
        self.rows = []
        self.last_view = None
        self.next_profile = None

    def compose(self):
        with ToolBar(classes='dev-tools'):
            yield Select(dev.VIEWS, value='variable', allow_blank=False, id='dev-view')
            yield Input(value='busybox', placeholder='Recipe / mc:CONFIG:RECIPE', id='dev-recipe')
            yield Button('Inspect', id='dev-inspect', variant='primary')
        with Horizontal(classes='dev-tools'):
            yield Input(value='SUMMARY', id='dev-first')
            yield Input(id='dev-second')
        with ToolBar(classes='dev-tools', max_rows=2):
            yield Select([('No queued operation', 'none')], value='none', allow_blank=False, id='dev-operation')
            yield Button('Run', id='dev-execute')
            yield Button('Open', id='dev-open')
            yield Button('Capture', id='dev-capture')
            yield Button('Compare', id='dev-compare')
            yield Button('New layer', id='dev-scaffold')
            yield Button('Clone', id='dev-clone')
            yield Button('Devices', id='dev-devices')
        with Horizontal(classes='dev-tools'):
            yield Input(placeholder='Local baseline capture JSON for Compare', id='dev-baseline')
        yield Static('Inspect real runtime evidence; Enter opens the selected row.', id='dev-state', markup=False)
        with Horizontal(id='dev-split'):
            yield DataTable(id='dev-rows', cursor_type='row')
            yield RichLog(id='dev-detail', wrap=True, markup=False, auto_scroll=False)

    def on_mount(self):
        table = self.query_one('#dev-rows', DataTable)
        table.add_column('Item', width=22)
        table.add_column('Value / state')
        table.border_title = 'Evidence'
        self.query_one('#dev-detail', RichLog).border_title = 'Detail'
        self.fields()
        self.set_interval(15, self.check_stale)

    def field(self, key):
        return self.query_one('#dev-' + key, Input).value.strip()

    @property
    def view(self):
        return str(self.query_one('#dev-view', Select).value)

    @on(Select.Changed, '#dev-view')
    def fields(self):
        if not self.is_mounted:
            return
        view = self.view
        if self.last_view is not None and self.last_view != view:
            self.query_one('#dev-first', Input).value = {'variable':'SUMMARY', 'ide':'core-image-minimal'}.get(view, '')
            self.query_one('#dev-second', Input).value = ''
        self.last_view = view
        a, b = dev.HINTS[view]
        self.query_one('#dev-first', Input).placeholder = a
        self.query_one('#dev-second', Input).placeholder = b
        if self.data and view != self.report_view:
            self.query_one('#dev-state', Static).update('Choose Inspect to load this view; previous capture remains available.')
        operations = {
            'rebuild': [('Dump signatures', 'signatures')],
            'ide': [('Generate IDE SDK', 'ide-sdk'), ('Export IDE mappings / database', 'ide-export'), ('Devtool modify', 'dev-modify'), ('Build workspace', 'dev-build')],
            'image': [('Trace selected package inclusion', 'inclusion')],
            'downloads': [('Prepare source mirrors', 'mirror'), ('Verify fetch offline', 'offline-fetch'), ('Verify full build offline', 'offline-build')],
            'kernel': [('Kernel config check', 'kernel-fragments'), ('Export kernel diff', 'kernel-diff'), ('Menuconfig (terminal)', 'menuconfig')],
            'upgrade': [('Check latest version', 'dev-latest'), ('Check upgrade status', 'dev-upgrade-status'), ('Upgrade recipe', 'dev-upgrade')],
            'board': [('Fleet status (all devices)', 'fleet'), ('Device status', 'status'), ('Deploy recipe', 'deploy'), ('Undeploy recipe', 'undeploy'), ('Run device test', 'test'),
                      ('Console (terminal)', 'console'), ('Acquire labgrid place', 'acquire'), ('Release labgrid place', 'release'), ('Power cycle place', 'power')],
            'security': [('Record selected issue review', 'review')],
            'config': [('Generate kas lock', 'kas-lock')],
            'capabilities': [('Prepare new kas workspace', 'prepare-work')],
            'recipe': [('Build recipe', 'build'), ('Devtool modify', 'dev-modify')],
        }.get(view, [('No queued operation', 'none')])
        selector = self.query_one('#dev-operation', Select)
        selector.set_options(operations)
        selector.value = operations[0][1]
        self.query_one('#dev-execute', Button).disabled = operations[0][1] == 'none'

    def ensure_idle(self):
        if self.busy or self.app.developer_busy or self.app.runner.active or any(j.status in {'queued', 'cancelling'} for j in self.app.runner.jobs):
            raise ValueError('Wait for the current build queue or Developer probe')

    def display_report(self, data, profile=None, view=None, job=None):
        self.data, self.rows = data, data.get('rows', [])[:2000]
        self.report_profile = copy.deepcopy(profile or self.app.profile)
        self.report_view, self.report_job = view or self.view, job
        self.stale = False
        table = self.query_one('#dev-rows', DataTable)
        table.clear()
        for i, row in enumerate(self.rows):
            table.add_row(Text(str(row.get('name', ''))), Text(str(row.get('value', ''))), key=str(i))
        output = self.query_one('#dev-detail', RichLog)
        output.clear()
        output.write(Text(data['title'] + '\n\n' + data.get('text', '')[:50000]))
        output.scroll_home(animate=False)
        self.query_one('#dev-state', Static).update(self.report_profile.name + ' · ' + data['title'] + ' · ' + str(len(self.rows)) + ' rows')

    @on(Button.Pressed, '#dev-inspect')
    @work(group='developer', exclusive=True)
    async def load(self):
        try:
            self.ensure_idle()
            self.busy = self.app.developer_busy = True
            profile = copy.deepcopy(self.next_profile or self.app.profile)
            self.next_profile = None
            view, recipe, first, second = self.view, self.field('recipe'), self.field('first'), self.field('second')
            self.query_one('#dev-state', Static).update('Inspecting ' + profile.name + ' / ' + view + '…')
            job = None
            if view == 'config':
                data = await self.config_report(profile, first or recipe)
            elif view == 'board':
                devices = dev.load_devices(self.app.store.directory / 'devices.json')
                rows = [{'name': d['name'], 'value': d.get('ssh') or d.get('labgrid_place') or 'custom console/test', 'device': d} for d in devices]
                files = sorted((self.app.store.directory / 'device-evidence').glob('*.json')) if (self.app.store.directory / 'device-evidence').exists() else []
                history = {row['id']: row for row in self.app.store.history()}
                evidence = []
                for file in files[-10:]:
                    item = json.loads(file.read_text())
                    saved = history.get(item.get('job'))
                    if saved: item.update(status=saved['status'], exit_code=saved['code'])
                    log = Path(item.get('log', ''))
                    if log.is_file(): item['output_tail'] = log.read_text(errors='replace')[-8000:]
                    evidence.append(item)
                data = report('DEVICE LABORATORY', rows, json.dumps(evidence, indent=2) if evidence else 'Configure Devices, select a real board, then run a command. No hardware results are simulated.', evidence=evidence)
            else:
                op, path, kwargs = view, '', {'recipe': recipe}
                if view == 'variable': kwargs['variable'] = first or 'SUMMARY'
                if view == 'browse': path = first or dev.runtime_build(profile); kwargs['query'] = second
                if view in {'rebuild', 'shutdown'}: path = first or dev.runtime_build(profile)
                if view == 'performance': path = first; kwargs['build'] = dev.runtime_build(profile)
                if view in {'security', 'failure', 'downloads', 'kernel'}: path = first
                if view in {'image', 'upgrade', 'capabilities'}: kwargs['recipe'] = first or recipe
                if view == 'kernel': kwargs['config'] = second
                if view == 'failure':
                    selected = first or str(self.app.selected_log or '')
                    if not selected:
                        raise ValueError('Select a failed build or enter a task log path')
                    path = selected
                    if not first and self.app.selected_job_id:
                        history = next((row for row in self.app.store.history() if row['id'] == self.app.selected_job_id), None)
                        if history:
                            metadata = json.loads(history['metadata'])
                            profile = Profile.from_dict(metadata['profile'])
                            job = {'id': history['id'], 'log': history['log'], 'status': history['status']}
                    if Path(path).is_file(): kwargs['text'] = Path(path).read_text(errors='replace')[:32*1024*1024]
                if view == 'downloads' and path and Path(path).is_file(): kwargs['text'] = Path(path).read_text(errors='replace')[:32*1024*1024]; path = ''
                data = await dev.inspect(profile, op, path, **kwargs)
                if view == 'capabilities':
                    self.app.capability_cache[(profile.name, kwargs['recipe'])] = data
                if view == 'ide':
                    data['source_mappings'] = dev.ide_mappings(profile)
                    data['text'] += '\nPATH MAPPING\nRuntime root: ' + profile.container_root + '\nHost root: ' + str(profile.root_path) + '\nFor kas-container, use its actual KAS_WORK_DIR mapping; host paths may belong to the container daemon filesystem.'
                if view == 'shutdown':
                    data['text'] += '\nORIGINAL JOB OBSERVATIONS\n' + '\n'.join(json.dumps({'job': j.id, 'status': j.status, 'stop_confirmed': j.stop_confirmed, 'observations': getattr(j, 'shutdown_evidence', {})}) for j in self.app.runner.jobs[-10:])
                if view == 'security':
                    reviews = self.app.store.directory / 'security-reviews.json'
                    if reviews.exists():
                        try:
                            data['reviews'] = dev.read_reviews(reviews)
                        except ValueError as exc:
                            data['reviews'] = {}
                            data['text'] += f'\n{exc}'
                            reviews = None
                    if reviews and reviews.exists():
                        data['text'] += '\nRECORDED DISPOSITIONS\n' + reviews.read_text()
                        for row in data['rows']:
                            issue = row.get('issue')
                            if issue:
                                review = data['reviews'].get(issue['package'] + '/' + issue['id'])
                                if review:
                                    expired = review['expires'] < datetime.now(timezone.utc).strftime('%Y-%m-%d')
                                    row['value'] += ' · ' + ('EXPIRED review' if expired else 'reviewed by ' + review['owner']) + ' · expires ' + review['expires']
            self.display_report(data, profile, view, job)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.query_one('#dev-state', Static).update('Unavailable: ' + str(exc)[-500:])
            self.notify(str(exc)[-1000:], severity='warning', timeout=12)
        finally:
            self.busy = self.app.developer_busy = False

    async def config_report(self, profile, recipe):
        from .commands import invocation
        from .leases import BuildLease
        from .runtime import request
        lease = BuildLease(profile)
        lease.acquire()
        try:
            cap = await request(profile, 'dev-capabilities', '', recipe=recipe)
            rows = [{'name': 'multiconfig', 'value': value} for value in cap.get('multiconfig', [])]
            rows += [{'name': name, 'value': str(value)} for name, value in cap.get('identity', {}).items()]
            if profile.mode not in {'kas', 'kas-container', 'wrapper'}:
                return report('PROFILE / MULTICONFIG CONTEXT', rows, json.dumps(asdict(profile), indent=2), identity=cap['identity'])
            inv = invocation(profile, ['kas', 'dump'])
            process = await asyncio.create_subprocess_exec(*inv.argv, cwd=inv.cwd, env=inv.env,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            try:
                output, _ = await asyncio.wait_for(process.communicate(), 120)
            finally:
                if process.returncode is None:
                    process.kill(); await process.wait()
            if process.returncode: raise ValueError(output.decode(errors='replace')[-3000:])
            return report('RESOLVED KAS / MULTICONFIG', rows, output.decode(errors='replace'), identity=cap['identity'], multiconfig=cap.get('multiconfig'))
        finally:
            lease.close()

    def selected(self):
        table = self.query_one('#dev-rows', DataTable)
        return self.rows[table.cursor_row] if self.rows and table.cursor_row < len(self.rows) else {}

    @on(DataTable.RowSelected, '#dev-rows')
    @on(Button.Pressed, '#dev-open')
    @work(group='developer-open', exclusive=True)
    async def open_row(self):
        try:
            self.ensure_idle()
            row = self.selected()
            if row.get('evidence'):
                output = self.query_one('#dev-detail', RichLog)
                output.clear(); output.write(Text(row['name'] + '\n' + row['evidence']))
                return
            if row.get('device'):
                self.query_one('#dev-first', Input).value = row['device']['name']
                return
            path = row.get('path')
            if not path:
                self.query_one('#dev-detail', RichLog).write(Text(json.dumps(row, indent=2)))
                return
            from .runtime import request
            from .leases import BuildLease
            profile = self.report_profile or self.app.profile
            lease = BuildLease(profile); lease.acquire()
            try:
                from .developer_agent import stamp
                # Query directory state in the runtime, never on the host by accident.
                info = await request(profile, 'dev-fingerprints', '', paths=[path])
                if row.get('directory') or row.get('name') in {'S', 'B', 'T', 'WORKDIR', 'RECIPE_SYSROOT', 'RECIPE_SYSROOT_NATIVE'}:
                    self.query_one('#dev-view', Select).value = 'browse'
                    self.fields()
                    self.query_one('#dev-first', Input).value = path
                    self.query_one('#dev-second', Input).value = ''
                    lease.close()
                    self.next_profile = profile
                    self.load()
                    return
                data = await request(profile, 'read', path)
            finally:
                lease.close()
            from .screens import RuntimeFileScreen
            editable = not Path(path).name.startswith(('log.do_', 'run.do_', 'do_')) and '.sigdata.' not in path
            self.app.push_screen(RuntimeFileScreen(profile, data, editable=editable, line=row.get('line', 1)), lambda _: self.mark_stale())
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity='warning')

    def mark_stale(self):
        self.stale = True
        self.query_one('#dev-state', Static).update('STALE · metadata may have changed; Inspect again before comparing')

    @work(group='developer-stale', exclusive=True)
    async def check_stale(self):
        if self.busy or self.app.developer_busy or self.app.runner.active or any(j.status == 'queued' for j in self.app.runner.jobs) or len(self.app.screen_stack) > 1:
            return
        if self.app.main_query('#workspace', TabbedContent).active != 'developer' or not self.data:
            return
        fingerprints = self.data.get('fingerprints', [])
        if fingerprints:
            try:
                current = await dev.inspect(self.report_profile, 'fingerprints', paths=[p['path'] for p in fingerprints], hashes=self.data.get('fingerprint_hashes', True))
                if current != fingerprints:
                    self.app.capability_cache.clear()
                    self.mark_stale()
                    if self.report_view == 'browse': self.load()
            except (ValueError, OSError):
                self.mark_stale()

    @on(Button.Pressed, '#dev-capture')
    def capture(self):
        try:
            if not self.data: raise ValueError('Inspect a view first')
            if self.stale: raise ValueError('Evidence is stale; Inspect again before capturing')
            path = dev.capture(self.app.store.directory, self.report_profile, self.report_view, self.data, self.report_job)
            if not self.field('baseline'): self.query_one('#dev-baseline', Input).value = str(path)
            self.notify('Saved capture: ' + str(path), timeout=10)
        except (ValueError, OSError) as exc:
            self.notify(str(exc), severity='warning')

    @on(Button.Pressed, '#dev-compare')
    def compare(self):
        try:
            if not self.data or self.stale: raise ValueError('Inspect current evidence before comparing')
            before = json.loads(Path(self.field('baseline')).expanduser().read_text())
            after = {'view': self.report_view, 'data': self.data}
            data = dev.compare_captures(before, after)
            path = dev.capture(self.app.store.directory, self.report_profile, self.report_view + '-diff', data, self.report_job)
            output = self.query_one('#dev-detail', RichLog)
            output.clear(); output.write(Text(data['title'] + '\n' + '\n'.join(row['name'] + ': ' + row['value'] for row in data['rows']) + '\n' + data['text']))
            output.scroll_home(animate=False)
            self.notify('Comparison saved: ' + str(path), timeout=10)
        except (ValueError, OSError, KeyError) as exc:
            self.notify(str(exc), severity='warning')

    @on(Button.Pressed, '#dev-scaffold')
    def scaffold(self):
        self.app.push_screen(ScaffoldScreen(self.app.profile), self.scaffold_result)

    def scaffold_result(self, data):
        if data:
            self.app.profiles_result(True)
            self.display_report(data, view='recipe')

    @on(Button.Pressed, '#dev-clone')
    def clone(self):
        self.app.push_screen(CloneProfileScreen(self.app.settings), lambda result: self.app.profiles_result(bool(result)))

    @on(Button.Pressed, '#dev-devices')
    def devices(self):
        self.app.push_screen(DevicesScreen(self.app.store.directory))

    @on(Button.Pressed, '#dev-execute')
    @work(group='developer-execute', exclusive=True)
    async def execute(self):
        try:
            self.ensure_idle()
            operation = str(self.query_one('#dev-operation', Select).value)
            recipe = self.field('recipe')
            profile = self.app.profile
            if operation == 'none': return
            if operation == 'review':
                issue = self.selected().get('issue')
                if not issue: raise ValueError('Select a vulnerability issue row')
                self.app.push_screen(DispositionScreen(self.app.store.directory, issue), lambda _: self.load())
                return
            if operation == 'prepare-work':
                self.app.developer_busy = True
                self.notify(await dev.prepare_kas_work(profile), timeout=12)
                return
            if operation == 'fleet':
                from .fleet import fleet_report, fleet_status
                self.query_one('#dev-state', Static).update('Probing every configured device…')
                rows = await fleet_status(self.app.store.directory / 'devices.json')
                output = self.query_one('#dev-detail', RichLog)
                output.clear(); output.write(Text(fleet_report(rows)))
                self.query_one('#dev-state', Static).update(f'Fleet status · {len(rows)} devices')
                return
            if self.view == 'board':
                await self.device_operation(operation, recipe)
                return
            if operation == 'ide-export':
                await self.export_ide()
                return
            if operation == 'inclusion':
                if not self.data or self.report_view != 'image': raise ValueError('Inspect an image and select a package')
                package = self.selected().get('name')
                if package not in self.data.get('packages', {}): raise ValueError('Select an installed package')
                from .runtime import request
                from .leases import BuildLease
                from .workflows import provenance_report
                self.app.developer_busy = True
                lease = BuildLease(self.report_profile); lease.acquire()
                try:
                    info = await request(self.report_profile, 'provenance', dev.runtime_build(self.report_profile), package=package, image=self.data['image'])
                finally: lease.close()
                self.data.setdefault('inclusion', {})[package] = info
                output = self.query_one('#dev-detail', RichLog)
                output.clear(); output.write(Text(provenance_report(info)))
                return
            if operation == 'ide-sdk':
                from .developer_agent import target
                self.app.developer_busy = True
                data = await dev.inspect(profile, 'ide', recipe=recipe)
                if not data['ide_sdk']: raise ValueError('devtool ide-sdk is unavailable in this release')
                argv = ['devtool', 'ide-sdk', recipe, target(self.field('first') or 'core-image-minimal')]
                if self.field('second'): argv += ['--target', self.field('second')]
                self.app.runner.submit(profile, 'Generate IDE SDK: ' + recipe, argv, 'ide-sdk')
            elif operation in {'mirror', 'offline-fetch', 'offline-build'}:
                argv = dev.runtime_command('offline', recipe=recipe, prepare=operation == 'mirror', full=operation == 'offline-build')
                self.app.runner.submit(profile, 'Developer: ' + operation + ' ' + recipe, argv, operation)
            else:
                self.app.action_command(operation, recipe)
        except (ValueError, OSError, KeyError) as exc:
            self.notify(str(exc), severity='warning', timeout=12)
        finally:
            self.app.developer_busy = False

    async def device_operation(self, operation, recipe):
        devices = dev.load_devices(self.app.store.directory / 'devices.json')
        device = next((d for d in devices if d['name'] == self.field('first')), None)
        if not device: raise ValueError('Select a device row or enter its profile name')
        identity = await asyncio.to_thread(dev.device_identity, self.field('second')) if operation in {'test', 'deploy'} else None
        argv = dev.board_command(device, operation, self.field('second'), recipe)
        if not shutil.which(argv[0]) and operation not in {'deploy', 'undeploy'}:
            raise ValueError(argv[0] + ' is unavailable on the host')
        directory = self.app.store.directory / 'device-evidence'
        directory.mkdir(exist_ok=True)
        profile = self.app.profile if operation in {'deploy', 'undeploy'} else Profile(name='device-' + device['name'], root=str(directory.resolve()))
        if operation == 'console':
            if not shutil.which('script'): raise ValueError('Install util-linux script to record an interactive console')
            ident = 'console-' + uuid.uuid4().hex[:12]
            transcript = directory / (ident + '.log')
            evidence_path = directory / (ident + '.json')
            evidence_path.write_text(json.dumps({'device': device['name'], 'operation': 'console', 'job': None,
                                                'log': str(transcript), 'status': 'opening'}, indent=2))
            evidence_path.chmod(0o600)
            self.app.run_interactive_for(profile, ['script', '--quiet', '--return', '--flush', '--command', shlex.join(argv), str(transcript)], evidence_path)
            return
        job = self.app.runner.submit(profile, device['name'] + ': ' + operation, argv, 'device-' + operation)
        evidence = {'device': device['name'], 'operation': operation, 'artifact_reference': identity,
                    'artifact_deployed_by_command': False, 'recipe': recipe, 'job': job.id, 'log': str(job.log),
                    'note': 'The artifact hash is a test reference. devtool deploy transfers recipe outputs, not this image file.'}
        path = directory / (job.id + '.json')
        path.write_text(json.dumps(evidence, indent=2)); path.chmod(0o600)
        self.notify('Queued device operation; evidence: ' + str(path), timeout=12)

    async def export_ide(self):
        if not self.data or self.report_view != 'ide': raise ValueError('Inspect the IDE bridge first')
        mappings = dev.ide_mappings(self.report_profile)
        directory = self.app.store.directory / 'exports' / ('ide-' + uuid.uuid4().hex[:12])
        directory.mkdir(parents=True)
        payload = {'sourceFileMap': mappings, 'gdb_substitute_path': ['set substitute-path ' + shlex.quote(a) + ' ' + shlex.quote(b) for a, b in mappings.items()],
                   'note': 'Use a remote/container IDE when toolchains/sysroots are not accessible on the client host. Configure source_mappings in F4 for kas paths.'}
        mapping = directory / 'path-mappings.json'
        mapping.write_text(json.dumps(payload, indent=2)); mapping.chmod(0o600)
        databases = [row['path'] for row in self.rows if row.get('path', '').endswith('compile_commands.json')]
        if databases:
            from .runtime import request
            from .leases import BuildLease
            lease = BuildLease(self.report_profile); lease.acquire()
            try:
                self.app.developer_busy = True
                result = await request(self.report_profile, 'read', databases[0])
            finally: lease.close()
            entries = dev.map_compile_database(json.loads(result['text']), mappings)
            path = directory / 'compile_commands.json'
            path.write_text(json.dumps(entries, indent=2)); path.chmod(0o600)
        self.notify('Exported IDE mappings' + (' and compile database' if databases else '; compile database unavailable') + ': ' + str(directory), timeout=15)
