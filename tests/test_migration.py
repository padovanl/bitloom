"""The migration assistant: rules from the official guides, chained releases, safe fixes, a new kas file."""
import json
import subprocess
import sys

import pytest

from bitloom.migration import RULES, apply, backups, kas_for, migrated_profile, path_between, preview, report, restore, scan, targets_for, write_kas
from bitloom.models import Profile

KAS = """header:
  version: 14
machine: qemux86-64
distro: acme
target: acme-image
repos:
  meta-openembedded:
    url: https://git.openembedded.org/meta-openembedded
    branch: scarthgap
    commit: 0123456789abcdef0123456789abcdef01234567
    layers:
      meta-oe:
  poky:
    url: https://git.yoctoproject.org/poky
    tag: yocto-5.0.8
    commit: dc4827b3660bc1a03a2bc3b0672615b50e9137ff
    layers:
      meta:
      meta-poky:
      meta-yocto-bsp:
  meta-acme:
    path: meta-acme
local_conf_header:
  mine: |
    INHERIT += "cve-check"
    EXTRA_IMAGE_FEATURES ?= "debug-tweaks"
"""

FILES = {
    "meta/conf/layer.conf": 'BBFILE_COLLECTIONS += "core"\nLAYERSERIES_CORENAMES = "scarthgap"\n',
    "meta-acme/conf/layer.conf": 'BBFILE_COLLECTIONS += "acme"\nLAYERSERIES_COMPAT_acme = "scarthgap"\n',
    "meta-acme/conf/distro/acme.conf": 'DISTRO = "acme"\nDISTRO_FEATURES = "systemd sysvinit ld-is-gold"\nDISTRO_FEATURES_BACKFILL_CONSIDERED = "pulseaudio"\n'
                                       'INHERIT += "create-spdx-2.2 cve-check"\nCVE_CHECK_SHOW_WARNINGS = "0"\nZSTD_COMPRESSION_LEVEL = "-3"\nPREFERRED_PROVIDER_virtual/${TARGET_PREFIX}gcc = "gcc-cross-${TARGET_ARCH}"\n',
    "meta-acme/conf/machine/board.conf": 'UBOOT_ENTRYPOINT ?= "20008000"\nKERNEL_IMAGETYPE = "fitImage"\nWIC_SECTOR_SIZE = "4096"\nUBOOT_CONFIG[sd] = "board_defconfig,sdcard,u-boot.img"\n',
    "meta-acme/recipes-app/hello/hello_1.0.bb": 'SUMMARY = "hello"\nLICENSE = "MIT"\nSRC_URI = "file://hello.c file://hello.service \\\n           git://example.com/lib.git;protocol=https"\nS = "${WORKDIR}"\n'
                                                'DEPENDS = "libnewt pkgconfig-native"\nRDEPENDS:${PN} = "python3-toml libnss-mdns"\nCVE_PRODUCT = "hello\\\\+"\n'
                                                'do_install() {\n    install -m 0644 ${WORKDIR}/hello.service ${D}${systemd_unitdir}/system\n    echo ${PKG_CONFIG_PATH}\n}\n',
    "meta-acme/recipes-app/tool/tool_git.bb": 'LICENSE = "MIT"\nSRC_URI = "git://example.com/tool.git;branch=main;protocol=https"\nS = "${WORKDIR}/git"\nFOO="bar"\ninherit siteconfig\n',
    "meta-acme/recipes-app/old/old_1.0.bb": 'LICENSE = "MIT"\nS = "${WORKDIR}/old-1.0/src"\n',
    "meta-acme/recipes-core/images/acme-image.bb": 'LICENSE = "MIT"\ninherit core-image\nIMAGE_FEATURES += "debug-tweaks"\n',
    "meta-acme/recipes-multimedia/mpeg2dec/mpeg2dec_%.bbappend": 'FILESEXTRAPATHS:prepend := "${THISDIR}/files:"\n',
    "meta-acme/wic/board.wks": "part / --source rootfs\n",
    "build/conf/local.conf": 'MACHINE = "board"\nDISTRO = "acme"\n',
}


def project(tmp_path):
    root = tmp_path / "product"
    for name, text in FILES.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    (root / "kas.yml").write_text(KAS)
    return Profile(name="acme", root=str(root), mode="kas-container", kas_file="kas.yml", environment={"KAS_WORK_DIR": str(tmp_path / "work")})


def test_path_and_targets():
    assert path_between("scarthgap", "wrynose") == ["styhead", "walnascar", "whinlatter", "wrynose"]
    assert path_between("whinlatter", "wrynose") == ["wrynose"]
    assert targets_for("scarthgap") == ["styhead", "walnascar", "whinlatter", "wrynose"]
    with pytest.raises(ValueError, match="not newer"):
        path_between("wrynose", "scarthgap")
    with pytest.raises(ValueError, match="No migration rules for langdale, mickledore, nanbield, scarthgap"):
        path_between("kirkstone", "wrynose")
    assert len({r.id for r in RULES}) == len(RULES) and all(r.step in ("styhead", "walnascar", "whinlatter", "wrynose") for r in RULES)


def test_scan_finds_what_the_guides_describe(tmp_path):
    data = scan(project(tmp_path), "wrynose")
    by_rule = {}
    for f in data["findings"]:
        by_rule.setdefault(f["rule"], []).append(f)
    expected = {"s-workdir", "workdir-files", "recipes-5.1", "classes-5.1", "debug-tweaks", "git-branch", "virtual-cross", "uboot-entry", "zstd-level",
                "ld-gold", "recipes-5.2", "poky-repo", "s-workdir-sub", "assign-space", "fitimage", "layerseries", "backfill", "spdx22", "cve-check",
                "cve-product", "wic-sector", "wks-location", "init-both", "uboot-config", "pkgconfig", "recipes-6.0"}
    assert expected <= set(by_rule), sorted(expected - set(by_rule))
    assert data["steps"][0]["guide"].endswith("migration-5.1.html") and data["layers"] == ["meta-acme"]
    assert any("libnewt" in f["detail"] for f in by_rule["recipes-5.1"]) and any("mpeg2dec" in f["detail"] for f in by_rule["recipes-5.1"])
    assert {f["where"].split(":")[0] for f in by_rule["debug-tweaks"]} == {"meta-acme/recipes-core/images/acme-image.bb", "kas.yml"}
    assert by_rule["git-branch"][0]["where"].endswith("hello_1.0.bb:3") and "lib.git" in by_rule["git-branch"][0]["detail"]
    assert data["counts"]["breaks"] > 20 and data["fixable"] >= 15
    text = report(data)
    assert "scarthgap → styhead → walnascar → whinlatter → wrynose" in text and "migration-6.0.html#cve-check-class-removed" in text


def test_safe_fixes_preview_apply_and_restore(tmp_path):
    profile = project(tmp_path)
    data = scan(profile, "wrynose")
    fixes = [x for f in data["findings"] for x in f["fixes"]]
    diffs = {d["path"].split("product/")[1]: d["diff"] for d in preview(fixes)}
    hello = diffs["meta-acme/recipes-app/hello/hello_1.0.bb"]
    assert '+S = "${UNPACKDIR}"' in hello and "${UNPACKDIR}/hello.service" in hello and '+RDEPENDS:${PN} = "python3-toml avahi-libnss-mdns"' in hello
    assert '+DEPENDS = "libnewt pkgconf-native"' in hello and '+CVE_PRODUCT = "hello+"' in hello
    distro = diffs["meta-acme/conf/distro/acme.conf"]
    assert '+DISTRO_FEATURES_OPTED_OUT = "pulseaudio"' in distro and '+ZSTD_COMPRESSION_LEVEL = "3"' in distro
    assert "virtual/cross-cc" in distro and '+INHERIT += "create-spdx"' in distro and '+OE_FRAGMENTS += "core/yocto/sbom-cve-check"' in distro
    assert '+CVE_CHECK_SHOW_WARNINGS' not in distro and "+SBOM_CVE_CHECK_SHOW_WARNINGS" in distro
    result = apply(profile, tmp_path / "state", fixes, [profile.root_path])
    root = profile.root_path
    tool = (root / "meta-acme/recipes-app/tool/tool_git.bb").read_text()
    assert "S = " not in tool and 'FOO = "bar"' in tool
    assert 'S = "${UNPACKDIR}/old-1.0/src"' in (root / "meta-acme/recipes-app/old/old_1.0.bb").read_text()
    image = (root / "meta-acme/recipes-core/images/acme-image.bb").read_text()
    assert "allow-empty-password allow-root-login empty-root-password post-install-logging" in image
    assert 'LAYERSERIES_COMPAT_acme = "wrynose"' in (root / "meta-acme/conf/layer.conf").read_text()
    machine = (root / "meta-acme/conf/machine/board.conf").read_text()
    assert 'UBOOT_ENTRYPOINT ?= "0x20008000"' in machine and 'WIC_CREATE_EXTRA_ARGS += "--sector-size 4096"' in machine
    kas = (root / "kas.yml").read_text()
    assert 'OE_FRAGMENTS += "core/yocto/sbom-cve-check"' in kas and "    INHERIT" not in kas and "allow-root-login" in kas
    again = scan(profile, "wrynose")
    assert again["fixable"] == 0 and len(again["findings"]) < len(data["findings"])    # what is left needs a human
    assert backups(tmp_path / "state")[0]["files"] == result["written"]
    restored = restore(tmp_path / "state", backups(tmp_path / "state")[0]["id"])
    assert len(restored) == len(result["written"]) and (root / "meta-acme/conf/layer.conf").read_text() == FILES["meta-acme/conf/layer.conf"]
    stale = [dict(fixes[0], old="something else")]
    with pytest.raises(ValueError, match="changed since the scan"):
        apply(profile, tmp_path / "state", stale, [profile.root_path])
    outside = [dict(fixes[0], path="/etc/passwd")]
    with pytest.raises(ValueError, match="outside your layers"):
        apply(profile, tmp_path / "state", outside, [profile.root_path])


def test_kas_for_the_new_release(tmp_path):
    profile = project(tmp_path)
    plan = kas_for(profile, "wrynose")
    text = plan["text"]
    assert plan["name"] == "kas-wrynose.yml" and "build_system: openembedded" in text
    assert "git.yoctoproject.org/poky" not in text and "tag: yocto-6.0.2" in text
    assert "  openembedded-core:\n" in text and "      meta:\n" in text and "  meta-yocto:\n" in text and "      meta-poky:\n" in text
    assert "    branch: wrynose\n" in text and "0123456789abcdef" not in text and "  meta-acme:\n    path: meta-acme" in text
    written = write_kas(profile, "wrynose")
    assert (profile.root_path / "kas-wrynose.yml").read_text() == text and (profile.root_path / "kas.yml").read_text() == KAS
    assert kas_for(profile, "wrynose")["name"] == "kas-wrynose-2.yml"            # never over an existing file
    moved = migrated_profile(profile, "wrynose", written["kas_file"])
    assert moved.name == "acme-wrynose" and moved.environment["KAS_WORK_DIR"].endswith("work-wrynose") and moved.kas_file == "kas-wrynose.yml"


def test_cli(tmp_path):
    from bitloom.models import Settings
    profile = project(tmp_path)
    settings = Settings(tmp_path / "profiles.json")
    settings.profiles, settings.active = [profile], "acme"
    settings.save()
    run = lambda *a: subprocess.run([sys.executable, "-m", "bitloom", "--config", str(tmp_path / "profiles.json"), "--state", str(tmp_path / "state"), *a],
                                    capture_output=True, text=True)
    out = run("--migrate", "--to", "wrynose")
    assert out.returncode == 2 and "Migration scarthgap → wrynose" in out.stdout
    data = json.loads(run("--migrate", "--to", "wrynose", "--format", "json").stdout)
    assert data["counts"]["breaks"] > 20
    applied = run("--migrate", "--to", "wrynose", "--apply")
    assert "fixes applied" in applied.stdout and 'LAYERSERIES_COMPAT_acme = "wrynose"' in (profile.root_path / "meta-acme/conf/layer.conf").read_text()


def test_launcher_script_profiles(tmp_path):
    """A wrapper profile (YML=kas.yml ./run_build.sh) finds its kas file through the variable and keeps using the script."""
    profile = project(tmp_path)
    from dataclasses import replace
    wrapper = replace(profile, mode="wrapper", kas_file="", launcher=["./run_build.sh"], environment={"YML": "kas.yml", "KAS_WORK_DIR": str(tmp_path / "work")})
    assert any(f["rule"] == "poky-repo" for f in scan(wrapper, "wrynose")["findings"])
    written = write_kas(wrapper, "wrynose")
    moved = migrated_profile(wrapper, "wrynose", written["kas_file"])
    assert moved.mode == "wrapper" and moved.launcher == ["./run_build.sh"] and moved.environment["YML"] == "kas-wrynose.yml"
    assert moved.environment["KAS_WORK_DIR"].endswith("work-wrynose")
