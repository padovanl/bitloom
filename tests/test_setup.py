"""Guided project setup: detection, checks, saving and live reload in TUI and web."""
import json
import os
import pytest

from bitloom.models import Profile, Settings
from bitloom.setup import check, detect, save


def project(tmp_path):
    root = tmp_path / 'product'
    (root / 'boards').mkdir(parents=True)
    (root / 'boards/board-a.yml').write_text('header:\n  version: 14\nmachine: qemuarm64\ntarget: product-image\nrepos:\n  meta-product:\n')
    (root / 'boards/common.yml').write_text('header:\n  version: 14\nrepos:\n  poky:\n    url: https://git.yoctoproject.org/poky\n')
    script = root / 'run_build.sh'
    script.write_text('#!/bin/bash\n# Project launcher\nkas-container "$1" "${YML}"\n')
    script.chmod(0o755)
    (root / 'poky').mkdir()
    (root / 'poky/oe-init-build-env').write_text('# init\n')
    (root / 'build/conf').mkdir(parents=True)
    (root / 'build/conf/local.conf').write_text('MACHINE = "qemux86-64"\n')
    return root


def test_detects_launchers_kas_files_and_host_builds(tmp_path):
    root = project(tmp_path)
    candidates = detect(root)
    modes = [c.mode for c in candidates]
    assert modes[0] == 'wrapper' and 'host' in modes and any(m in {'kas', 'kas-container'} for m in modes)
    wrapper = candidates[0].profile
    assert wrapper['launcher'] == ['./run_build.sh'] and wrapper['environment'] == {'YML': 'boards/board-a.yml'}
    kas = next(c for c in candidates if c.mode in {'kas', 'kas-container'})
    assert kas.profile['kas_file'] == 'boards/board-a.yml' and kas.profile['machine'] == 'qemuarm64' and kas.profile['targets'] == ['product-image']
    host = next(c for c in candidates if c.mode == 'host')
    assert host.profile['init_script'] == 'poky/oe-init-build-env' and host.profile['machine'] == 'qemux86-64'
    rows = dict((m, s) for s, m in check(Profile.from_dict(wrapper)))
    assert rows['launcher ./run_build.sh'] == 'OK' and rows['YML=boards/board-a.yml'] == 'OK'
    bad = check(Profile(name='x', root=str(root), mode='kas-container', kas_file='missing.yml'))
    assert ('ERR', 'kas file missing.yml') in bad and ('ERR', 'set KAS_WORK_DIR to a separate directory') in bad


def test_save_replaces_first_run_default(tmp_path, monkeypatch):
    root = project(tmp_path)
    monkeypatch.chdir(root)
    settings = Settings(tmp_path / 'state/profiles.json')
    assert [p.name for p in settings.profiles] == ['default']
    save(settings, Profile.from_dict(detect(root)[0].profile))
    saved = json.loads((tmp_path / 'state/profiles.json').read_text())
    assert [p['name'] for p in saved['profiles']] == ['product-run-build'] and saved['active'] == 'product-run-build'


async def test_tui_wizard_saves_and_reloads(tmp_path, monkeypatch):
    from textual.widgets import Input
    from bitloom.app import BitloomApp
    from bitloom.screens import SetupScreen
    root = project(tmp_path)
    monkeypatch.chdir(root)
    app = BitloomApp(tmp_path / 'state/profiles.json', tmp_path / 'state')
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause(.8)
        assert isinstance(app.screen, SetupScreen)          # first run opens the wizard
        screen = app.screen
        assert screen.candidates[0].mode == 'wrapper'
        await pilot.press('down')                           # second proposal
        await pilot.pause(.2)
        assert screen.query_one('#setup-name', Input).value == screen.candidates[1].profile['name']
        await pilot.press('up')
        await pilot.pause(.2)
        await pilot.press('ctrl+o')
        await pilot.pause(.6)
        assert not isinstance(app.screen, SetupScreen)
        assert app.profile.name == 'product-run-build' and app.profile.mode == 'wrapper'
        assert app.main_query('#profile').value == 'product-run-build'
        from bitloom.screens import ProjectsScreen
        await pilot.press('9', 'w')                          # projects hub from Configuration
        await pilot.pause(.5)
        assert isinstance(app.screen, ProjectsScreen)
        await pilot.press('o')
        app.screen.query_one('#open-dir', Input).value = str(root)
        await pilot.press('enter')
        await pilot.pause(.5)
        # The folder already has a profile: Bitloom switches to it instead of asking again.
        assert not isinstance(app.screen, SetupScreen) and app.profile.name == 'product-run-build'
    app.store.close()


def test_web_setup_endpoints(tmp_path):
    import threading
    import urllib.request
    from bitloom.cli import make_demo
    from bitloom.web import Dashboard, create_server
    root = project(tmp_path)
    board = Dashboard(make_demo(tmp_path / 'demo'), tmp_path / 'state', token='t')
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'

    def call(path, body=None):
        request = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {'X-Bitloom-Token': 't', 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(request).read())
    try:
        found = call('/api/setup/scan?dir=' + str(root))['candidates']
        assert found[0]['mode'] == 'wrapper'
        checks = call('/api/setup/check', {'profile': found[0]['profile']})['checks']
        assert all(row['status'] != 'ERR' for row in checks)
        assert call('/api/setup/save', {'profile': found[0]['profile']})['active'] == 'product-run-build'
        assert Settings(board.config).active == 'product-run-build'
    finally:
        server.shutdown()


def test_kas_work_directory_of_a_profile_is_recognised(tmp_path):
    """Scanning a kas work directory offered a plain host build; it now names the profile that owns it."""
    from bitloom.models import Profile
    from bitloom.setup import detect
    work = tmp_path / 'work'
    (work / 'openembedded-core').mkdir(parents=True)
    (work / 'openembedded-core/oe-init-build-env').write_text('# init\n')
    (work / 'build/conf').mkdir(parents=True)
    (work / 'build/conf/local.conf').write_text('MACHINE = "qemux86-64"\n')
    owner = Profile(name='product', root=str(tmp_path), mode='kas-container', kas_file='kas.yml', environment={'KAS_WORK_DIR': str(work)})
    host = next(c for c in detect(work, [owner]) if c.mode == 'host')
    assert 'kas work directory of profile product' in host.evidence[0] and host.score == 1 and host.hints
    assert 'kas work directory' not in detect(work)[0].evidence[0]


def products(tmp_path):
    """A launcher with two products sharing a base file, the way company projects pick what to build."""
    (tmp_path / "kas").mkdir()
    (tmp_path / "kas/base.yml").write_text("header:\n  version: 14\nmachine: qemux86-64\ntarget: core-image-minimal\nrepos:\n  poky:\n")
    (tmp_path / "kas/alpha.yml").write_text("header:\n  version: 14\n  includes:\n    - kas/base.yml\n")
    (tmp_path / "kas/beta.yml").write_text("header:\n  version: 14\n  includes:\n    - kas/base.yml\nmachine: qemuarm64\ntarget:\n  - beta-image\n  - beta-sdk\n")
    script = tmp_path / "run_kas.sh"
    script.write_text('#!/bin/bash\nTOP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\nexport KAS_WORK_DIR=$TOP/builds/$(basename "$YML" .yml)\n'
                      'cmd=$1; shift\nexec kas-container "$cmd" "$@" "$YML"\n')
    script.chmod(0o755)
    return script


def test_wrapper_per_product_with_includes_and_work_dir(tmp_path):
    """YML=<product>.yml ./run_kas.sh build projects: one profile per product, fragments skipped,
    machine resolved through includes and KAS_WORK_DIR read from the script."""
    from bitloom.setup import check, detect, kas_files, script_work_dir
    from bitloom.models import Profile
    script = products(tmp_path)
    assert [p.name for p in kas_files(tmp_path)][-1] == "base.yml"          # the fragment comes last
    wrappers = [c for c in detect(tmp_path) if c.mode == "wrapper"]
    assert [c.profile["name"] for c in wrappers] == ["alpha", "beta"]
    alpha, beta = (c.profile for c in wrappers)
    assert alpha["environment"] == {"YML": "kas/alpha.yml", "KAS_WORK_DIR": str(tmp_path / "builds/alpha")}
    assert (alpha["machine"], alpha["targets"]) == ("qemux86-64", ["core-image-minimal"])
    assert (beta["machine"], beta["targets"]) == ("qemuarm64", ["beta-image", "beta-sdk"])
    assert wrappers[0].title == "YML=kas/alpha.yml ./run_kas.sh build"
    kas_proposals = [c.profile["kas_file"] for c in detect(tmp_path) if c.mode != "wrapper"]
    assert "kas/alpha.yml" in kas_proposals                                  # includes-only files are configurations too
    results = check(Profile.from_dict(alpha))
    assert any(status == "WARN" and "no build" in text for status, text in results)
    (tmp_path / "builds/alpha/build/conf").mkdir(parents=True)
    assert any(status == "OK" and text.startswith("build directory") for status, text in check(Profile.from_dict(alpha)))
    script.write_text("#!/bin/bash\nKAS_WORK_DIR=$SOMETHING/x kas-container build $YML\n")
    assert script_work_dir(script, tmp_path, {"YML": "kas/alpha.yml"}) == ""
    assert any("does not seem to pass its arguments" in text for _, text in check(Profile.from_dict(alpha)))


async def test_tui_save_all_products(tmp_path, monkeypatch):
    """^A in the guided setup saves one profile per product; the first is active, P switches."""
    from bitloom.app import BitloomApp
    from bitloom.models import Settings
    from bitloom.screens import SetupScreen
    root = tmp_path / "project"
    root.mkdir()
    products(root)
    monkeypatch.chdir(root)
    app = BitloomApp(tmp_path / "state/profiles.json", tmp_path / "state")
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause(.8)
        assert isinstance(app.screen, SetupScreen)
        await pilot.press("ctrl+a")
        await pilot.pause(.8)
        assert not isinstance(app.screen, SetupScreen) and app.profile.name == "alpha"
    app.store.close()
    saved = Settings(tmp_path / "state/profiles.json")
    assert [p.name for p in saved.profiles] == ["alpha", "beta"] and saved.active == "alpha"
    assert {p.environment["YML"] for p in saved.profiles} == {"kas/alpha.yml", "kas/beta.yml"}


def test_web_saves_all_products(tmp_path):
    import json
    import threading
    import urllib.request
    from bitloom.models import Settings
    from bitloom.setup import detect
    from bitloom.web import Dashboard, create_server
    root = tmp_path / "project"
    root.mkdir()
    products(root)
    board = Dashboard(tmp_path / "state/profiles.json", tmp_path / "state", token="t")
    server = create_server(board, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        found = [c.profile for c in detect(root) if c.mode == "wrapper"]
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/setup/save", json.dumps({"profiles": found}).encode(),
                                         {"X-Bitloom-Token": "t", "Content-Type": "application/json"})
        assert json.loads(urllib.request.urlopen(request).read()) == {"active": "alpha", "saved": ["alpha", "beta"]}
        saved = Settings(tmp_path / "state/profiles.json")
        assert [p.name for p in saved.profiles] == ["alpha", "beta"] and saved.active == "alpha"
    finally:
        server.shutdown()


def test_work_dir_default_with_nested_expansion(tmp_path):
    from bitloom.setup import script_work_dir
    script = tmp_path / 'run.sh'
    script.write_text('#!/bin/bash\nexport KAS_WORK_DIR="${KAS_WORK_DIR:-$PWD/build-${YML%.yml}}"\nkas-container "$@" "$YML"\n')
    assert script_work_dir(script, tmp_path, {'YML': 'kas/panel.yml'}) == str(tmp_path / 'build-kas/panel')


def test_bitbake_setup_workspaces_and_availability(tmp_path):
    """bitbake-setup: workspaces are proposed as host profiles; its operations exist only when the project's
    BitBake ships the tool, and fragments only with bitbake-config-build."""
    from bitloom.commands import BY_ID, arguments, availability, invocation
    from bitloom.models import Profile
    top = tmp_path / "bitbake-builds"
    setup_dir = top / "poky-master-poky-distro_poky-machine_qemux86-64"
    (setup_dir / "build/conf").mkdir(parents=True)
    (setup_dir / "config").mkdir()
    (setup_dir / "layers/bitbake/bin").mkdir(parents=True)
    (top / "site.conf").write_text("")
    (setup_dir / "build/init-build-env").write_text("# generated\n")
    (setup_dir / "build/conf/toolcfg.conf").write_text('OE_FRAGMENTS += "core/yocto/sstate-mirror-cdn distro/poky machine/qemux86-64"\n')
    for tool in ("bitbake", "bitbake-config-build"):
        (setup_dir / "layers/bitbake/bin" / tool).write_text("#!/bin/sh\n")
    [candidate] = [c for c in detect(top) if c.title.startswith("bitbake-setup")]
    profile = Profile.from_dict(candidate.profile)
    assert (profile.mode, profile.init_script, profile.machine, profile.distro) == ("host", "build/init-build-env", "qemux86-64", "poky")
    assert "source build/init-build-env >/dev/null" in invocation(profile, ["bitbake", "busybox"]).argv[-1]
    ok, reason = availability(BY_ID["setup-status"], "wrynose", profile)
    assert ok is False and "bitbake-setup is not in this project's BitBake" in reason      # this BitBake lacks it
    (setup_dir / "layers/bitbake/bin/bitbake-setup").write_text("#!/bin/sh\n")
    assert availability(BY_ID["setup-status"], "wrynose", profile) == (True, "")
    assert availability(BY_ID["fragment-enable"], "wrynose", profile)[0] is True
    assert arguments(BY_ID["fragment-enable"], {"fragment": "core/yocto/sstate-mirror-cdn"})[-1] == "core/yocto/sstate-mirror-cdn"
    with pytest.raises(ValueError):
        arguments(BY_ID["fragment-enable"], {"fragment": "rm -rf"})
    poky = Profile(name="old", root=str(tmp_path / "poky-checkout"), mode="host")
    (tmp_path / "poky-checkout/bitbake/bin").mkdir(parents=True)
    (tmp_path / "poky-checkout/bitbake/bin/bitbake").write_text("")
    ok, reason = availability(BY_ID["fragments"], "scarthgap", poky)
    assert ok is False and "bitbake-config-build is not in this project's BitBake" in reason and "scarthgap" in reason


def test_machine_and_distro_where_the_build_has_them(tmp_path):
    """The top bars show MACHINE and DISTRO from wherever the build takes them, and nothing when nothing says it."""
    from bitloom.models import Profile
    from bitloom.setup import machine_and_distro
    root = tmp_path / "p"
    (root / "kas").mkdir(parents=True)
    (root / "kas/base.yml").write_text("header:\n  version: 14\nmachine: qemuarm64\ndistro: poky\n")
    (root / "kas/product.yml").write_text("header:\n  version: 14\n  includes:\n    - kas/base.yml\ndistro: acme\n")
    kas = Profile(name="k", root=str(root), mode="kas-container", kas_file="kas/product.yml")
    assert machine_and_distro(kas) == {"MACHINE": "qemuarm64", "DISTRO": "acme"}
    wrapper = Profile(name="w", root=str(root), mode="wrapper", launcher=["./run.sh"], environment={"YML": "kas/base.yml"})
    assert machine_and_distro(wrapper) == {"MACHINE": "qemuarm64", "DISTRO": "poky"}
    (root / "build/conf").mkdir(parents=True)
    (root / "build/conf/toolcfg.conf").write_text('OE_FRAGMENTS += "machine/genericarm64 distro/poky-altcfg"\n')
    host = Profile(name="h", root=str(root), mode="host")
    assert machine_and_distro(host) == {"MACHINE": "genericarm64", "DISTRO": "poky-altcfg"}
    (root / "build/conf/toolcfg.conf").unlink()
    (root / "build/conf/local.conf").write_text('MACHINE ?= "qemux86-64"\n')
    assert machine_and_distro(host) == {"MACHINE": "qemux86-64", "DISTRO": ""}
    assert machine_and_distro(Profile(name="x", root=str(root), mode="host", machine="board", distro="mine")) == {"MACHINE": "board", "DISTRO": "mine"}


def test_kas_owns_the_generated_configuration(tmp_path):
    """With kas, local.conf is generated from local_conf_header: findings point there, the migration skips the copy."""
    from bitloom.models import Profile
    from bitloom.setup import kas_local_conf_lines, profile_kas_files
    root = tmp_path / "p"
    (root / "build/conf").mkdir(parents=True)
    (root / "kas.yml").write_text('header:\n  version: 14\nmachine: qemux86-64\nlocal_conf_header:\n  base: |\n    IMAGE_FSTYPES = "tar.bz2"\n    INHERIT += "rm_work"\n'
                                  '  extra: |\n    IMAGE_INSTALL:append = " htop"\nrepos:\n  x:\n    path: x\n')
    (root / "build/conf/local.conf").write_text('IMAGE_FSTYPES = "tar.bz2"\nINHERIT += "rm_work"\nIMAGE_INSTALL:append = " htop"\nDEPENDS_append = " x"\n')
    profile = Profile(name="k", root=str(root), mode="kas-container", kas_file="kas.yml")
    assert profile_kas_files(profile) == [(root / "kas.yml").resolve()]
    assert kas_local_conf_lines(root / "kas.yml") == [(6, 'IMAGE_FSTYPES = "tar.bz2"'), (7, 'INHERIT += "rm_work"'), (9, 'IMAGE_INSTALL:append = " htop"')]
    from bitloom.practices import review
    rows = {r["id"]: r for r in review(profile, [], "wrynose")["rules"]}
    where = {f["where"] for f in rows["product-config-in-layers"]["findings"]}
    assert where == {"kas.yml:6", "kas.yml:9"}
    assert rows["buildhistory"]["findings"][0]["where"] == "kas.yml (local_conf_header)"
    from bitloom.migration import Context
    ctx = Context(profile, [], profile_kas_files(profile))
    assert (root / "build/conf/local.conf") not in ctx.files and (root / "kas.yml").resolve() in ctx.files
