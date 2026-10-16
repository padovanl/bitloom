"""Device trees read back without dtc: parse, DTS text, the summary, the deployed files, CLI and web."""
import json
import struct
import subprocess
import sys
import threading
import urllib.request

import pytest

from bitloom.devicetree import find, format_value, load, parse, report, to_dts
from bitloom.models import Profile


from bitloom.devicetree import encode as fdt


s = lambda *t: b"".join(x.encode() + b"\0" for x in t)
cells = lambda *c: struct.pack(f">{len(c)}I", *c)
BOARD = {"name": "", "props": [("model", s("Acme Board rev B")), ("compatible", s("acme,board-b", "acme,soc")), ("#address-cells", cells(1))], "children": [
    {"name": "chosen", "props": [("bootargs", s("console=ttyS0,115200 root=/dev/mmcblk0p2")), ("stdout-path", s("serial0:115200n8"))]},
    {"name": "memory@80000000", "props": [("device_type", s("memory")), ("reg", cells(0x80000000, 0x20000000))]},
    {"name": "intc@1000", "props": [("compatible", s("arm,gic-400")), ("phandle", cells(1)), ("interrupt-controller", b"")]},
    {"name": "serial@2000", "props": [("compatible", s("ns16550a")), ("reg", cells(0x2000, 0x100)), ("interrupt-parent", cells(1)), ("status", s("okay"))]},
    {"name": "serial@3000", "props": [("compatible", s("ns16550a")), ("status", s("disabled")), ("mac", bytes([0, 1, 2]))]},
]}
OVERLAY = {"name": "", "children": [{"name": "fragment@0", "props": [("target-path", s("/serial@3000"))], "children": [
    {"name": "__overlay__", "props": [("status", s("okay"))]}]}, {"name": "__fixups__", "props": []}]}


def workspace(tmp_path):
    images = tmp_path / "ws/build/tmp/deploy/images/acme-board"
    images.mkdir(parents=True)
    (images / "acme-board-b--6.12-r0-acme-board-20261018.dtb").write_bytes(fdt(BOARD))
    (images / "acme-board-b.dtb").symlink_to("acme-board-b--6.12-r0-acme-board-20261018.dtb")
    (images / "overlays").mkdir()
    (images / "overlays/uart2.dtbo").write_bytes(fdt(OVERLAY))
    return Profile(name="dt", root=str(tmp_path / "ws"), mode="host")


def test_parse_and_dts():
    root, header = parse(fdt(BOARD))
    assert header["version"] == 17
    text = to_dts(root, header)
    assert text.startswith("/dts-v1/;") and 'model = "Acme Board rev B";' in text
    assert 'compatible = "acme,board-b", "acme,soc";' in text and "intc_1000: intc@1000 {" in text
    assert "interrupt-parent = <&intc_1000>;" in text and "reg = <0x80000000 0x20000000>;" in text
    assert "interrupt-controller;" in text and "mac = [00 01 02];" in text
    assert format_value("x", s("a")) == '"a"' and format_value("x", cells(7)) == "<0x7>"
    for broken, message in [(b"x" * 10, "too short"), (b"\0" * 40, "magic"), (fdt(BOARD)[:60], "outside")]:
        with pytest.raises(ValueError, match=message):
            parse(broken)


def test_deployed_device_trees(tmp_path):
    profile = workspace(tmp_path)
    rows = find(profile)
    assert [(r["name"], r["machine"], r["overlay"]) for r in rows] == [("acme-board-b.dtb", "acme-board", False), ("uart2.dtbo", "acme-board", True)]
    data = load(profile, "acme-board-b.dtb")
    assert data["model"] == "Acme Board rev B" and data["bootargs"].startswith("console=ttyS0") and data["memory"] == ["<0x80000000 0x20000000>"]
    assert [d["path"] for d in data["enabled"]] == ["/intc@1000", "/serial@2000"] and [d["path"] for d in data["disabled"]] == ["/serial@3000"]
    assert "DISABLED" in report(data) and "KERNEL_DEVICETREE" in report(data)
    assert load(profile, "uart2.dtbo")["overlay"]
    with pytest.raises(LookupError, match="Deployed: acme-board-b.dtb, uart2.dtbo"):
        load(profile, "nope.dtb")


def test_cli_and_web(tmp_path):
    from bitloom.models import Settings
    from bitloom.web import Dashboard, create_server
    profile = workspace(tmp_path)
    settings = Settings(tmp_path / "profiles.json")
    settings.profiles, settings.active = [profile], "dt"
    settings.save()
    out = subprocess.run([sys.executable, "-m", "bitloom", "--config", str(tmp_path / "profiles.json"), "--devicetree", "acme-board-b.dtb"], capture_output=True, text=True)
    assert out.returncode == 0 and "model        Acme Board rev B" in out.stdout
    listed = subprocess.run([sys.executable, "-m", "bitloom", "--config", str(tmp_path / "profiles.json"), "--devicetree"], capture_output=True, text=True)
    assert "acme-board-b.dtb" in listed.stdout and "uart2.dtbo" in listed.stdout
    dts = subprocess.run([sys.executable, "-m", "bitloom", "--config", str(tmp_path / "profiles.json"), "--devicetree", "acme-board-b.dtb", "--format", "dts"], capture_output=True, text=True)
    assert dts.stdout.startswith("/dts-v1/;")
    board = Dashboard(tmp_path / "profiles.json", tmp_path / "state", token="t")
    server = create_server(board, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/api"
    get = lambda path: json.loads(urllib.request.urlopen(urllib.request.Request(base + path, headers={"X-Bitloom-Token": "t"})).read())
    try:
        assert [r["name"] for r in get("/devicetree?profile=dt")["files"]] == ["acme-board-b.dtb", "uart2.dtbo"]
        one = get("/devicetree?profile=dt&name=acme-board-b.dtb&machine=acme-board")
        assert one["model"] == "Acme Board rev B" and "serial@3000" in one["dts"]
    finally:
        server.shutdown()
