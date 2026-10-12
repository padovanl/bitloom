"""SBOM inspection, CRA readiness, release-aware operations and SBOM settings."""
import json
from datetime import date

import pytest

from bitloom.cli import make_demo
from bitloom.commands import BY_ID, availability
from bitloom.models import Profile

SPDX3 = {
    "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
    "@graph": [
        {"type": "CreationInfo", "@id": "_:c", "created": "2026-10-01T00:00:00Z", "createdUsing": ["http://tool"]},
        {"type": "Tool", "spdxId": "http://tool", "name": "OpenEmbedded Core create-spdx.bbclass"},
        {"type": "software_Package", "spdxId": "p1", "name": "busybox", "software_packageVersion": "1.36.1",
         "externalIdentifier": [{"type": "ExternalIdentifier", "externalIdentifierType": "packageUrl", "identifier": "pkg:yocto/busybox@1.36.1"}],
         "suppliedBy": "acme"},
        {"type": "software_Package", "spdxId": "p2", "name": "mystery"},
        {"type": "simplelicensing_LicenseExpression", "spdxId": "l1", "simplelicensing_licenseExpression": "GPL-2.0-only"},
        {"type": "Relationship", "spdxId": "r1", "relationshipType": "hasConcludedLicense", "from": "p1", "to": ["l1"]},
        {"type": "security_Vulnerability", "spdxId": "v1", "externalIdentifier": [{"externalIdentifierType": "cve", "identifier": "CVE-2026-0001"}]},
        {"type": "security_VexAffectedVulnAssessmentRelationship", "spdxId": "x1", "from": "v1", "to": ["p1"], "relationshipType": "affects"},
        {"type": "security_VexFixedVulnAssessmentRelationship", "spdxId": "x2", "from": "v1", "to": ["p1"], "relationshipType": "fixedIn"},
    ],
}
SPDX2 = {"spdxVersion": "SPDX-2.2", "creationInfo": {"created": "2024-05-01T00:00:00Z", "creators": ["Tool: OpenEmbedded Core create-spdx.bbclass"]},
         "packages": [{"name": "busybox", "versionInfo": "1.36.1", "licenseConcluded": "GPL-2.0-only", "supplier": "Organization: OpenEmbedded ()",
                       "externalRefs": [{"referenceCategory": "SECURITY", "referenceType": "cpe23Type", "referenceLocator": "cpe:2.3:a:busybox:busybox:1.36.1"}]},
                      {"name": "zlib", "versionInfo": "1.3.1", "licenseConcluded": "NOASSERTION"}]}


def core_layer(root, series):
    conf = root / 'poky/meta/conf'
    conf.mkdir(parents=True, exist_ok=True)
    (conf / 'layer.conf').write_text(f'LAYERSERIES_CORENAMES = "{series}"\n')


def test_spdx3_and_spdx2_quality(tmp_path):
    from bitloom.sbom import analyse, sbom_report
    images = tmp_path / 'build/tmp/deploy/images/qemux86-64'
    images.mkdir(parents=True)
    (images / 'core-image-minimal-qemux86-64.rootfs.spdx.json').write_text(json.dumps(SPDX3))
    first = analyse(images / 'core-image-minimal-qemux86-64.rootfs.spdx.json')
    assert first['format'] == 'SPDX 3.0.1' and first['packages'] == 2
    assert first['with_purl'] == .5 and first['with_license'] == .5 and first['with_supplier'] == .5
    assert first['vex'] == {'affected': 1, 'fixed': 1} and first['vex_examples']['affected'] == ['CVE-2026-0001']
    assert first['missing_identity'] == ['mystery'] and first['tools'] == ['OpenEmbedded Core create-spdx.bbclass']
    old = tmp_path / 'old.spdx.json'
    old.write_text(json.dumps(SPDX2))
    second = analyse(old)
    assert second['format'] == 'SPDX 2.2' and second['with_cpe'] == .5 and second['with_license'] == .5 and second['missing_license'] == ['zlib']
    text = sbom_report(Profile(root=str(tmp_path)))
    assert 'PURL  50.0%' in text and 'affected: CVE-2026-0001' in text


def test_spdx3_coverage_counts_installed_packages(tmp_path):
    """Real OE image SBOMs also list recipes (with -native build tools) and downloaded sources;
    counting them reported 55% licence coverage for an image whose packages all had one."""
    from bitloom.sbom import analyse
    graph = [dict(e) for e in SPDX3['@graph']]
    for element in graph:
        if element.get('spdxId') == 'p1':
            element['software_primaryPurpose'] = 'install'
    graph += [{"type": "software_Package", "spdxId": "r", "name": "acl-native", "software_primaryPurpose": "specification"},
              {"type": "software_Package", "spdxId": "s", "name": "acl-2.3.2.tar.gz", "software_primaryPurpose": "source"}]
    path = tmp_path / 'image.spdx.json'
    path.write_text(json.dumps({**SPDX3, '@graph': graph}))
    result = analyse(path)
    assert result['packages'] == 1 and result['with_license'] == 1.0 and result['missing_identity'] == []
    assert result['other_elements'] == {'specification': 1, 'source': 1, 'other': 1}


def test_release_detection_and_cra_timeline(tmp_path):
    from bitloom.sbom import cra_report
    from bitloom.versions import describe, detect_release
    core_layer(tmp_path, 'scarthgap')
    profile = Profile(root=str(tmp_path))
    assert detect_release(profile) == 'scarthgap' and describe('scarthgap') == 'scarthgap 5.0 LTS'
    (tmp_path / 'build/conf').mkdir(parents=True)
    (tmp_path / 'build/conf/local.conf').write_text('INHERIT += "buildhistory"\n')
    text = cra_report(profile, tmp_path / 'state', today=date(2026, 10, 12))
    assert 'scarthgap 5.0 LTS' in text and 'buildhistory enabled' in text
    assert 'in force 2026-09-11' in text and 'from     2027-12-11' in text
    assert 'INHERIT += "cve-check" (scarthgap predates sbom-cve-check' in text
    core_layer(tmp_path, 'kirkstone')
    assert 'WARN  Yocto release support' in cra_report(profile, today=date(2026, 10, 12))


def test_operations_follow_the_release():
    assert availability(BY_ID['sbom-cve-recipe'], 'scarthgap')[0] is False
    assert 'Run recipe CVE check' in availability(BY_ID['sbom-cve-recipe'], 'scarthgap')[1]
    assert availability(BY_ID['cve'], 'wrynose')[0] is False
    assert 'sbom-cve-check' in availability(BY_ID['cve'], 'wrynose')[1]
    assert availability(BY_ID['cve'], 'scarthgap')[0] is True
    assert availability(BY_ID['sbom-cve-recipe'], None)[0] is None
    assert availability(BY_ID['build'], 'kirkstone') == (True, '')


def test_ci_skips_what_the_release_lacks(tmp_path, capsys):
    import argparse
    from bitloom.ci import main
    config = make_demo(tmp_path / 'demo')
    core_layer(tmp_path / 'demo', 'scarthgap')
    args = argparse.Namespace(config=config, state=tmp_path / 'ci', ci=['sbom-cve-recipe:busybox'], profile=None,
                              junit=str(tmp_path / 'j.xml'), summary=str(tmp_path / 's.json'), annotations='github', fail_fast=False)
    assert main(args) == 1  # nothing ran successfully
    out = capsys.readouterr().out
    assert '::warning title=demo: Recipe CVE analysis from its SBOM (sbom-cve-check) · busybox skipped' in out
    summary = json.loads((tmp_path / 's.json').read_text())
    assert summary['ok'] and summary['jobs'][0]['status'] == 'skipped' and summary['jobs'][0]['release'] == 'scarthgap'
    assert '<skipped message=' in (tmp_path / 'j.xml').read_text()


def test_settings_render_apply_and_parse(tmp_path):
    from bitloom.sbom_settings import BEGIN, OPTIONS, apply, availability, current, kas_files_with_overlay, preview
    conf = tmp_path / 'build/conf'
    conf.mkdir(parents=True)
    (conf / 'local.conf').write_text('MACHINE = "qemux86-64"\nSPDX_PRETTY = "1"\n')
    host = Profile(root=str(tmp_path))
    managed, elsewhere = current(host)
    assert managed == {} and elsewhere == {'pretty': '1'}
    values = {'create-spdx': '1', 'supplier': 'Acme "Corp"', 'include-vex': 'all', 'buildhistory': '1'}
    path, backup = apply(host, values)
    text = path.read_text()
    assert text.count(BEGIN) == 1 and 'SPDX_PACKAGE_SUPPLIER_name = "Acme \'Corp\'"' in text and 'BUILDHISTORY_COMMIT = "1"' in text
    assert backup.read_text() == 'MACHINE = "qemux86-64"\nSPDX_PRETTY = "1"\n'
    apply(host, {'create-spdx': '1'})
    text = path.read_text()
    assert text.count(BEGIN) == 1 and 'SPDX_INCLUDE_VEX' not in text and text.startswith('MACHINE = "qemux86-64"')
    assert current(host)[0] == {'create-spdx': '1'}
    kas = Profile(root=str(tmp_path), mode='kas', kas_file='kas.yml')
    assert 'local_conf_header:\n  bitloom-sbom: |\n    INHERIT += "create-spdx"' in preview(kas, {'create-spdx': '1', 'sbom-cve-check': '1'})
    apply(kas, {'create-spdx': '1', 'sbom-cve-check': '1'})
    assert current(kas)[0] == {'create-spdx': '1', 'sbom-cve-check': '1'}
    assert kas_files_with_overlay(kas) == 'kas.yml:bitloom-sbom.yml'
    unverified = [o.id for o in OPTIONS if not o.verified]
    assert availability(next(o for o in OPTIONS if o.id == 'supplier'), 'wrynose')[0] is True
    assert 'verify' in availability(next(o for o in OPTIONS if o.id == 'supplier'), 'wrynose')[1] and unverified


async def test_settings_screen_keyboard_flow(tmp_path):
    from bitloom.app import BitloomApp
    from bitloom.screens import SbomSettingsScreen
    config = make_demo(tmp_path / 'demo')
    core_layer(tmp_path / 'demo', 'scarthgap')
    app = BitloomApp(config, tmp_path / 'state')
    async with app.run_test(size=(150, 46)) as pilot:
        await pilot.pause(.5)
        assert app.release == 'scarthgap'
        await pilot.press('9', 's')
        await pilot.pause(.3)
        screen = app.screen
        assert isinstance(screen, SbomSettingsScreen)
        await pilot.press('space')                       # create-spdx on
        ids = [o.id for o in __import__('bitloom.sbom_settings', fromlist=['OPTIONS']).OPTIONS]
        table = screen.query_one('#sbom-options')
        table.move_cursor(row=ids.index('sbom-cve-check'))
        await pilot.press('space')                       # refused on scarthgap
        assert 'sbom-cve-check' not in screen.values
        table.move_cursor(row=ids.index('supplier'))     # SPDX 3 only: refused on scarthgap
        await pilot.press('enter')
        assert not screen.query_one('#sbom-text').display and 'supplier' not in screen.values
        table.move_cursor(row=ids.index('include-sources'))
        await pilot.press('enter')
        assert screen.values == {'create-spdx': '1', 'include-sources': '1'}
        await pilot.press('ctrl+o')
        await pilot.pause(.3)
        assert not isinstance(app.screen, SbomSettingsScreen)
        text = (tmp_path / 'demo/build/conf/local.conf').read_text()
        assert 'INHERIT += "create-spdx"' in text and 'SPDX_INCLUDE_SOURCES = "1"' in text
    app.store.close()


def test_spdx22_image_from_manifest_and_package_documents(tmp_path):
    """Layout of a real Scarthgap build: IMAGE.spdx.tar.zst + manifest + tmp/deploy/spdx documents."""
    from bitloom.sbom import analyse, sbom_files
    tmp = tmp_path / 'build/tmp'
    images = tmp / 'deploy/images/qemux86-64'
    images.mkdir(parents=True)
    (images / 'core-image-minimal-qemux86-64.rootfs-1.manifest').write_text('busybox core2_64 1.36.1\nbase-files qemux86_64 3.0.14\nmystery core2_64 1.0\n')
    (images / 'core-image-minimal-qemux86-64.rootfs-1.spdx.tar.zst').write_bytes(b'zstd')
    packages, recipes = tmp / 'deploy/spdx/core2-64/packages', tmp / 'deploy/spdx/core2-64/recipes'
    packages.mkdir(parents=True); recipes.mkdir(parents=True)
    (tmp / 'deploy/spdx/qemux86_64/packages').mkdir(parents=True)
    (packages / 'busybox.spdx.json').write_text(json.dumps({'spdxVersion': 'SPDX-2.2', 'packages': [
        {'name': 'busybox', 'versionInfo': '1.36.1', 'licenseConcluded': 'NOASSERTION', 'licenseDeclared': 'GPL-2.0-only', 'supplier': 'Organization: OpenEmbedded ()'}]}))
    (recipes / 'recipe-busybox.spdx.json').write_text(json.dumps({'spdxVersion': 'SPDX-2.2', 'packages': [
        {'name': 'busybox', 'sourceInfo': 'CVEs fixed: CVE-2023-42364 CVE-2021-42380',
         'externalRefs': [{'referenceCategory': 'SECURITY', 'referenceType': 'http://spdx.org/rdf/references/cpe23Type', 'referenceLocator': 'cpe:2.3:*:*:busybox:1.36.1'}]}]}))
    (tmp / 'deploy/spdx/qemux86_64/packages/base-files.spdx.json').write_text(json.dumps({'spdxVersion': 'SPDX-2.2', 'packages': [
        {'name': 'base-files', 'versionInfo': '3.0.14', 'licenseDeclared': 'GPL-2.0-only', 'supplier': 'Organization: Acme'}]}))
    reverse = tmp / 'pkgdata/qemux86-64/runtime-reverse'
    reverse.mkdir(parents=True)
    (reverse / 'busybox').write_text('PN: busybox\nPV: 1.36.1\n')
    files = sbom_files(Profile(root=str(tmp_path)))
    assert [f.name for f in files] == ['core-image-minimal-qemux86-64.rootfs-1.manifest']
    result = analyse(files[0])
    assert result['packages'] == 3 and result['unresolved_packages'] == 1
    assert round(result['with_cpe'], 2) == .33 and round(result['with_license'], 2) == .67
    assert round(result['with_supplier'], 2) == .33  # the OpenEmbedded placeholder is not a supplier
    assert result['vex'] == {'CVEs recorded fixed by recipes': 2}
