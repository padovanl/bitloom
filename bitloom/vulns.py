"""Vulnerability findings from SBOM-based CVE tools, merged into one view.

Sources (all optional, read offline):
* Yocto CVE JSON: cve-check (tmp/log/cve/cve-summary.json, <image>.rootfs.json) and
  sbom-cve-check (<image>.rootfs.sbom-cve-check.yocto.json), the same format.
* Grype JSON produced from an SPDX SBOM (*.grype.json in the state directory).
Scanners Bitloom can run as jobs: Grype on the newest SBOM, VulnScout in CI mode."""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .commands import which
from .models import Profile

SEVERITY = (("critical", 9.0), ("high", 7.0), ("medium", 4.0), ("low", 0.1))


@dataclass
class Finding:
    id: str
    package: str
    version: str
    status: str          # Unpatched | Patched | Ignored | (grype) affected
    score: float | None
    severity: str
    detail: str
    summary: str
    vector: str
    link: str
    source: str
    review: str = ""


def severity_of(score: float | None, label: str = "") -> str:
    if label:
        return label.lower()
    if score is None:
        return "unknown"
    return next((name for name, low in SEVERITY if score >= low), "none")


def _score(issue: dict) -> float | None:
    for key in ("scorev4", "scorev3", "scorev2"):
        try:
            value = float(issue.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None


def parse_yocto(path: Path, source: str) -> list[Finding]:
    data = json.loads(path.read_text(errors="replace"))
    findings = []
    for package in data.get("package", []):
        for issue in package.get("issue", []):
            score = _score(issue)
            findings.append(Finding(issue.get("id", "?"), package.get("name", "?"), package.get("version", ""), issue.get("status", "?"), score,
                                    severity_of(score), issue.get("detail", ""), (issue.get("summary") or issue.get("description") or "")[:600],
                                    issue.get("vectorString") or issue.get("vector", ""), issue.get("link", ""), source))
    return findings


def parse_grype(path: Path) -> list[Finding]:
    data = json.loads(path.read_text(errors="replace"))
    findings = []
    for match in data.get("matches", []):
        vulnerability, artifact = match.get("vulnerability", {}), match.get("artifact", {})
        scores = [c.get("metrics", {}).get("baseScore") for c in vulnerability.get("cvss", []) if c.get("metrics", {}).get("baseScore")]
        fix = vulnerability.get("fix", {})
        detail = ("fixed in " + ", ".join(fix.get("versions", []))) if fix.get("versions") else fix.get("state", "")
        findings.append(Finding(vulnerability.get("id", "?"), artifact.get("name", "?"), artifact.get("version", ""), "Unpatched",
                                max(scores) if scores else None, severity_of(max(scores) if scores else None, vulnerability.get("severity", "") if vulnerability.get("severity") not in {None, "Unknown", "Negligible"} else ""),
                                detail, (vulnerability.get("description") or "")[:600], "", vulnerability.get("dataSource", ""), "grype"))
    return findings


def sources(profile: Profile, state: Path | None = None) -> list[tuple[str, Path]]:
    """(label, path) of every report found, newest first per kind."""
    found = []
    images = profile.build_path / "tmp/deploy/images"
    if images.is_dir():
        for path in sorted(images.rglob("*.sbom-cve-check.yocto.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if not path.is_symlink():
                found.append(("sbom-cve-check · " + path.name, path))
        for path in sorted(images.rglob("*.rootfs.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if not path.is_symlink() and not path.name.endswith(".sbom-cve-check.yocto.json"):
                found.append(("cve-check image · " + path.name, path))
    summary = profile.build_path / "tmp/log/cve/cve-summary.json"
    if summary.is_file():
        found.append(("cve-check summary", summary))
    if state:
        scans = Path(state) / "vulnerability-scans"
        if scans.is_dir():
            found += [("grype · " + p.name, p) for p in sorted(scans.glob("*.grype.json"), key=lambda p: p.stat().st_mtime, reverse=True)]
    return found


def load(profile: Profile, state: Path | None = None, source: str = "") -> tuple[list[Finding], list[str]]:
    """Findings of one source (label) or of the newest report of each kind; plus errors."""
    available = sources(profile, state)
    chosen, kinds = [], set()
    for label, path in available:
        kind = label.split(" · ")[0]
        if (source and label == source) or (not source and kind not in kinds):
            chosen.append((label, path))
            kinds.add(kind)
    findings, errors = [], []
    for label, path in chosen:
        try:
            findings += parse_grype(path) if label.startswith("grype") else parse_yocto(path, label.split(" · ")[0])
        except (OSError, ValueError) as exc:
            errors.append(f"{path.name}: {exc}")
        except (AttributeError, TypeError, KeyError) as exc:
            errors.append(f"{path.name}: unexpected report structure ({exc})")
    if state:
        from .developer import read_reviews
        try:
            reviews = read_reviews(Path(state) / "security-reviews.json")
        except (OSError, ValueError) as exc:
            reviews = {}
            errors.append(str(exc))
        for finding in findings:
            review = reviews.get(f"{finding.package}/{finding.id}")
            if review:
                finding.review = f"{review.get('owner', '?')} until {review.get('expires', '?')}"
    # One row per CVE and package: prefer the most specific (unpatched) assessment.
    unique = {}
    for finding in findings:
        key = (finding.id, finding.package)
        if key not in unique or (finding.status == "Unpatched" and unique[key].status != "Unpatched"):
            unique[key] = finding
    rank = {name: i for i, (name, _) in enumerate(SEVERITY)}
    ordered = sorted(unique.values(), key=lambda f: (f.status != "Unpatched", rank.get(f.severity, 9), -(f.score or 0), f.package, f.id))
    return ordered, errors


def select(findings: list[Finding], status: str = "unpatched", min_score: float = 0.0, text: str = "") -> list[Finding]:
    needle = text.casefold()
    result = []
    for finding in findings:
        if status == "unpatched" and finding.status != "Unpatched":
            continue
        if status == "reviewed" and not finding.review:
            continue
        if min_score and (finding.score or 0) < min_score:
            continue
        if needle and needle not in f"{finding.id} {finding.package} {finding.summary} {finding.detail}".casefold():
            continue
        result.append(finding)
    return result


def counts(findings: list[Finding]) -> dict:
    result = {"total": len(findings), "unpatched": 0, "patched": 0, "ignored": 0, "reviewed": 0}
    for finding in findings:
        result[finding.status.lower()] = result.get(finding.status.lower(), 0) + 1
        result["reviewed"] += bool(finding.review)
        if finding.status == "Unpatched":
            result["unpatched_" + finding.severity] = result.get("unpatched_" + finding.severity, 0) + 1
    return result


NO_REPORT = ("No CVE report yet. Wrynose: enable sbom-cve-check (Configuration → SBOM settings, or bitbake-config-build "
             "enable-fragment core/yocto/sbom-cve-check) and build the image; older releases: INHERIT += \"cve-check\". "
             "Or scan the newest SPDX SBOM with Grype (Artifacts → v → g).")


def report(findings: list[Finding], errors: list[str], status="unpatched", min_score=0.0) -> str:
    if not findings and not errors:
        return NO_REPORT
    shown = select(findings, status, min_score)
    c = counts(findings)
    lines = [f"Vulnerabilities · {c['total']} assessed · {c['unpatched']} unpatched · {c['patched']} patched · {c['ignored']} ignored · {c['reviewed']} reviewed",
             "Severity from CVSS (v4, v3, then v2). 'Unpatched' means the tool found no fix in the recipe; review before acting.", ""]
    lines += [f"{f.severity.upper():9} {('%.1f' % f.score) if f.score else '  — ':>4}  {f.id:18} {f.package} {f.version}  [{f.status}] {f.detail}"
              + (f"  ✔ {f.review}" if f.review else "") for f in shown[:500]]
    if len(shown) > 500:
        lines.append(f"… {len(shown) - 500} more")
    lines += [f"! {e}" for e in errors]
    return "\n".join(lines)


def to_csv(findings: list[Finding]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(asdict(findings[0]).keys()) if findings else ["id"])
    writer.writeheader()
    for finding in findings:
        writer.writerow(asdict(finding))
    return stream.getvalue()


def scanners() -> dict:
    return {name: which(name) for name in ("grype", "vulnscout")}


def grype_argv(sbom: Path, output: Path) -> list[str]:
    if not which("grype"):
        raise ValueError("grype is not installed (https://github.com/anchore/grype)")
    if sbom.name.endswith(".manifest"):
        raise ValueError("Grype needs an SPDX JSON SBOM; SPDX 2.2 images ship an archive: extract IMAGE.spdx.tar.zst first")
    return ["grype", f"sbom:{sbom}", "-o", "json", "--file", str(output)]


def vulnscout_argv(project: str, sbom: Path, cve_json: Path | None, condition: str) -> list[str]:
    if not which("vulnscout"):
        raise ValueError("vulnscout is not in PATH (https://github.com/savoirfairelinux/vulnscout)")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", project):
        raise ValueError("Invalid project name")
    argv = ["vulnscout", "--project", project, "--add-spdx", str(sbom)]
    if cve_json:
        argv += ["--add-cve-check", str(cve_json)]
    return argv + ["--match-condition", condition]
