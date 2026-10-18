"""Which recipe installs a file, and the Image explorer: from pkgdata, manifests and the rootfs archive."""
import bz2
import io
import json
import tarfile
import threading
import urllib.request

from bitloom.inspectors import metadata
from bitloom.models import Profile


def build(tmp_path):
    """A workspace after an image build: pkgdata, a manifest and a multi-stream tar.bz2 rootfs (as pbzip2 writes)."""
    root = tmp_path / "ws"
    for layer, files in {"meta": {"recipes-core/base-files/base-files_3.0.bb": "", "recipes-core/glibc/glibc_2.43.bb": ""},
                         "meta-mine": {"recipes-core/base-files/base-files_%.bbappend": ""}}.items():
        (root / layer / "conf").mkdir(parents=True)
        (root / layer / "conf/layer.conf").write_text("x\n")
        for name, text in files.items():
            (root / layer / name).parent.mkdir(parents=True, exist_ok=True)
            (root / layer / name).write_text(text)
    runtime = root / "build/tmp/pkgdata/qemux86-64/runtime"
    runtime.mkdir(parents=True)
    (runtime / "base-files").write_text('PN: base-files\nPV: 3.0\nRDEPENDS:base-files: \nFILES_INFO:base-files: {"/etc/motd": 5, "/etc/hostname": 6}\n')
    (runtime / "glibc").write_text('PN: glibc\nPV: 2.43\nPKG:glibc: libc6\nFILES_INFO:glibc: {"/lib/libc.so.6": 2000}\n')
    (runtime / "packagegroup-core-boot").write_text("PN: packagegroup-core-boot\nPV: 1.0\nRDEPENDS:packagegroup-core-boot: base-files libc6 (>= 2.43)\nFILES_INFO:packagegroup-core-boot: {}\n")
    (runtime / "glibc.packaged").write_text("")
    images = root / "build/tmp/deploy/images/qemux86-64"
    images.mkdir(parents=True)
    (images / "my-image-qemux86-64.rootfs-20261018120000.manifest").write_text("base-files qemux86_64 3.0\nlibc6 x86_64 2.43\npackagegroup-core-boot all 1.0\n")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in {"./etc/motd": b"hello", "./etc/hostname": b"board\n", "./etc/passwd": b"root:x:0:0\n", "./lib/libc.so.6": b"\0ELF" + b"x" * 1996}.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        link = tarfile.TarInfo("./etc/mtab")
        link.type, link.linkname = tarfile.SYMTYPE, "/proc/mounts"
        archive.addfile(link)
    raw = buffer.getvalue()
    half = len(raw) // 2
    (images / "my-image-qemux86-64.rootfs-20261018120000.tar.bz2").write_bytes(bz2.compress(raw[:half]) + bz2.compress(raw[half:]))
    return Profile(name="p", root=str(root), mode="host")


def test_which_recipe_installs(tmp_path):
    from bitloom.whois import lookup, report
    profile = build(tmp_path)
    entries = metadata(profile)
    motd = lookup(profile, "/etc/motd", entries)
    row = motd["results"][0]
    assert (row["package"], row["recipe"], row["layer"], row["mine"]) == ("base-files", "base-files", "meta", False)
    assert row["images"] == [{"image": "my-image", "machine": "qemux86-64", "pulled_in_by": ["packagegroup-core-boot"]}]
    assert [a["layer"] for a in row["appends"]] == ["meta-mine"] and row["appends"][0]["mine"]
    assert "edit your append" in report(motd)                       # an append of yours exists: change that one
    libc = lookup(profile, "libc6", entries)["results"][0]          # the name in the image, renamed from glibc
    assert (libc["package"], libc["installed_as"], libc["recipe"]) == ("glibc", "libc6", "glibc")
    assert "glibc_%.bbappend to your layer" in report(lookup(profile, "glibc", entries))
    passwd = lookup(profile, "/etc/passwd", entries)
    assert not passwd["results"] and "useradd" in passwd["note"]   # made while the image is assembled


def test_image_explorer(tmp_path):
    from bitloom.rootfs import built_images, listing, read, summary
    profile = build(tmp_path)
    [image] = built_images(profile)
    assert (image["image"], image["machine"], image["kind"]) == ("my-image", "qemux86-64", "archive")
    totals = summary(profile, "my-image", "qemux86-64")
    assert totals["total"] == 5 + 6 + 11 + 2000 and totals["files"] == 4 and totals["package_count"] == 2
    assert totals["packages"][0]["package"] == "libc6" and totals["packages"][0]["recipe"] == "glibc"
    assert any(p["package"] == "(not from a package)" for p in totals["packages"])
    etc = {c["name"]: c for c in listing(profile, "my-image", "qemux86-64", "/etc")["children"]}
    assert etc["motd"]["package"] == "base-files" and etc["mtab"]["type"] == "link" and etc["mtab"]["target"] == "/proc/mounts"
    assert read(profile, "my-image", "qemux86-64", "/etc/hostname")["text"] == "board\n"
    assert read(profile, "my-image", "qemux86-64", "/lib/libc.so.6")["binary"]


def test_web_image_and_whois(tmp_path):
    from bitloom.models import Settings
    from bitloom.web import Dashboard, create_server
    profile = build(tmp_path)
    settings = Settings(tmp_path / "profiles.json")
    settings.profiles, settings.active = [profile], "p"
    settings.save()
    board = Dashboard(tmp_path / "profiles.json", tmp_path / "state", token="t")
    server = create_server(board, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/api"

    def get(path):
        return json.loads(urllib.request.urlopen(urllib.request.Request(base + path, headers={"X-Bitloom-Token": "t"})).read())
    try:
        assert get("/image/list?profile=p")["images"][0]["image"] == "my-image"
        assert get("/image/dir?profile=p&image=my-image&machine=qemux86-64&dir=/etc")["size"] == 5 + 6 + 11
        assert get("/image/file?profile=p&image=my-image&machine=qemux86-64&path=/etc/motd")["text"] == "hello"
        assert get("/whois?profile=p&q=/etc/motd")["results"][0]["recipe"] == "base-files"
    finally:
        server.shutdown()


def test_append_starts_from_the_device_file(tmp_path):
    from bitloom.studio import fields, plan
    profile = Profile(name="p", root=str(tmp_path), mode="host")
    values = {f.id: f.default for f in fields("append", "wrynose", [])}
    values.update(recipe="base-files", file="motd", file_content="Welcome to the board\n")
    result = plan("append", values, profile, "wrynose")
    assert result["files"]["recipes-core/base-files/files/motd"] == "Welcome to the board\n"


def systemd_image(tmp_path):
    """A systemd image: units in /lib, enablement links in /etc, a masked unit, udev rules (one disabled), D-Bus."""
    root = tmp_path / "sd"
    runtime = root / "build/tmp/pkgdata/qemuarm64/runtime"
    runtime.mkdir(parents=True)
    (runtime / "openssh").write_text('PN: openssh\nPV: 9.9\nPKG:openssh: openssh-sshd\nFILES_INFO:openssh: {"/lib/systemd/system/sshd.socket": 10, "/lib/systemd/system/sshd@.service": 10}\n')
    (runtime / "systemd").write_text('PN: systemd\nPV: 257\nFILES_INFO:systemd: {"/lib/systemd/systemd": 1, "/lib/systemd/system/systemd-networkd.service": 1, "/lib/udev/rules.d/80-net-setup-link.rules": 1}\n')
    images = root / "build/tmp/deploy/images/qemuarm64"
    images.mkdir(parents=True)
    files = {"./lib/systemd/systemd": b"\0ELF",
             "./lib/systemd/system/sshd.socket": b"[Unit]\nDescription=OpenSSH Server Socket\n[Socket]\nListenStream=22\n",
             "./lib/systemd/system/sshd@.service": b"[Unit]\nDescription=OpenSSH Per-Connection Daemon\n[Service]\nExecStart=-/usr/sbin/sshd -i\n",
             "./lib/systemd/system/systemd-networkd.service": b"[Unit]\nDescription=Network Configuration\n[Service]\nExecStart=!!/lib/systemd/systemd-networkd\n",
             "./lib/systemd/system/multi-user.target": b"[Unit]\nDescription=Multi-User System\n",
             "./lib/udev/rules.d/80-net-setup-link.rules": b"# Network link names\nACTION==\"add\", IMPORT{builtin}=\"net_setup_link\"\nNAME=\"$env{ID_NET_NAME}\"\n",
             "./lib/udev/rules.d/60-serial.rules": b"# Serial\nSUBSYSTEM==\"tty\", GOTO=\"x\"\n",
             "./usr/share/dbus-1/system-services/org.freedesktop.network1.service": b"[D-BUS Service]\nName=org.freedesktop.network1\nExec=/bin/false\nUser=root\nSystemdService=dbus-org.freedesktop.network1.service\n"}
    links = {"./etc/systemd/system/multi-user.target.wants/systemd-networkd.service": "/lib/systemd/system/systemd-networkd.service",
             "./etc/systemd/system/sockets.target.wants/sshd.socket": "/lib/systemd/system/sshd.socket",
             "./etc/systemd/system/default.target": "/lib/systemd/system/multi-user.target",
             "./etc/systemd/system/getty@.service": "/dev/null",
             "./etc/udev/rules.d/80-net-setup-link.rules": "/dev/null"}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.uname, info.gname = len(data), "root", "root"
            archive.addfile(info, io.BytesIO(data))
        for name, target in links.items():
            info = tarfile.TarInfo(name)
            info.type, info.linkname = tarfile.SYMTYPE, target
            archive.addfile(info)
    (images / "acme-image-qemuarm64.rootfs.tar.bz2").write_bytes(bz2.compress(buffer.getvalue()))
    return Profile(name="sd", root=str(root), mode="host")


def test_services_in_the_image(tmp_path):
    from bitloom import rootfs
    profile = systemd_image(tmp_path)
    data = rootfs.services(profile, "acme-image", "qemuarm64")
    assert data["init"] == "systemd" and data["default_target"] == "multi-user.target"
    units = {u["name"]: u for u in data["units"]}
    assert units["systemd-networkd.service"]["enabled"] == ["multi-user.target"] and units["systemd-networkd.service"]["exec"] == "/lib/systemd/systemd-networkd"
    assert units["sshd.socket"]["enabled"] == ["sockets.target"] and units["sshd.socket"]["recipe"] == "openssh"
    assert units["sshd@.service"]["enabled"] == [] and units["sshd@.service"]["exec"] == "/usr/sbin/sshd -i"
    assert units["getty@.service"]["masked"]
    assert set(data["starts"]) == {"systemd-networkd.service", "sshd.socket"}
    rules = {(r["name"], r["local"]): r for r in data["udev"]}
    assert rules[("80-net-setup-link.rules", True)]["masked"] and rules[("80-net-setup-link.rules", False)]["overridden"]
    assert rules[("60-serial.rules", False)]["rules"] == 1 and rules[("60-serial.rules", False)]["comment"] == "Serial"
    assert data["dbus"] == [{"name": "org.freedesktop.network1", "path": "/usr/share/dbus-1/system-services/org.freedesktop.network1.service", "kind": "activation",
                             "bus": "system", "exec": "/bin/false", "unit": "dbus-org.freedesktop.network1.service", "package": "", "recipe": ""}]
    text = rootfs.services_report(data)
    assert "● systemd-networkd.service" in text and "disabled in /etc" in text and "replaced by /etc" in text
    assert rootfs.listing(profile, "acme-image", "qemuarm64", "/lib/systemd/system")["children"][0]["owner"] == "root:root"
