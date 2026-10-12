"""Damaged inputs found by edge-case sweeps: clear messages instead of tracebacks."""
import json
import subprocess
import sys

import pytest

from bitloom.models import ConfigError, Settings


@pytest.mark.parametrize('content, message', [
    ('{nope', 'not valid JSON'),
    ('[]', 'JSON object'),
    ('{"profiles": 3}', 'array of objects'),
    ('{"active": "ghost", "profiles": [{"name": "a", "root": "/x"}]}', "active profile 'ghost'"),
    ('{"profiles": [{"name": "a", "root": null}]}', 'root must be a folder path'),
])
def test_damaged_profiles_file(tmp_path, content, message):
    path = tmp_path / 'profiles.json'
    path.write_text(content)
    with pytest.raises(ConfigError, match=message):
        Settings(path)


def test_empty_profiles_file_and_missing_active(tmp_path):
    path = tmp_path / 'profiles.json'
    path.write_text('')
    assert Settings(path).implicit_default  # like a first start
    path.write_text('{"profiles": [{"name": "b", "root": "/x"}, {"name": "c", "root": "/y"}]}')
    assert Settings(path).active == 'b'


def test_cli_reports_config_errors_without_traceback(tmp_path):
    path = tmp_path / 'profiles.json'
    path.write_text('{nope')
    result = subprocess.run([sys.executable, '-m', 'bitloom', '--config', str(path), '--state', str(tmp_path / 's'), '--cra'],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 2 and 'not valid JSON' in result.stderr and 'Traceback' not in result.stderr


def test_damaged_reviews_are_reported_and_never_overwritten(tmp_path):
    from bitloom.developer import read_reviews, security_disposition
    from bitloom.models import Profile
    from bitloom.sbom import cra_checks
    from bitloom.vulns import load
    reviews = tmp_path / 'security-reviews.json'
    reviews.write_text('[1, 2]')
    with pytest.raises(ValueError, match='must map'):
        read_reviews(reviews)
    with pytest.raises(ValueError):
        security_disposition(reviews, {'package': 'p', 'id': 'CVE-1', 'status': 'Unpatched'}, 'me', 'why', '2999-01-01')
    assert reviews.read_text() == '[1, 2]'
    profile = Profile(root=str(tmp_path))
    row = next(r for r in cra_checks(profile, tmp_path) if r[1] == 'Vulnerability dispositions')
    assert row[0] == 'WARN' and 'must map' in row[2]
    _, errors = load(profile, tmp_path)
    assert any('must map' in e for e in errors)


def test_damaged_history_database(tmp_path):
    from bitloom.store import Store
    (tmp_path / 'history.sqlite3').write_text('not a database')
    with pytest.raises(ConfigError, match='move it away'):
        Store(tmp_path)


def test_unexpected_sbom_and_report_structures(tmp_path):
    from bitloom.models import Profile
    from bitloom.sbom import analyse, sbom_report
    from bitloom.vulns import load
    images = tmp_path / 'build/tmp/deploy/images/qemux86-64'
    images.mkdir(parents=True)
    (images / 'a.rootfs.spdx.json').write_text(json.dumps({'spdxVersion': 'SPDX-2.2', 'packages': [None, {'externalRefs': None, 'name': 'x'}]}))
    (images / 'b.rootfs.spdx.json').write_text(json.dumps({'@graph': [None, {'type': {'not': 'a type'}}]}))
    (images / 'd.rootfs.spdx.json').write_text(json.dumps({'@graph': [None, {'type': 'software_Package', 'name': 'y', 'externalIdentifier': 'oops'}]}))
    (images / 'c.rootfs.sbom-cve-check.yocto.json').write_text(json.dumps({'package': 'nope'}))
    assert analyse(images / 'a.rootfs.spdx.json')['packages'] == 1
    assert analyse(images / 'd.rootfs.spdx.json')['missing_identity'] == ['y']
    with pytest.raises(ValueError, match='unexpected SPDX structure'):
        analyse(images / 'b.rootfs.spdx.json')
    assert 'unexpected SPDX structure' in sbom_report(Profile(root=str(tmp_path)))
    _, errors = load(Profile(root=str(tmp_path)), None)
    assert any('unexpected report structure' in e for e in errors)
