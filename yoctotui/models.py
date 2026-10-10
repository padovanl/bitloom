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

    @property
    def root_path(self) -> Path:
        return Path(self.root).expanduser().resolve()

    @property
    def build_path(self) -> Path:
        p = Path(self.build_dir).expanduser()
        return p.resolve() if p.is_absolute() else self.root_path / p

    def validate(self) -> None:
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
        if self.mode in {"container", "kas-container"}:
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
