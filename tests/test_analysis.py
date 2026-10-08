from pathlib import Path
import pytest
from bitloom.analysis import metadata_search, manifest_diff, sstate_report, warning_report
from bitloom.inspectors import Entry


def test_metadata_content_search_limits_and_missing_files(tmp_path):
    recipe = tmp_path / 'demo.bb'
    recipe.write_text('SUMMARY = "Demo"\nSRC_URI = "file://fix.patch"\n')
    entries = [Entry('demo.bb', 'bb', recipe), Entry('missing', 'bb', tmp_path/'missing')]
    result = metadata_search(entries, 'src_uri')
    assert f'{recipe}:2:' in result and 'skipped: 1' in result
    assert 'Result limit reached: 1' in metadata_search(entries, 'Demo', limit=1)
    with pytest.raises(ValueError):
        metadata_search(entries, ' ')


def test_manifest_diff_preserves_architectures_and_versions(tmp_path):
    old, new = tmp_path/'old.manifest', tmp_path/'new.manifest'
    old.write_text('busybox core2-64 1.0\nlibfoo all 2.0\nremoved all 1\n')
    new.write_text('busybox core2-64 1.1\nlibfoo arm 2.0\nadded all 1\n')
    result = manifest_diff(old,new)
    assert 'Added: 2 · Removed: 2 · Version changes: 1' in result
    assert '~ busybox [core2-64] 1.0 -> 1.1' in result
    assert '+ libfoo [arm]' in result and '- libfoo [all]' in result
    new.write_text('busybox all 1\nbusybox all 2\n')
    with pytest.raises(ValueError, match='Conflicting'):
        manifest_diff(old,new)


def test_sstate_rates_handle_zero_and_missing_current(tmp_path):
    log=tmp_path/'build.log'
    log.write_text('Sstate summary: Wanted 10 Local 3 Mirrors 2 Missed 5 Current 10\nSstate summary: Wanted 0 Local 0 Mirrors 0 Missed 0 Current 0\nSstate summary: Wanted 2 Local 0 Mirrors 1 Missed 1\n')
    result=sstate_report(log)
    assert 'hit rate: 50.0%' in result and 'current tasks: 75.0%' in result
    assert 'no wanted tasks' in result and 'Current unreported' in result


def test_warning_groups_ignore_command_header(tmp_path):
    log=tmp_path/'build.log'
    log.write_text('$ echo WARNING: ignored\n2026-10-10 10:00:00 - WARNING: fetch fallback\nWARNING: fetch fallback\nWARNING: license issue\n')
    result=warning_report(log)
    assert 'Occurrences: 3 · distinct messages: 2' in result
    assert '2 × fetch fallback' in result and 'ignored' not in result
