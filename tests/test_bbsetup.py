"""New projects with bitbake-setup: offered only where the release has it, run as a job, in the build image or on the host."""
import os
import subprocess
import sys

import pytest

from bitloom import bbsetup
from bitloom.commands import fragment_selected, invocation
from bitloom.models import Profile
from bitloom.projects import bbsetup_plan, bbsetup_request


def test_plan_follows_the_official_template(tmp_path):
    plan = bbsetup_plan(str(tmp_path / "top"), "acme", "wrynose", "qemuarm64", "poky")
    assert plan["tool"] == "bitbake-setup" and plan["setup"] == str(tmp_path / "top/acme")
    assert plan["command"][-4:] == ["poky-wrynose", "poky", "machine/qemuarm64", "distro/poky"]
    assert "--non-interactive" in plan["command"] and "init --non-interactive" in plan["display"]
    from bitloom import module_command
    assert plan["job"][:3] == module_command("bitloom.bbsetup")[:3] and "--top" in plan["job"]   # runs from any install, .deb and .pyz included
    with pytest.raises(ValueError, match="not available for scarthgap.*BitBake 2.16"):
        bbsetup_plan(str(tmp_path / "x"), "acme", "scarthgap", "qemux86-64", "poky")
    with pytest.raises(ValueError, match="offers MACHINE"):
        bbsetup_plan(str(tmp_path / "x"), "acme", "wrynose", "beaglebone-yocto", "poky")
    with pytest.raises(ValueError, match="offers DISTRO"):
        bbsetup_plan(str(tmp_path / "x"), "acme", "wrynose", "qemuarm64", "acme")
    (tmp_path / "full").mkdir(); (tmp_path / "full/x").write_text("x")
    with pytest.raises(ValueError, match="not empty"):
        bbsetup_plan(str(tmp_path / "full"), "acme", "wrynose", "qemuarm64", "poky")


def test_request_runs_in_the_build_image_at_the_same_path(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name, *a, **k: "/usr/bin/docker" if name == "docker" else None)
    plan = bbsetup_plan(str(tmp_path / "top"), "acme", "wrynose", "qemuarm64", "poky")
    request = bbsetup_request(plan, "container", "qemuarm64", "poky", "core-image-base")
    profile = request["profile"]
    assert (profile.mode, profile.engine, profile.image) == ("container", "docker", bbsetup.IMAGE)
    assert profile.root == profile.container_root == str(tmp_path / "top/acme") and profile.init_script == "build/init-build-env"
    assert request["job"][-4:] == ["--engine", "docker", "--image", bbsetup.IMAGE] and profile.targets == ["core-image-base"]
    assert bbsetup_request(plan, "host", "qemuarm64", "poky", "")["profile"].mode == "host"
    prefix = bbsetup.container_prefix("docker", bbsetup.IMAGE, tmp_path / "top")
    assert f"{tmp_path / 'top'}:{tmp_path / 'top'}" in prefix and prefix[-3:] == ["--entrypoint", "", bbsetup.IMAGE]


def test_fragments_own_machine_and_distro(tmp_path):
    """bitbake-setup selects MACHINE/DISTRO with fragments: exporting them too makes BitBake stop."""
    root = tmp_path / "acme"
    (root / "build/conf").mkdir(parents=True)
    (root / "build/init-build-env").write_text("")
    profile = Profile(name="acme", root=str(root), mode="host", init_script="build/init-build-env", machine="qemuarm64", distro="poky")
    assert fragment_selected(profile) == set()
    assert invocation(profile, ["bitbake", "x"]).env["MACHINE"] == "qemuarm64"
    (root / "build/conf/toolcfg.conf").write_text('OE_FRAGMENTS += "distro/poky machine/qemuarm64"\n')
    env = invocation(profile, ["bitbake", "x"]).env
    assert fragment_selected(profile) == {"MACHINE", "DISTRO"} and "MACHINE" not in env.get("BB_ENV_PASSTHROUGH_ADDITIONS", "").split()
    assert env.get("MACHINE") != "qemuarm64" or os.environ.get("MACHINE") == "qemuarm64"


def test_helper_runs_bitbake_setup(tmp_path):
    """The job itself, with a stand-in bitbake-setup on the PATH, on the host."""
    fake = tmp_path / "bin/bitbake-setup"
    fake.parent.mkdir()
    fake.write_text("#!/bin/sh\necho \"ARGS $*\"\nmkdir -p \"$PWD/acme/build\"\n")
    fake.chmod(0o755)
    env = {**os.environ, "PATH": f"{fake.parent}:{os.environ['PATH']}"}
    code = "import bitloom.bbsetup as b, sys; b.host_problems = lambda: []; sys.argv = sys.argv[:1] + sys.argv[1:]; raise SystemExit(b.main())"
    result = subprocess.run([sys.executable, "-c", code, "--top", str(tmp_path / "top"), "--release", "wrynose", "--name", "acme",
                             "--choice", "machine/qemuarm64", "--choice", "distro/poky"], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "init --non-interactive --no-init-vscode --setup-dir-name acme poky-wrynose poky machine/qemuarm64 distro/poky" in result.stdout
    assert "setup ready in" in result.stdout


def test_kas_files_own_machine_and_distro(tmp_path):
    """An overlay's DISTRO applies: the profile's values are not exported over what the kas files say."""
    root = tmp_path / "p"
    root.mkdir()
    (root / "kas.yml").write_text("header:\n  version: 14\nmachine: qemux86-64\ndistro: poky\n")
    (root / "acme.yml").write_text("header:\n  version: 14\ndistro: acme\n")
    profile = Profile(name="k", root=str(root), mode="kas", kas_file="kas.yml:acme.yml", machine="qemux86-64", distro="poky")
    env = invocation(profile, ["bitbake", "x"]).env
    assert fragment_selected(profile) == {"MACHINE", "DISTRO"}
    assert "DISTRO" not in env.get("BB_ENV_PASSTHROUGH_ADDITIONS", "").split() and env.get("DISTRO") != "poky" or __import__("os").environ.get("DISTRO") == "poky"
    bare = Profile(name="b", root=str(root), mode="kas", kas_file="none.yml", machine="board")
    assert invocation(bare, ["bitbake", "x"]).env["MACHINE"] == "board"      # nothing in kas: the profile decides
