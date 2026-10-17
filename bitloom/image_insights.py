"""Insights on a built image, for the charts of the Image view: where the space goes (by layer, recipe and kind
of file), licences, what listens on the network, which packages everything depends on, and a quick security
look (setuid files, world-writable paths, root password, development files left in the image).

Everything comes from what the build left on disk: the root filesystem archive, pkgdata and the manifest."""
from __future__ import annotations

import re
import time

from .models import Profile

KINDS = (  # first match wins: (label, test on path)
    ("Debug symbols", lambda p: "/.debug/" in p or p.startswith(("/usr/lib/debug/", "/usr/src/debug/"))),
    ("Development files", lambda p: p.startswith(("/usr/include/", "/usr/share/pkgconfig/")) or "/pkgconfig/" in p or p.endswith((".a", ".la", ".h"))),
    ("Kernel and modules", lambda p: p.startswith(("/boot/", "/lib/modules/", "/usr/lib/modules/"))),
    ("Firmware", lambda p: p.startswith(("/lib/firmware/", "/usr/lib/firmware/"))),
    ("Documentation and locales", lambda p: p.startswith(("/usr/share/doc/", "/usr/share/man/", "/usr/share/info/", "/usr/share/locale/", "/usr/share/i18n/", "/usr/lib/locale/"))),
    ("Python", lambda p: re.match(r"/usr/lib(64)?/python3", p) is not None),
    ("Libraries", lambda p: re.search(r"\.so(\.\d+)*$", p) is not None or p.startswith(("/lib/", "/usr/lib/", "/lib64/", "/usr/lib64/"))),
    ("Programs", lambda p: re.match(r"^/(usr/)?(s?bin|libexec)/", p) is not None),
    ("Configuration", lambda p: p.startswith("/etc/")),
    ("Data and other", lambda p: True),
)
# Daemons recognised by their program, and the port they listen on by default.
DAEMONS = {
    "/usr/sbin/sshd": ("tcp", 22, "OpenSSH server"), "/usr/sbin/dropbear": ("tcp", 22, "Dropbear SSH server"),
    "/usr/sbin/lighttpd": ("tcp", 80, "lighttpd web server"), "/usr/sbin/nginx": ("tcp", 80, "nginx web server"),
    "/usr/sbin/httpd": ("tcp", 80, "Apache httpd"), "/usr/sbin/avahi-daemon": ("udp", 5353, "Avahi mDNS"),
    "/usr/bin/dnsmasq": ("udp", 53, "dnsmasq DNS/DHCP"), "/usr/sbin/dnsmasq": ("udp", 53, "dnsmasq DNS/DHCP"),
    "/usr/sbin/mosquitto": ("tcp", 1883, "Mosquitto MQTT broker"), "/sbin/rpcbind": ("tcp", 111, "rpcbind"), "/usr/sbin/rpcbind": ("tcp", 111, "rpcbind"),
    "/usr/sbin/chronyd": ("udp", 123, "chrony NTP"), "/usr/sbin/ntpd": ("udp", 123, "NTP daemon"), "/usr/sbin/snmpd": ("udp", 161, "Net-SNMP agent"),
    "/usr/sbin/vsftpd": ("tcp", 21, "vsftpd FTP server"), "/usr/sbin/smbd": ("tcp", 445, "Samba"), "/usr/bin/redis-server": ("tcp", 6379, "Redis"),
    "/usr/sbin/telnetd": ("tcp", 23, "telnet server"), "/usr/sbin/in.telnetd": ("tcp", 23, "telnet server"),
}
_cache: dict[str, tuple[float, dict]] = {}


def _kind(path: str) -> str:
    return next(label for label, test in KINDS if test(path))


def _top(rows: dict, limit: int, other: str = "Other", by: str = "size") -> list[dict]:
    """Biggest first; the tail folds into one Other row so a chart never needs a ninth colour."""
    ordered = sorted(rows.items(), key=lambda kv: (-kv[1][by], kv[0]))
    shown = [{"name": k, **v} for k, v in ordered[:limit]]
    rest = ordered[limit:]
    if rest:
        shown.append({"name": other, "size": sum(v["size"] for _, v in rest), "files": sum(v.get("files", 0) for _, v in rest),
                      "packages": sum(v.get("packages", 0) for _, v in rest), "other": True, "count": len(rest)})
    return shown


def _human(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def report(d: dict) -> str:
    """The same insights as text, for a terminal or a CI log."""
    pct = lambda n: f"{100 * n / max(1, d['total']):.1f}%"
    lines = [f"IMAGE INSIGHTS {d['image']} ({d['machine']})", "",
             f"{_human(d['total'])} on the device · {d['files']} files · {d['packages']} packages · {d['boot']} started at boot ({d['init']}) · "
             f"{len(d['ports'])} ports listening · {len(d['setuid'])} setuid/setgid files", "", "BY LAYER"]
    lines += [f"  {r['name']:<28} {_human(r['size']):>10} {pct(r['size']):>6}" + ("  (yours)" if r.get("mine") else "") for r in d["layers"]]
    lines += ["", "BY KIND OF FILE"] + [f"  {r['name']:<28} {_human(r['size']):>10} {pct(r['size']):>6}" for r in d["kinds"]]
    lines += ["", "BIGGEST RECIPES"] + [f"  {r['name']:<28} {_human(r['size']):>10} {pct(r['size']):>6}" for r in d["recipes"]]
    lines += ["", "LICENCES"] + [f"  {r['packages']:>3} packages  {r['name']}" for r in d["licences"]]
    lines += ["", "LISTENING"] + ([f"  {p['port']}/{p['proto']:<4} {p['what']:<28} {p['how']}{'' if p['boot'] else ' · on demand'}" for p in d["ports"]] or ["  nothing listens on the network"])
    lines += ["", "SECURITY"]
    if d["root"]:
        lines.append(f"  root password: {d['root']['password']}")
    sizes = re.compile(r"(\d+) bytes")
    for f in d["findings"]:
        mark = "✖" if f["level"] == "error" else "▲" if f["level"] == "warning" else "●"
        lines.append(f"  {mark} {sizes.sub(lambda m: _human(int(m[1])), f['text'])}: {f['fix']}")
    lines += [f"  setuid/setgid: {', '.join(s['path'] for s in d['setuid']) or 'none'}", f"  world-writable without sticky bit: {', '.join(d['writable'][:10]) or 'none'}"]
    return "\n".join(lines)


def insights(profile: Profile, image: str, machine: str, entries=None) -> dict:
    from . import rootfs
    from .inspectors import organize
    from .studio import product_layers
    from .whois import load, manifests
    from .inspectors import recipe_name
    found = rootfs._find(profile, image, machine)
    key = f"{profile.name}:{found['source']}"
    cached = _cache.get(key)
    if cached and cached[0] == found["mtime"]:
        return cached[1]
    files = rootfs._entries(found["source"])
    owner = rootfs.owners(profile)
    packages = load(profile)["packages"]
    entries = organize(list(entries)) if entries is not None else []
    mine = {path.name for path in product_layers(entries, profile)}
    layer_of = {}
    for entry in entries:
        if entry.kind == "bb":
            layer_of.setdefault(recipe_name(entry)[0], entry.layer)
    by_layer, by_recipe, by_kind = {}, {}, {}
    setuid, writable, total, count = [], [], 0, 0
    for path, info in files.items():
        if info["type"] == "dir":
            if info["mode"] & 0o002 and not info["mode"] & 0o1000:
                writable.append(path)
            continue
        if info["type"] != "file":
            continue
        size = info["size"]
        total += size
        count += 1
        package, recipe = owner.get(path, ("", ""))
        layer = layer_of.get(recipe, "unknown layer") if recipe else "not from a package"
        for table, name in ((by_layer, layer), (by_recipe, recipe or "not from a package"), (by_kind, _kind(path))):
            row = table.setdefault(name, {"size": 0, "files": 0})
            row["size"] += size
            row["files"] += 1
        if info["mode"] & 0o6000:
            setuid.append({"path": path, "mode": f"{info['mode'] & 0o7777:04o}", "setuid": bool(info["mode"] & 0o4000), "package": package, "recipe": recipe})
        if info["mode"] & 0o002:
            writable.append(path)
    for name, row in by_layer.items():
        row["mine"] = name in mine
    installed = next((m["packages"] for m in manifests(profile) if m["image"] == image and m["machine"] == machine), [])
    final = {info["renamed"]: name for name, info in packages.items()}
    licences: dict[str, dict] = {}
    package_size = {}
    for path, (package, _) in owner.items():
        if path in files and files[path]["type"] == "file":
            package_size[package] = package_size.get(package, 0) + files[path]["size"]
    for installed_name in installed:
        name = final.get(installed_name, installed_name)
        info = packages.get(name)
        if not info:
            continue
        expression = re.sub(r"\s+", " ", info.get("license") or "unknown").strip()
        row = licences.setdefault(expression, {"size": 0, "packages": 0, "names": []})
        row["size"] += package_size.get(installed_name, 0)
        row["packages"] += 1
        row["names"].append(installed_name)
    # Who depends on whom among the installed packages: the hubs every update has to care about.
    depended: dict[str, set] = {}
    installed_set = set(installed)
    for installed_name in installed:
        info = packages.get(final.get(installed_name, installed_name), {})
        for dep in info.get("depends", []):
            dep = re.sub(r"\(.*", "", dep).strip()
            if dep in installed_set and dep != installed_name:
                depended.setdefault(dep, set()).add(installed_name)
    hubs = sorted(({"package": p, "dependants": len(d), "examples": sorted(d)[:6]} for p, d in depended.items()), key=lambda r: (-r["dependants"], r["package"]))[:12]
    # What listens: configured sockets and daemons, with whether they start at boot.
    services = rootfs.services(profile, image, machine)
    starts = set(services["starts"])
    texts = rootfs._contents(found["source"], {p for p in ("/etc/ssh/sshd_config", "/etc/default/dropbear", "/etc/inetd.conf", "/etc/shadow", "/etc/passwd", "/etc/services") if p in files})
    ports = []
    for unit in services["units"]:
        for listen in unit.get("listen", []):
            proto, _, address = listen.partition(" ")
            number = re.search(r"(\d+)$", address.strip())
            if number:
                ports.append({"proto": proto, "port": int(number[1]),
                              "service": unit["name"], "what": unit["description"] or unit["name"], "how": f"systemd socket ({address})",
                              "boot": unit["name"] in starts, "package": unit["package"]})
    for program, (proto, port, what) in DAEMONS.items():
        if program in files:
            configured = port
            if program.endswith("sshd"):
                setting = re.search(r"^\s*Port\s+(\d+)", texts.get("/etc/ssh/sshd_config", ""), re.M)
                configured = int(setting[1]) if setting else port
            if program.endswith("dropbear"):
                setting = re.search(r"-p\s*(?:[\d.]*:)?(\d+)", texts.get("/etc/default/dropbear", ""))
                configured = int(setting[1]) if setting else port
            name = program.rsplit("/", 1)[1]
            boot = any(name in s or s.startswith(name.split(".")[0]) for s in starts)
            if not any(p["port"] == configured and p["proto"] == proto for p in ports):
                ports.append({"proto": proto, "port": configured, "service": name, "what": what, "how": "program in the image (default port)" if configured == port else "its configuration",
                              "boot": boot, "package": owner.get(program, ("", ""))[0]})
    for line in texts.get("/etc/inetd.conf", "").splitlines():
        parts = line.split()
        if len(parts) >= 6 and not line.lstrip().startswith("#"):
            number = re.search(rf"^{re.escape(parts[0])}\s+(\d+)/(tcp|udp)", texts.get("/etc/services", ""), re.M)
            ports.append({"proto": number[2] if number else parts[2][:3], "port": int(number[1]) if number else 0, "service": parts[0], "what": f"inetd: {parts[5]}",
                          "how": "/etc/inetd.conf", "boot": True, "package": owner.get("/etc/inetd.conf", ("", ""))[0]})
    ports.sort(key=lambda p: (p["proto"], p["port"]))
    # Accounts: a root without password, or a shell for accounts that should have none.
    root = {}
    shadow = {line.split(":")[0]: line.split(":") for line in texts.get("/etc/shadow", "").splitlines() if line.count(":") >= 2}
    passwd = {line.split(":")[0]: line.split(":") for line in texts.get("/etc/passwd", "").splitlines() if line.count(":") >= 6}
    if "root" in shadow or "root" in passwd:
        secret = shadow["root"][1] if "root" in shadow else passwd["root"][1]
        root = {"password": "none (anyone can log in as root)" if secret == "" else "locked" if secret.startswith(("!", "*")) else "set",
                "empty": secret == ""}
    sshd = texts.get("/etc/ssh/sshd_config", "")
    findings = []
    if root.get("empty"):
        findings.append({"level": "error", "text": "root has no password", "fix": "remove debug-tweaks / empty-root-password / allow-empty-password from IMAGE_FEATURES, or set one with EXTRA_USERS_PARAMS"})
    if re.search(r"^\s*PermitRootLogin\s+yes", sshd, re.M):
        findings.append({"level": "warning", "text": "SSH allows root login", "fix": "PermitRootLogin prohibit-password (or no) in an openssh append"})
    if re.search(r"^\s*PermitEmptyPasswords\s+yes", sshd, re.M):
        findings.append({"level": "error", "text": "SSH accepts empty passwords", "fix": "remove allow-empty-password from IMAGE_FEATURES"})
    if any(p["port"] == 23 for p in ports):
        findings.append({"level": "warning", "text": "a telnet server is in the image", "fix": "use SSH; remove the telnetd package"})
    development = by_kind.get("Development files", {"size": 0})["size"] + by_kind.get("Debug symbols", {"size": 0})["size"]
    if development:
        findings.append({"level": "info", "text": f"{development} bytes of headers, static libraries or debug symbols on the device",
                         "fix": "remove dev-pkgs / dbg-pkgs from IMAGE_FEATURES, or the -dev packages from IMAGE_INSTALL"})
    docs = by_kind.get("Documentation and locales", {"size": 0})["size"]
    if docs > 512 * 1024:
        findings.append({"level": "info", "text": f"{docs} bytes of documentation and locales", "fix": "IMAGE_LINGUAS = \"\" and doc-pkgs out of IMAGE_FEATURES; or add the doc-free tasks to your distro"})
    data = {
        "image": image, "machine": machine, "total": total, "files": count, "packages": len(installed),
        "layers": _top(by_layer, 6), "recipes": _top(by_recipe, 12), "kinds": sorted(({"name": k, **v} for k, v in by_kind.items()), key=lambda r: -r["size"]),
        "licences": [{"name": r["name"], "size": r["size"], "packages": r["packages"], **({"names": r["names"][:8]} if "names" in r else {})}
                     for r in _top(licences, 8, by="packages")],
        "hubs": hubs, "ports": ports, "boot": len(starts), "init": services["init"],
        "setuid": sorted(setuid, key=lambda r: r["path"]), "writable": sorted(writable)[:50], "root": root, "findings": findings,
        "computed": time.time(),
    }
    _cache[key] = (found["mtime"], data)
    return data
