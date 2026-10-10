from __future__ import annotations

import argparse
from pathlib import Path


def make_demo(directory: Path):
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
        args.config = make_demo(args.state / "demo")
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
