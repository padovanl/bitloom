from __future__ import annotations

import argparse
from pathlib import Path


DEMO_TOOL = "Bitloom demo sample - not produced by a real build"


def release_samples(release: str) -> dict[str, str]:
    """Release-specific sample files: core layer series, SBOM format and CVE evidence."""
    import json
    image = "build/tmp/deploy/images/qemux86-64/demo-image-qemux86-64.rootfs"
    if release == "scarthgap":
        sbom = {"spdxVersion": "SPDX-2.2", "name": "demo-image (demo sample)", "creationInfo": {"created": "2026-01-01T00:00:00Z", "creators": ["Tool: " + DEMO_TOOL]},
                "packages": [{"name": "busybox", "versionInfo": "1.36.1", "licenseConcluded": "GPL-2.0-only", "supplier": "Organization: Demo Corp",
                              "externalRefs": [{"referenceCategory": "SECURITY", "referenceType": "cpe23Type", "referenceLocator": "cpe:2.3:a:busybox:busybox:1.36.1:*:*:*:*:*:*:*"}]},
                             {"name": "openssh", "versionInfo": "9.6p1", "licenseConcluded": "BSD-2-Clause",
                              "externalRefs": [{"referenceCategory": "SECURITY", "referenceType": "cpe23Type", "referenceLocator": "cpe:2.3:a:openbsd:openssh:9.6p1:*:*:*:*:*:*:*"}]},
                             {"name": "demo-agent", "versionInfo": "1.0", "licenseConcluded": "NOASSERTION"}]}
        return {"poky/meta/conf/layer.conf": 'BBFILE_COLLECTIONS += "core"\nLAYERSERIES_CORENAMES = "scarthgap"\n',
                image + ".spdx.json": json.dumps(sbom, indent=1),
                "build/tmp/log/cve/cve-summary.json": json.dumps({"note": DEMO_TOOL, "package": [{"name": "openssh", "issue": [{"id": "CVE-0000-0001", "status": "Unpatched"}]}]}, indent=1)}
    graph = [{"type": "CreationInfo", "@id": "_:c", "created": "2026-06-01T00:00:00Z", "createdUsing": ["tool"]},
             {"type": "Tool", "spdxId": "tool", "name": DEMO_TOOL}]
    for index, (name, version, purl, supplier) in enumerate([("busybox", "1.37.0", True, True), ("openssh", "10.0p1", True, True), ("demo-agent", "1.0", False, False)]):
        package = {"type": "software_Package", "spdxId": f"p{index}", "name": name, "software_packageVersion": version}
        if purl:
            package["externalIdentifier"] = [{"type": "ExternalIdentifier", "externalIdentifierType": "packageUrl", "identifier": f"pkg:yocto/{name}@{version}"}]
        if supplier:
            package["suppliedBy"] = "demo-corp"
        graph.append(package)
    graph += [{"type": "simplelicensing_LicenseExpression", "spdxId": "l0", "simplelicensing_licenseExpression": "GPL-2.0-only"},
              {"type": "Relationship", "spdxId": "r0", "relationshipType": "hasConcludedLicense", "from": "p0", "to": ["l0"]},
              {"type": "Relationship", "spdxId": "r1", "relationshipType": "hasConcludedLicense", "from": "p1", "to": ["l0"]}]
    for index, (cve, kind, package) in enumerate([("CVE-0000-0001", "Affected", "p1"), ("CVE-0000-0002", "Fixed", "p0"), ("CVE-0000-0003", "NotAffected", "p0")]):
        graph += [{"type": "security_Vulnerability", "spdxId": f"v{index}", "externalIdentifier": [{"externalIdentifierType": "cve", "identifier": cve}]},
                  {"type": f"security_Vex{kind}VulnAssessmentRelationship", "spdxId": f"x{index}", "from": f"v{index}", "to": [package]}]
    return {"layers/openembedded-core/meta/conf/layer.conf": 'BBFILE_COLLECTIONS += "core"\nLAYERSERIES_CORENAMES = "wrynose"\n',
            image + ".spdx.json": json.dumps({"@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld", "@graph": graph}, indent=1),
            image + ".sbom-cve-check.yocto.json": json.dumps({"note": DEMO_TOOL, "affected": ["CVE-0000-0001"]}, indent=1)}


def prepare_demo(state: Path) -> Path:
    """Generic demo plus Scarthgap and Wrynose sample workspaces as extra profiles."""
    from .models import Profile, Settings
    config = make_demo(state / "demo")
    settings = Settings(config)
    names = {p.name for p in settings.profiles}
    for release in ("scarthgap", "wrynose"):
        root = make_demo(state / f"demo-{release}", release=release).parents[1]
        if f"demo-{release}" not in names:
            settings.profiles.append(Profile(name=f"demo-{release}", root=str(root.resolve()), targets=["demo-image"]))
    settings.save()
    return config


def make_demo(directory: Path, release: str | None = None):
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "meta-demo/conf/layer.conf": 'BBFILE_COLLECTIONS += "demo"\nBBFILE_PRIORITY_demo = "6"\nLAYERSERIES_COMPAT_demo = "scarthgap"\n',
        "meta-demo/recipes-core/images/demo-image.bb": 'SUMMARY = "Demo gateway image"\nLICENSE = "MIT"\ninherit core-image\nIMAGE_INSTALL:append = " openssh demo-agent"\n',
        "meta-demo/recipes-apps/demo-agent/demo-agent_1.0.bb": 'SUMMARY = "Device telemetry agent"\nLICENSE = "MIT"\nSRC_URI = "file://agent.c"\n',
        "build/conf/local.conf": 'MACHINE = "qemux86-64"\nDISTRO = "poky"\nBB_NUMBER_THREADS = "8"\nPARALLEL_MAKE = "-j8"\nINHERIT += "buildhistory buildstats"\n',
        "build/conf/bblayers.conf": 'BBLAYERS = "${TOPDIR}/../meta-demo"\n',
        "build/tmp/work/core2-64-poky-linux/demo-agent/1.0-r0/temp/log.do_compile.1234": 'NOTE: Starting compile\nagent.c:12: error: unknown type name telemetry_t\nERROR: oe_runmake failed\nERROR: Task demo-agent:do_compile failed with exit code 1\n',
        # Sample of BitBake's console log (BB_CONSOLELOG) for a build started outside Bitloom.
        "build/tmp/log/cooker/qemux86-64/20260101120000.log": 'NOTE: Demo sample console log, not an actual build\nNOTE: Running task 1 of 2 (/demo/meta-demo/recipes-apps/demo-agent/demo-agent_1.0.bb:do_compile)\nNOTE: recipe demo-agent-1.0-r0: task do_compile: Started\nERROR: demo-agent-1.0-r0 do_compile: oe_runmake failed\nERROR: Logfile of failure stored in: /demo/build/tmp/work/core2-64-poky-linux/demo-agent/1.0-r0/temp/log.do_compile.1234\nNOTE: recipe demo-agent-1.0-r0: task do_compile: Failed\nNOTE: Tasks Summary: Attempted 2 tasks of which 0 didn\'t need to be rerun and 1 failed.\n\nSummary: 1 task failed:\n  /demo/meta-demo/recipes-apps/demo-agent/demo-agent_1.0.bb:do_compile\n',
        "build/tmp/deploy/images/qemux86-64/demo-image.manifest": 'busybox 1.36.1\nopenssh 9.6p1\ndemo-agent 1.0\n',
        "build/downloads/example-source.tar.gz.done": 'Demo marker, not an actual download\n',
        "build/sstate-cache/ab/example.siginfo": 'Demo signature, not reusable sstate\n',
        "kas.yml": 'header:\n  version: 14\nmachine: qemux86-64\ndistro: poky\ntarget: demo-image\n',
    }
    if release:
        files.update(release_samples(release))
    for name, content in files.items():
        p = directory / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(content)
    config = directory / ".bitloom/profiles.json"
    if not config.exists():
        from .models import Profile, Settings
        settings = Settings(config)
        settings.profiles = [Profile(name="demo", root=str(directory.resolve()), targets=["demo-image"])]
        settings.active = "demo"
        settings.save()
    return config


def main():
    parser = argparse.ArgumentParser(description="Bitloom — Yocto / BitBake development cockpit")
    parser.add_argument("--config", type=Path, default=Path(".bitloom/profiles.json"))
    parser.add_argument("--state", type=Path, default=Path(".bitloom"))
    parser.add_argument("--demo", action="store_true", help="Create an isolated sample workspace; no fake build execution")
    parser.add_argument("--doctor", action="store_true", help="Print host setup and profile diagnostics without opening the TUI")
    ci = parser.add_argument_group("CI/CD (headless, serial)")
    ci.add_argument("--ci", action="append", metavar="ACTION[:TARGET]", help="Run an operation without the TUI; repeat for several (e.g. --ci kas-build --ci build:core-image-minimal)")
    ci.add_argument("--profile", action="append", metavar="NAME", help="Profile for --ci; repeat for a profile matrix (default: active profile)")
    ci.add_argument("--junit", metavar="FILE", help="Write a JUnit XML report")
    ci.add_argument("--summary", metavar="FILE", help="Write a JSON summary (status, sstate reuse, warnings, failed tasks, images)")
    ci.add_argument("--annotations", choices=["auto", "github", "gitlab", "plain"], default="auto", help="Log sections and error annotations")
    ci.add_argument("--fail-fast", action="store_true", help="Stop the matrix at the first failure")
    parser.add_argument("--sbom", action="store_true", help="Print SBOM quality (SPDX 3/2.2: identifiers, licences, suppliers, VEX)")
    parser.add_argument("--cra", action="store_true", help="Print CRA readiness evidence; exit 2 when a check warns")
    parser.add_argument("--fleet", action="store_true", help="Probe every device in <state>/devices.json; exit 1 unless all are online")
    parser.add_argument("--network", action="store_true", help="With --doctor: also probe mirrors, hash equivalence and PR servers")
    parser.add_argument("--list-actions", action="store_true", help="List all available operations")
    parser.add_argument("--embedded", action="store_true", help="Run jobs in the TUI process; exit stops jobs")
    parser.add_argument("--service-status", action="store_true")
    parser.add_argument("--service-stop", action="store_true", help="Stop an idle build service")
    parser.add_argument("--web", action="store_true", help="Serve the web dashboard (shares the build service with the TUI)")
    parser.add_argument("--host", default="127.0.0.1", help="Web dashboard address (default: loopback only)")
    parser.add_argument("--port", type=int, default=8765, help="Web dashboard port (0 picks a free one)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser for --web")
    args = parser.parse_args()
    if args.service_status or args.service_stop:
        from .daemon import rpc
        import json
        try:
            print(json.dumps(rpc(args.state, {"op": "stop" if args.service_stop else "status"}), indent=2))
        except (OSError, ValueError) as exc:
            parser.exit(1, f"bitloom: build service unavailable for {args.state}: {exc}\n")
        return
    if args.ci:
        from .ci import main as ci_main
        raise SystemExit(ci_main(args))
    if args.fleet:
        from .fleet import main as fleet
        raise SystemExit(fleet(args.state))
    if args.list_actions:
        from .commands import ACTIONS
        for a in ACTIONS:
            print(f"{a.id:20} {a.group:12} {a.title}")
        return
    if args.demo:
        args.config = prepare_demo(args.state)
    if args.sbom or args.cra:
        from .models import Settings
        from .sbom import cra_report, sbom_report
        profile = Settings(args.config).profile
        text = sbom_report(profile) if args.sbom else ""
        if args.cra:
            text = (text + "\n\n" if text else "") + cra_report(profile, args.state)
        print(text)
        raise SystemExit(2 if args.cra and "\nWARN " in "\n" + text else 0)
    if args.doctor:
        from .models import Settings
        from .inspectors import diagnostics
        profile = Settings(args.config).profile
        rows = diagnostics(profile)
        for status, name, detail in rows:
            print(f"{status:5} {name:24} {detail}")
        if args.network:
            from .infra import network_report
            print()
            print(network_report(profile))
        if any(status == "WARN" for status, _, _ in rows):
            parser.exit(2)
        return
    if args.web:
        from .web import serve
        try:
            serve(args.config, args.state, args.host, args.port, open_browser=not args.no_browser)
        except (OSError, ValueError, TypeError) as exc:
            parser.exit(1, f"bitloom: {exc}\n")
        return
    from .app import BitloomApp
    try:
        app = BitloomApp(args.config, args.state, persistent=not (args.embedded or args.demo))
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"bitloom: {exc}\n")
    app.run()
