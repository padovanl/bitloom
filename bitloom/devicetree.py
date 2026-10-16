"""Device trees of a build: the .dtb and .dtbo files BitBake deployed, read back as DTS text without dtc.

A flattened device tree is a small binary format (a header, a block of nodes and properties, a block of
property names); reading it in Python means no host tool is needed and the same answer comes from every
runtime. The summary says what a board developer asks first: the model and compatible strings, which
devices are enabled and which are disabled, and where the overlays are."""
from __future__ import annotations

import re
import struct
from pathlib import Path

from .models import Profile

MAGIC = 0xD00DFEED
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9
LIMIT = 4 * 1024 * 1024


class Node:
    def __init__(self, name: str):
        self.name, self.props, self.children = name, [], []

    def get(self, key: str):
        return next((value for name, value in self.props if name == key), None)


def parse(data: bytes) -> tuple[Node, dict]:
    """Bytes of a .dtb or .dtbo → the root node, and the header (version, boot CPU)."""
    if len(data) < 40:
        raise ValueError("Not a device tree: file too short")
    magic, total, off_struct, off_strings, _rsv, version, _last, boot_cpu, size_strings, size_struct = struct.unpack(">10I", data[:40])
    if magic != MAGIC:
        raise ValueError("Not a device tree: wrong magic number")
    if total > len(data) or off_struct + size_struct > total or off_strings + size_strings > total:
        raise ValueError("Damaged device tree: blocks outside the file")
    strings = data[off_strings:off_strings + size_strings]
    pos, end = off_struct, off_struct + size_struct
    stack: list[Node] = []
    root = None

    def word():
        nonlocal pos
        value = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        return value
    while pos < end:
        token = word()
        if token == BEGIN_NODE:
            stop = data.index(b"\0", pos)
            node = Node(data[pos:stop].decode(errors="replace"))
            pos = (stop + 4) & ~3
            if stack:
                stack[-1].children.append(node)
            else:
                root = node
            stack.append(node)
        elif token == END_NODE:
            if not stack:
                raise ValueError("Damaged device tree: unbalanced nodes")
            stack.pop()
        elif token == PROP:
            length, name_off = word(), word()
            value = data[pos:pos + length]
            pos = (pos + length + 3) & ~3
            name = strings[name_off:strings.index(b"\0", name_off)].decode(errors="replace")
            if not stack:
                raise ValueError("Damaged device tree: property outside a node")
            stack[-1].props.append((name, value))
        elif token == NOP:
            continue
        elif token == END:
            break
        else:
            raise ValueError(f"Damaged device tree: unknown token {token}")
    if root is None:
        raise ValueError("Empty device tree")
    return root, {"version": version, "boot_cpu": boot_cpu, "size": total}


def encode(tree: dict) -> bytes:
    """A tree {"name", "props": [(name, bytes)], "children": [...]} as a flattened device tree (version 17).
    Used for the demo workspace and the tests; real trees come from dtc in the kernel build."""
    strings, offsets, body = b"", {}, b""
    word = lambda v: struct.pack(">I", v)

    def node(n):
        nonlocal strings, body
        name = n["name"].encode() + b"\0"
        body += word(BEGIN_NODE) + name + b"\0" * (-len(name) % 4)
        for key, value in n.get("props", []):
            if key not in offsets:
                offsets[key] = len(strings)
                strings += key.encode() + b"\0"
            body += word(PROP) + word(len(value)) + word(offsets[key]) + value + b"\0" * (-len(value) % 4)
        for child in n.get("children", []):
            node(child)
        body += word(END_NODE)
    node(tree)
    body += word(END)
    off_struct = 40 + 16
    off_strings = off_struct + len(body)
    header = struct.pack(">10I", MAGIC, off_strings + len(strings), off_struct, off_strings, 40, 17, 16, 0, len(strings), len(body))
    return header + b"\0" * 16 + body + strings


def _text(*values: str) -> bytes:
    return b"".join(v.encode() + b"\0" for v in values)


def _cells(*values: int) -> bytes:
    return struct.pack(f">{len(values)}I", *values)


def demo_board() -> bytes:
    """The labelled sample device tree of the demo workspace."""
    t, c = _text, _cells
    uart = lambda addr, status: {"name": f"serial@{addr:x}", "props": [("compatible", t("ns16550a")), ("reg", c(addr, 0x100)), ("interrupt-parent", c(1)), ("status", t(status))]}
    return encode({"name": "", "props": [("model", t("Demo sample board (not real hardware)")), ("compatible", t("demo,board", "demo,soc")), ("#address-cells", c(1)), ("#size-cells", c(1))], "children": [
        {"name": "chosen", "props": [("bootargs", t("console=ttyS0,115200 root=/dev/mmcblk0p2 rootwait")), ("stdout-path", t("serial0:115200n8"))]},
        {"name": "aliases", "props": [("serial0", t("/soc/serial@10000"))]},
        {"name": "memory@80000000", "props": [("device_type", t("memory")), ("reg", c(0x80000000, 0x40000000))]},
        {"name": "cpus", "props": [("#address-cells", c(1)), ("#size-cells", c(0))], "children": [
            {"name": f"cpu@{i}", "props": [("compatible", t("arm,cortex-a53")), ("device_type", t("cpu")), ("reg", c(i))]} for i in range(4)]},
        {"name": "soc", "props": [("compatible", t("simple-bus")), ("#address-cells", c(1)), ("#size-cells", c(1)), ("ranges", b"")], "children": [
            {"name": "interrupt-controller@8000", "props": [("compatible", t("arm,gic-400")), ("reg", c(0x8000, 0x1000)), ("interrupt-controller", b""), ("phandle", c(1))]},
            uart(0x10000, "okay"), uart(0x11000, "disabled"),
            {"name": "mmc@20000", "props": [("compatible", t("demo,sdhci")), ("reg", c(0x20000, 0x1000)), ("bus-width", c(4)), ("status", t("okay"))]},
            {"name": "ethernet@30000", "props": [("compatible", t("demo,gmac")), ("reg", c(0x30000, 0x2000)), ("phy-mode", t("rgmii")), ("status", t("okay"))]},
            {"name": "i2c@40000", "props": [("compatible", t("demo,i2c")), ("reg", c(0x40000, 0x100)), ("status", t("okay"))], "children": [
                {"name": "rtc@68", "props": [("compatible", t("dallas,ds1307")), ("reg", c(0x68))]}]},
            {"name": "spi@50000", "props": [("compatible", t("demo,spi")), ("reg", c(0x50000, 0x100)), ("status", t("disabled"))]},
            {"name": "gpu@60000", "props": [("compatible", t("demo,gpu")), ("reg", c(0x60000, 0x10000)), ("status", t("disabled"))]}]}]})


def _strings(value: bytes) -> list[str] | None:
    """A property is shown as text when it is one or more printable NUL-terminated strings."""
    if not value or value[-1] != 0 or b"\0\0" in value:
        return None
    parts = value[:-1].split(b"\0")
    if all(p and all(32 <= c < 127 for c in p) for p in parts):
        return [p.decode() for p in parts]
    return None


def format_value(name: str, value: bytes, phandles: dict[int, str] | None = None) -> str:
    if not value:
        return ""
    text = _strings(value)
    if text is not None:
        return ", ".join(f'"{t}"' for t in text)
    if len(value) % 4 == 0:
        cells = struct.unpack(f">{len(value) // 4}I", value)
        if phandles and name in ("interrupt-parent", "clocks", "phys", "pinctrl-0", "pinctrl-1", "resets", "power-domains", "dmas", "gpios") and cells and cells[0] in phandles:
            first = f"&{phandles[cells[0]]}"
            return "<" + " ".join([first] + [f"0x{c:x}" for c in cells[1:]]) + ">"
        return "<" + " ".join(f"0x{c:x}" for c in cells) + ">"
    return "[" + " ".join(f"{b:02x}" for b in value) + "]"


def _labels(root: Node) -> dict[int, str]:
    """phandle → a readable label: the node name (uart@1000 → uart_1000), as dtc -s would let you reference it."""
    found, used = {}, set()

    def walk(node):
        handle = node.get("phandle") or node.get("linux,phandle")
        if handle and len(handle) == 4:
            label = re.sub(r"[^A-Za-z0-9_]", "_", node.name or "root")
            label = label if not label[0].isdigit() else "n" + label
            base, n = label, 1
            while label in used:
                n += 1
                label = f"{base}_{n}"
            used.add(label)
            found[struct.unpack(">I", handle)[0]] = label
        for child in node.children:
            walk(child)
    walk(root)
    return found


def to_dts(root: Node, header: dict) -> str:
    """DTS text, close to what dtc -I dtb -O dts prints (phandles shown as &label where the meaning is clear)."""
    phandles = _labels(root)
    lines = ["/dts-v1/;", ""]

    def walk(node, depth):
        pad = "\t" * depth
        handle = node.get("phandle") or node.get("linux,phandle")
        label = phandles.get(struct.unpack(">I", handle)[0]) if handle and len(handle) == 4 else None
        lines.append(f"{pad}{label + ': ' if label and node.name else ''}{node.name or '/'} {{")
        for name, value in node.props:
            shown = format_value(name, value, phandles)
            lines.append(f"{pad}\t{name}" + (f" = {shown};" if shown else ";"))
        for child in node.children:
            lines.append("")
            walk(child, depth + 1)
        lines.append(f"{pad}}};")
    walk(root, 0)
    return "\n".join(lines) + "\n"


def summary(root: Node) -> dict:
    """What a board developer looks for first."""
    devices, disabled = [], []

    def text(node, key):
        value = node.get(key)
        parts = _strings(value) if value is not None else None
        return parts or []

    def walk(node, path):
        here = f"{path.rstrip('/')}/{node.name}" if node.name else "/"
        compatible = text(node, "compatible")
        status = (text(node, "status") or ["okay"])[0]
        if compatible and node.name:
            row = {"path": here, "compatible": compatible, "status": status}
            (devices if status in ("okay", "ok") else disabled).append(row)
        for child in node.children:
            walk(child, here)
    walk(root, "")
    overlay = any(c.name.startswith("fragment@") for c in root.children) or any(c.name == "__fixups__" for c in root.children)
    chosen = next((c for c in root.children if c.name == "chosen"), None)
    return {"model": (text(root, "model") or [""])[0], "compatible": text(root, "compatible"), "overlay": overlay,
            "bootargs": (text(chosen, "bootargs") or [""])[0] if chosen else "", "stdout": (text(chosen, "stdout-path") or [""])[0] if chosen else "",
            "enabled": devices, "disabled": disabled,
            "memory": [format_value("reg", c.get("reg")) for c in root.children if c.name.startswith("memory") and c.get("reg")]}


def find(profile: Profile) -> list[dict]:
    """The device trees BitBake deployed, newest first: one entry per file name and machine."""
    rows = {}
    for path in profile.build_path.glob("tmp*/deploy/images/*/**/*"):
        if path.suffix not in (".dtb", ".dtbo") or not path.is_file():
            continue
        machine = path.relative_to(profile.build_path).parts[3]          # tmp/deploy/images/<machine>/…
        real = path.resolve()
        try:
            stat = real.stat()
        except OSError:
            continue
        # deploy keeps the versioned file and a short symbolic link to it: show the short name, read the real file.
        rows[(machine, path.name)] = {"name": path.name, "machine": machine, "path": str(path), "real": str(real), "size": stat.st_size,
                                      "mtime": stat.st_mtime, "overlay": path.suffix == ".dtbo", "link": path.is_symlink()}
    seen, result = set(), []
    for row in sorted(rows.values(), key=lambda r: (not r["link"], len(r["name"]))):
        if (row["machine"], row["real"]) in seen:
            continue
        seen.add((row["machine"], row["real"]))
        result.append(row)
    result.sort(key=lambda r: (r["overlay"], r["machine"], r["name"]))
    return result


def load(profile: Profile, name: str, machine: str = "") -> dict:
    """One deployed device tree by file name (and machine when several build it), decompiled and summarised."""
    rows = [r for r in find(profile) if r["name"] == name and (not machine or r["machine"] == machine)]
    if not rows:
        available = ", ".join(sorted({r["name"] for r in find(profile)})) or "none: this machine deploys no device tree (x86 and most QEMU machines do not)"
        raise LookupError(f"No device tree {name}. Deployed: {available}")
    row = rows[0]
    path = Path(row["real"])
    if path.stat().st_size > LIMIT:
        raise ValueError("Device tree larger than 4 MiB: not read")
    root, header = parse(path.read_bytes())
    return {**row, **header, **summary(root), "dts": to_dts(root, header)}


def report(data: dict) -> str:
    lines = [f"DEVICE TREE {data['name']} ({data['machine']})", ""]
    if data["overlay"]:
        lines.append("overlay      yes: applied on top of a base device tree by the bootloader")
    if data["model"]:
        lines.append(f"model        {data['model']}")
    if data["compatible"]:
        lines.append(f"compatible   {', '.join(data['compatible'])}")
    if data["bootargs"]:
        lines.append(f"bootargs     {data['bootargs']}")
    if data["stdout"]:
        lines.append(f"console      {data['stdout']}")
    lines += [f"enabled      {len(data['enabled'])} devices · disabled {len(data['disabled'])}", ""]
    for title, rows in (("ENABLED", data["enabled"]), ("DISABLED", data["disabled"])):
        if rows:
            lines.append(title)
            lines += [f"  {r['path']:<48} {r['compatible'][0]}" for r in rows[:200]]
            lines.append("")
    lines.append("Change it: a .dts or .dtsi in your BSP layer (KERNEL_DEVICETREE), or an overlay; never edit the kernel's tree upstream.")
    return "\n".join(lines)
