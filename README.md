<p align="center"><img src="docs/assets/bitloom-icon.svg" width="120" height="120" alt="Bitloom woven B icon"></p>

# Bitloom

**A terminal cockpit for everyday Yocto and BitBake development.** Build images, inspect recipes, develop with devtool, follow failures, and manage local caches from one keyboard-friendly interface.

*Weaving layers, recipes and builds into one terminal workspace.*

Python 3.10+ · Textual · Linux / WSL2 · Host · Docker · Podman · kas · kas-container

![Bitloom build cockpit](docs/assets/builds.png)

## Inspiration and thanks

Bitloom is inspired by the idea behind [yoctui](https://github.com/0xbadcaffe/yoctui): bringing everyday Yocto and BitBake work into a terminal interface. Thank you to [0xbadcaffe](https://github.com/0xbadcaffe), the author of yoctui, for the inspiration and for sharing the project with the community. Bitloom has its own implementation and interface.

## Start in one minute

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
bitloom --demo
```

The executable is `bitloom`; `yoctotui` remains available as a compatibility alias. The Python package and existing `.yoctotui` configuration/state paths retain their names.

The demo creates an isolated sample workspace under `.yoctotui/demo`. Its metadata and screenshots are labelled demo data. It does **not** simulate successful Yocto builds or download Yocto.

For a real project, launch `bitloom`, press **F4**, and configure a profile. Alternatively:

```bash
mkdir -p .yoctotui
cp examples/profiles.json .yoctotui/profiles.json
# Replace the example paths before starting.
bitloom --config .yoctotui/profiles.json
```

![Animated tour of the actual TUI](docs/assets/tour.gif)

## What you can do

| Area | Capabilities |
| --- | --- |
| Builds | Independent reconnectable build service, serial queue, persistent SQLite history, streaming logs, observed live recipe tasks, task progress, exit status, retries with original profile, cancellation, SDK/eSDK, recipe tasks, forced compile, dry runs, parsing |
| Runtimes | Initialized host environment; kas config composition; fresh Docker/Podman containers; existing containers; official kas-container wrapper |
| Layers | Expandable layer tree, search local layers, priorities through BitBake, add/remove/create, overlays, appends, cross-layer dependencies, edit metadata with backups |
| Recipes | Browse `.bb`, `.bbappend`, `.bbclass` and kas YAML, compile/patch/package individual recipes, list tasks, evaluate environment |
| Development | devtool modify/add/build/build-image/reset/finish/update/upgrade, upstream version checks, device deployment, devshell, kernel menuconfig and config checks |
| Errors and logs | Build and task log browsers, case-insensitive search with context, error-only view, pause/resume, failure notifications, exports, build summary and timestamped slow-task reports |
| Downloads | Fetch a recipe or all target dependencies, size/age inventory, orphan marker and partial-download audit, concrete prune plans |
| Shared state | Local inventory, age-based prune plans, recipe cleansstate, signature dumps/diffs, `-S printdiff` |
| Analysis | Runtime file/directory access and backed-up editing, binary artifact export with SHA-256 verification, failure diagnosis, image package/file provenance, preflight, snapshots and comparison, reproducibility bundles, conservative signature-reference cache plans; search metadata contents with file/line locations, compare package manifests by architecture, inspect sstate hit rates, group repeated warnings, export reports |
| Workbench | Filter evaluated environment variables, compare two snapshots, browse generated dependency edges and transitive/reverse dependency context, buildhistory Git diff |
| Outputs | Discover images, SDKs, manifests, licenses, SBOMs, buildstats and buildhistory files; text preview, read-only tar rootfs inventory (permissions, owners, links), and binary artifact paths |
| Configuration | Multiple named profiles, custom environment/runtime arguments, local.conf and bblayers.conf editor, backups, external-change detection, diagnostics |
| Releases | Local branch/revision/tag report, dirty-tree status and literal layer-series compatibility checks; separate profiles and build directories per release |
| Testing and security | testimage, ptest, CVE and SPDX command entry points when the required classes/configuration exist |
| Utilities | Argument-based custom commands, interactive terminal handoff, command filtering, keyboard shortcuts, command palette, CLI diagnostics |

The [command reference](docs/commands.md) documents every built-in action. The [user guide](docs/guide.md) describes complete workflows and runtime constraints.

## Reconnectable builds and evidence workflows

Real sessions use an independent local service: close the terminal and reconnect with the same `--state` directory. Ctrl+Q detaches; F5 explicitly stops a job. `--embedded` retains the previous stop-on-exit behavior. Inspect an idle service with `--service-status`, or stop it with `--service-stop`.

The **Analysis** selector connects signature explanations, failure diagnosis, runtime filesystem access, image provenance, snapshot comparison, devtool review, reproducibility exports, preflight and conservative cache reference plans. Shared/exclusive advisory cache locks coordinate cooperating Bitloom builders. Read the [workflow guide](docs/guide.md#evidence-workflows) for inputs, bounds and limitations.

![Real container image provenance](docs/assets/real-kas-provenance.png)

## Keyboard

| Key | Action |
| --- | --- |
| F2 | Search and queue a command |
| F3 | Refresh local metadata, logs, diagnostics and artifacts |
| F4 | Edit profiles |
| F5 | Open build interruption options |
| F6 | Retry the selected job |
| F7 | Preview and save a terminal theme |
| Alt+1…5 | Builds, metadata, task logs, workbench, caches |
| Ctrl+L | Focus build log search |
| Ctrl+P | Textual command palette |
| Ctrl+Q | Detach from service and exit; embedded/demo stops owned jobs |
| Enter | Select a build log or open a metadata/task/artifact row |
| Tab / Shift+Tab | Move focus |
| Escape | Close a dialog |

The interface uses compact single-line controls, a terminal navigator, split history/output and syntax-highlighted metadata previews. **140 × 42** shows the complete workspace; below 105 columns it switches to tabs and hides side panes. The [compact terminal capture](docs/assets/compact.png) shows the 90 × 28 layout. Host CPU/RAM and workspace filesystem usage are sampled every two seconds and explicitly labelled as host resources.

## Build interruption and recovery

**Stop…** offers three explicit choices:

- **Let finish** leaves the build running.
- **Graceful stop** sends exactly one SIGINT to the host BitBake client, or to the main process of a fresh container managed by Bitloom. BitBake can finish its currently executing tasks. The TUI does not escalate this request automatically.
- **Force + recovery** terminates the managed process/container and offers `bitbake -c clean` for recipes observed running in the log. Finished tasks are removed from that active set. Recovery is withheld if runtime shutdown is unconfirmed. Work files may contain developer edits: the recovery dialog makes the selection explicit.

kas wrappers and pre-existing containers do not expose a guaranteed client PID. Graceful stop is disabled there; forced client termination requires checking the external build server before manually cleaning. A build interruption does not normally rewrite `.bb` files, and an observed active recipe is **not proof of corruption**. Task detection depends on standard BitBake log messages.

## Real Yocto validation

The reproducible integration configuration is [tests/integration/kas-minimal.yml](tests/integration/kas-minimal.yml): Poky **yocto-5.0.8**, **qemux86-64**, **core-image-minimal**, executed through the same Runner used by the TUI.

```bash
# Install the official wrapper inside the project venv, not system-wide.
curl -fL https://raw.githubusercontent.com/siemens/kas/4.8.1/kas-container \
  -o .venv/bin/kas-container
chmod +x .venv/bin/kas-container
PATH="$PWD/.venv/bin:$PATH" python tools/validate_kas.py \
  --work /tmp/yoctotui-kas-validation --engine docker
```

Docker/Podman must be running. The kas image supplies Yocto build dependencies. The first build downloads sources and can take considerable time/disk space. `.validation/` contains logs, SQLite history and `result.json`; it is ignored by Git. Use a Linux filesystem for work files. Docker installed via Snap has a private `/tmp`; see the [troubleshooting guide](docs/guide.md#troubleshooting).

**Verified on 2026-10-10:** all 4,064 tasks succeeded in 57m 10s through kas-container; the rootfs archive and eight runtime probes passed.

![Actual successful kas-container build](docs/assets/real-kas-build.png)

See the [validation report](docs/validation.md) for the actual result and limitations. Screenshots and GIFs show a sample workspace; they are not evidence of a completed Yocto image.

## Development and documentation

```bash
pip install -e . pytest pytest-asyncio
python -m pytest -q
python -m yoctotui --list-actions
python -m yoctotui --doctor

# Regenerate actual UI screenshots and GIF (optional tooling).
pip install pillow cairosvg
python tools/capture_docs.py
```

The static [documentation site](docs/index.html) is ready for GitHub Pages. The workflow uploads `docs/` on pushes to `main` and supports manual dispatch. In the GitHub repository, select **Settings → Pages → Source → GitHub Actions**. A GitHub remote and a push are required to publish; local files alone do not create a public site.

## Practical limits

This is an initial functional release. Each command remains subject to the selected Yocto release, runtime, device access and configuration. Inventory scans are bounded, age-based pruning does not perform signature reachability analysis, and no cache is pruned automatically. External builders sharing a cache cannot be detected reliably. Logs and profiles can contain proprietary paths or credentials; review exports before sharing them. Custom commands accept argv, not shell expressions.

No CI claim implies a full Yocto build: unit/UI tests and the opt-in container integration are separate validations.

## Terminal themes

Press **F7** or choose **Themes** in the toolbar to preview and save one of 12 palettes: Bitloom, Nord, Dracula, Tokyo Night, Catppuccin Mocha, Gruvbox, Solarized Dark, Ocean, Forest, Ember, Paper and High Contrast. Paper is a light theme; High Contrast uses a black background and bright foreground. Cancel restores the previous palette. The choice is stored separately from build profiles in the state's `appearance.json` and is restored next launch.

![Actual terminal theme previews](docs/assets/themes.gif)

The [Bitloom icon](docs/assets/bitloom-icon.svg) combines a woven B with horizontal layer threads and a vertical build thread. SVG is the source; PNG variants provide favicon, touch-icon and sharing support.

## Build, launch and try the local Yocto workspace

Run these commands from the repository root in a Linux/WSL terminal. Bitloom is a Python application: editable installation is sufficient for development; no native compilation is required.

### Install for development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
bitloom --help
bitloom --demo
```

If themes appear monochrome and your shell sets `NO_COLOR`, run `unset NO_COLOR` before launching.

In this prepared workspace, `.venv` and kas-container already exist. You can start directly with `source .venv/bin/activate`.

### Build distributable packages

```bash
source .venv/bin/activate
python -m pip install 'setuptools>=61' build wheel
python -m build --no-isolation
```

Outputs are `dist/yoctotui-0.1.0-py3-none-any.whl` and `dist/yoctotui-0.1.0.tar.gz`. The distribution name remains yoctotui; its executable is **bitloom**. The source archive includes the English manuals, Pages assets, examples and integration tools. To install the wheel into another environment:

```bash
python3 -m venv /tmp/bitloom-wheel
/tmp/bitloom-wheel/bin/python -m pip install dist/yoctotui-0.1.0-py3-none-any.whl
/tmp/bitloom-wheel/bin/bitloom --help
```

### Open the already built local test workspace

The verified local workspace uses **Poky yocto-5.0.8 / Scarthgap**, **qemux86-64**, **core-image-minimal** and a pinned kas container image. Yocto tools execute inside Docker; the host runs only the TUI and container wrapper. `.validation` is local generated state and is intentionally absent from a fresh Git clone.

```bash
source .venv/bin/activate
python tools/prepare_validation.py
bitloom --config .validation/profiles.json --state .validation
```

The helper recreates the test profile from `.validation/result.json` when available. It preserves history and other profiles, uses the recorded workspace and does not build anything. On this machine the recorded directory is `/tmp/yoctotui-kas-validation`; with Docker Snap, its contents are in the daemon's namespace and may appear empty on the host. In the container, the build directory is `/work/build`. Use Analysis runtime tools to browse it.

1. Keep `core-image-minimal` in the top target field and press **Build** for an incremental image build. Existing matching task outputs are reused.
2. Select its history row to follow the complete log. **F2** opens recipe tasks, fetch, SDK, layers and devtool actions; change the target to `busybox` to inspect or build one recipe.
3. In **Analysis**, choose **Build preflight** and enter `/work/build`. For **Package provenance**, set the top target back to `core-image-minimal` and enter `/bin/sh`; the verified inclusion chain is `packagegroup-core-boot → busybox`.
4. Try **Runtime directory** with `/work/build/tmp/deploy/images/qemux86-64`, or **Capture snapshot** with `/work/build`. **F7** previews and saves a theme.
5. **Ctrl+Q** detaches while the service continues. Launch the same command again to reconnect. **F5** opens explicit interruption choices; choose Let finish if you want the build to complete.

```bash
bitloom --state .validation --service-status
bitloom --state .validation --service-stop
```

The last command stops an idle service only. Stop it before running integration scripts that need exclusive access to `.validation`; closing the TUI alone does not stop the service.

### Reproduce on a fresh machine

Docker must be available and the build work directory must be on a Linux filesystem. Install the official wrapper if needed:

```bash
source .venv/bin/activate
curl -fL https://raw.githubusercontent.com/siemens/kas/4.8.1/kas-container -o .venv/bin/kas-container
chmod +x .venv/bin/kas-container
python tools/prepare_validation.py --work /tmp/yoctotui-kas-validation --engine docker
bitloom --config .validation/profiles.json --state .validation
```

Press Build to initialize and build the image. The first build downloads repositories/sources and needs substantially more time and disk than the verified incremental run. The helper does not repair container mount permissions: if Docker Snap creates the dedicated mount as root, follow the [runtime troubleshooting guide](docs/guide.md#troubleshooting).

For scripted verification, with the service stopped:

```bash
python tools/validate_kas.py --work /tmp/yoctotui-kas-validation --engine docker
python tools/prepare_validation.py
python tools/probe_kas.py
python tools/probe_workflows.py
```

`validate_kas.py` builds the image and verifies its rootfs; probes then exercise real runtime operations. `probe_workflows.py` submits a warm build to a separate persistent service and stops that service after completion. Unit/UI checks run with `python -m pytest -q`; they do not require a Yocto build.

### Preview the Pages site locally

```bash
python -m pip install '.[docs]'
python tools/build_docs.py
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. The Pages workflow is included, but this workspace has no GitHub remote and no public deployment yet.
