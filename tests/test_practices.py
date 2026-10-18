"""Yocto best practices: built-in rules, per-project tuning and company rules, CLI and web."""
import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

from bitloom.models import Profile
from bitloom.practices import CONFIG, load_config, report, review, save_config, try_rule


def layer(root, name, conf, files=None):
    (root / name / "conf").mkdir(parents=True)
    (root / name / "conf/layer.conf").write_text(conf)
    for path, text in (files or {}).items():
        (root / name / path).parent.mkdir(parents=True, exist_ok=True)
        (root / name / path).write_text(text)


def project(tmp_path):
    root = tmp_path / "product"
    layer(root, "meta", 'BBFILE_COLLECTIONS += "core"\nLAYERSERIES_CORENAMES = "wrynose"\nLAYERSERIES_COMPAT_core = "wrynose"\n',
          {"recipes-core/busybox/busybox_1.37.bb": 'LICENSE = "GPL-2.0-only"\nLIC_FILES_CHKSUM = "file://LICENSE;md5=1"\n',
           "recipes-core/images/core-image-minimal.bb": 'LICENSE = "MIT"\ninherit core-image\n'})
    good = ('BBPATH .= ":${LAYERDIR}"\nBBFILE_COLLECTIONS += "good"\nBBFILE_PATTERN_good = "^${LAYERDIR}/"\nBBFILE_PRIORITY_good = "7"\n'
            'LAYERDEPENDS_good = "core"\nLAYERSERIES_COMPAT_good = "wrynose"\n')
    layer(root, "meta-good", good, {
        "README.md": "Good layer\n", "COPYING.MIT": "MIT\n", "SECURITY.md": "mail us\n",
        "recipes-app/hello/hello_1.0.bb": 'LICENSE = "MIT"\nLIC_FILES_CHKSUM = "file://LICENSE;md5=1"\nSRC_URI = "git://example.com/h.git;branch=main"\nSRCREV = "0123456789abcdef0123456789abcdef01234567"\n',
        "recipes-core/busybox/busybox_%.bbappend": 'FILESEXTRAPATHS:prepend := "${THISDIR}/files:"\n',
        "recipes-core/images/acme-image.bb": 'LICENSE = "MIT"\ninherit core-image\n'})
    layer(root, "bad-layer", 'BBFILE_COLLECTIONS += "bad"\nLAYERDEPENDS_bad = "core missing-layer"\nLAYERSERIES_COMPAT_bad = "scarthgap"\nDISTRO_FEATURES:append = " x11"\n', {
        "recipes-core/busybox/busybox_1.37.bb": 'LICENSE = "GPL-2.0-only"\n',
        "recipes-app/tool/tool_2.0.bb": 'SRC_URI = "https://example.com/tool-2.0.tar.gz"\nSRCREV = "${AUTOREV}"\nDEPENDS_append = " zlib"\n',
        "recipes-app/tool/files/fix.patch": "--- a\n+++ b\n",
        "recipes-app/ghost/ghost_%.bbappend": 'FILESEXTRAPATHS_prepend := "${THISDIR}/files"\n',
        "recipes-core/images/core-image-base.bbappend": 'IMAGE_INSTALL:append = " tool"\n'})
    (root / "build/conf").mkdir(parents=True)
    (root / "build/conf/local.conf").write_text('MACHINE = "qemux86-64"\nDISTRO = "poky"\nEXTRA_IMAGE_FEATURES = "debug-tweaks"\nIMAGE_INSTALL:append = " htop"\n')
    return Profile(name="p", root=str(root), mode="host")


def by_id(data):
    return {row["id"]: row for row in data["rules"]}


def test_builtin_rules_find_what_is_wrong_and_where(tmp_path):
    rows = by_id(review(project(tmp_path)))
    failing = {rid for rid, row in rows.items() if row["status"] == "fail"}
    assert {"layer-name", "layer-conf", "layer-compat", "layer-depends", "layer-readme", "layer-conf-globals", "no-copied-recipes",
            "bbappend-matches", "filesextrapaths", "override-syntax", "no-image-append", "recipe-license", "src-checksums", "srcrev-pinned",
            "patch-upstream-status", "no-debug-access", "own-distro", "product-config-in-layers", "buildhistory", "rm-work", "shared-caches"} <= failing
    where = lambda rid: " ".join(f["where"] + " " + f["detail"] for f in rows[rid]["findings"])
    assert "bad-layer" in where("layer-name") and "meta-good" not in where("layer-name")
    assert "scarthgap" in where("layer-compat") and "missing-layer" in where("layer-depends")
    assert "DISTRO_FEATURES" in where("layer-conf-globals")
    assert "ghost_%.bbappend" in where("bbappend-matches") and "busybox_%" not in where("bbappend-matches")
    assert "tool_2.0.bb:3" in where("override-syntax") and "AUTOREV" in where("srcrev-pinned")
    assert "debug-tweaks" in where("no-debug-access") and "core-image-base.bbappend" in where("no-image-append")
    assert "busybox_1.37.bb" in where("recipe-license") and "acme-image" not in where("recipe-license")    # images need no LIC_FILES_CHKSUM
    # Only your layers are judged: the upstream busybox recipe has no LIC_FILES_CHKSUM issue reported.
    assert "meta/recipes-core" not in where("recipe-license")


def test_project_tuning_and_company_rules(tmp_path):
    profile = project(tmp_path)
    save_config(profile, {"disabled": ["own-distro"], "severity": {"rm-work": "error"}, "rules": [
        {"id": "acme-maintainer", "title": "Recipes name a maintainer", "severity": "warning",
         "check": {"type": "files-must-match", "files": "*.bb", "pattern": "^MAINTAINER\\s*="}},
        {"id": "no-x11", "title": "No X11 in products", "check": {"type": "files-must-not-match", "files": "*.conf", "pattern": "x11"}},
        {"id": "codeowners", "title": "Layers list their owners", "severity": "info", "check": {"type": "layer-file-exists", "path": "CODEOWNERS"}},
        {"id": "seccomp", "title": "seccomp in DISTRO_FEATURES", "check": {"type": "variable", "name": "MACHINE", "op": "equals", "value": "acme-board"}},
    ]})
    assert (profile.root_path / CONFIG).is_file()
    rows = by_id(review(profile))
    assert rows["own-distro"]["status"] == "off" and rows["rm-work"]["severity"] == "error"
    assert rows["acme-maintainer"]["status"] == "fail" and rows["acme-maintainer"]["custom"]
    assert any("layer.conf" in f["where"] for f in rows["no-x11"]["findings"])
    assert {f["where"] for f in rows["codeowners"]["findings"]} == {"meta-good", "bad-layer"}
    assert "expected “acme-board”" in rows["seccomp"]["findings"][0]["detail"]
    text = report(review(profile), "md")
    assert text.startswith("# Yocto best practices") and "## Company" in text


def test_try_a_rule_before_saving_it(tmp_path):
    profile = project(tmp_path)
    rule = lambda check: {"id": "draft", "title": "Draft", "check": check}
    missing = try_rule(profile, rule({"type": "files-must-match", "files": "*.bb", "pattern": "^SRCREV"}))
    assert missing["status"] == "fail" and {"meta-good", "bad-layer"} == set(missing["layers"])
    assert any("busybox_1.37.bb" in f["where"] for f in missing["findings"]) and not any(f["where"].startswith("meta/") for f in missing["findings"])
    assert try_rule(profile, rule({"type": "files-must-match", "files": "*.nothing", "pattern": "x"}))["status"] == "n/a"
    assert try_rule(profile, rule({"type": "layer-file-exists", "path": "README.md"}))["findings"] == [{"where": "bad-layer", "detail": "no README.md"}]
    assert not (profile.root_path / CONFIG).exists()                       # nothing saved
    with pytest.raises(ValueError, match="regular expression"):
        try_rule(profile, rule({"type": "files-must-not-match", "files": "*.bb", "pattern": "["}))


def test_selected_distro_is_what_the_build_uses(tmp_path):
    """A distro file says DISTRO = "acme" about itself; the build still selects poky."""
    profile = project(tmp_path)
    (profile.root_path / "meta-good/conf/distro").mkdir(parents=True)
    (profile.root_path / "meta-good/conf/distro/acme.conf").write_text('DISTRO = "acme"\nDISTRO_FEATURES:append = " seccomp"\n')
    equals = lambda name, value: try_rule(profile, {"id": "dd", "title": "d", "check": {"type": "variable", "name": name, "op": "equals", "value": value}})["status"]
    assert equals("DISTRO", "acme") == "fail" and equals("DISTRO", "poky") == "pass"
    assert try_rule(profile, {"id": "ss", "title": "s", "check": {"type": "variable", "name": "DISTRO_FEATURES", "op": "contains", "value": "seccomp"}})["status"] == "pass"
    profile.distro = "acme"
    assert equals("DISTRO", "acme") == "pass"


@pytest.mark.parametrize("bad, message", [
    ({"rules": [{"id": "layer-name", "title": "x", "check": {"type": "layer-file-exists", "path": "a"}}]}, "already used"),
    ({"rules": [{"id": "x1", "title": "x", "check": {"type": "shell", "command": "rm -rf /"}}]}, "check.type"),
    ({"rules": [{"id": "x1", "title": "x", "check": {"type": "files-must-match", "files": "*.bb", "pattern": "("}}]}, "regular expression"),
    ({"rules": [{"id": "x1", "title": "x", "check": {"type": "layer-file-exists", "path": "../../etc/passwd"}}]}, "inside the layer"),
    ({"severity": {"rm-work": "fatal"}}, "severity"),
])
def test_company_rules_are_validated(tmp_path, bad, message):
    profile = project(tmp_path)
    with pytest.raises(ValueError, match=message):
        save_config(profile, {"disabled": [], "severity": {}, "rules": [], **bad})
    (profile.root_path / CONFIG).write_text("{not json")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_config(profile)


def test_cli_exit_status_for_ci(tmp_path):
    from bitloom.models import Settings
    profile = project(tmp_path)
    settings = Settings(tmp_path / "profiles.json")
    settings.profiles, settings.active = [profile], "p"
    settings.save()
    run = lambda *extra: subprocess.run([sys.executable, "-m", "bitloom", "--config", str(tmp_path / "profiles.json"), "--state", str(tmp_path / "state"), "--practices", *extra],
                                        capture_output=True, text=True)
    failing = run("--format", "json")
    assert failing.returncode == 2 and json.loads(failing.stdout)["errors"] > 0
    assert run("--fail-on", "never").returncode == 0


def test_web_practices_api(tmp_path):
    from bitloom.models import Settings
    from bitloom.web import Dashboard, create_server
    profile = project(tmp_path)
    settings = Settings(tmp_path / "profiles.json")
    settings.profiles, settings.active = [profile], "p"
    settings.save()
    board = Dashboard(tmp_path / "profiles.json", tmp_path / "state", token="t")
    server = create_server(board, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/api"

    def call(path, body=None, raw=False):
        request = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {"X-Bitloom-Token": "t", "Content-Type": "application/json"})
        try:
            data = urllib.request.urlopen(request).read()
            return data.decode() if raw else json.loads(data)
        except urllib.error.HTTPError as error:
            return {"status": error.code, **json.loads(error.read())}
    try:
        data = call("/practices?profile=p")
        assert data["errors"] > 0 and data["score"] is not None
        saved = call("/practices", {"profile": "p", "disabled": ["rm-work"]})
        assert by_id(saved)["rm-work"]["status"] == "off" and json.loads((profile.root_path / CONFIG).read_text())["disabled"] == ["rm-work"]
        refused = call("/practices", {"profile": "p", "rules": [{"id": "x", "title": "", "check": {}}]})
        assert refused["status"] == 400
        tried = call("/practices/try", {"profile": "p", "rule": {"id": "draft", "title": "Draft", "check": {"type": "layer-file-exists", "path": "SECURITY.md"}}})
        assert tried["status"] == "fail" and tried["total"] == 1
        assert call("/practices/try", {"profile": "p", "rule": {"id": "draft", "title": "Draft", "check": {"type": "shell"}}})["status"] == 400
        assert call("/practices/export?profile=p&format=md", raw=True).startswith("# Yocto best practices")
    finally:
        server.shutdown()
