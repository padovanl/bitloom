from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Profile:
    name: str = "default"
    root: str = "."
    build_dir: str = "build"
    mode: str = "host"  # host, kas, container, kas-container, wrapper
    init_script: str = ""
    kas_file: str = "kas.yml"
    engine: str = "docker"
    image: str = ""
    container_name: str = ""
    container_root: str = "/work"
    machine: str = ""
    distro: str = ""
    downloads: str = ""
    sstate: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    container_args: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=lambda: ["core-image-minimal"])
    source_mappings: dict[str, str] = field(default_factory=dict)
    # wrapper mode: a project launcher script that runs kas for you.
    # kas subcommands become launcher + [subcommand]; other commands use
    # launcher + launcher_shell with {command} replaced by the quoted argv.
    launcher: list[str] = field(default_factory=list)
    launcher_shell: list[str] = field(default_factory=lambda: ["shell", "-c", "{command}"])

    @classmethod
    def from_dict(cls, data: dict, unknown: list | None = None) -> "Profile":
        """Build from stored JSON, ignoring keys from newer or older Bitloom versions."""
        from dataclasses import fields
        known = {f.name for f in fields(cls)}
        if unknown is not None:
            unknown.extend(sorted(set(data) - known))
        return cls(**{k: v for k, v in data.items() if k in known})

    @property
    def root_path(self) -> Path:
        return Path(self.root).expanduser().resolve()

    @property
    def build_path(self) -> Path:
        value = self.build_dir
        if self.mode in {"kas", "kas-container", "wrapper"} and self.build_dir == "build":
            value = self.environment.get("KAS_BUILD_DIR") or str(Path(self.environment.get("KAS_WORK_DIR", str(self.root_path))) / "build")
        p = Path(value).expanduser()
        return p.resolve() if p.is_absolute() else self.root_path / p

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Profile name is required")
        if not isinstance(self.environment, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in self.environment.items()):
            raise ValueError("environment must contain string keys and values")
        if not isinstance(self.container_args, list) or any(not isinstance(a, str) for a in self.container_args):
            raise ValueError("container_args must be an array of strings")
        if not isinstance(self.targets, list) or any(not isinstance(t, str) for t in self.targets):
            raise ValueError("targets must be an array of strings")
        if not isinstance(self.source_mappings, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not Path(k).is_absolute() or not Path(v).is_absolute() for k, v in self.source_mappings.items()):
            raise ValueError('source_mappings must map absolute runtime paths to absolute host paths')
        if self.mode not in {"host", "kas", "container", "kas-container", "wrapper"}:
            raise ValueError("Mode must be host, kas, container, kas-container or wrapper")
        if not isinstance(self.launcher, list) or any(not isinstance(a, str) for a in self.launcher):
            raise ValueError("launcher must be an array of strings")
        if not isinstance(self.launcher_shell, list) or any(not isinstance(a, str) for a in self.launcher_shell):
            raise ValueError("launcher_shell must be an array of strings")
        if self.mode == "wrapper":
            if not self.launcher or not self.launcher[0].strip():
                raise ValueError('wrapper mode needs a launcher, e.g. ["./scripts/kas-wrapper.sh"]')
            if not any("{command}" in part for part in self.launcher_shell):
                raise ValueError("launcher_shell must contain {command}")
        if self.engine not in {"docker", "podman"}:
            raise ValueError("Container engine must be docker or podman")
        if self.mode == "container" and not (self.image or self.container_name):
            raise ValueError("Configure a container image or existing container name")
        if not re.fullmatch(r"/[\w/.-]+", self.container_root):
            raise ValueError("container_root must be an absolute container path")
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) for k in self.environment):
            raise ValueError("Invalid environment variable name")
        if self.mode == "container":
            try:
                self.build_path.relative_to(self.root_path)
            except ValueError as exc:
                raise ValueError("Container build directory must be inside root") from exc


class Settings:
    """Personal profiles plus read-only team profiles from "include" files.

    Includes are JSON files with a "profiles" array, typically on NFS or in a
    shared repository. Relative include paths resolve from this file's folder.
    """
    def __init__(self, path: Path):
        self.path = path
        self.profiles: list[Profile] = []
        self.active = "default"
        self.include: list[str] = []
        self.shared: dict[str, str] = {}
        self.include_warnings: list[str] = []
        self.ignored_keys: list[str] = []
        if path.exists():
            data = json.loads(path.read_text())
            self.active = data.get("active", "default")
            ignored = []
            self.profiles = [Profile.from_dict(p, ignored) for p in data.get("profiles", [])]
            self.ignored_keys = sorted(set(ignored))
            self.include = data.get("include", [])
            if not isinstance(self.include, list) or any(not isinstance(i, str) for i in self.include):
                raise ValueError("include must be an array of file paths")
        self.load_shared()
        if not self.profiles:
            self.profiles = [Profile(root=str(Path.cwd()))]
        for profile in self.profiles:
            profile.validate()
        if len({p.name for p in self.profiles}) != len(self.profiles):
            raise ValueError("Profile names must be unique")
        if self.active not in {p.name for p in self.profiles}:
            raise ValueError("Active profile must exist")

    def include_path(self, value: str) -> Path:
        path = Path(os.path.expandvars(value)).expanduser()
        return (path if path.is_absolute() else self.path.parent / path).resolve()

    def load_shared(self) -> None:
        own = {p.name for p in self.profiles if p.name not in self.shared}
        self.profiles = [p for p in self.profiles if p.name not in self.shared]
        self.shared, self.include_warnings = {}, []
        for value in self.include:
            source = self.include_path(value)
            try:
                data = json.loads(source.read_text())
                for raw in data.get("profiles", []):
                    profile = Profile.from_dict(raw)
                    profile.validate()
                    if profile.name in own or profile.name in self.shared:
                        self.include_warnings.append(f"{source}: profile '{profile.name}' already defined; kept the first")
                        continue
                    self.shared[profile.name] = str(source)
                    self.profiles.append(profile)
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                # An unreachable NFS share must not prevent personal profiles from loading.
                self.include_warnings.append(f"{source}: {exc}")

    @property
    def own_profiles(self) -> list[Profile]:
        return [p for p in self.profiles if p.name not in self.shared]

    @property
    def profile(self) -> Profile:
        return next((p for p in self.profiles if p.name == self.active), self.profiles[0])

    def save(self) -> None:
        if len({p.name for p in self.profiles}) != len(self.profiles):
            raise ValueError("Profile names must be unique")
        for p in self.profiles:
            p.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        data = {"active": self.active, "profiles": [asdict(p) for p in self.own_profiles]}
        if self.include:
            data["include"] = self.include
        temporary.write_text(json.dumps(data, indent=2))
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)


def read_assignments(path: Path) -> dict[str, str]:
    """Read simple literal assignments; BitBake expansion is obtained via bitbake -e."""
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r'^\s*([\w:.-]+)\s*(?:\?\?=|\?=|:=|=)\s*"(.*?)"\s*(?:#.*)?$', line)
        if m:
            values[m[1]] = m[2]
    return values
