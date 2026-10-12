<p align="center"><img src="docs/assets/bitloom-icon.svg" width="120" height="120" alt="Bitloom woven B icon"></p>

# Bitloom

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/padovanl/bitloom)](https://github.com/padovanl/bitloom/releases/latest)
[![CI and tests](https://github.com/padovanl/bitloom/actions/workflows/tests.yml/badge.svg)](https://github.com/padovanl/bitloom/actions/workflows/tests.yml)
[![Release CI](https://github.com/padovanl/bitloom/actions/workflows/release.yml/badge.svg)](https://github.com/padovanl/bitloom/actions/workflows/release.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)

**A terminal cockpit and web dashboard for everyday Yocto and BitBake development.** Build images, inspect recipes, develop with devtool, follow failures, create your own distribution, check SBOMs for the Cyber Resilience Act and manage caches, from a keyboard-first terminal UI or a browser, sharing one build service.

*Weaving layers, recipes and builds into one terminal workspace.*

Python 3.10+ · Textual · Linux / WSL2 · Host · Docker · Podman · kas · kas-container

![Bitloom idle demo workspace](docs/assets/welcome.png)

## Highlights

* **Builds that survive the terminal**: a local build service with a serial queue and history; detach, reconnect, follow from the browser. Live progress, ETA, errors-only view, root-cause diagnosis of failed builds, comparison with the previous run, graceful stop and recovery.
* **Keyboard first**: numbers open sections, letters act, `/` searches, `?` lists every key; editors use nano keys (`^O`, `^X`, `^W`). → [Keyboard](docs/keyboard.md)
* **Web dashboard**: `bitloom --web`, the same service in a browser with live output, Toaster-style summaries, toasts and a `Ctrl+K` palette. → [Web](docs/web.md)
* **Projects**: guided setup that detects kas files, Poky checkouts and kas launcher scripts; new projects pinned to Scarthgap or Wrynose; clone from Git. → [Projects](docs/projects.md)
* **SBOM, CRA and releases**: SPDX 3 / 2.2 quality, VEX, vulnerabilities from sbom-cve-check, cve-check and Grype, CRA readiness and timeline, SBOM settings with explanations; features follow the detected Yocto release. → [Compliance](docs/compliance.md)
* **Studio**: create your own distribution, machines, images, recipes and layers with a live preview. → [Studio](docs/studio.md)
* **Developer workbench** (`F10`): variable origins, rebuild signatures, failed-task investigation, devtool, SDK/IDE setup, image comparisons, devices. → [Developer](docs/developer.md)
* **Daily helpers**: notifications when a build ends (desktop, ntfy, Slack/Teams), ETA, run comparison, tmp/work usage. → [Guide](docs/guide.md#daily-helpers)
* **Teams and CI/CD**: headless `--ci` matrix with JUnit and annotations, shared team profiles, infrastructure checks, device fleet, image matrix, builds started outside Bitloom. → [Teams](docs/teams.md)

## Install

From the [Releases page](https://github.com/padovanl/bitloom/releases) (replace `1.2.3`):

```bash
sudo apt install ./bitloom_1.2.3_all.deb      # Debian / Ubuntu, dependencies included

tar -xzf bitloom-1.2.3.tar.gz && cd bitloom-1.2.3   # any Linux / WSL2
python3 -m venv .venv && .venv/bin/python -m pip install .
```

Verify with `sha256sum --check --ignore-missing SHA256SUMS`. Docker or Podman, kas and Yocto are separate tools for real builds. Details: [installation](docs/guide.md#install-from-a-github-release).

## Start

```bash
./setup-demo.sh            # from a checkout: venv, sample workspace, opens the TUI
bitloom --demo             # Scarthgap and Wrynose samples (P switches profile)
bitloom --web --demo       # the dashboard
bitloom                    # in your project: the guided setup proposes a profile
```

<details><summary>Animation: tour of the TUI</summary>

![Animated tour of the actual TUI](docs/assets/tour.gif)
</details>

## Documentation

| | |
| --- | --- |
| [User guide](docs/guide.md) | Profiles and runtimes, workflows, logs, caches, analysis, themes, troubleshooting |
| [Manual testbook](README.testbook.md) | Step-by-step acceptance of every feature and all 74 operations |
| [Command reference](docs/commands.md) · [Keyboard](docs/keyboard.md) | Generated from the code |
| [Validation](docs/validation.md) | Real Scarthgap and Wrynose builds through kas-container and what was verified |
| [Research map](docs/roadmap.md) | Sources, criticisms of earlier Yocto interfaces and how Bitloom answers them |

Browse it locally with `python tools/serve_docs.py --port 8000`.

## CRA and EN 40000

The CRA harmonised standards are being drafted as the [EN 40000 series](https://cyber-regulation.com/article/en-40000-series-explained); [prEN 40000-1-3](https://standards.iteh.ai/catalog/standards/cen/487254bf-baa1-48e9-be33-658b37f6fb90/pren-40000-1-3) covers vulnerability handling (receipt, assessment, remediation, communication, tracking). Bitloom does not implement or certify the standard: its compliance views are organised around the build evidence such a process relies on. It is engineering evidence, not legal advice.

## Development

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

Screenshots, the documentation site, release packages and the real kas validation builds are described in [Documentation and verification](docs/guide.md#documentation-and-verification) and [Build, launch and try the local Yocto workspace](docs/guide.md#build-launch-and-try-the-local-yocto-workspace).

## Inspiration and thanks

Bitloom is inspired by the idea behind [yoctui](https://github.com/0xbadcaffe/yoctui): bringing everyday Yocto and BitBake work into a terminal interface. Thank you to [0xbadcaffe](https://github.com/0xbadcaffe), the author of yoctui, for the inspiration and for sharing the project with the community. Bitloom has its own implementation and interface. Hob, Toaster and knotty taught what to avoid; see the [research map](docs/roadmap.md#answering-the-criticisms-of-earlier-yocto-interfaces).

## License

Bitloom is released under the [MIT License](LICENSE). Bundled Python dependencies retain their own licenses.
