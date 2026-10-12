"""Shareable exports of CVE findings: Markdown, HTML, CSV, JSON and SARIF.

Every format carries the links a reviewer needs (NVD, CVE.org, OSV, GitHub advisories),
the sources and filters used, and Yocto remediation guidance."""
from __future__ import annotations

import csv
import html
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from . import __version__
from .vulns import Finding, counts

FORMATS = {
    "md": ("Markdown report", "text/markdown"),
    "html": ("HTML report (printable)", "text/html"),
    "csv": ("CSV spreadsheet", "text/csv"),
    "json": ("JSON for scripts", "application/json"),
    "sarif": ("SARIF 2.1.0 (GitHub code scanning)", "application/sarif+json"),
}
SEVERITIES = ("critical", "high", "medium", "low", "none", "unknown")
STATUSES = ("Unpatched", "Patched", "Ignored")
REMEDIATION = [
    "Upgrade the recipe to a release that fixes the CVE (devtool upgrade, or a newer layer revision).",
    "Backport the fix as a patch whose header carries `CVE: CVE-YYYY-NNNN`; cve-check and sbom-cve-check then report it as Patched.",
    "Correct wrong matches with `CVE_PRODUCT` / `CVE_VERSION` in the recipe.",
    'Record an assessment upstream with `CVE_STATUS[CVE-YYYY-NNNN] = "not-applicable-config: reason"`.',
    "Record an internal review (owner, reason, expiry) in Bitloom: Artifacts → v → r. A review never marks the CVE fixed.",
]


@dataclass
class Meta:
    profile: str = ""
    release: str = ""
    sources: list = field(default_factory=list)
    filters: str = ""
    errors: list = field(default_factory=list)
    generated: str = field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat())


def links(identifier: str, link: str = "") -> list[tuple[str, str]]:
    """Reference links for an identifier, most useful first."""
    out = []
    if identifier.startswith("CVE-"):
        out = [("NVD", f"https://nvd.nist.gov/vuln/detail/{identifier}"), ("CVE.org", f"https://www.cve.org/CVERecord?id={identifier}"),
               ("OSV", f"https://osv.dev/vulnerability/{identifier}")]
    elif identifier.startswith("GHSA-"):
        out = [("GitHub", f"https://github.com/advisories/{identifier}"), ("OSV", f"https://osv.dev/vulnerability/{identifier}")]
    elif identifier:
        out = [("OSV", f"https://osv.dev/vulnerability/{identifier}")]
    # Only web links from the report: a javascript: or file: URL must never become a clickable link.
    if link and link.startswith(("https://", "http://")) and link not in {url for _, url in out}:
        out.append(("source", link))
    return out


def _order(finding: Finding):
    return (STATUSES.index(finding.status) if finding.status in STATUSES else 9, -(finding.score or 0), finding.package, finding.id)


def _cell(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def _score(finding: Finding) -> str:
    return f"{finding.score:.1f}" if finding.score else "—"


def _summary_rows(all_findings: list[Finding]):
    table = {s: {st: 0 for st in STATUSES} for s in SEVERITIES}
    for finding in all_findings:
        if finding.status in STATUSES:
            table.setdefault(finding.severity, {st: 0 for st in STATUSES})[finding.status] += 1
    return [(severity, row) for severity, row in table.items() if any(row.values())]


def to_markdown(findings: list[Finding], all_findings: list[Finding], meta: Meta) -> str:
    c = counts(all_findings)
    unpatched = sorted((f for f in findings if f.status == "Unpatched"), key=_order)
    others = sorted((f for f in findings if f.status != "Unpatched"), key=_order)
    out = [f"# Vulnerability report — {meta.profile or 'Bitloom'}", "",
           f"Generated {meta.generated} by Bitloom {__version__}" + (f" · Yocto {meta.release}" if meta.release else "") + ".", ""]
    if meta.sources:
        out += ["**Sources**", "", *(f"- {source}" for source in meta.sources), ""]
    if meta.filters:
        out += [f"**Filters**: {meta.filters}", ""]
    out += ["> Engineering evidence from the build's CVE tools, not a legal or conformity assessment. "
            "*Unpatched* means the tool found no fix in the recipe; review each finding before acting.", "",
            "## Summary", "",
            f"{c['total']} assessed · **{c['unpatched']} unpatched** · {c['patched']} patched · {c['ignored']} ignored · {c['reviewed']} reviewed in Bitloom.", "",
            "| Severity | Unpatched | Patched | Ignored |", "| --- | ---: | ---: | ---: |"]
    out += [f"| {severity} | {row['Unpatched']} | {row['Patched']} | {row['Ignored']} |" for severity, row in _summary_rows(all_findings)]
    out += ["", f"## Unpatched ({len(unpatched)})", ""]
    if unpatched:
        out += ["| Severity | CVSS | ID | Package | Version | Detail | Review | Links |", "| --- | ---: | --- | --- | --- | --- | --- | --- |"]
        for f in unpatched:
            refs = " · ".join(f"[{name}]({url})" for name, url in links(f.id, f.link))
            out.append(f"| {f.severity} | {_score(f)} | **{_cell(f.id)}** | {_cell(f.package)} | {_cell(f.version)} | {_cell(f.detail)} | {_cell(f.review) or '—'} | {refs} |")
        out += ["", "### By package", ""]
        packages: dict[str, list[Finding]] = {}
        for f in unpatched:
            packages.setdefault(f"{f.package} {f.version}".strip(), []).append(f)
        for package, items in sorted(packages.items(), key=lambda kv: (-max((f.score or 0) for f in kv[1]), kv[0])):
            worst = max(items, key=lambda f: f.score or 0)
            out += [f"#### {package} — {len(items)} unpatched, worst {worst.severity} {_score(worst)}", ""]
            for f in items:
                first = links(f.id, f.link)[0][1] if links(f.id, f.link) else ""
                text = f" — {_cell(f.summary)[:300]}" if f.summary else ""
                out.append(f"- [{f.id}]({first}) · {f.severity} {_score(f)} · {_cell(f.detail) or 'no detail'}{text}")
            out.append("")
    else:
        out += ["No unpatched findings with these filters.", ""]
    if others:
        out += [f"## Patched and ignored ({len(others)})", "", "<details><summary>Show the list</summary>", "",
                "| Status | ID | Package | Version | Detail |", "| --- | --- | --- | --- | --- |"]
        out += [f"| {f.status} | [{_cell(f.id)}]({links(f.id, f.link)[0][1] if links(f.id, f.link) else ''}) | {_cell(f.package)} | {_cell(f.version)} | {_cell(f.detail)} |"
                for f in others]
        out += ["", "</details>", ""]
    out += ["## How to act in Yocto", "", *(f"{i}. {step}" for i, step in enumerate(REMEDIATION, 1)), ""]
    if meta.errors:
        out += ["## Problems reading reports", "", *(f"- {_cell(e)}" for e in meta.errors), ""]
    return "\n".join(out)


def to_html(findings: list[Finding], all_findings: list[Finding], meta: Meta) -> str:
    """Self-contained page with the same content as the Markdown report; prints well to PDF."""
    e = html.escape
    c = counts(all_findings)
    unpatched = sorted((f for f in findings if f.status == "Unpatched"), key=_order)
    others = sorted((f for f in findings if f.status != "Unpatched"), key=_order)

    def refs(f):
        return " ".join(f'<a href="{e(url)}">{e(name)}</a>' for name, url in links(f.id, f.link))
    rows = "".join(f'<tr><td><span class="sev {e(f.severity)}">{e(f.severity)}</span></td><td class="num">{_score(f)}</td><td><b>{e(f.id)}</b></td>'
                   f"<td>{e(f.package)}</td><td>{e(f.version)}</td><td>{e(f.detail)}</td><td>{e(f.review) or '—'}</td><td class='refs'>{refs(f)}</td></tr>"
                   for f in unpatched) or '<tr><td colspan="8">No unpatched findings with these filters.</td></tr>'
    summary = "".join(f'<tr><td><span class="sev {e(s)}">{e(s)}</span></td><td class="num">{r["Unpatched"]}</td><td class="num">{r["Patched"]}</td><td class="num">{r["Ignored"]}</td></tr>'
                      for s, r in _summary_rows(all_findings))
    def first(f):
        found = links(f.id, f.link)
        return f'<a href="{e(found[0][1])}">{e(f.id)}</a>' if found else e(f.id)
    rest = "".join(f"<tr><td>{e(f.status)}</td><td>{first(f)}</td><td>{e(f.package)}</td><td>{e(f.version)}</td><td>{e(f.detail)}</td></tr>"
                   for f in others)
    sources = "".join(f"<li>{e(s)}</li>" for s in meta.sources)
    steps = "".join(f"<li>{e(step).replace('`', '')}</li>" for step in REMEDIATION)
    problems = "".join(f"<li>{e(p)}</li>" for p in meta.errors)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vulnerability report — {e(meta.profile)}</title>
<style>
:root {{ color-scheme: light dark; --fg:#1c2430; --muted:#5b6878; --line:#e3e8ee; --bg:#fff; --soft:#f6f8fa; --link:#0b6bcb; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fg:#e6edf3; --muted:#9aa7b6; --line:#2a3542; --bg:#0d1117; --soft:#151c25; --link:#6cb6ff; }} }}
body {{ font: 15px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--fg); background: var(--bg); max-width: 1100px; margin: 32px auto; padding: 0 20px; }}
h1 {{ font-size: 28px; margin: 0 0 6px; }} h2 {{ margin-top: 36px; border-top: 1px solid var(--line); padding-top: 18px; font-size: 20px; }}
.meta, .note {{ color: var(--muted); }} .note {{ border-left: 4px solid #0f7d6e; background: var(--soft); padding: 10px 14px; border-radius: 0 8px 8px 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; margin: 12px 0; }} th, td {{ border: 1px solid var(--line); padding: 6px 9px; text-align: left; vertical-align: top; }}
th {{ background: var(--soft); }} .num {{ text-align: right; font-variant-numeric: tabular-nums; }} a {{ color: var(--link); }} .refs a {{ margin-right: 6px; }}
.sev {{ display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; border: 1px solid currentColor; }}
.critical {{ color: #c62828; }} .high {{ color: #d84315; }} .medium {{ color: #a66a00; }} .low {{ color: #2e6fbf; }} .none, .unknown {{ color: var(--muted); }}
@media print {{ body {{ margin: 0; max-width: none; }} a {{ color: inherit; }} details {{ display: block; }} }}
</style></head><body>
<h1>Vulnerability report — {e(meta.profile)}</h1>
<p class="meta">Generated {e(meta.generated)} by Bitloom {e(__version__)}{(" · Yocto " + e(meta.release)) if meta.release else ""}{(" · Filters: " + e(meta.filters)) if meta.filters else ""}</p>
{f"<p><b>Sources</b></p><ul>{sources}</ul>" if sources else ""}
<p class="note">Engineering evidence from the build's CVE tools, not a legal or conformity assessment. <i>Unpatched</i> means the tool found no fix in the recipe; review each finding before acting.</p>
<h2>Summary</h2><p>{c['total']} assessed · <b>{c['unpatched']} unpatched</b> · {c['patched']} patched · {c['ignored']} ignored · {c['reviewed']} reviewed in Bitloom.</p>
<table style="width:auto;min-width:420px"><tr><th>Severity</th><th>Unpatched</th><th>Patched</th><th>Ignored</th></tr>{summary}</table>
<h2>Unpatched ({len(unpatched)})</h2>
<table><tr><th>Severity</th><th>CVSS</th><th>ID</th><th>Package</th><th>Version</th><th>Detail</th><th>Review</th><th>Links</th></tr>{rows}</table>
{f"<h2>Patched and ignored ({len(others)})</h2><details><summary>Show the list</summary><table><tr><th>Status</th><th>ID</th><th>Package</th><th>Version</th><th>Detail</th></tr>{rest}</table></details>" if others else ""}
<h2>How to act in Yocto</h2><ol>{steps}</ol>
{f"<h2>Problems reading reports</h2><ul>{problems}</ul>" if problems else ""}
</body></html>
'''


def to_csv(findings: list[Finding]) -> str:
    stream = io.StringIO()
    names = list(Finding.__dataclass_fields__) + ["nvd", "osv"]
    writer = csv.DictWriter(stream, fieldnames=names)
    writer.writeheader()
    for f in sorted(findings, key=_order):
        refs = dict(links(f.id, f.link))
        writer.writerow({**asdict(f), "nvd": refs.get("NVD", refs.get("GitHub", "")), "osv": refs.get("OSV", "")})
    return stream.getvalue()


def to_json(findings: list[Finding], all_findings: list[Finding], meta: Meta) -> str:
    return json.dumps({"generator": f"Bitloom {__version__}", **asdict(meta), "counts": counts(all_findings),
                       "findings": [{**asdict(f), "links": dict(links(f.id, f.link))} for f in sorted(findings, key=_order)]}, indent=2)


def to_sarif(findings: list[Finding], meta: Meta) -> str:
    """SARIF 2.1.0: GitHub code scanning shows one alert per unpatched finding, ranked by
    security-severity (the CVSS score). Patched and ignored findings are left out."""
    level = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}
    rules, results = {}, []
    for f in sorted(findings, key=_order):
        if f.status != "Unpatched":
            continue
        refs = links(f.id, f.link)
        rules.setdefault(f.id, {
            "id": f.id, "name": f.id.replace("-", ""),
            "shortDescription": {"text": f"{f.id} in {f.package}"},
            "fullDescription": {"text": (f.summary or f.id)[:1000]},
            "helpUri": refs[0][1] if refs else "",
            "help": {"text": "\n".join(REMEDIATION).replace("`", ""), "markdown": "\n".join(f"{i}. {s}" for i, s in enumerate(REMEDIATION, 1))},
            "properties": {"security-severity": f"{f.score:.1f}" if f.score else "0.0", "tags": ["security", "vulnerability", f.severity],
                           "precision": "high" if f.detail == "version-in-range" else "medium"}})
        results.append({
            "ruleId": f.id, "level": level.get(f.severity, "note"),
            "message": {"text": f"{f.package} {f.version}: {f.id} ({f.severity} {_score(f)}, {f.detail or 'unpatched'}) reported by {f.source}"},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": f"yocto/{f.package}"}, "region": {"startLine": 1}},
                           "logicalLocations": [{"name": f"{f.package} {f.version}", "kind": "package"}]}],
            "partialFingerprints": {"bitloom/v1": f"{f.package}/{f.id}"},
            "properties": {"package": f.package, "version": f.version, "source": f.source, "review": f.review}})
    return json.dumps({"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0", "runs": [{
        "tool": {"driver": {"name": "Bitloom", "version": __version__, "informationUri": "https://github.com/padovanl/bitloom",
                            "rules": list(rules.values())}},
        "automationDetails": {"id": f"bitloom/{meta.profile}/"},
        "results": results}]}, indent=2)


def export(fmt: str, findings: list[Finding], all_findings: list[Finding], meta: Meta) -> str:
    if fmt == "md":
        return to_markdown(findings, all_findings, meta)
    if fmt == "html":
        return to_html(findings, all_findings, meta)
    if fmt == "csv":
        return to_csv(findings)
    if fmt == "json":
        return to_json(findings, all_findings, meta)
    if fmt == "sarif":
        return to_sarif(findings, meta)
    raise ValueError(f"Unknown format {fmt!r}: use " + ", ".join(FORMATS))


def build(profile, state, fmt: str, status="unpatched", min_score=0.0, text="", source="") -> tuple[str, str]:
    """(content, file name) for the active filters, shared by the TUI, the web dashboard and the CLI."""
    from .versions import describe, detect_release
    from .vulns import load, select, sources
    all_findings, errors = load(profile, state, source)
    shown = select(all_findings, status, min_score, text)
    filters = [f"status {status}"] + ([f"CVSS ≥ {min_score:g}"] if min_score else []) + ([f"text “{text}”"] if text else []) + ([f"source {source}"] if source else [])
    meta = Meta(profile=profile.name, release=describe(detect_release(profile)), sources=[label for label, _ in sources(profile, state)],
                filters=" · ".join(filters), errors=errors)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    extension = {"sarif": "sarif"}.get(fmt, fmt)
    return export(fmt, shown, all_findings, meta), f"vulnerabilities-{profile.name}-{stamp}.{extension}"
