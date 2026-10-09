# Bitloom manual testbook

This is an executable learning path and acceptance checklist, not a report of tests already performed. Run it yourself against your environment. All project text and evidence should remain in English. Record PASS, FAIL or N/A with the reason and a log/screenshot. Do not count an unavailable device, class or runtime as a successful test.

## Contents

1. [Build and installation](#1-build-and-installation)
2. [Launch with kas-container](#2-launch-with-kas-container)
3. [UI and profile acceptance](#3-ui-and-profile-acceptance)
4. [Build, downloads and recipe tasks](#4-build-downloads-and-recipe-tasks)
5. [Create a layer and recipes from the TUI](#5-create-a-layer-and-recipes-from-the-tui)
6. [Editing and devtool](#6-editing-and-devtool)
7. [Logs, reports and analysis](#7-logs-reports-and-analysis)
8. [State, reconnect and interruption](#8-state-reconnect-and-interruption)
9. [Caches](#9-caches)
10. [Runtime variants and optional features](#10-runtime-variants-and-optional-features)
11. [Every command-center action](#11-every-command-center-action)
12. [Record results and restore the experiment](#12-record-results-and-restore-the-experiment)
13. [Feature assessment](#13-feature-assessment)

Run chapters 1–5 first. Image builds, SDKs, security databases and hardware tests take substantially longer than UI/navigation tests. Chapter 11 is the command coverage ledger; it references fixtures and prerequisites from the preceding chapters.

## 1. Build and installation

### B01 — Fresh checkout and demo

Requires Linux/WSL2, Bash, Python 3.10+ with venv support and internet access.

```bash
./setup-demo.sh --dev --no-launch
source .venv/bin/activate
bitloom --help
python -m bitloom --list-actions
COLORTERM=truecolor bitloom --demo
```

Expected: .venv is created/reused, the executable and module work, and the demo opens. The demo provides sample files; it does not provide BitBake or fabricate successful Yocto builds. Exit with Ctrl+Q; Esc closes a dialog first. Repeat setup: existing sample files are retained.

### B02 — Wheel and source archive

```bash
python -m pip install build wheel
python -m build --no-isolation
```

Expected: `dist/bitloom-<project-version>.tar.gz` and `dist/bitloom-<project-version>-py3-none-any.whl`. Install the wheel into a separate venv and run its bitloom --help from outside the checkout. Extract the source archive and verify LICENSE, setup-demo.sh, this testbook, examples, tools and docs are present.

### B03 — Debian release package

On a system providing dpkg-deb:

```bash
python tools/build_release.py 0.9.0 --output dist/manual-release-0.9.0
(cd dist/manual-release-0.9.0 && sha256sum --check SHA256SUMS)
dpkg-deb --info dist/manual-release-0.9.0/bitloom_0.9.0_all.deb
```

Use a new output directory if repeating. Expected: source, wheel, .deb and checksums use version 0.9.0; the checkout's version stays unchanged. Install the .deb in a disposable Debian/Ubuntu machine/container with Python 3.10+ using `sudo apt install ./bitloom_0.9.0_all.deb`. Run `/usr/bin/bitloom --help` from /tmp; verify dependencies under /opt/bitloom/lib and MIT license under /usr/share/doc/bitloom/copyright. Remove with `sudo apt remove bitloom`. Publishing a GitHub release is a separate operator action and is not required by this testbook.

## 2. Launch with kas-container

Docker or Podman must already work. Keep Yocto work files on a Linux filesystem. Bitloom itself can reside in the current checkout. The pinned kas image provides the Yocto toolchain dependencies.

```bash
source .venv/bin/activate
curl -fL https://raw.githubusercontent.com/siemens/kas/4.8.1/kas-container \
  -o .venv/bin/kas-container
chmod +x .venv/bin/kas-container
docker info
```

### K01 — Reuse this checkout's verified build

If `.validation/result.json` exists:

```bash
python tools/prepare_validation.py
COLORTERM=truecolor bitloom --config .validation/profiles.json --state .validation
```

F4 is a JSON editor: duplicate an object in the profiles array, give it a unique name, set active or choose it with the top selector, then Save profiles. There is currently no dedicated cloning wizard.

Expected: kas-integration profile, kas-container runtime, qemux86-64/poky. The helper preserves history and takes KAS_WORK_DIR from the recorded result. With Docker Snap the daemon's /tmp can differ from host /tmp. Use runtime file operations with `/work/build`; an empty host directory does not prove the container build is missing.

Use this path for read-only inspection or routine rebuilds. Use K02 for tests that change configuration, devtool state or caches.

### K02 — Prepare an isolated manual-test profile

Run from the checkout with the venv activated. This writes a new state/configuration directory, without touching `.validation` or the integration YAML:

```bash
python - <<'PY'
from pathlib import Path
from bitloom.models import Profile, Settings
root = Path.cwd().resolve()
settings = Settings(root / '.manual-testbook/profiles.json')
if settings.path.exists():
    raise SystemExit('Manual profiles already exist; reuse them or choose a new state directory.')
settings.profiles = [Profile(
    name='manual-kas', root=str(root), mode='kas-container',
    kas_file='tests/integration/kas-minimal.yml', machine='qemux86-64', distro='poky',
    targets=['core-image-minimal'], environment={
        'KAS_CONTAINER_ENGINE': 'docker',
        'KAS_WORK_DIR': '/tmp/bitloom-manual-work',
        'KAS_CONTAINER_IMAGE': 'ghcr.io/siemens/kas/kas@sha256:fef6f850106a6823e65e133ed8157a847431dea4aa2de3a636c11f65e9977476',
    })]
settings.active = 'manual-kas'
settings.save()
PY
COLORTERM=truecolor bitloom \
  --config .manual-testbook/profiles.json --state .manual-testbook
```

For Podman change KAS_CONTAINER_ENGINE and use podman info. This dedicated workspace may require a cold build. Existing edits to the base integration YAML are included; record its Git diff before testing.

### K03 — Checkout and validate configuration

F2 → Checkout kas repositories; then Dump resolved kas configuration. Expected: checked-out pinned Poky revision and the merged machine/distro/target. In Analysis run Build preflight on `/work/build`; missing build configuration before the first build is a prerequisite finding, not a fake PASS. Build busybox, then core-image-minimal to populate pkgdata, artifacts and reports needed below. Run Generate kas lock file and inspect its actual output; kas release support determines the result.

## 3. UI and profile acceptance

| Case | Steps | Expected result |
| --- | --- | --- |
| U01 | F8/F9 through all sections, including Analysis and Help; Ctrl+L; Ctrl+P | Navigation works; log focus and command palette open. Alt+number is optional terminal-dependent behavior, not the primary shortcut. |
| U02 | F2 filter by fetch, layer and devtool; choose an action; leave a required field blank | Matching actions appear; missing input is rejected before submission; preview matches argv. |
| U03 | F4 duplicate manual-kas, rename it, edit targets/environment and select it | Named profile persists after restart; the selected profile drives new jobs. Invalid mode/duplicate names/environment types are rejected. |
| U04 | Resize to 160×50, 120×36, 90×28, 80×24, 60×20, 140×20, then back | Logs remain usable, secondary panels disappear, and panels return when space is available. F2/F4/F7 dialogs fit at 60×20. |
| U05 | F7 preview all fourteen themes, Cancel; repeat, Save Soft Slate or Linen and restart with the same state | Cancel restores the old palette; Save persists. Focus a report pane: the border changes, its background stays stable. |
| U06 | Inspect CPU/RAM and filesystem cards | Values update and are labelled host measurements, including with container profiles. Machine/distro header reflects explicit/literal settings; evaluated environment remains authoritative. |
| U07 | Run a several-second job and watch history, then wait after completion | Elapsed advances every second while running, stops at completion; status, exit code and logs agree. |
| U09 | Configuration → Refresh; run `bitloom --config .manual-testbook/profiles.json --doctor` | Actual diagnostics distinguish missing host-visible files/tools from available ones; runtime preflight tests container paths separately. |
| U08 | Open Profiles or Themes while a job emits output; close it | Output continues; returning to Builds shows accumulated logs, without widget errors. |

## 4. Build, downloads and recipe tasks

### R01 — Incremental recipe and image builds

Set top target to busybox. Run Build target twice. Expected: successful jobs in history and less work on the second build. Run List recipe tasks, Dry run and Parse metadata. Progress represents task messages observed in logs, not CPU usage or an exact remaining-time estimate. Setscene and normal task phases may have different counters; a 100% observed counter alone does not mean the process exited.

Run Fetch recipe sources, Unpack recipe, Apply recipe patches, Configure recipe, Compile recipe, Install recipe and Package recipe on busybox. Force compile should execute compilation even when otherwise current. Run custom task with target busybox and task `listtasks` and check the generated command.

Set core-image-minimal: Build target and Build root filesystem. Verify completion by success/exit 0, then locate the image manifest and rootfs archive through Runtime directory at `/work/build/tmp/deploy/images/qemux86-64`.

### R02 — Cleanup behavior

On the dedicated workspace, run Clean recipe work directory on busybox, then rebuild. Record work/sstate reuse. Run Clean recipe + sstate and rebuild; local recipe sstate is removed, while configured mirrors may still supply results. Run Clean recipe + sstate + downloads only when you deliberately want source removal and refetch; record the affected recipe and rebuild afterward. It does not mean delete every shared cache file.

### R03 — Fetch and download audit

Run Fetch all target dependencies on core-image-minimal. Inspect downloads through Runtime directory, and run Download audit in Workbench for host-visible cache paths. Expected: fetch success and actual inventory/report. Host cache inventory cannot discover Docker-private files by guessing host paths; use runtime operations when that filesystem is not mounted on the host.

## 5. Create a layer and recipes from the TUI

### L01 — Layer creation and registration

F2 → Create layer, path `/work/meta-bitloom`. Expected: conf/layer.conf and generated skeleton. Inspect it with Analysis → Runtime file. Show layers and priorities does not list the new layer until registered.

F2 → Add layer with the same path; Show layers and priorities should include it. Also test Show recipes, Show recipe appends, Show overlaid recipes and Show cross-layer dependencies. An empty report can be correct; record it rather than inventing conflicts.

Remove layer, confirm it disappears, then add it again. Removal unregisters the layer; it does not delete its files. Generated bblayers.conf changes may be replaced by kas, so make registration reproducible in L03.

### L02 — New recipe and file handling

Metadata → New file, or Analysis → Create runtime file. Enter:

```text
/work/meta-bitloom/recipes-example/bitloom-hello/bitloom-hello_1.0.bb
```

Choose a recipe template, then replace its content with:

```bitbake
SUMMARY = "Bitloom manual acceptance recipe"
LICENSE = "CLOSED"
S = "${WORKDIR}"
do_install() {
    install -d ${D}${bindir}
    printf '#!/bin/sh\necho "Hello from Bitloom v1"\n' > ${D}${bindir}/bitloom-hello
    chmod 0755 ${D}${bindir}/bitloom-hello
}
```

CLOSED is only for this private test fixture. Use the actual license and checksums in distributable recipes.

Expected: missing parent folders are created, the recipe is saved inside the selected runtime, and its containing directory opens in Analysis. Repeat creation at the same path: an error appears and existing content remains unchanged. Cancel another unsaved file: it must not exist. Also create a notes.txt using the empty template and verify its directory listing.

Edit the saved recipe with Edit runtime file; change v1 to v2. Verify a backup is reported. Open an editor, change the same file externally before saving, then Save: the hash conflict must reject the stale edit. Creating/editing metadata while this session has a queued/running build is rejected.

### L03 — Persist the layer and image customization in kas

On the HOST, create `kas-testbook.yml` at the checkout root using your IDE. Alternatively create it from New file with a host profile pointed at the checkout. A kas/container file dialog targets the container, so do not assume a host path is available there.

```yaml
header:
  version: 14
  includes:
    - tests/integration/kas-minimal.yml
repos:
  manual-experiment:
    path: /work/meta-bitloom
local_conf_header:
  manual-experiment: |
    IMAGE_INSTALL:append = " bitloom-hello"
```

Duplicate manual-kas in F4, call it manual-layer, keep the same KAS_WORK_DIR and container environment, and set kas_file to kas-testbook.yml. Run Build kas configuration. Expected: kas registers the layer and the image manifest contains bitloom-hello. Build bitloom-hello separately, edit its greeting and rebuild both recipe/image. Changes should be detected without cleaning every time.

### L04 — .bbappend and external refresh

Use New file → Recipe append to create `/work/meta-bitloom/recipes-core/busybox/busybox_%.bbappend`:

```bitbake
SUMMARY:append = " (manual experiment)"
```

Show recipe appends should match it. Resolve busybox environment and verify SUMMARY. Run Explain sstate differences before/after a metadata change and inspect what actually changed; a SUMMARY-only change need not force compilation.

With a HOST profile, select a locally indexed layer/recipe and create, edit, then delete a .bb file from your IDE. Within five seconds Metadata should reflect each change. Its selected file/layer expansion should survive changes when still present. Container-only metadata is viewed through runtime operations: open Runtime directory and add/remove a file through a second kas shell. Within fifteen seconds while idle the listing should refresh. Automatic scans pause with a modal open. F3 rescans local metadata; Analyze refreshes a runtime directory immediately.

## 6. Editing and devtool

### D01 — Existing recipe development

On busybox: Workspace status → Modify recipe → Workspace status → Build workspace recipe. Inspect the source directory reported by devtool; use Devtool review on that directory for status, commit and diff evidence. Make a source change with the runtime editor or an available editor in Open kas shell. Devtool build and Build image with workspace recipes should use the workspace.

Commit source changes in the devtool source repository before Finish recipe into layer, destination `/work/meta-bitloom`. Inspect the emitted .bbappend/patches, then rebuild. Reset workspace recipe removes workspace integration; inspect retained source files separately. Use Update recipe from source as an alternative export experiment and inspect its actual destination/output. Do not run finish/update blindly against upstream layers.

### D02 — Create a source-based recipe

Using New file, create these files under `/work/bitloom-source`:

CMakeLists.txt:

```cmake
cmake_minimum_required(VERSION 3.16)
project(bitloom_dev C)
add_executable(bitloom-dev main.c)
install(TARGETS bitloom-dev DESTINATION bin)
```

main.c:

```c
#include <stdio.h>
int main(void) { puts("Bitloom devtool fixture"); return 0; }
```

Add a LICENSE file containing your chosen actual license. Run Add source as recipe with target bitloom-dev and path /work/bitloom-source. Expected: devtool creates workspace metadata; Build workspace recipe succeeds. Inspect the generated recipe rather than assuming the automatic license/build-system detection is correct. Finish into your layer and inspect exported files. Also run Create recipe from URL/source with source /work/bitloom-source: inspect the generated recipe output; this action does not promise to save it at a destination filename.

### D03 — Interactive terminal handoff

Open kas shell: run pwd and a read-only bitbake-layers show-layers, then exit. Expected: the terminal is handed off and the TUI returns. Open recipe development shell on busybox, then exit. Run Configure help on a compatible recipe and inspect the options. Menuconfig and QEMU are covered in optional tests below.

## 7. Logs, reports and analysis

### A01 — Logs and controlled failure

Through Custom command run `python3 -c 'print("ERROR: manual diagnostic fixture"); raise SystemExit(7)'`. Expected: failed job, exit 7, actual log content and notification. This is an intentional test failure, not a successful Yocto build. Retry with F6: the same argv/profile is used, even after changing the active profile.

Select a build log, search error with different case, clear search, toggle Errors and Pause/Resume. Expected: matching context, paused display with continued capture, and accumulated output after resume. Export log and verify the local file. In Task logs, filter/select/read a real task log; Failed task log requires a actual BitBake failure with a reported task-log path. Temporarily add a failing do_install body to bitloom-hello, build it, inspect the task log/notification, then restore the recipe and rebuild. Review backups rather than editing them as recipes.

### A02 — Workbench

Resolve busybox environment; filter PN, PV, WORKDIR, S, B and MACHINE. Load recorded output, save/resolve a second environment after a metadata change, then Env diff: changes should match the experiment. Resolve one BitBake variable with variable MACHINE. Generate graph for core-image-minimal, load Dependencies and inspect direct, reverse and transitive edges using Why this task? Missing edges are reported as missing evidence, not proof of no dependency.

Build history diff requires buildhistory commits; inspect its Git diff after image package changes. Build report should describe selected log status/task/sstate/warnings. Timings requires available timestamps/buildstats evidence; missing timing data should be reported. Download audit requires accessible cache paths.

### A03 — Runtime files, artifacts and package ownership

Runtime directory `/work/build/tmp/deploy/images/qemux86-64` → choose an actual artifact path. Runtime file previews text manifests; binary files should be exported through Export runtime artifact, first field runtime path, second field a new LOCAL destination. Expected: SHA-256 verified export; existing destinations rejected. Text previews are limited to 2 MiB, binary export to 1 GiB, listings to 2,000 entries.

Use Artifacts → Read file and Rootfs inventory for HOST-visible artifacts. For a container-only rootfs, export it first and inspect the local copy with a host profile. Tar inventory is read-only and does not extract symlinks into the filesystem.

List built packages, List package files with target busybox, Find package owning a path with `/bin/sh`, and Find recipe for package with busybox. For Package provenance set top target core-image-minimal and first field /bin/sh. Expected: pkgdata owner, recipe and available inclusion chains; alternatives and package-manager decisions can limit the explanation.

### A04 — Every Analysis report

| Operation | Inputs/fixture | Expected result |
| --- | --- | --- |
| Search metadata | Search a known local recipe text | File/line matches; container-only files are not silently treated as host files. |
| Compare manifests | Two LOCAL exported manifests, before/after bitloom-hello inclusion | Added/removed/version/architecture changes agree with files. |
| Sstate efficiency | Selected real build log or LOCAL log path | Observed hit/miss statistics, with unavailable data distinguished. |
| Warning groups | A real log with repeated warnings | Grouped counts, not invented warnings. |
| Failure diagnosis | Select controlled failed job | Diagnosis from actual captured text; sensitive values redacted in exported bundles. |
| Runtime directory / file / edit / create / export | L02 and A03 | Covered creation, limits, backup, conflicts, refresh and hash checks. |
| Build preflight | /work/build | Permissions, disk/inodes and config presence; advisory thresholds labelled. |
| Capture snapshot | /work/build, before/after image change | JSON saved locally; configs/revisions/manifests/artifacts and observed image identity where available. Note the saved paths. |
| Compare snapshots | First and second LOCAL snapshot JSON paths | Differences reflect your recorded change. |
| Reproducibility bundle | /work/build | Local JSON bundle with actual profile/config/revision evidence and redaction; add a synthetic API_TOKEN=testbook-not-a-secret to the profile and verify redaction. It does not promise reproducible binaries by itself. |
| Why rebuilding? | First field busybox | Captures printdiff/signature context while idle; conclusion respects available evidence. |
| Package provenance | Image target core-image-minimal; first /bin/sh | Actual pkgdata owner/recipe/chains as above. |
| Devtool review | Actual devtool source directory | Commit/status/diff, including uncommitted changes. |
| Cache reference plan | Runtime cache directory; second actual stamps directory | Referenced/unproven classifications; no automatic deletion based on one build's references. |

Click Export on reports and verify local content and path. Close/reopen a modal during background output and ensure the report/log widgets still work.

## 8. State, reconnect and interruption

### S01 — Queue, history and reconnect

Submit two short jobs; expected serial execution, queued/running transitions, correct final status. Start a longer recipe task, Ctrl+Q, reopen with exactly the same --state. Expected: persistent service and build continue, history/logs reconnect. Clients attached to the same service share its serial queue. For the overlap test, start a separate service with a DIFFERENT --state directory but the same profile/build directory: exclusive build ownership should reject simultaneous execution rather than race BitBake. Compare F6 retry after changing profiles: original job profile must be retained.

After jobs finish, from another terminal:

```bash
bitloom --state .manual-testbook --service-status
bitloom --state .manual-testbook --service-stop
```

Expected: actual state and idle shutdown. Start/reconnect again. A stop request while work is active must not silently terminate it. Test --embedded with a separate state and short job: Ctrl+Q stops owned jobs, unlike the default persistent session. Demo also uses embedded behavior.

### S02 — Interruption and recovery

On a disposable build, F5 → Let finish: job continues. Host or freshly managed direct-container profiles can expose Graceful stop: sends one SIGINT and waits, with no automatic escalation. kas wrappers and existing containers do not guarantee the client PID; Graceful stop is disabled there. Record this as expected runtime-specific behavior.

Force + recovery must show observed active recipes and only offer recovery when shutdown is confirmed. With wrappers/external servers verify remaining work before manually cleaning; termination of the wrapper is not proof that BitBake stopped. Recovery uses recipe clean, not editing .bb files. An observed active recipe is not proof of corruption. Rebuild afterward and preserve interruption logs.

## 9. Caches

### C01 — Inventory and reviewed prune

Create deliberately disposable HOST cache fixtures from the checkout:

```bash
python - <<'PY'
from pathlib import Path
import os, time
root = Path('.manual-testbook/cache-fixture').resolve()
for sub, names in {'downloads': ['example.tar.gz', 'example.tar.gz.done', 'partial.part', 'orphan.done'], 'sstate': ['example.siginfo']}.items():
    folder = root / sub
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        path = folder / name
        if path.exists():
            continue
        path.write_text('Disposable manual cache fixture; not reusable Yocto data\n')
        old = time.time() - 40 * 86400
        os.utime(path, (old, old))
print(root)
PY
```

In F4 add a host profile using the checkout root and set downloads/sstate to those printed absolute folders. It is for inventory/prune tests, not Yocto builds. Choose age 30 days. The fixture files are synthetic and must be labelled as such in evidence.

For a HOST-visible dedicated cache, configure the profile's downloads/sstate paths. In Caches select Downloads or Shared state, Scan, filter by filename and choose an age. Expected: real counts/sizes/mtime, concrete candidates, cancellation leaves files intact. Confirm only against disposable fixture files, then rescan and verify those exact files are gone. Paths/symlinks outside the selected root must not be deleted. Running/queued jobs and advisory cache leases must prevent unsafe conflicting operations.

For kas container-private paths, use Runtime directory and Cache reference plan. The local prune UI does not magically mount daemon-private storage. Download audit should distinguish source files, done markers, partial files and orphan markers when observed.

### C02 — Signatures

Dump signatures and Explain sstate differences on busybox. Find actual .siginfo/.sigdata paths using runtime directories, then Read signature file and Compare signature files with two real files. Expected: parsed signature evidence; no change can legitimately produce no difference. Run Cache reference plan with `/work/build/sstate-cache` only if that is the actual cache location (resolve SSTATE_DIR first), and second `/work/build/tmp/stamps` if present. Unproven entries are not declared safe to delete.

## 10. Runtime variants and optional features

| Case | Setup and action | Expected / N/A condition |
| --- | --- | --- |
| X01 Host | F4 host profile, valid root/build_dir and oe-init-build-env; Parse, build recipe, env and New file | Commands use initialized host environment. N/A if host Yocto toolchain intentionally absent. |
| X02 Native kas | kas installed locally, mode kas and valid YAML; dump/shell/build | Same arguments routed through local kas. N/A if only container tooling installed. |
| X03 Fresh direct container | mode container, engine/image/container_root/init_script and correct mounts | Parse/build/runtime files run inside managed fresh container; stop options reflect managed PID. Requires a suitable Yocto image. |
| X04 Existing container | Configure container_name for a running compatible container | docker/podman exec routing works; no claim of owning external server lifetime. |
| X05 Podman | Repeat kas-container/directed container profile with Podman | Real command succeeds on working runtime; otherwise record unavailable runtime. |
| X06 Release context | Configuration → Versions; change local layer branch/revision in isolated profile | Actual branches/tags/revisions/dirty trees and literal layer-series checks; container-private Git trees require runtime snapshot/review. |
| X07 SDK/eSDK | Build SDK / Build extensible SDK on image | SDK artifacts created; installer paths visible/exportable. Long test; disk/time required. |
| X08 Kernel | linux-yocto target; Kernel menuconfig, Export kernel config changes, Validate kernel config fragments | Terminal handoff and actual fragment/diff output; task availability depends on kernel recipe/classes. |
| X09 QEMU | Built compatible image with a bootable runqemu-supported rootfs format (the base tar.bz2 alone is insufficient), usable QEMU/KVM/display permissions; Boot image with QEMU | Guest boots; stop/exit guest and return to TUI. Container wrapper arguments/device support may need custom configuration. |
| X10 testimage | Configure testimage class and usable target runner | Tests run and results reported. N/A until runner/class prerequisites exist. |
| X11 ptest | Recipe inherits ptest and image/distro enables it | compile_ptest_base succeeds. Missing task is a prerequisite failure/N/A, not PASS. |
| X12 CVE | cve-check class and database/network configured | Real check output/database/artifacts. Record date/database revision because results change. |
| X13 SPDX | create-spdx class configured | Actual SPDX task/artifacts; generated format depends on Yocto release. |
| X14 Device deploy | Accessible SSH target, dedicated test device and built devtool recipe | Deploy/undeploy changes actual target; record device/path. N/A without device. |
| X15 Recipe upgrade | Suitable upstream recipe/version/network; latest-version, check-upgrade-status, upgrade | Actual available version/status and workspace diff. Pick a supported recipe; empty or unsupported result is documented. |
| X16 Configuration editing | Host local.conf/bblayers.conf editor; runtime editor for container files | Backups and external-change conflicts work. Evaluated env reflects deliberate change; kas YAML remains the source of regenerated configuration. |
| X17 Custom argv | Custom command with a space-containing argument; then quoted literal shell operator | Argument boundary preserved; shell operators are not executed unless you explicitly invoke a shell yourself. |

## 11. Every command-center action

The following ledger is generated from the current ACTIONS list. Match each title in F2; check preview, supplied inputs, status/exit code and log. In the Result column record PASS/FAIL/N/A and evidence. A prerequisite skip is not action coverage. All actions producing queued jobs must also appear in persistent history; interactive actions hand off and return to the terminal.

| Case / action ID | F2 title | Inputs | Scenario / prerequisites | Expected evidence | Result |
| --- | --- | --- | --- | --- | --- |
| CMD001 / `build` | Build target | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD002 / `dry-run` | Dry run | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD003 / `parse` | Parse metadata | none | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD004 / `fetch` | Fetch recipe sources | target=busybox | R03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD005 / `fetch-all` | Fetch all target dependencies | target=core-image-minimal | R03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD006 / `unpack` | Unpack recipe | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD007 / `patch` | Apply recipe patches | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD008 / `configure` | Configure recipe | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD009 / `compile` | Compile recipe | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD010 / `force-compile` | Force compile | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD011 / `install` | Install recipe | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD012 / `package` | Package recipe | target=busybox | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD013 / `rootfs` | Build root filesystem | target=core-image-minimal | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD014 / `sdk` | Build SDK | target=core-image-minimal | X07; long image build | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD015 / `esdk` | Build extensible SDK | target=core-image-minimal | X07; long image build | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD016 / `task` | Run custom task | target=busybox; task=listtasks | R01 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD017 / `clean` | Clean recipe work directory | target=busybox | R02 | Work files removed; subsequent build may reuse sstate. | TODO |
| CMD018 / `cleansstate` | Clean recipe + sstate | target=busybox | R02 | Recipe work/local sstate removed; rebuild succeeds. | TODO |
| CMD019 / `cleanall` | Clean recipe + sstate + downloads | target=busybox | R02 | Recipe downloads removed as well; refetch/rebuild succeeds. | TODO |
| CMD020 / `environment` | Resolve recipe environment | target=busybox | A02/C02 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD021 / `tasks` | List recipe tasks | target=busybox | A02/C02 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD022 / `graph` | Generate dependency graph | target=core-image-minimal | A02/C02 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD023 / `signatures` | Dump signatures | target=busybox | A02/C02 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD024 / `sig-diff` | Explain sstate differences | target=busybox | A02/C02 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD025 / `layers` | Show layers and priorities | none | L01/L04 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD026 / `recipes` | Show recipes | none | L01/L04 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD027 / `appends` | Show recipe appends | none | L01/L04 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD028 / `overlay` | Show overlaid recipes | none | L01/L04 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD029 / `layer-add` | Add layer | path=/work/meta-bitloom | L01/L04 | Layer appears in show-layers. | TODO |
| CMD030 / `layer-remove` | Remove layer | path=/work/meta-bitloom | L01/L04 | Layer unregistered; files retained. | TODO |
| CMD031 / `layer-create` | Create layer | path=/work/meta-bitloom | L01/L04 | New conf/layer.conf and skeleton exist. | TODO |
| CMD032 / `layer-depends` | Show cross-layer dependencies | none | L01/L04 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD033 / `dev-status` | Workspace status | none | D01/D02; X14/X15 when applicable | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD034 / `dev-modify` | Modify recipe | target=busybox | D01/D02; X14/X15 when applicable | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD035 / `dev-add` | Add source as recipe | target=bitloom-dev; path=/work/bitloom-source | D01/D02; X14/X15 when applicable | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD036 / `dev-build` | Build workspace recipe | target=bitloom-dev | D01/D02; X14/X15 when applicable | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD037 / `dev-image` | Build image with workspace recipes | target=core-image-minimal | D01/D02; X14/X15 when applicable | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD038 / `dev-reset` | Reset workspace recipe | target=bitloom-dev | D01/D02; X14/X15 when applicable | Workspace recipe removed; inspect retained sources. | TODO |
| CMD039 / `dev-finish` | Finish recipe into layer | target=bitloom-dev; path=/work/meta-bitloom | D01/D02; X14/X15 when applicable | Committed changes exported into destination layer. | TODO |
| CMD040 / `dev-update` | Update recipe from source | target=busybox | D01/D02; X14/X15 when applicable | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD041 / `dev-upgrade` | Upgrade recipe | target=busybox | X15; select suitable upstream recipe | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD042 / `dev-latest` | Check upstream version | target=busybox | X15; select suitable upstream recipe | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD043 / `dev-deploy` | Deploy to device | target=busybox; device=root@YOUR_TEST_DEVICE | X14; actual SSH device required | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD044 / `dev-undeploy` | Undeploy from device | target=busybox; device=root@YOUR_TEST_DEVICE | X14; actual SSH device required | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD045 / `dev-config` | Configure help | target=busybox | D01/D02; X14/X15 when applicable | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD046 / `dev-upgrade-status` | Check recipe upgrade status | target=busybox | X15; select suitable upstream recipe | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD047 / `recipe-create` | Create recipe from URL/source | source=/work/bitloom-source | D02 | Generated recipe output inspected; no assumed destination file. | TODO |
| CMD048 / `packages` | List built packages | none | A03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD049 / `package-files` | List package files | target=busybox | A03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD050 / `find-path` | Find package owning a path | path=/bin/sh | A03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD051 / `package-recipe` | Find recipe for package | target=busybox | A03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD052 / `license` | Generate SPDX SBOM | target=core-image-minimal | X13; create-spdx configured | Configured SPDX task produces actual artifacts. | TODO |
| CMD053 / `testimage` | Run image tests | target=core-image-minimal | X10/X11 | Configured runner produces actual test results. | TODO |
| CMD054 / `ptest` | Build ptest packages | target=busybox | X11; enabled ptest-capable recipe | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD055 / `devshell` | Open recipe development shell | target=busybox | D03/X08/X09 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD056 / `menuconfig` | Kernel menuconfig | target=linux-yocto | D03/X08/X09 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD057 / `qemu` | Boot image with QEMU | target=qemux86-64 | D03/X08/X09 | Guest boots with supported rootfs format and runtime devices. | TODO |
| CMD058 / `kas-build` | Build kas configuration | none | K03/L03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD059 / `kas-checkout` | Checkout kas repositories | none | K03/L03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD060 / `kas-dump` | Dump resolved kas configuration | none | K03/L03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD061 / `kas-shell` | Open kas shell | none | K03/L03 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD062 / `custom` | Custom command (argument list) | command=python3 -c 'print("manual argv test")' | X17 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD063 / `getvar` | Resolve one BitBake variable | variable=MACHINE | A02/C02 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD064 / `dumpsig` | Read signature file | path=actual runtime path from the preceding test | A02/C02 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD065 / `diffsigs` | Compare signature files | path=actual runtime path from the preceding test; path2=second actual runtime path | A02/C02 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD066 / `kernel-diff` | Export kernel config changes | target=linux-yocto | X08 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD067 / `kernel-fragments` | Validate kernel config fragments | target=linux-yocto | X08 | Actual command output; exit/status agrees with the operation and its prerequisites. | TODO |
| CMD068 / `cve` | Run recipe CVE check | target=busybox | X12 | Configured CVE task/database produces actual results. | TODO |
| CMD069 / `kas-lock` | Generate kas lock file | none | K03/L03 | Lock output/revision matches installed kas behavior. | TODO |

Rows are not a single destructive execution sequence. Recreate the relevant workspace state before devtool finish/reset/update/upgrade, and choose actual signature/artifact paths where requested. Mark direct hardware and unsupported runtime tests N/A with prerequisites recorded.

## 12. Record results and restore the experiment

Use one row per case in your own result file:

| Case | PASS / FAIL / N/A | Runtime and profile | Evidence path | Notes / missing prerequisite |
| --- | --- | --- | --- | --- |
| B01 | TODO | | | |

Record Git commit, Python/Textual versions, Docker/Podman and kas versions, image digest, Poky commit, MACHINE/DISTRO, cache/mirror configuration and modified YAML. Preserve selected job IDs, exported logs/reports/snapshots and screenshots. A successful command entry point alone is not proof that its intended artifact was created.

After testing, finish or reset devtool work deliberately, remove experiment appends/recipes only after saving wanted work, switch back to the base kas profile, and rebuild. Removing a package from IMAGE_INSTALL and rebuilding should remove it from the image manifest. Stop the service only when idle. Keep the manual work directory until evidence is saved; do not delete .validation or a shared cache as cleanup for this book.

Automated implementation checks are complementary:

```bash
python -m pytest -q
python tools/check_testbook.py
python tools/build_docs.py
```

## 13. Feature assessment

These are proposed improvements, not implemented capabilities or manual PASS claims. The [research roadmap](https://padovanl.github.io/bitloom/roadmap.html) records public developer experiences, upstream technical sources, priorities and current boundaries, reviewed on 2026-10-10. Individual discussions are qualitative evidence, not a representative demand survey. Priority reflects Bitloom's assessment of daily usefulness.

### Proposed acceptance experiments

All rows remain **PLANNED** until their feature ships. The baseline column points to experiments you can run **now** with existing features; it does not imply that the proposed UI exists. Keep proposal results separate from the implemented cases in chapters 1–12. Where an experiment modifies configuration or sources, use the isolated layer/profile from chapters 2 and 5 and restore the change after saving evidence.

| Proposal | Proposed workflow / priority | Baseline available now | Future experiment and expected evidence | Status |
| --- | --- | --- | --- | --- |
| P01 | Variable assignment and override explanation / First | A02 env filtering/diff; L04 SUMMARY append | Set SUMMARY in the test recipe and append to it in a matching .bbappend. Resolve the recipe: show final value, both assignment locations, applicable override context and runtime Enter-to-edit. Edit externally and verify the capture becomes stale. | PLANNED |
| P02 | Recipe context and selectable runtime tree / First | L02 creation; A03 runtime listing/edit; L04 appends | Use a container-only layer. Select a recipe and navigate provider/version, active appends, source/build/temp directories and logs using the keyboard. Show evaluated paths and refresh after file creation/deletion; verify 80×24 layout. | PLANNED |
| P03 | Rebuild and cache-miss explanation / First | C02 signature tools; A04 Why rebuilding? | Save signatures for bitloom-hello, change its installed greeting and compare the next capture. Link observed changed variables/tasks to signature evidence; an unchanged subsequent build should show no new metadata change. Mark absent signatures or unreachable mirrors as incomplete evidence, not a guessed cause. | PLANNED |
| P04 | Structured failed-task investigation / First | A01 controlled failure, search and task-log retrieval | Add a deliberate bbfatal in a test recipe task, build, and open the failure context. Link the exact task log, executed script, diagnostic and original profile; export them. Correct it and rebuild; the old failure remains attached to its original job. | PLANNED |
| P05 | Layer/recipe scaffolding with registration / Next | L01–L04; D02 | Create a licensed CMake fixture through the proposed wizard. Preview layer.conf, recipe, source/license inputs and kas composition; cancel creates nothing. Save/register, verify show-layers/show-appends, build and inspect the image manifest. Existing files must be preserved. | PLANNED |
| P06 | IDE/SDK bridge / Next | D02 CMake source; X07 SDK/eSDK | On a release supporting devtool ide-sdk, generate its SDK/project configuration for the fixture. Open it in a supported IDE/container context, change the greeting and build with the cross-toolchain. Verify source/sysroot mappings and artifact architecture. Debugging requires a matching image and target. | PLANNED |
| P07 | Image regression dashboard / Next | A03 rootfs/provenance; A04 manifest/snapshot comparison | Capture a successful image, add the test package and rebuild. Show added files/packages, package byte delta, recipe/inclusion evidence and available permission/owner changes. Remove it and repeat. Reject or clearly flag comparisons across incompatible machine/configuration baselines. | PLANNED |
| P08 | Buildstats and runtime performance / Next | U06 host cards; A02 timings; Artifacts buildstats | Enable buildstats, run a build and display measured task durations/timeline. Repeat in a container with known memory/CPU limits: show those limits separately from host figures. Overlapping task durations must not become a false wall-clock total; absent stats are unavailable. | PLANNED |
| P09 | Profile cloning, kas diff and multiconfig / Next | U03 JSON profile editing; K03 dump/lock | Clone a profile into a distinct build directory and compare resolved kas settings. With configured multiconfig, identify context in targets, environment captures and results. Jobs sharing a build directory remain serialized; variants keep separate history/evidence and configuration ownership. | PLANNED |
| P10 | Fetch diagnosis and offline preparation / Next | R03 fetch/audit; A01/A04 diagnosis | Use an isolated tiny-source recipe to induce a missing-URI and then a checksum failure. Show separate evidence and recommendations. Restore it, prepare source mirrors and run a network-disabled verification in the isolated profile. Report source readiness separately from full-build offline readiness. | PLANNED |
| P11 | Image CVE/SBOM review / Later | X12/X13 actual reports and artifact discovery | Import release-appropriate reports for two images, identify installed packages and new/changed issues, and record database date. Review an exception with owner/reason/expiry while retaining upstream status. Missing reports are unavailable; an unpatched finding alone is not proof of runtime exploitability. | PLANNED |
| P12 | Kernel and upgrade comparison / Later | X08 fragment/check output; X15 devtool upgrade; X06 versions | Change a kernel fragment and compare requested settings with final configuration/check output. Separately upgrade a test recipe/layer in a copied profile; compare selected version/appends/patches and parse/build results against the baseline. Preserve developer edits and original kas revisions. | PLANNED |
| P13 | Device console/deploy/test evidence / Later | X14 deployment; X10 testimage | On a dedicated test board or configured labgrid place, deploy a recorded artifact, capture serial/SSH logs and run a defined test. Link results to image hash/device/job. Disconnect it and show unavailable state. N/A without equipment; board flashing is never simulated as success. | PLANNED |
| P14 | Runtime capabilities and shutdown evidence / Foundation | U09 doctor; A04 preflight; S02 interruption | Compare profiles with and without optional task classes or terminal/device access. Disable unsupported actions with the observed prerequisite. Exercise kas interruption and retain client/container/server evidence separately; recovery remains unavailable while server shutdown is unconfirmed. | PLANNED |

The first batch should connect P01–P04, with P14 supporting capability checks and interruption evidence. Any implementation must preserve current backups, external-change conflict detection, build-directory ownership and clear host/runtime path labels. A shipped proposal should move into the relevant chapters with concrete steps and actual captures before its status is changed to an implemented acceptance case.
