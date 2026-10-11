"""Keyboard-only operation: sections, contextual keys, dialogs and nano editor keys."""
import json

from textual.widgets import DataTable, Input, Select, TabbedContent, TextArea

from bitloom.app import BitloomApp
from bitloom.cli import make_demo
from bitloom.keys import SECTIONS, SECTION_KEYS, reference_markdown
from bitloom.screens import ActionScreen, FileScreen, KeysScreen, ProfilePickerScreen


def active(app):
    return app.query_one('#workspace', TabbedContent).active


async def test_number_keys_focus_each_section_list(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.4)
        assert app.focused.id == 'history'
        for ident, number, *_ in SECTIONS:
            await pilot.press(number)
            await pilot.pause(.1)
            assert active(app) == ident
        # Cycling works in both directions, including back to Builds.
        await pilot.press('1', 'right_square_bracket')
        await pilot.pause(.1)
        assert active(app) == 'metadata' and app.focused.id == 'metadata-table'
        await pilot.press('left_square_bracket')
        await pilot.pause(.1)
        assert active(app) == 'builds' and app.focused.id == 'history'
    app.store.close()


async def test_section_keys_are_contextual_and_never_steal_typing(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.4)
        shown = {binding.key for _, binding, enabled, _ in app.screen.active_bindings.values() if enabled}
        assert {'s', 'r', 'e', 'p'} <= shown
        await pilot.press('e')
        assert app.errors_only
        await pilot.press('e')
        assert not app.errors_only
        # / focuses the section filter; typed letters stay in the field.
        await pilot.press('slash', 'e', 'r', 'r')
        assert app.focused.id == 'log-search'
        assert app.query_one('#log-search', Input).value == 'err'
        assert not app.errors_only
        await pilot.press('escape')
        assert app.focused.id == 'history'
        await pilot.press('2')
        await pilot.pause(.1)
        shown = {binding.key for _, binding, enabled, _ in app.screen.active_bindings.values() if enabled}
        assert 's' not in shown and {'b', 'm', 'n'} <= shown
        await pilot.press('j')
        assert app.query_one('#metadata-table', DataTable).cursor_row == 1
        await pilot.press('k')
        assert app.query_one('#metadata-table', DataTable).cursor_row == 0
        # t edits the build target where no section key uses t; Enter opens the build.
        await pilot.press('1', 't')
        assert app.focused.id == 'target'
        await pilot.press('enter')
        await pilot.pause(.2)
        assert isinstance(app.screen, ActionScreen)
    app.store.close()


async def test_command_center_arrows_and_enter_queue(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.3)
        await pilot.press('f2')
        await pilot.pause(.2)
        screen = app.screen
        assert isinstance(screen, ActionScreen) and screen.focused.id == 'action-search'
        for key in 'custom command':
            await pilot.press('space' if key == ' ' else key)
        await pilot.press('down', 'up')
        assert screen.query_one('#action', Select).value == 'custom'
        await pilot.press('tab', 'tab')
        assert screen.focused.id == 'field-command'
        for key in 'true':
            await pilot.press(key)
        await pilot.press('enter')
        await pilot.pause(.3)
        assert not isinstance(app.screen, ActionScreen)
        assert app.runner.jobs and app.runner.jobs[-1].command == ['true']
        await app.runner.consumer
    app.store.close()


async def test_help_picker_and_dialog_keys(tmp_path):
    config = make_demo(tmp_path / 'demo')
    data = json.loads(config.read_text())
    second = dict(data['profiles'][0], name='second')
    data['profiles'].append(second)
    config.write_text(json.dumps(data))
    app = BitloomApp(config, tmp_path / 'state')
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.3)
        await pilot.press('question_mark')
        assert isinstance(app.screen, KeysScreen)
        await pilot.press('ctrl+x')
        assert not isinstance(app.screen, KeysScreen)
        await pilot.press('ctrl+g')
        assert isinstance(app.screen, KeysScreen)
        await pilot.press('escape')
        await pilot.press('P')
        assert isinstance(app.screen, ProfilePickerScreen)
        await pilot.press('j', 'enter')
        await pilot.pause(.3)
        assert app.settings.active == 'second'
        assert app.query_one('#profile', Select).value == 'second'
    app.store.close()


async def test_nano_editor_keys(tmp_path):
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    path = tmp_path / 'demo/build/conf/local.conf'
    original = path.read_text()
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.3)
        await pilot.press('9', 'l')
        await pilot.pause(.2)
        screen = app.screen
        assert isinstance(screen, FileScreen) and screen.editable
        editor = screen.query_one('#content', TextArea)
        assert editor.has_focus
        # ^K twice accumulates two lines, ^U pastes them back at the cursor.
        await pilot.press('ctrl+k', 'ctrl+k')
        assert editor.text.splitlines()[0] == original.splitlines()[2]
        await pilot.press('ctrl+u')
        assert editor.text == original
        # ^W searches; Enter selects the match.
        await pilot.press('ctrl+w')
        for key in 'PARALLEL':
            await pilot.press(key)
        await pilot.press('enter')
        assert editor.selected_text == 'PARALLEL'
        assert editor.has_focus
        await pilot.press('ctrl+k')
        # ^X refuses once while modified, ^O writes with a backup.
        await pilot.press('ctrl+x')
        assert app.screen is screen
        await pilot.press('ctrl+o')
        await pilot.pause(.2)
        assert 'PARALLEL_MAKE' not in path.read_text()
        assert list(path.parent.glob('local.conf.bak-*'))
        await pilot.press('ctrl+x')
        assert app.screen is not screen
    app.store.close()


def test_reference_lists_every_section_key():
    text = reference_markdown()
    for keys in SECTION_KEYS.values():
        for key, _, label, _ in keys:
            assert f'| `{key}` | {label} |' in text
    assert 'Ctrl+O' in text and 'Ctrl+K' in text


async def test_console_builds_from_outside_bitloom(tmp_path):
    from bitloom.screens import ConsoleBuildsScreen
    from bitloom.inspectors import console_logs
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    cooker = tmp_path / 'demo/build/tmp/log/cooker/qemux86-64'
    (cooker / '20260102120000.log').write_text("NOTE: Tasks Summary: Attempted 5 tasks of which 5 didn't need to be rerun and all succeeded.\n")
    assert [e.detail for e in console_logs(app.profile)] == ['success', 'failed']
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause(.3)
        await pilot.press('c')
        await pilot.pause(.4)
        assert isinstance(app.screen, ConsoleBuildsScreen)
        failed = next(i for i, e in enumerate(app.screen.entries) if e.detail == 'failed')
        for _ in range(failed):
            await pilot.press('j')
        await pilot.press('enter')
        await pilot.pause(.4)
        assert app.selected_log.name == '20260101120000.log' and app.selected_job_id is None
        await pilot.press('e')
        await pilot.pause(.3)
        assert any('oe_runmake failed' in str(line.text) for line in app.query_one('#log').lines)
    app.store.close()
