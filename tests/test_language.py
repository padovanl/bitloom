"""The BitBake language assistant: vocabulary from the project, completion by context, explanations, diagnostics."""
import json
import subprocess
import sys
import threading
import urllib.request

import pytest

from bitloom.language import complete, explain, lint, vocabulary
from bitloom.models import Profile


def project(tmp_path):
    root = tmp_path / "ws"
    files = {
        "meta/conf/layer.conf": 'BBFILE_COLLECTIONS += "core"\n',
        "meta/conf/documentation.conf": 'IMAGE_FEATURES[doc] = "The primary list of features to include in an image."\n'
                                         'IMAGE_INSTALL[doc] = "Packages to install into an image."\ndo_compile[doc] = "Compiles the source"\n',
        "meta/conf/bitbake.conf": 'UNPACKDIR ??= "${WORKDIR}/sources"\nSRC_URI ?= ""\n',
        "meta/conf/machine/qemuarm64.conf": 'MACHINEOVERRIDES =. "qemuall:"\n',
        "meta/files/common-licenses/MIT": "MIT\n", "meta/files/common-licenses/GPL-2.0-only": "GPL\n",
        "meta/classes-recipe/systemd.bbclass": 'SYSTEMD_AUTO_ENABLE ??= "enable"\n',
        "meta/classes-recipe/core-image.bbclass": 'IMAGE_FEATURES[validitems] += "ssh-server-openssh debug-tweaks"\nCOMPLEMENTARY_GLOB[dev-pkgs] = "*-dev"\n',
        "meta/classes-global/base.bbclass": "addtask fetch\ndo_unpack() {\n}\n",
        "meta/recipes-core/busybox/busybox_1.37.bb": 'SUMMARY = "busybox"\n',
        "meta/recipes-core/glibc/glibc-common.inc": 'SUMMARY = "glibc"\n',
        "meta-poky/conf/layer.conf": 'BBFILE_COLLECTIONS += "poky"\n', "meta-poky/conf/distro/poky.conf": 'DISTRO = "poky"\n',
        "build/conf/local.conf": 'MACHINE = "qemuarm64"\n',
    }
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    return Profile(name="lang", root=str(root), mode="host")


def test_vocabulary_and_completion(tmp_path):
    v = vocabulary(project(tmp_path))
    assert v["docs"]["IMAGE_FEATURES"].startswith("The primary list") and "do_compile" in v["tasks"] and "do_unpack" in v["tasks"]
    assert {"systemd", "core-image", "base"} <= set(v["classes"]) and "recipes-core/glibc/glibc-common.inc" in v["includes"]
    assert v["machines"] == {"qemuarm64": "meta"} and "poky" in v["distros"] and {"MIT", "GPL-2.0-only"} <= set(v["licences"])
    assert {"ssh-server-openssh", "debug-tweaks", "dev-pkgs"} <= set(v["image_features"]) and "UNPACKDIR" in v["variables"]
    labels = lambda before: [i["label"] for i in complete(v, before)["items"]]
    assert labels("IMAGE_F") == ["IMAGE_FEATURES"] and "inherit" in labels("inh")
    assert labels("inherit sys") == ["systemd"] and labels("inherit core-image sy") == ["systemd"]
    assert labels("require recipes-core/gl") == ["recipes-core/glibc/glibc-common.inc"]
    assert labels("IMAGE_INSTALL:app") == ["append"] and "qemuarm64" in labels("IMAGE_INSTALL:qemu")
    assert labels("SRC_URI[sha") == ["sha256sum"] and labels('S = "${UNPA') == ["UNPACKDIR"]
    assert labels('IMAGE_INSTALL:append = " busy') == ["busybox"] and labels('IMAGE_FEATURES += "ssh') == ["ssh-server-openssh"]
    assert labels('MACHINE = "qemu') == ["qemuarm64"] and labels('LICENSE = "MI') == ["MIT"]
    assert labels("addtask mine after do_comp") == ["do_compile"]
    result = complete(v, "inherit sys")
    assert result["from"] == len("inherit ") and result["word"] == "sys"


def test_explain(tmp_path):
    v = vocabulary(project(tmp_path))
    assert explain(v, "IMAGE_FEATURES")["kind"] == "variable" and explain(v, "inherit")["kind"] == "keyword"
    assert explain(v, "systemd")["kind"] == "class" and explain(v, "qemuarm64")["kind"] == "machine"
    assert explain(v, "IMAGE_INSTAL")["suggest"] == ["IMAGE_INSTALL"] and explain(v, "do_compile")["kind"] == "task"


def test_lint(tmp_path):
    v = vocabulary(project(tmp_path))
    text = '\n'.join([
        'SUMMARY = "x"', 'IMAGE_INSTALL:append = "htop"', 'DEPENDS_append = " zlib"', 'FILESEXTRAPATHS:prepend := "${THISDIR}/files"',
        'inherit systemmd', 'IMAGE_INSTAL += "foo"', 'LICENSE = MIT', 'MACHINE = "qemuarm65"', 'IMAGE_FEATURES += "debug-tweak dev-pkgs"',
        'SRC_URI = "file://a \\', '    file://b"', 'python do_x() {', '    bb.note("x = y")', '}', 'def helper(d):', '    continue_here = 1', '',
        'require recipes-core/missing/thing.inc', 'SUMMARY = "unclosed', 'MY_OWN_PORT = "8080"', 'inherit_defer ${@bb.utils.contains("A", "b", "c", "", d)}'])
    problems = {(p["line"], p["message"].split("”")[0]) for p in lint(v, text, "x.bb")}
    lines = {p[0] for p in problems}
    assert lines == {2, 3, 4, 5, 6, 7, 8, 9, 18, 19}, sorted(problems)
    found = {p["line"]: p for p in lint(v, text, "x.bb")}
    assert "did you mean “systemd”" in found[5]["fix"] and "IMAGE_INSTALL" in found[6]["fix"] and found[6]["level"] == "info"
    assert "debug-tweak" in found[9]["message"] and found[3]["level"] == "error" and found[2]["fix"] == 'IMAGE_INSTALL:append = " htop"'
    assert lint(v, 'python __anonymous () {\n    if True:\n        pass\n}\n', "x.bbclass") == []
    assert [p["message"] for p in lint(v, "do_install() {\n    true\n", "x.bb")] == ["a function's { is never closed"]


def test_cli_and_web(tmp_path):
    from bitloom.models import Settings
    from bitloom.web import Dashboard, create_server
    profile = project(tmp_path)
    settings = Settings(tmp_path / "profiles.json")
    settings.profiles, settings.active = [profile], "lang"
    settings.save()
    layer = tmp_path / "meta-mine/recipes-app/hello"
    layer.mkdir(parents=True)
    (layer / "hello_1.0.bb").write_text('SUMMARY = "hello"\nDEPENDS_append = " zlib"\n')
    (layer / "ok_1.0.bb").write_text('SUMMARY = "ok"\n')
    cli = lambda *a: subprocess.run([sys.executable, "-m", "bitloom", "--config", str(tmp_path / "profiles.json"), *a], capture_output=True, text=True)
    out = cli("--lint", str(tmp_path / "meta-mine"))
    assert out.returncode == 2 and "hello_1.0.bb:2: ✖ old override syntax" in out.stdout and "2 files · 1 errors" in out.stdout
    assert cli("--lint", str(layer / "ok_1.0.bb")).returncode == 0
    assert json.loads(cli("--lint", str(layer), "--format", "json").stdout)["error"] == 1
    explained = cli("--explain", "IMAGE_FEATURES")
    assert explained.returncode == 0 and "The primary list" in explained.stdout and cli("--explain", "NOPE_NOPE").returncode == 1
    board = Dashboard(tmp_path / "profiles.json", tmp_path / "state", token="t")
    server = create_server(board, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/api/lang"
    call = lambda path, body=None: json.loads(urllib.request.urlopen(urllib.request.Request(base + path, json.dumps(body).encode() if body else None,
                                                                                               {"X-Bitloom-Token": "t", "Content-Type": "application/json"})).read())
    try:
        assert [i["label"] for i in call("/complete?profile=lang&before=inherit%20sys")["items"]] == ["systemd"]
        assert call("/explain?profile=lang&word=IMAGE_FEATURES")["kind"] == "variable"
        assert call("/lint", {"profile": "lang", "text": 'DEPENDS_append = " x"\n', "filename": "a.bb"})["problems"][0]["line"] == 1
    finally:
        server.shutdown()
