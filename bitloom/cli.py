from __future__ import annotations

import argparse
import sys
import shutil
import subprocess
from pathlib import Path


DEMO_TOOL = "Bitloom demo sample - not produced by a real build"


def cve_sample(tool: str) -> str:
    """Yocto CVE JSON (cve-check / sbom-cve-check) with labelled sample identifiers."""
    import json
    issue = lambda ident, status, score, detail, summary: {"id": ident, "status": status, "scorev3": score, "detail": detail,
                                                           "summary": f"Demo sample ({tool}), not a real vulnerability: {summary}", "link": ""}
    return json.dumps({"version": "1", "note": DEMO_TOOL, "package": [
        {"name": "openssh", "layer": "meta", "version": "9.6p1", "issue": [
            issue("CVE-0000-0001", "Unpatched", "8.1", "version-in-range", "remote pre-authentication issue"),
            issue("CVE-0000-0004", "Patched", "5.3", "fixed-version", "information disclosure")]},
        {"name": "busybox", "layer": "meta", "version": "1.36.1", "issue": [
            issue("CVE-0000-0002", "Unpatched", "9.8", "version-in-range", "buffer overflow in a shell applet"),
            issue("CVE-0000-0003", "Ignored", "4.0", "not-applicable-config", "feature disabled in this configuration")]},
        {"name": "demo-agent", "layer": "meta-demo", "version": "1.0", "issue": [
            issue("CVE-0000-0005", "Unpatched", "5.5", "version-in-range", "local denial of service")]}]}, indent=1)


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
                "build/tmp/log/cve/cve-summary.json": cve_sample("cve-check")}
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
            image + ".sbom-cve-check.yocto.json": cve_sample("sbom-cve-check")}


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
    board = directory / "build/tmp/deploy/images/demo-board/demo-board.dtb"
    if not board.exists():
        from .devicetree import demo_board
        board.parent.mkdir(parents=True, exist_ok=True)
        board.write_bytes(demo_board())
    config = directory / ".bitloom/profiles.json"
    if not config.exists():
        from .models import Profile, Settings
        settings = Settings(config)
        settings.profiles = [Profile(name="demo", root=str(directory.resolve()), targets=["demo-image"])]
        settings.active = "demo"
        settings.save()
    return config


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--run-module":
        # bitloom.pyz runs its own modules this way (python -m cannot see inside the archive).
        import runpy
        module = sys.argv[2]
        if not module.startswith("bitloom."):
            raise SystemExit("bitloom: --run-module only runs Bitloom's own modules")
        sys.argv = [module, *sys.argv[3:]]
        runpy.run_module(module, run_name="__main__", alter_sys=True)
        return
    from . import __version__
    parser = argparse.ArgumentParser(description="Bitloom — Yocto / BitBake development cockpit")
    parser.add_argument("--version", action="store_true", help="Show the version, the author and the licence, and exit")
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
    parser.add_argument("--vulns", action="store_true", help="Print CVE findings (cve-check, sbom-cve-check, Grype) for the active profile")
    parser.add_argument("--min-cvss", type=float, default=0.0, help="With --vulns: only findings at or above this CVSS score")
    parser.add_argument("--fail-on-unpatched", action="store_true", help="With --vulns: exit 2 when an unpatched finding matches")
    parser.add_argument("--format", choices=["text", "md", "html", "csv", "json", "sarif", "dts"], default="text",
                        help="With --vulns: report format (md/html readable reports with NVD/OSV links, csv, json, sarif for GitHub code scanning)")
    parser.add_argument("-o", "--output", type=Path, help="With --vulns or --practices: write the report to this file instead of standard output")
    parser.add_argument("--all-statuses", action="store_true", help="With --vulns: include patched and ignored findings, not only unpatched")
    parser.add_argument("--work-usage", action="store_true", help="Print disk usage per recipe in tmp/work with rm_work advice")
    parser.add_argument("--practices", action="store_true", help="Review the project against Yocto best practices and bitloom-practices.json; exits 2 on errors (or warnings with --fail-on warning)")
    parser.add_argument("--fail-on", choices=["error", "warning", "never"], default="error", help="--practices and --lint: what makes the exit status 2")
    parser.add_argument("--services", nargs="?", const="", metavar="IMAGE[:MACHINE]", help="What starts on the device: init system, systemd units or SysV scripts, udev rules and D-Bus services of a built image (newest when omitted)")
    parser.add_argument("--migrate", action="store_true", help="What changes to move the project to a newer Yocto release (--to), from the official migration guides; exit 2 when something breaks the build")
    parser.add_argument("--to", metavar="SERIES", help="--migrate: the target release (default: the newest Bitloom covers, for example wrynose)")
    parser.add_argument("--apply", action="store_true", help="--migrate: apply the safe fixes (originals kept in the state folder)")
    parser.add_argument("--lint", nargs="+", metavar="FILE", help="Check BitBake files (.bb, .bbappend, .bbclass, .inc, .conf; folders are searched) against the project's layers; exit 2 on errors (with --fail-on warning also on warnings)")
    parser.add_argument("--explain", metavar="WORD", help="What a variable, task, class, keyword, machine or distro means in this project")
    parser.add_argument("--insights", nargs="?", const="", metavar="IMAGE[:MACHINE]", help="Where the space of a built image goes, its licences, what listens and a security look (--format json for CI)")
    parser.add_argument("--devicetree", nargs="?", const="", metavar="NAME.dtb", help="The device trees the build deployed, or one of them decompiled and summarised (--format dts for the DTS text); no dtc needed")
    parser.add_argument("--who-installs", metavar="FILE_OR_PACKAGE", help="Which recipe puts a file (/etc/motd) or package (libc6) in the built images, and how to change it")
    parser.add_argument("--fleet", action="store_true", help="Probe every device in <state>/devices.json; exit 1 unless all are online")
    parser.add_argument("--network", action="store_true", help="With --doctor: also probe mirrors, hash equivalence and PR servers")
    parser.add_argument("--list-actions", action="store_true", help="List all available operations")
    parser.add_argument("--embedded", action="store_true", help="Run jobs in the TUI process; exit stops jobs")
    parser.add_argument("--service-status", action="store_true")
    parser.add_argument("--service-stop", action="store_true", help="Stop an idle build service")
    parser.add_argument("--service-install", action="store_true", help="Run the build service as a systemd user service (with --web also the dashboard, with a stable URL)")
    parser.add_argument("--service-uninstall", action="store_true", help="Stop and remove the systemd user services")
    parser.add_argument("--service-name", default="bitloom", help="Unit name for --service-install/--service-uninstall (default bitloom)")
    parser.add_argument("--keys", action="store_true", help="Show the section keys in use (yours from ~/.config/bitloom/keys.json, and why any were refused)")
    parser.add_argument("--persistent-token", action="store_true", help="--web: keep the dashboard token in the state folder, so the URL survives restarts")
    parser.add_argument("--web", action="store_true", help="Serve the web dashboard (shares the build service with the TUI)")
    parser.add_argument("--host", default="127.0.0.1", help="Web dashboard address (default: loopback only)")
    parser.add_argument("--port", type=int, default=8765, help="Web dashboard port (0 picks a free one)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser for --web")
    args = parser.parse_args()
    if args.version:
        print(f"bitloom {__version__}\nBitloom, originally created by Luca Padovan (https://github.com/padovanl/bitloom)\n"
              "AGPL-3.0-or-later: free software, see LICENSE and NOTICE")
        return 0
    from .models import ConfigError
    try:
        _commands(parser, args)
    except ConfigError as exc:
        parser.exit(2, f"bitloom: {exc}\n")


def _commands(parser, args) -> None:
    if args.keys:
        from .keys import OVERRIDE_ERRORS, SECTION_TITLES, effective_table, keys_file
        print(f"Section keys · yours in {keys_file()}" + ("" if keys_file().is_file() else " (none yet)"))
        for section, label, key, default in effective_table():
            print(f"  {SECTION_TITLES.get(section, section):<14} {label:<22} {key:<8} {'(default ' + default + ')' if key != default else ''}")
        for error in OVERRIDE_ERRORS:
            print("✖ " + error)
        raise SystemExit(1 if OVERRIDE_ERRORS else 0)
    if args.service_install or args.service_uninstall:
        from . import userservice
        try:
            lines = userservice.uninstall(args.service_name) if args.service_uninstall else \
                userservice.install(Path(args.state).resolve(), Path(args.config).resolve(), args.service_name, args.web, args.host, args.port)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            parser.exit(1, f"bitloom: {exc}\n")
        print("\n".join(lines))
        return
    if args.service_status:
        from . import userservice
        if shutil.which("systemctl") and (userservice.unit_dir() / f"{args.service_name}.service").exists():
            print("\n".join(userservice.status(args.service_name)))
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
    if args.practices:
        from .models import Settings
        from .practices import report, review
        profile = Settings(args.config).profile
        data = review(profile)
        text = report(data, args.format if args.format in {"md", "json", "text"} else "text")
        if args.output:
            Path(args.output).write_text(text + "\n")
            print(f"Wrote {args.output}")
        else:
            print(text)
        failing = data["errors"] + (data["warnings"] if args.fail_on == "warning" else 0)
        raise SystemExit(2 if args.fail_on != "never" and failing else 0)
    if args.migrate:
        from .inspectors import metadata
        from .migration import apply, report, scan, targets_for
        from .models import Settings
        from .studio import product_layers
        from .versions import detect_release
        profile = Settings(args.config).profile
        entries = metadata(profile)
        source = detect_release(profile, entries)
        options = targets_for(source)
        target = args.to or (options[-1] if options else "")
        if not target:
            parser.exit(1, f"bitloom: no newer release to migrate {source or 'this project'} to\n")
        try:
            data = scan(profile, target, entries, source)
        except ValueError as exc:
            parser.exit(1, f"bitloom: {exc}\n")
        if args.apply:
            fixes = [fix for finding in data["findings"] for fix in finding["fixes"]]
            roots = [profile.root_path, *product_layers(entries, profile)]
            result = apply(profile, args.state, fixes, roots)
            print(f"{len(fixes)} fixes applied to {len(result['written'])} files; originals in {result['backup'] or 'nothing to change'}")
            data = scan(profile, target, entries, source)
        print(report(data, args.format if args.format in {"md", "json", "text"} else "text"))
        raise SystemExit(2 if data["counts"]["breaks"] else 0)
    if args.lint or args.explain:
        import json
        from .inspectors import metadata
        from .language import BITBAKE_SUFFIXES, explain, lint, vocabulary
        from .models import Settings
        profile = Settings(args.config).profile
        vocab = vocabulary(profile, metadata(profile))
        if args.explain:
            data = explain(vocab, args.explain)
            print(json.dumps(data, indent=2) if args.format == "json" else
                  f"{data['word']} · {data['kind']}\n{data['doc']}" if data["doc"] else
                  f"{data['word']}: not known in this project" + (f"; did you mean {', '.join(data['suggest'])}?" if data.get("suggest") else ""))
            raise SystemExit(0 if data["doc"] else 1)
        files = []
        for item in args.lint:
            path = Path(item)
            files += sorted(p for p in path.rglob("*") if p.suffix in BITBAKE_SUFFIXES and p.is_file()) if path.is_dir() else [path]
        results, counts = [], {"error": 0, "warning": 0, "info": 0}
        for path in files:
            try:
                problems = lint(vocab, path.read_text(errors="replace"), str(path))
            except OSError as exc:
                problems = [{"line": 0, "level": "error", "message": str(exc), "fix": ""}]
            for problem in problems:
                counts[problem["level"]] += 1
                results.append({"file": str(path), **problem})
        if args.format == "json":
            print(json.dumps({"files": len(files), **counts, "problems": results}, indent=2))
        else:
            mark = {"error": "✖", "warning": "▲", "info": "●"}
            for r in results:
                print(f"{r['file']}:{r['line']}: {mark[r['level']]} {r['message']}" + (f"\n    → {r['fix']}" if r["fix"] else ""))
            print(f"{len(files)} files · {counts['error']} errors · {counts['warning']} warnings · {counts['info']} notes")
        failing = counts["error"] + (counts["warning"] if args.fail_on == "warning" else 0)
        raise SystemExit(2 if args.fail_on != "never" and failing else 0)
    if args.insights is not None:
        import json
        from . import rootfs
        from .image_insights import insights, report
        from .inspectors import metadata
        from .models import Settings
        profile = Settings(args.config).profile
        built = rootfs.built_images(profile)
        image = next((i for i in built if args.insights in ("", i["image"], f"{i['image']}:{i['machine']}")), None)
        if image is None:
            print("No built image" + (f" called {args.insights}" if args.insights else "") + ". Built: " + (", ".join(f"{i['image']}:{i['machine']}" for i in built) or "none"))
            raise SystemExit(1)
        data = insights(profile, image["image"], image["machine"], metadata(profile))
        print(json.dumps(data, indent=2) if args.format == "json" else report(data))
        return
    if args.devicetree is not None:
        import json
        from . import devicetree
        from .models import Settings
        profile = Settings(args.config).profile
        if not args.devicetree:
            rows = devicetree.find(profile)
            print("\n".join(f"{r['machine']:<20} {r['name']:<40} {'overlay' if r['overlay'] else 'base'}" for r in rows)
                  or "No device tree deployed: this machine has none (x86 and most QEMU machines), or nothing is built yet.")
            return
        name, _, machine = args.devicetree.partition(":")
        try:
            data = devicetree.load(profile, name, machine)
        except (LookupError, ValueError) as exc:
            print(exc)
            raise SystemExit(1)
        print(data["dts"] if args.format == "dts" else json.dumps({k: v for k, v in data.items() if k != "dts"}, indent=2) if args.format == "json" else devicetree.report(data))
        return
    if args.services is not None:
        from . import rootfs
        from .models import Settings
        profile = Settings(args.config).profile
        built = rootfs.built_images(profile)
        image = next((i for i in built if args.services in ("", i["image"], f"{i['image']}:{i['machine']}")), None)
        if image is None:
            print("No built image to inspect" + (f" called {args.services}" if args.services else "") + ". Built: " + (", ".join(f"{i['image']}:{i['machine']}" for i in built) or "none"))
            raise SystemExit(1)
        print(rootfs.services_report(rootfs.services(profile, image["image"], image["machine"])))
        return
    if args.who_installs:
        from .inspectors import metadata
        from .models import Settings
        from .whois import lookup, report
        profile = Settings(args.config).profile
        print(report(lookup(profile, args.who_installs, metadata(profile))))
        return
    if args.work_usage:
        from .insights import work_report
        from .models import Settings
        print(work_report(Settings(args.config).profile))
        return
    if args.vulns:
        from .models import Settings
        from .vulns import load, report, select
        profile = Settings(args.config).profile
        findings, errors = load(profile, args.state)
        if args.format == "text":
            text = report(findings, errors, "all" if args.all_statuses else "unpatched", args.min_cvss)
        else:
            from .vulnexport import build
            text, _ = build(profile, args.state, args.format, "all" if args.all_statuses else "unpatched", args.min_cvss)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text if text.endswith("\n") else text + "\n")
            print(f"Wrote {args.output} ({args.format})", file=sys.stderr)
        else:
            print(text)
        raise SystemExit(2 if args.fail_on_unpatched and select(findings, "unpatched", args.min_cvss) else 0)
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
            serve(args.config, args.state, args.host, args.port, open_browser=not args.no_browser, persistent=args.persistent_token)
        except (OSError, ValueError, TypeError) as exc:
            parser.exit(1, f"bitloom: {exc}\n")
        return
    from .app import BitloomApp
    try:
        app = BitloomApp(args.config, args.state, persistent=not (args.embedded or args.demo))
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"bitloom: {exc}\n")
    app.run()
