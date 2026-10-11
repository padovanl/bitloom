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
        await pilot.pause(.2)
        assert list((tmp_path / 'state/exports').glob('vulnerabilities-*.csv'))
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
