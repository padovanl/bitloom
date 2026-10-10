"""Host setup and shared-infrastructure checks for teams: filesystems, limits,
mirrors, hash equivalence and PR services. Network probes run only on demand."""
from __future__ import annotations

import os
import re
import shutil
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

from .models import Profile, read_assignments

NETWORK_FS = {"nfs", "nfs4", "cifs", "smb3", "smbfs", "9p", "drvfs", "fuse.sshfs", "ceph", "glusterfs", "lustre", "gpfs"}
GiB = 1024 ** 3


def mounts() -> list[tuple[str, str]]:
    """(mount point, filesystem type), longest mount points first."""
    result = []
    try:
        for line in Path("/proc/mounts").read_text().splitlines():
            parts = line.split()
            if len(parts) >= 3:
                result.append((parts[1].replace("\\040", " "), parts[2]))
    except OSError:
        pass
    return sorted(result, key=lambda item: len(item[0]), reverse=True)


def filesystem(path: Path, table=None) -> str:
    # Non-strict resolve follows symlinks of the existing prefix; a not-yet-created
    # build directory still maps to the mount that will hold it.
    resolved = str(Path(path).resolve())
    for point, kind in table if table is not None else mounts():
        if resolved == point or resolved.startswith(point.rstrip("/") + "/"):
            return kind
    return "unknown"


def wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def host_checks() -> list[tuple[str, str, str]]:
    """Prerequisites a new team member usually discovers one failed build at a time."""
    results = []
    cores = os.cpu_count() or 1
    results.append(("OK" if cores >= 4 else "WARN", "CPU cores", f"{cores} (4+ recommended; BB_NUMBER_THREADS defaults to this)"))
    try:
        mem = {line.split(":")[0]: int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines()}
        total = mem["MemTotal"]
        level = "OK" if total >= 16 * GiB else "WARN"
        results.append((level, "Memory", f"{total / GiB:.1f} GiB (16 GiB+ for parallel C++ builds; ~2 GiB per compile job)"))
    except (OSError, KeyError, ValueError):
        pass
    results.append(("OK" if sys.version_info >= (3, 10) else "WARN", "Python", sys.version.split()[0]))
    locale = os.environ.get("LC_ALL") or os.environ.get("LANG", "")
    results.append(("OK" if "utf-8" in locale.lower() or "utf8" in locale.lower() else "WARN", "Locale",
                    (locale or "unset") + " (BitBake requires a UTF-8 locale)"))
    try:
        watches = int(Path("/proc/sys/fs/inotify/max_user_watches").read_text())
        results.append(("OK" if watches >= 65536 else "WARN", "inotify watches", f"{watches} (raise fs.inotify.max_user_watches for large trees and IDEs)"))
    except (OSError, ValueError):
        pass
    try:
        import resource
        soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
        results.append(("OK" if soft >= 4096 or soft == resource.RLIM_INFINITY else "WARN", "Open files limit", f"{soft} (4096+ avoids 'Too many open files')"))
    except (ImportError, ValueError, OSError):
        pass
    engines = [name for name in ("docker", "podman") if shutil.which(name)]
    results.append(("OK" if engines else "INFO", "Container engine", ", ".join(engines) or "none in PATH (needed for container and kas-container profiles)"))
    for tool in ("kas", "kas-container", "git"):
        found = shutil.which(tool)
        results.append(("OK" if found else "INFO", tool, found or "not in PATH"))
    if wsl():
        results.append(("INFO", "WSL", "Keep build directories on the Linux filesystem; /mnt/<drive> (drvfs) is slow and breaks permissions"))
    return results


def filesystem_checks(profile: Profile, table=None) -> list[tuple[str, str, str]]:
    from .inspectors import cache_path
    conf = read_assignments(profile.build_path / "conf/local.conf")
    tmpdir = conf.get("TMPDIR", "").replace("${TOPDIR}", str(profile.build_path))
    tmp = Path(tmpdir) if tmpdir and "${" not in tmpdir else profile.build_path / "tmp"
    results = []
    for label, path, shared_ok in (("Build directory", profile.build_path, False), ("TMPDIR", tmp, False),
                                   ("DL_DIR", cache_path(profile, "downloads"), True), ("SSTATE_DIR", cache_path(profile, "sstate"), True)):
        kind = filesystem(path, table)
        if kind in NETWORK_FS and not shared_ok:
            level, note = "WARN", "network filesystem: TMPDIR/build on NFS/CIFS is unsupported (locking, hard links, speed)"
        elif kind in NETWORK_FS:
            level, note = "INFO", "shared cache on a network filesystem: fine for downloads/sstate; prefer SSTATE_MIRRORS read-only plus a local SSTATE_DIR when many builders write"
        elif kind == "unknown":
            level, note = "INFO", "filesystem type not detected"
        else:
            level, note = "OK", "local filesystem"
        results.append((level, f"{label} filesystem", f"{kind} · {path} · {note}"))
    return results


def endpoints(profile: Profile) -> list[tuple[str, str]]:
    """Literal shared-infrastructure settings from local.conf: (variable, endpoint)."""
    conf = read_assignments(profile.build_path / "conf/local.conf")
    found = []
    for name in ("SSTATE_MIRRORS", "PREMIRRORS", "MIRRORS"):
        for url in re.findall(r"((?:https?|ftp|file)://[^\s\\\\]+)", conf.get(name, "")):
            found.append((name, url.replace("/PATH;downloadfilename=PATH", "").replace("/PATH", "")))
    for name in ("BB_HASHSERVE", "BB_HASHSERVE_UPSTREAM", "PRSERV_HOST"):
        value = conf.get(name, "").strip()
        if value:
            found.append((name, value))
    return found


def probe(endpoint: str, timeout=3.0) -> tuple[str, str]:
    """Reachability only: TCP connect for services and URLs, existence for file:// paths."""
    if endpoint in {"auto", "localhost:0"}:
        return "OK", "local server started by BitBake"
    if endpoint.startswith("file://"):
        path = Path(urlparse(endpoint).path)
        return ("OK", "directory reachable") if path.is_dir() else ("WARN", "path missing or not mounted")
    if "://" in endpoint:
        parsed = urlparse(endpoint)
        host, port = parsed.hostname, parsed.port or {"https": 443, "http": 80, "ftp": 21}.get(parsed.scheme, 80)
    else:
        host, _, port = endpoint.rpartition(":")
        if host.startswith("unix") or not port.isdigit():
            return "INFO", "not a host:port endpoint"
        host, port = host.strip("[]"), int(port)
    if not host:
        return "INFO", "no host"
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "OK", f"TCP {host}:{port} reachable"
    except OSError as exc:
        return "WARN", f"TCP {host}:{port} unreachable: {exc}"


def network_report(profile: Profile) -> str:
    rows = endpoints(profile)
    lines = [f"Shared infrastructure · {profile.name}", f"Source: literal values in {profile.build_path / 'conf/local.conf'} (kas writes it on first build).",
             "Checks reachability only (TCP connect / mounted path); it does not download or authenticate.", ""]
    if not rows:
        lines.append("No SSTATE_MIRRORS, PREMIRRORS, MIRRORS, BB_HASHSERVE or PRSERV_HOST set. Teams usually share a read-only sstate mirror and a hash equivalence server.")
    for name, endpoint in rows:
        status, detail = probe(endpoint)
        lines.append(f"{status:5} {name:22} {endpoint}\n      {detail}")
    lines += ["", "FILESYSTEMS", *[f"{s:5} {n:24} {d}" for s, n, d in filesystem_checks(profile)]]
    return "\n".join(lines)
