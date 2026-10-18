"""Add a layer: Layer Index resolution with dependencies, URL and mirror, the kas plan, the checkout plan, web and CLI."""
import json

import pytest

from bitloom import layerindex
from bitloom.layerindex import Layer, from_url, kas_plan, mirror, resolve
from bitloom.models import Profile

# A small Layer Index: meta-virtualization needs meta-oe (needs openembedded-core) and meta-python.
INDEX = {
    "branches/": [{"id": 1, "name": "master"}, {"id": 34, "name": "wrynose"}],
    "layerItems/?filter=name%3Ameta-virtualization": [{"id": 59, "name": "meta-virtualization", "vcs_url": "https://git.yoctoproject.org/meta-virtualization", "summary": "virt"}],
    "layerItems/?filter=id:1": [{"id": 1, "name": "openembedded-core", "vcs_url": "https://git.openembedded.org/openembedded-core"}],
    "layerItems/?filter=id:2": [{"id": 2, "name": "meta-oe", "vcs_url": "https://git.openembedded.org/meta-openembedded"}],
    "layerItems/?filter=id:3": [{"id": 3, "name": "meta-python", "vcs_url": "https://git.openembedded.org/meta-openembedded"}],
    "layerBranches/?filter=layer:59": [{"id": 590, "branch": 34, "vcs_subdir": "", "collection": "virtualization-layer"}],
    "layerBranches/?filter=layer:1": [{"id": 10, "branch": 34, "vcs_subdir": "meta", "collection": "core"}],
    "layerBranches/?filter=layer:2": [{"id": 20, "branch": 34, "vcs_subdir": "meta-oe", "collection": "openembedded-layer"}],
    "layerBranches/?filter=layer:3": [{"id": 30, "branch": 34, "vcs_subdir": "meta-python", "collection": "meta-python"}],
    "layerDependencies/?filter=layerbranch:590": [{"dependency": 2, "required": True}, {"dependency": 3, "required": True}, {"dependency": 1, "required": False}],
    "layerDependencies/?filter=layerbranch:20": [{"dependency": 1, "required": True}],
    "layerDependencies/?filter=layerbranch:30": [{"dependency": 2, "required": True}],
    "layerDependencies/?filter=layerbranch:10": [],
    "layerItems/?filter=name%3Ameta-old": [{"id": 70, "name": "meta-old", "vcs_url": "https://example.com/meta-old"}],
    "layerBranches/?filter=layer:70": [{"id": 700, "branch": 1, "vcs_subdir": ""}],
}

KAS = """header:
  version: 14
machine: qemux86-64
repos:
  openembedded-core:
    url: https://git.openembedded.org/openembedded-core
    branch: wrynose
    layers:
      meta:
  meta-acme:
    path: meta-acme
local_conf_header:
  x: |
    FOO = "1"
"""


@pytest.fixture
def index(monkeypatch):
    monkeypatch.setattr(layerindex, "_get", lambda path, timeout=20: INDEX[path])


def test_resolve_with_dependencies(index):
    layers = resolve("meta-virtualization", "wrynose", {"core"})
    assert [l.name for l in layers] == ["openembedded-core", "meta-oe", "meta-python", "meta-virtualization"]
    assert layers[0].present and not layers[1].present and layers[1].subdir == "meta-oe" and layers[1].repo == "meta-openembedded"
    assert set(layers[1].required_by) == {"meta-python", "meta-virtualization"} and layers[3].branch == "wrynose"
    with pytest.raises(LookupError, match="meta-old has no wrynose branch"):
        resolve("meta-old", "wrynose", set())


def test_url_and_mirror():
    layers = from_url("https://github.com/acme/meta-acme-bsp.git", "", "wrynose")
    assert layers[0].name == "meta-acme-bsp" and layers[0].repo == "meta-acme-bsp"
    mirror(layers, "https://git.corp.example/mirrors/")
    assert layers[0].url == "https://git.corp.example/mirrors/meta-acme-bsp.git"
    with pytest.raises(ValueError, match="relative"):
        from_url("https://x.example/r.git", "../etc", "main")
    with pytest.raises(ValueError, match="URL"):
        from_url("rm -rf /", "", "main")


def test_kas_plan_groups_layers_by_repository(tmp_path, index):
    root = tmp_path / "p"
    root.mkdir()
    (root / "kas.yml").write_text(KAS)
    profile = Profile(name="k", root=str(root), mode="kas-container", kas_file="kas.yml")
    plan = kas_plan(profile, resolve("meta-virtualization", "wrynose", {"core"}))
    text = plan["text"]
    assert "  meta-openembedded:\n    url: https://git.openembedded.org/meta-openembedded\n    branch: wrynose\n    layers:\n      meta-oe:\n      meta-python:\n" in text
    assert "  meta-virtualization:\n    url: https://git.yoctoproject.org/meta-virtualization\n    branch: wrynose\n" in text
    assert text.index("meta-virtualization:") < text.index("local_conf_header:") and text.count("openembedded-core:") == 1
    # A layer of a repository the file already has goes under its layers.
    extra = kas_plan(profile, [Layer("meta-selftest", "https://git.openembedded.org/openembedded-core", "meta-selftest", "wrynose")])
    assert "      meta:\n      meta-selftest:\n" in extra["text"]
    state = tmp_path / "state"
    written = layerindex.apply_kas(profile, state, plan)
    assert (root / "kas.yml").read_text() == text and written["backup"]
    from bitloom.migration import backups, restore
    restore(state, backups(state)[0]["id"])
    assert (root / "kas.yml").read_text() == KAS


def test_checkout_plan_for_bitbake_on_the_machine(tmp_path, index):
    root = tmp_path / "p"
    (root / "layers").mkdir(parents=True)
    profile = Profile(name="h", root=str(root), mode="host", init_script="build/init-build-env")
    plan = layerindex.plan(profile, resolve("meta-virtualization", "wrynose", {"core"}), [])
    titles = [s["title"] for s in plan["steps"]]
    assert titles == ["Clone meta-openembedded", "Add meta-oe", "Add meta-python", "Clone meta-virtualization", "Add meta-virtualization"]
    clone = plan["steps"][0]["argv"]
    assert clone[:4] == ["git", "clone", "--branch", "wrynose"] and clone[-1] == str(root / "layers/meta-openembedded")
    assert plan["steps"][1]["argv"] == ["bitbake-layers", "add-layer", str(root / "layers/meta-openembedded/meta-oe")]


def test_web_plan_and_add(tmp_path, index, monkeypatch):
    import threading, urllib.request
    from bitloom.models import Settings
    from bitloom.web import Dashboard, create_server
    monkeypatch.setattr(layerindex, "branch_exists", lambda url, branch, timeout=30: True)
    root = tmp_path / "p"
    (root / "meta/conf").mkdir(parents=True)
    (root / "meta/conf/layer.conf").write_text('BBFILE_COLLECTIONS += "core"\nLAYERSERIES_CORENAMES = "wrynose"\n')
    (root / "kas.yml").write_text(KAS)
    settings = Settings(tmp_path / "profiles.json")
    settings.profiles, settings.active = [Profile(name="k", root=str(root), mode="kas", kas_file="kas.yml")], "k"
    settings.save()
    board = Dashboard(tmp_path / "profiles.json", tmp_path / "state", token="t")
    server = create_server(board, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    post = lambda path, body: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/layers/{path}",
                                         json.dumps(body).encode(), {"X-Bitloom-Token": "t", "Content-Type": "application/json"})).read())
    try:
        plan = post("plan", {"profile": "k", "name": "meta-virtualization", "mirror": "https://mirror.example/git"})
        assert plan["series"] == "wrynose" and [l["name"] for l in plan["layers"] if not l["present"]] == ["meta-oe", "meta-python", "meta-virtualization"]
        assert "https://mirror.example/git/meta-virtualization" in plan["plan"]["diff"] and not plan["warnings"]
        done = post("add", {"profile": "k", "name": "meta-virtualization", "mirror": "https://mirror.example/git"})
        assert done["written"]["written"] and "url: https://mirror.example/git/meta-openembedded" in (root / "kas.yml").read_text()
    finally:
        server.shutdown()
