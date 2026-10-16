"""One registry decides what each Yocto release can do: operations, SBOM/CRA settings, Studio and checks."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from bitloom import capabilities
from bitloom.capabilities import CAPABILITIES, check, check_all, has, matrix
from bitloom.commands import ACTIONS, BY_ID, availability
from bitloom.models import Profile
from bitloom.sbom_settings import OPTIONS, availability as option_availability, requirement


def project(tmp_path, release):
    """A checkout shaped like the real ones: Poky 5.0 (one repository) or the split 6.0 repositories."""
    root = tmp_path / release
    if release == "scarthgap":
        meta, bitbake = root / "poky/meta", root / "poky/bitbake"
        classes = ["create-spdx", "create-spdx-2.2", "cve-check"]
        tools = ["bitbake", "bitbake-layers"]
    else:
        meta, bitbake = root / "openembedded-core/meta", root / "bitbake"
        classes = ["create-spdx", "create-spdx-3.0", "sbom-cve-check", "sbom-cve-check-recipe", "vex"]
        tools = ["bitbake", "bitbake-layers", "bitbake-config-build", "bitbake-setup"]
    (meta / "conf").mkdir(parents=True)
    (meta / "conf/layer.conf").write_text(f'BBFILE_COLLECTIONS += "core"\nLAYERSERIES_CORENAMES = "{release}"\n')
    for name in classes:
        folder = meta / ("classes-recipe" if "spdx" not in name else "classes")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.bbclass").write_text("# class\n")
    (bitbake / "bin").mkdir(parents=True)
    for tool in tools:
        (bitbake / "bin" / tool).write_text("#!/bin/sh\n")
    capabilities._classes_cache.clear()
    return Profile(name=release, root=str(root), mode="host")


EXPECTED = {   # capability: (scarthgap, wrynose) on the two checkouts above
    "spdx2": (True, False), "spdx3": (False, True), "spdx-supplier-3": (False, True),
    "cve-check": (True, False), "sbom-cve-check": (False, True), "sbom-cve-check-recipe": (False, True), "recipe-sbom": (False, True),
    "vex": (False, True), "fragments": (False, True), "bitbake-setup": (False, False),
    "unpackdir": (False, True), "image-access-split": (False, True), "debug-tweaks": (True, False), "systemd-default": (False, True),
}


def test_every_capability_on_both_releases(tmp_path):
    assert set(EXPECTED) == set(CAPABILITIES)
    old, new = project(tmp_path, "scarthgap"), project(tmp_path, "wrynose")
    for name, (on_old, on_new) in EXPECTED.items():
        assert check(name, "scarthgap", old)[0] is on_old, name
        assert check(name, "wrynose", new)[0] is on_new, name
    # A missing capability says why and what to use instead.
    ok, reason = check("sbom-cve-check", "scarthgap", old)
    assert not ok and "sbom-cve-check.bbclass is not in this project's layers" in reason and "use cve-check class instead" in reason
    assert "use sbom-cve-check" in check("cve-check", "wrynose", new)[1]
    assert "not set up with bitbake-setup" in check("bitbake-setup", "wrynose", new)[1]
    assert [row["available"] for row in matrix("wrynose", new)] == [EXPECTED[row["name"]][1] for row in matrix("wrynose", new)]


def test_project_evidence_beats_the_release_number(tmp_path):
    """A backported class is offered; a release number alone is used only when the layers are not visible."""
    old = project(tmp_path, "scarthgap")
    (old.root_path / "poky/meta/classes-recipe/vex.bbclass").write_text("# backport\n")
    capabilities._classes_cache.clear()
    assert check("vex", "scarthgap", old) == (True, "")
    unseen = Profile(name="remote", root=str(tmp_path / "missing"), mode="host")
    assert check("vex", "scarthgap", unseen)[0] is False                  # 5.0 predates vex: release decides
    assert check("vex", None, unseen)[0] is None                          # nothing to go on: unknown, not "no"
    assert check("bitbake-setup", "wrynose", unseen)[0] is None           # a tool-only check cannot guess
    assert check_all(("sbom-cve-check", "fragments"), "scarthgap", unseen)[0] is False


def test_registry_is_consistent():
    for action in ACTIONS:
        assert all(name in CAPABILITIES for name in action.needs), action.id
        assert not action.instead or action.instead in BY_ID, action.id
    for option in OPTIONS:
        assert all(name in CAPABILITIES for name in option.needs), option.id
    for cap in CAPABILITIES.values():
        assert not cap.instead or cap.instead in CAPABILITIES, cap.name


def test_operations_per_release(tmp_path):
    old, new = project(tmp_path, "scarthgap"), project(tmp_path, "wrynose")
    unavailable = lambda series, profile: {a.id for a in ACTIONS if availability(a, series, profile)[0] is False}
    assert unavailable("scarthgap", old) == {"sbom-cve-recipe", "recipe-sbom", "vex", "sbom-cve-enable", "sbom-cve-disable",
                                             "fragments", "fragment-enable", "fragment-disable", "setup-status", "setup-update"}
    assert unavailable("wrynose", new) == {"cve", "setup-status", "setup-update"}
    ok, reason = availability(BY_ID["sbom-cve-recipe"], "scarthgap", old)
    assert not ok and "Run recipe CVE check (cve-check)" in reason            # the operation to use instead
    ok, reason = availability(BY_ID["cve"], "wrynose", new)
    assert not ok and "Recipe CVE analysis from its SBOM" in reason


def test_sbom_settings_per_release(tmp_path):
    old, new = project(tmp_path, "scarthgap"), project(tmp_path, "wrynose")
    off = lambda series, profile: {o.id for o in OPTIONS if option_availability(o, series, profile)[0] is False}
    assert {"supplier", "image-supplier", "sbom-cve-check", "sbom-cve-warnings", "vex-class"} <= off("scarthgap", old)
    assert "supplier-22" not in off("scarthgap", old) and "cve-check" not in off("scarthgap", old)
    assert {"supplier-22", "cve-check"} <= off("wrynose", new) and "sbom-cve-check" not in off("wrynose", new)
    assert requirement(next(o for o in OPTIONS if o.id == "sbom-cve-check")).startswith("sbom-cve-check on image SBOMs · 6.0+")
    assert requirement(next(o for o in OPTIONS if o.id == "pretty")) == "any release"


def test_studio_follows_the_release(tmp_path):
    from bitloom.studio import fields, plan
    old, new = project(tmp_path, "scarthgap"), project(tmp_path, "wrynose")
    features = lambda series: next(f for f in fields("image", series, []) if f.id == "features").choices
    assert "debug-tweaks" in features("scarthgap") and "allow-root-login" not in features("scarthgap")
    assert "allow-root-login" in features("wrynose") and "debug-tweaks" not in features("wrynose")
    init = lambda series: next(f for f in fields("distro", series, []) if f.id == "init").default
    assert (init("scarthgap"), init("wrynose")) == ("sysvinit", "systemd")
    values = lambda series: {**{f.id: f.default for f in fields("append", series, [])}, "recipe": "base-files", "file": "motd"}
    old_append = plan("append", values("scarthgap"), old, "scarthgap")["files"]["recipes-core/base-files/base-files_%.bbappend"]
    new_append = plan("append", values("wrynose"), new, "wrynose")["files"]["recipes-core/base-files/base-files_%.bbappend"]
    assert "${WORKDIR}/motd" in old_append and "${UNPACKDIR}/motd" in new_append
    with pytest.raises(ValueError, match="debug-tweaks was removed"):
        plan("image", {**{f.id: f.default for f in fields("image", "wrynose", [])}, "features": "debug-tweaks"}, new, "wrynose")
    supplier = lambda series, profile: plan("distro", {f.id: f.default for f in fields("distro", series, [])}, profile, series)["files"]["conf/distro/acme.conf"]
    assert "SPDX_SUPPLIER" in supplier("scarthgap", old) and "SPDX_PACKAGE_SUPPLIER_name" in supplier("wrynose", new)


def test_web_refuses_what_the_release_lacks(tmp_path):
    from bitloom.models import Settings
    from bitloom.web import Dashboard, create_server
    old = project(tmp_path, "scarthgap")
    settings = Settings(tmp_path / "profiles.json")
    settings.profiles, settings.active = [old], "scarthgap"
    settings.save()
    board = Dashboard(tmp_path / "profiles.json", tmp_path / "state", token="t")
    server = create_server(board, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/api"

    def call(path, body=None):
        request = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {"X-Bitloom-Token": "t", "Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(request).read())
        except urllib.error.HTTPError as error:
            return {"status": error.code, **json.loads(error.read())}
    try:
        actions = {a["id"]: a for a in call("/actions")}
        assert actions["vex"]["needs"] == ["vex"] and actions["build"]["needs"] == []
        refused = call("/jobs", {"profile": "scarthgap", "action": "vex", "values": {"target": "busybox"}})
        assert refused.get("status") == 400 and "vex.bbclass is not in this project's layers" in refused["error"]
        options = {o["id"]: o for o in call("/compliance?profile=scarthgap")["options"]}
        assert options["sbom-cve-check"]["available"] is False and "6.0+" in options["sbom-cve-check"]["requires"]
    finally:
        server.shutdown()
