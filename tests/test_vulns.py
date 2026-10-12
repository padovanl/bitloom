"""Vulnerability findings: Yocto CVE JSON (cve-check / sbom-cve-check), Grype, reviews, gates."""
import json

from bitloom.cli import prepare_demo
from bitloom.models import Profile, Settings
from bitloom.vulns import counts, load, parse_grype, parse_yocto, select, severity_of, sources

GRYPE = {"matches": [{"vulnerability": {"id": "CVE-2024-0001", "severity": "High", "description": "overflow",
                                        "cvss": [{"metrics": {"baseScore": 7.5}}], "fix": {"versions": ["1.2.4"], "state": "fixed"}},
                      "artifact": {"name": "zlib", "version": "1.2.3"}}]}


def wrynose(tmp_path):
    settings = Settings(prepare_demo(tmp_path / 'state'))
    return next(p for p in settings.profiles if p.name == 'demo-wrynose')


def test_parsers_and_severity(tmp_path):
    profile = wrynose(tmp_path)
    found = sources(profile, tmp_path / 'state')
    assert found and found[0][0].startswith('sbom-cve-check')
    findings = parse_yocto(found[0][1], 'sbom-cve-check')
    assert {f.id for f in findings} >= {'CVE-0000-0001', 'CVE-0000-0002'}
    critical = next(f for f in findings if f.id == 'CVE-0000-0002')
    assert critical.score == 9.8 and critical.severity == 'critical' and critical.package == 'busybox'
    grype = tmp_path / 'scan.grype.json'
    grype.write_text(json.dumps(GRYPE))
    row = parse_grype(grype)[0]
    assert row.id == 'CVE-2024-0001' and row.severity == 'high' and row.detail == 'fixed in 1.2.4' and row.source == 'grype'
    assert severity_of(None) == 'unknown' and severity_of(4.0) == 'medium'


def test_load_merges_reviews_and_filters(tmp_path):
    profile = wrynose(tmp_path)
    state = tmp_path / 'state'
    (state / 'security-reviews.json').write_text(json.dumps({'busybox/CVE-0000-0002': {'owner': 'alice', 'expires': '2027-01-01'}}))
    scans = state / 'vulnerability-scans'
    scans.mkdir()
    (scans / 'img.grype.json').write_text(json.dumps(GRYPE))
    findings, errors = load(profile, state)
    assert not errors and {f.source for f in findings} == {'sbom-cve-check', 'grype'}
    assert findings[0].status == 'Unpatched' and findings[0].severity == 'critical'      # ordered by urgency
    assert next(f for f in findings if f.id == 'CVE-0000-0002').review == 'alice until 2027-01-01'
    c = counts(findings)
    assert c['unpatched'] == 4 and c['patched'] == 1 and c['ignored'] == 1 and c['reviewed'] == 1
    assert [f.id for f in select(findings, 'unpatched', 9.0)] == ['CVE-0000-0002']
    assert [f.id for f in select(findings, 'reviewed')] == ['CVE-0000-0002']
    assert [f.id for f in select(findings, 'all', 0, 'zlib')] == ['CVE-2024-0001']


def test_cli_gate_and_cra_row(tmp_path, capsys, monkeypatch):
    import argparse, sys
    from bitloom import cli
    from bitloom.sbom import cra_checks
    profile = wrynose(tmp_path)
    rows = {item: (status, detail) for status, item, detail in cra_checks(profile, tmp_path / 'state')}
    assert rows['Unpatched vulnerabilities'][0] == 'WARN' and '3 unpatched' in rows['Unpatched vulnerabilities'][1]
    config = tmp_path / 'wry.json'
    data = {'active': 'demo-wrynose', 'profiles': [profile.__dict__]}
    config.write_text(json.dumps(data))
    for argv, code in ((['--vulns', '--fail-on-unpatched', '--min-cvss', '9'], 2), (['--vulns', '--fail-on-unpatched', '--min-cvss', '9.9'], 0)):
        monkeypatch.setattr(sys, 'argv', ['bitloom', '--config', str(config), '--state', str(tmp_path / 'state'), *argv])
        try:
            cli.main()
        except SystemExit as exit:
            assert exit.code == code
    assert 'CVE-0000-0002' in capsys.readouterr().out


async def test_tui_vulnerabilities_keyboard(tmp_path):
    from textual.widgets import Input
    from bitloom.app import BitloomApp
    from bitloom.developer_ui import DispositionScreen
    from bitloom.screens import VulnerabilitiesScreen
    config = prepare_demo(tmp_path / 'state')
    settings = Settings(config); settings.active = 'demo-wrynose'; settings.save()
    app = BitloomApp(config, tmp_path / 'state')
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause(.5)
        await pilot.press('6', 'v')
        await pilot.pause(.5)
        screen = app.screen
        assert isinstance(screen, VulnerabilitiesScreen) and len(screen.shown) == 3 and screen.shown[0].id == 'CVE-0000-0002'
        await pilot.press('slash')
        for key in 'openssh':
            await pilot.press(key)
        await pilot.pause(.2)
        assert [f.id for f in screen.shown] == ['CVE-0000-0001']
        await pilot.press('enter', 'x')
        await pilot.pause(.3)
        await pilot.press('enter')          # first format: Markdown
        await pilot.pause(.3)
        report = next((tmp_path / 'state/exports').glob('vulnerabilities-demo-wrynose-*.md')).read_text()
        assert 'CVE-0000-0001' in report and 'CVE-0000-0002' not in report.split('## How to act')[0]   # the filter applies
        assert 'https://nvd.nist.gov/vuln/detail/CVE-0000-0001' in report
        await pilot.press('r')
        await pilot.pause(.3)
        assert isinstance(app.screen, DispositionScreen)
    app.store.close()


def test_web_vulnerabilities(tmp_path):
    import threading, urllib.request
    from bitloom.web import Dashboard, create_server
    config = prepare_demo(tmp_path / 'state')
    board = Dashboard(config, tmp_path / 'state', token='t')
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        request = urllib.request.Request(f'http://127.0.0.1:{server.server_address[1]}/api/vulnerabilities?profile=demo-scarthgap&status=all',
                                         headers={'X-Bitloom-Token': 't'})
        data = json.loads(urllib.request.urlopen(request).read())
        assert data['sources'] == ['cve-check summary'] and data['counts']['total'] == 5 and data['shown'] == 5
        assert set(data['scanners']) == {'grype', 'vulnscout'}
    finally:
        server.shutdown()


def test_exports_carry_links_and_filters(tmp_path):
    import csv, io
    from bitloom.vulnexport import FORMATS, build, links
    profile = wrynose(tmp_path)
    state = tmp_path / 'state'
    md, name = build(profile, state, 'md')
    assert name.endswith('.md') and '## Unpatched (3)' in md and '[OSV](https://osv.dev/vulnerability/CVE-0000-0002)' in md
    assert '<details>' not in md                       # unpatched only: no patched/ignored block
    full, _ = build(profile, state, 'md', status='all')
    assert '## Patched and ignored (2)' in full and 'CVE_STATUS' in full
    page, _ = build(profile, state, 'html', status='all')
    assert page.startswith('<!doctype html>') and '<script' not in page and 'href="https://www.cve.org/CVERecord?id=CVE-0000-0002"' in page
    rows = list(csv.DictReader(io.StringIO(build(profile, state, 'csv')[0])))
    assert rows[0]['id'] == 'CVE-0000-0002' and rows[0]['nvd'].endswith('CVE-0000-0002')
    data = json.loads(build(profile, state, 'json', min_score=8)[0])
    assert [f['id'] for f in data['findings']] == ['CVE-0000-0002', 'CVE-0000-0001'] and data['counts']['total'] == 5
    assert data['filters'] == 'status unpatched · CVSS ≥ 8' and data['findings'][0]['links']['NVD']
    sarif = json.loads(build(profile, state, 'sarif')[0])
    run = sarif['runs'][0]
    assert sarif['version'] == '2.1.0' and len(run['results']) == 3 and run['results'][0]['level'] == 'error'
    assert run['tool']['driver']['rules'][0]['properties']['security-severity'] == '9.8'
    assert links('GHSA-abcd-1234-wxyz')[0] == ('GitHub', 'https://github.com/advisories/GHSA-abcd-1234-wxyz')
    assert set(FORMATS) == {'md', 'html', 'csv', 'json', 'sarif'}


def test_html_export_escapes_report_text(tmp_path):
    from bitloom.vulnexport import Meta, to_html
    from bitloom.vulns import Finding
    evil = Finding(id='CVE-2026-0001', package='<img src=x onerror=alert(1)>', version='1', status='Unpatched', score=9.0,
                   severity='critical', detail='<b>x</b>', summary='', vector='', link='javascript:alert(1)', source='t')
    page = to_html([evil], [evil], Meta(profile='<script>'))
    assert '<img src=x' not in page and '<script>' not in page and '&lt;img' in page
    assert 'javascript:' not in page


def test_cli_and_web_exports(tmp_path, monkeypatch, capsys):
    import sys, threading, urllib.request
    from bitloom.cli import main
    from bitloom.web import Dashboard, create_server
    config = prepare_demo(tmp_path / 'state')
    settings = Settings(config); settings.active = 'demo-wrynose'; settings.save()
    out = tmp_path / 'report.sarif'
    monkeypatch.setattr(sys, 'argv', ['bitloom', '--config', str(config), '--state', str(tmp_path / 'state'), '--vulns', '--format', 'sarif', '-o', str(out)])
    try:
        main()
    except SystemExit as exit_code:
        assert exit_code.code == 0
    assert json.loads(out.read_text())['runs'][0]['results']
    board = Dashboard(config, tmp_path / 'state', token='t')
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        request = urllib.request.Request(f'http://127.0.0.1:{server.server_address[1]}/api/vulnerabilities/export?profile=demo-wrynose&format=html&status=all',
                                         headers={'X-Bitloom-Token': 't'})
        response = urllib.request.urlopen(request)
        assert 'attachment; filename="vulnerabilities-demo-wrynose-' in response.headers['Content-Disposition']
        assert response.headers['Content-Type'].startswith('text/html') and b'Vulnerability report' in response.read()
    finally:
        server.shutdown()
