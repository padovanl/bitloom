"""Offline SBOM inspection (SPDX 3 JSON-LD as produced by Yocto 5.1+/6.0 Wrynose, and
SPDX 2.2 JSON) and an engineering checklist for EU Cyber Resilience Act readiness.

This reports evidence present in the build directory. It is not a conformity
assessment or legal advice."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from .models import Profile, read_assignments

MAX_BYTES = 512 * 1024 * 1024
MISSING = {"", "NOASSERTION", "NONE", None}
VEX_TYPES = {
    "security_VexFixedVulnAssessmentRelationship": "fixed",
    "security_VexNotAffectedVulnAssessmentRelationship": "not affected",
    "security_VexAffectedVulnAssessmentRelationship": "affected",
    "security_VexUnderInvestigationVulnAssessmentRelationship": "under investigation",
}


def sbom_files(profile: Profile) -> list[Path]:
    """Image/SDK SBOMs in deploy directories, newest first (symlinked stable names skipped).

    SPDX 3 images ship one IMAGE.spdx.json. SPDX 2.2 images (up to 5.0) ship an
    IMAGE.spdx.tar.zst archive; its image manifest stands in for it, joined with the
    per-package documents in tmp/deploy/spdx, so no zstd tooling is needed."""
    found = []
    for folder in (profile.build_path / "tmp/deploy/images", profile.build_path / "tmp/deploy/sdk"):
        if not folder.is_dir():
            continue
        found += [p for p in folder.rglob("*.spdx.json") if p.is_file() and not p.is_symlink()]
        for archive in folder.rglob("*.spdx.tar.zst"):
            manifest = archive.with_name(archive.name[:-len(".spdx.tar.zst")] + ".manifest")
            if archive.is_file() and not archive.is_symlink() and manifest.is_file() and manifest not in found:
                found.append(manifest)
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def _deploy_spdx(manifest: Path) -> Path:
    # tmp/deploy/images/<machine>/<image>.manifest → tmp/deploy/spdx
    return manifest.parents[2] / "spdx"


def _analyse_spdx2_image(manifest: Path) -> dict:
    spdx = _deploy_spdx(manifest)
    pkgdata = manifest.parents[3] / "pkgdata"
    arches = [p for p in spdx.iterdir() if p.is_dir() and p.name not in {"by-hash", "by-namespace"}] if spdx.is_dir() else []
    rows, fixed, missing = [], set(), 0
    recipes = {}
    for line in manifest.read_text(errors="replace").splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        name, arch, version = fields[0], fields[1], fields[2]
        candidates = [spdx / arch / "packages" / f"{name}.spdx.json", spdx / arch.replace("_", "-") / "packages" / f"{name}.spdx.json"]
        candidates += [folder / "packages" / f"{name}.spdx.json" for folder in arches]
        path = next((c for c in candidates if c.is_file()), None)
        if path is None:
            missing += 1
            rows.append({"name": name, "version": version, "purl": False, "cpe": False, "license": False, "supplier": False})
            continue
        package = (json.loads(path.read_text(errors="replace")).get("packages") or [{}])[0]
        recipe_name = name
        for reverse in pkgdata.glob(f"*/runtime-reverse/{name}"):
            match = re.search(r"^PN: (\S+)", reverse.read_text(errors="replace"), re.M)
            if match:
                recipe_name = match[1]
                break
        if recipe_name not in recipes:
            recipe_path = path.parents[1] / "recipes" / f"recipe-{recipe_name}.spdx.json"
            recipe = (json.loads(recipe_path.read_text(errors="replace")).get("packages") or [{}])[0] if recipe_path.is_file() else {}
            recipes[recipe_name] = recipe
            info = recipe.get("sourceInfo", "")
            if info.startswith("CVEs fixed:"):
                fixed.update(info.split(":", 1)[1].split())
        recipe = recipes[recipe_name]
        refs = recipe.get("externalRefs", []) + package.get("externalRefs", [])
        supplier = package.get("supplier") or recipe.get("supplier")
        rows.append({"name": name, "version": package.get("versionInfo") or version,
                     "purl": any("purl" in str(r.get("referenceType", "")).lower() for r in refs),
                     "cpe": any("cpe" in str(r.get("referenceType", "")).lower() for r in refs),
                     "license": any(package.get(k) not in MISSING for k in ("licenseConcluded", "licenseDeclared")),
                     # The OpenEmbedded placeholder does not identify the manufacturer.
                     "supplier": supplier not in MISSING and "OpenEmbedded ()" not in str(supplier)})
    summary = _summary(manifest, "SPDX 2.2 (image manifest + per-package documents)", None, ["OpenEmbedded create-spdx 2.2"], rows,
                       Counter({"CVEs recorded fixed by recipes": len(fixed)}) if fixed else Counter(), {"CVEs recorded fixed by recipes": sorted(fixed)[:15]} if fixed else {})
    summary["unresolved_packages"] = missing
    return summary


def _types(element) -> set[str]:
    kind = element.get("type") or element.get("@type") or ""
    return set(kind if isinstance(kind, list) else [kind])


def analyse(path: Path) -> dict:
    """Package identity, licensing, supplier and vulnerability coverage of one SBOM."""
    if path.name.endswith(".manifest"):
        return _analyse_spdx2_image(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f"{path} exceeds {MAX_BYTES // 1024 // 1024} MiB")
    data = json.loads(path.read_text(errors="replace"))
    if isinstance(data, dict) and str(data.get("spdxVersion", "")).startswith("SPDX-2"):
        return _analyse_spdx2(path, data)
    graph = data.get("@graph") if isinstance(data, dict) else None
    if not isinstance(graph, list):
        raise ValueError(f"{path.name}: not an SPDX 2 document or SPDX 3 JSON-LD graph")
    return _analyse_spdx3(path, data, graph)


def _analyse_spdx2(path, data):
    packages = data.get("packages", [])
    rows = []
    for package in packages:
        refs = package.get("externalRefs", [])
        rows.append({"name": package.get("name"), "version": package.get("versionInfo"),
                     "purl": any("purl" in str(r.get("referenceType", "")).lower() for r in refs),
                     "cpe": any("cpe" in str(r.get("referenceType", "")).lower() for r in refs),
                     "license": package.get("licenseConcluded") not in MISSING or package.get("licenseDeclared") not in MISSING,
                     "supplier": package.get("supplier") not in MISSING})
    created = data.get("creationInfo", {})
    return _summary(path, "SPDX " + data["spdxVersion"].split("-", 1)[1], created.get("created"), created.get("creators", []), rows, Counter(), [])


def _analyse_spdx3(path, data, graph):
    by_id = {e.get("spdxId") or e.get("@id"): e for e in graph if isinstance(e, dict)}
    licensed, vex, cves = set(), Counter(), {}
    for element in graph:
        if not isinstance(element, dict):
            continue
        types = _types(element)
        relation = element.get("relationshipType")
        if relation in {"hasConcludedLicense", "hasDeclaredLicense"}:
            licensed.add(element.get("from"))
        for kind, status in VEX_TYPES.items():
            if kind in types:
                vex[status] += 1
                vulnerability = by_id.get(element.get("from"), {})
                ident = next((x.get("identifier") for x in vulnerability.get("externalIdentifier", []) if x.get("identifier")), element.get("from"))
                cves.setdefault(status, set()).add(ident)
    rows = []
    for element in graph:
        if not isinstance(element, dict) or "software_Package" not in _types(element):
            continue
        identifiers = element.get("externalIdentifier", []) or []
        kinds = {x.get("externalIdentifierType") for x in identifiers if isinstance(x, dict)}
        rows.append({"name": element.get("name"), "version": element.get("software_packageVersion"),
                     "purl": bool(element.get("software_packageUrl")) or "packageUrl" in kinds,
                     "cpe": bool(kinds & {"cpe22", "cpe23"}),
                     "license": element.get("spdxId") in licensed, "supplier": bool(element.get("suppliedBy"))})
    creation = next((e for e in graph if isinstance(e, dict) and "CreationInfo" in _types(e)), {})
    context = json.dumps(data.get("@context", ""))
    version = "SPDX " + (re.search(r"spdx\.org/rdf/(3[\d.]*)", context) or [None, "3"])[1]
    tools = [by_id.get(t, {}).get("name", t) for t in creation.get("createdUsing", [])] if creation else []
    examples = {status: sorted(map(str, ids))[:15] for status, ids in cves.items()}
    return _summary(path, version, creation.get("created"), tools, rows, vex, examples)


def _summary(path, version, created, tools, rows, vex, examples):
    total = len(rows)

    def share(key):
        return sum(1 for row in rows if row[key]) / total if total else 0.0
    return {"file": str(path), "format": version, "created": created, "tools": tools, "packages": total,
            "with_version": share("version"), "with_purl": share("purl"), "with_cpe": share("cpe"),
            "with_license": share("license"), "with_supplier": share("supplier"),
            "vex": dict(vex), "vex_examples": examples,
            "missing_license": sorted({r["name"] for r in rows if not r["license"] and r["name"]})[:25],
            "missing_identity": sorted({r["name"] for r in rows if not r["purl"] and not r["cpe"] and r["name"]})[:25]}


def sbom_report(profile: Profile, limit=6) -> str:
    files = sbom_files(profile)
    lines = ["SBOM quality · " + profile.name, "Machine-readable SBOMs found in tmp/deploy. Coverage shows what a vulnerability or",
             "licence scanner can match automatically; gaps need recipe metadata (PURL/CPE via CVE_PRODUCT, LICENSE, supplier).", ""]
    if not files:
        lines += ["No *.spdx.json SBOM found.", "Enable create-spdx (default in Poky since 4.1; SPDX 3 by default from 5.1, mandatory in 6.0 Wrynose) and build an image."]
        return "\n".join(lines)
    for path in files[:limit]:
        try:
            s = analyse(path)
        except (OSError, ValueError) as exc:
            lines += [f"✖ {path.name}: {exc}", ""]
            continue
        pct = lambda value: f"{100 * value:5.1f}%"
        lines += [f"◆ {path.relative_to(profile.build_path)}", f"  {s['format']} · created {s['created'] or '?'} · {', '.join(map(str, s['tools'])) or 'tool not recorded'}",
                  f"  packages {s['packages']:>6}   version {pct(s['with_version'])}   PURL {pct(s['with_purl'])}   CPE {pct(s['with_cpe'])}",
                  f"  licence  {pct(s['with_license'])}   supplier {pct(s['with_supplier'])}"]
        if s["vex"]:
            lines.append("  VEX      " + " · ".join(f"{status} {count}" for status, count in sorted(s["vex"].items())))
            for status in ("affected", "under investigation"):
                if s["vex_examples"].get(status):
                    lines.append(f"    {status}: " + ", ".join(s["vex_examples"][status]))
        else:
            lines.append("  VEX      none in this document (Wrynose: sbom-cve-check / vex class; older: cve-check)")
        if s.get("unresolved_packages"):
            lines.append(f"  {s['unresolved_packages']} installed packages without an SPDX document in tmp/deploy/spdx")
        if s["missing_license"]:
            lines.append("  no licence: " + ", ".join(s["missing_license"]))
        if s["missing_identity"]:
            lines.append("  no PURL/CPE: " + ", ".join(s["missing_identity"]))
        lines.append("")
    if len(files) > limit:
        lines.append(f"{len(files) - limit} older SBOM files not shown.")
    return "\n".join(lines)


DEADLINES = [(date(2026, 9, 11), "Reporting of actively exploited vulnerabilities and severe incidents (Art. 14): early warning within 24 h via the ENISA single reporting platform"),
             (date(2027, 12, 11), "Essential requirements apply (Annex I): secure by default, vulnerability handling, SBOM, security updates")]


def cra_report(profile: Profile, state: Path | None = None, today: date | None = None) -> str:
    today = today or date.today()
    rows = cra_checks(profile, state, today)
    lines = [f"CRA readiness · {profile.name}", "Engineering evidence from this build directory for Regulation (EU) 2024/2847. Not a conformity assessment or legal advice.", "",
             *[f"{status:5} {item:30} {detail}" for status, item, detail in rows], "", "TIMELINE"]
    lines += [f"{'in force' if when <= today else 'from':8} {when:%Y-%m-%d}  {text}" for when, text in DEADLINES]
    lines += ["", "STANDARDS", "EN 40000-1-3 (draft, CEN/CENELEC JTC 13): vulnerability handling process - receipt, assessment, remediation,",
              "communication and tracking. Bitloom contributes per-build SBOM quality, VEX status, dispositions with owner/expiry and evidence bundles."]
    return "\n".join(lines)


def cra_checks(profile: Profile, state: Path | None = None, today: date | None = None) -> list[tuple[str, str, str]]:
    today = today or date.today()
    deploy = profile.build_path / "tmp/deploy"
    conf = read_assignments(profile.build_path / "conf/local.conf")
    rows = []

    def add(status, item, detail):
        rows.append((status, item, detail))
    from .versions import INFO, detect_release
    series = detect_release(profile)
    if series in INFO:
        version, end, lts = INFO[series]
        left = (end - today).days
        status = "WARN" if left < 0 or not lts else "OK"
        add(status, "Yocto release support", f"{series} {version}{' LTS' if lts else ''} · community support until {end:%Y-%m}" + (" (ended)" if left < 0 else f" ({left // 30} months)"))
    else:
        add("INFO", "Yocto release support", (series or "not detected") + " · CRA expects security updates for the product support period; plan LTS upgrades")
    sboms = sbom_files(profile)
    if sboms:
        try:
            summary = analyse(sboms[0])
            add("OK", "Machine-readable SBOM", f"{summary['format']} · {summary['packages']} packages · {sboms[0].name}")
            add("OK" if summary["with_purl"] >= .9 else "WARN", "Component identifiers", f"PURL {100 * summary['with_purl']:.0f}% · CPE {100 * summary['with_cpe']:.0f}% (needed to match vulnerability databases)")
            add("OK" if summary["with_license"] >= .9 else "WARN", "Licence information", f"{100 * summary['with_license']:.0f}% of packages")
            add("OK" if summary["vex"] else "WARN", "Vulnerability status (VEX)", " · ".join(f"{k} {v}" for k, v in summary["vex"].items()) or "no VEX assessments in the latest SBOM")
        except (OSError, ValueError) as exc:
            add("WARN", "Machine-readable SBOM", str(exc))
    else:
        add("WARN", "Machine-readable SBOM", "no *.spdx.json in tmp/deploy; enable create-spdx and build the product image")
    reports = [p.name for p in (deploy / "images").rglob("*") if p.is_file() and re.search(r"sbom-cve-check|\.vex\.|cve", p.name)] if (deploy / "images").is_dir() else []
    legacy = (profile.build_path / "tmp/log/cve/cve-summary.json").exists()
    if reports:
        add("OK", "Vulnerability analysis", f"{len(reports)} report files (e.g. {reports[0]})")
    elif legacy:
        add("OK", "Vulnerability analysis", "cve-check summary in tmp/log/cve (pre-6.0 releases)")
    else:
        from .versions import ORDER
        if series in ORDER and ORDER[series] >= ORDER["wrynose"]:
            hint = "enable sbom-cve-check (Configuration → SBOM settings, or bitbake-config-build enable-fragment core/yocto/sbom-cve-check)"
        elif series in ORDER:
            hint = f'INHERIT += "cve-check" ({series} predates sbom-cve-check, which arrives with 6.0 Wrynose)'
        else:
            hint = 'Wrynose: sbom-cve-check fragment; older releases: INHERIT += "cve-check"'
        add("WARN", "Vulnerability analysis", "none found: " + hint)
    local = profile.build_path / "conf/local.conf"
    raw = local.read_text(errors="replace") if local.exists() else ""
    inherit = " ".join(re.findall(r'^\s*(?:INHERIT|USER_CLASSES)\s*(?:\+=|\?=|=|:append\s*=)\s*"([^"]*)"', raw, re.M))
    add("OK" if "buildhistory" in inherit else "INFO", "Change traceability", "buildhistory enabled" if "buildhistory" in inherit else "enable buildhistory (BUILDHISTORY_COMMIT = \"1\") to version image/package changes")
    if state:
        reviews = Path(state) / "security-reviews.json"
        if reviews.exists():
            entries = json.loads(reviews.read_text())
            expired = [k for k, v in entries.items() if v.get("expires", "9999") < today.isoformat()]
            add("WARN" if expired else "OK", "Vulnerability dispositions", f"{len(entries)} recorded in Bitloom, {len(expired)} expired")
        else:
            add("INFO", "Vulnerability dispositions", "none recorded (Developer → Security → Record review)")
        bundles = list((Path(state) / "exports").glob("bundle-*.json")) if (Path(state) / "exports").is_dir() else []
        add("OK" if bundles else "INFO", "Reproducibility evidence", f"{len(bundles)} bundles exported" if bundles else "export a reproducibility bundle per release (Analysis)")
    return rows
