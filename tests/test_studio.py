"""Studio: layers, distributions, machines, images, recipes and appends."""
import pytest
from pathlib import Path

from bitloom.cli import make_demo
from bitloom.models import Profile
from bitloom.studio import create, fields, kas_overlay, plan


def values(kind, series, layers, **extra):
    result = {f.id: f.default for f in fields(kind, series, layers)}
    result.update(extra)
    return result


def test_plans_follow_the_release(tmp_path):
    profile = Profile(root=str(tmp_path))
    distro = plan('distro', values('distro', 'wrynose', [], new_layer='meta-acme', supplier='Acme'), profile, 'wrynose')
    text = distro['files']['conf/distro/acme.conf']
    assert 'require conf/distro/poky.conf' in text and 'INIT_MANAGER = "systemd"' in text and 'SPDX_IMAGE_SUPPLIER_name = "Acme"' in text
    assert 'LAYERSERIES_COMPAT_acme = "wrynose"' in distro['files']['conf/layer.conf'] and distro['activate'] == {'distro': 'acme'}
    old = plan('distro', values('distro', 'scarthgap', [], new_layer='meta-acme', supplier='Acme'), profile, 'scarthgap')
    assert 'SPDX_IMAGE_SUPPLIER' not in old['files']['conf/distro/acme.conf'] and 'INIT_MANAGER = "sysvinit"' in old['files']['conf/distro/acme.conf']
    assert 'SPDX_SUPPLIER = "Organization: Acme"' in old['files']['conf/distro/acme.conf']
    image_fields = {f.id: f for f in fields('image', 'wrynose', [])}
    assert 'debug-tweaks' not in image_fields['features'].choices and 'allow-root-login' in image_fields['features'].choices
    assert 'debug-tweaks' in {f.id: f for f in fields('image', 'scarthgap', [])}['features'].choices
    with pytest.raises(ValueError, match='debug-tweaks'):
        plan('image', values('image', 'wrynose', [], new_layer='meta-acme', features='debug-tweaks'), profile, 'wrynose')
    machine = plan('machine', values('machine', 'wrynose', [], new_layer='meta-acme'), profile, 'wrynose')
    assert 'require conf/machine/qemux86-64.conf' in machine['files']['conf/machine/acme-board.conf']
    append = plan('append', values('append', 'wrynose', [], new_layer='meta-acme'), profile, 'wrynose')
    assert '${UNPACKDIR}/motd' in append['files']['recipes-core/base-files/base-files_%.bbappend']
    assert '${WORKDIR}/motd' in plan('append', values('append', 'scarthgap', [], new_layer='meta-acme'), profile, 'scarthgap')['files']['recipes-core/base-files/base-files_%.bbappend']
    recipe = plan('recipe', values('recipe', 'wrynose', [], new_layer='meta-acme'), profile, 'wrynose')
    assert 'recipes-example/acme-hello/acme-hello_1.0.bb' in recipe['files']
    with pytest.raises(ValueError):
        plan('distro', values('distro', 'wrynose', [], new_layer='Bad Name'), profile, 'wrynose')


def test_create_into_existing_layer_never_overwrites(tmp_path):
    profile = Profile(root=str(tmp_path))
    first = plan('layer', values('layer', 'scarthgap', []), profile, 'scarthgap')
    create(profile, first)
    layer = tmp_path / 'meta-acme'
    assert (layer / 'conf/layer.conf').exists()
    with pytest.raises(ValueError, match='exists'):
        create(profile, first)
    image = plan('image', values('image', 'scarthgap', [layer], layer=str(layer)), profile, 'scarthgap')
    assert not image['new_layer']
    create(profile, image)
    assert (layer / 'recipes-core/images/acme-image.bb').exists()
    with pytest.raises(ValueError, match='never overwrites'):
        create(profile, image)
    outside = dict(image, layer='/etc', new_layer=False)
    with pytest.raises(ValueError, match='only inside'):
        create(profile, outside)
    (tmp_path / '.git').mkdir()  # the project is the repository: kas resolves url-less repos to its top
    kas = Profile(root=str(tmp_path), mode='kas', kas_file='kas.yml')
    name, text = kas_overlay(kas, plan('distro', values('distro', 'wrynose', [], new_layer='meta-new'), kas, 'wrynose'))
    # No url and no path: the repository holding the overlay; a relative path would resolve against KAS_WORK_DIR.
    assert name == 'kas-studio-meta-new.yml' and 'distro: acme' in text and 'layers:\n      "meta-new":' in text and 'path:' not in text
    _, existing = kas_overlay(kas, image)
    assert 'repos:' not in existing and 'target: acme-image' in existing


async def test_studio_keyboard_flow(tmp_path):
    from textual.widgets import Input, OptionList
    from bitloom.app import BitloomApp
    from bitloom.screens import StudioScreen
    app = BitloomApp(make_demo(tmp_path / 'demo'), tmp_path / 'state')
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause(.5)
        await pilot.press('2', 'c')
        await pilot.pause(.5)
        screen = app.screen
        assert isinstance(screen, StudioScreen) and screen.kind == 'distro'
        await pilot.press('up')                                              # arrows switch the form
        await pilot.pause(.4)
        assert screen.kind == 'layer' and screen.query('#f-collection')
        await pilot.press('down')
        await pilot.pause(.4)
        assert screen.kind == 'distro'
        assert screen.query_one('#f-layer').value.endswith('meta-demo')      # existing product layer offered first
        screen.query_one('#f-name', Input).value = 'demo-os'
        await pilot.pause(.3)
        assert screen.plan and 'conf/distro/demo-os.conf' in screen.plan['files']
        await pilot.press('ctrl+o')
        await pilot.pause(.5)
        assert not isinstance(app.screen, StudioScreen)
        assert (tmp_path / 'demo/meta-demo/conf/distro/demo-os.conf').exists()
        assert app.profile.distro == 'demo-os'
    app.store.close()


def test_fields_explain_themselves_and_errors_name_the_field(tmp_path):
    """Every field says which section it belongs to; choices explain what they mean; errors point at a field."""
    from bitloom.studio import FieldError, SECTIONS, explain
    for kind in ("layer", "distro", "machine", "image", "recipe", "append"):
        for field in fields(kind, "wrynose", []):
            assert field.section in SECTIONS, (kind, field.id)
            if field.kind in {"choice", "multi"} and field.id not in {"layer", "priority", "license"}:
                assert field.hints, (kind, field.id)          # every option set is explained
    profile = Profile(name="p", root=str(tmp_path), mode="host")
    with pytest.raises(FieldError) as error:
        plan("image", values("image", "wrynose", [], size="lots"), profile, "wrynose")
    assert error.value.field == "size"
    with pytest.raises(FieldError) as error:
        plan("distro", values("distro", "wrynose", [], name="Acme"), profile, "wrynose")
    assert error.value.field == "name"
    result = plan("distro", values("distro", "wrynose", []), profile, "wrynose")
    assert result["main"] == "conf/distro/acme.conf"
    steps = explain(profile, result, use=False)
    assert "new layer meta-acme" in steps[0] and "bitbake-layers add-layer" in steps[1] and 'DISTRO = "acme"' in steps[2]
    assert "Set DISTRO acme in profile p" in explain(profile, result, use=True)[2]
    kas = Profile(name="k", root=str(tmp_path), mode="kas-container", kas_file="kas.yml")
    image = plan("image", values("image", "wrynose", []), kas, "wrynose")
    assert image["main"] == "recipes-core/images/acme-image.bb"
    assert any("kas-studio-meta-acme.yml" in step and "builds acme-image" in step for step in explain(kas, image, use=False))


def test_web_studio_lists_layers_and_creates_with_edits(tmp_path):
    """The web Studio shows where files go (your layers and their files) and creates planned files
    as edited by hand before Create."""
    import json
    import threading
    import urllib.error
    import urllib.request
    from bitloom.daemon import rpc
    from bitloom.web import Dashboard, create_server
    config = make_demo(tmp_path / 'demo')
    board = Dashboard(config, tmp_path / 'state', token='t')
    server = create_server(board, '127.0.0.1', 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'

    def call(path, body=None):
        request = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {'X-Bitloom-Token': 't', 'Content-Type': 'application/json'})
        try:
            return json.loads(urllib.request.urlopen(request).read())
        except urllib.error.HTTPError as error:
            return {'status': error.code, **json.loads(error.read())}
    try:
        layers = call('/api/studio/layers?profile=demo')['layers']
        mine = next(l for l in layers if l['name'] == 'meta-demo')
        assert mine['writable'] and 'conf/layer.conf' in call('/api/studio/files?profile=demo&layer=' + urllib.request.quote(mine['path']))['files']
        values = {f['id']: f['default'] for f in call('/api/studio/fields?profile=demo&kind=image')['fields']}
        values['layer'] = mine['path']
        plan = call('/api/studio/preview', {'profile': 'demo', 'kind': 'image', 'values': values})
        edited = plan['files'][plan['main']] + 'IMAGE_LINGUAS = ""\n'
        created = call('/api/studio/create', {'profile': 'demo', 'kind': 'image', 'values': values, 'edits': {plan['main']: edited, 'not-planned.bb': 'x'}})
        path = next(p for p in created['written'] if p.endswith(plan['main']))
        assert Path(path).read_text() == edited and not any(p.endswith('not-planned.bb') for p in created['written'])
    finally:
        server.shutdown()
        try:
            rpc(board.state, {'op': 'stop'})
        except (OSError, ValueError):
            pass
