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
    mode: str = "host"  # host, kas, container, kas-container
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

    @property
    def root_path(self) -> Path:
        return Path(self.root).expanduser().resolve()

    @property
    def build_path(self) -> Path:
        value = self.build_dir
        if self.mode in {"kas", "kas-container"} and self.build_dir == "build":
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
        if self.mode not in {"host", "kas", "container", "kas-container"}:
            raise ValueError("Mode must be host, kas, container or kas-container")
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
    def __init__(self, path: Path):
        self.path = path
        self.profiles: list[Profile] = []
        self.active = "default"
        if path.exists():
            data = json.loads(path.read_text())
            self.active = data.get("active", "default")
            self.profiles = [Profile(**p) for p in data.get("profiles", [])]
        if not self.profiles:
            self.profiles = [Profile(root=str(Path.cwd()))]
        for profile in self.profiles:
            profile.validate()
        if len({p.name for p in self.profiles}) != len(self.profiles):
            raise ValueError("Profile names must be unique")
        if self.active not in {p.name for p in self.profiles}:
            raise ValueError("Active profile must exist")

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
        temporary.write_text(json.dumps({"active": self.active, "profiles": [asdict(p) for p in self.profiles]}, indent=2))
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
