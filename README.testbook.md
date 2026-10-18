# Bitloom manual testbook

This is an executable learning path and acceptance checklist, not a report of tests already performed. Run it yourself against your environment. All project text and evidence should remain in English. Record PASS, FAIL or N/A with the reason and a log/screenshot. Do not count an unavailable device, class or runtime as a successful test.

## Contents

0. [Guided tour — start here](#0-guided-tour--start-here): every feature on the two built workspaces, no long builds
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
13. [Developer acceptance](#13-developer-acceptance)
14. [Keyboard, web, compliance, Studio and teams](#14-keyboard-web-compliance-studio-and-teams)

New here? Follow chapter 0 first. For full acceptance, run chapters 1–5 first. Image builds, SDKs, security databases and hardware tests take substantially longer than UI/navigation tests. Chapter 11 is the command coverage ledger; it references fixtures and prerequisites from the preceding chapters.

## 0. Guided tour — start here

One path through every feature of the TUI and the web dashboard, in an order where each step builds on the previous one. It uses the two real kas workspaces that are already built on this machine, so no step runs a long build: the longest optional step takes about nine minutes, everything else seconds. Build times below were measured on these workspaces with a warm sstate cache.

Each step says **what to do** and **what you should see**. If you do not see it, note the step number: that is a bug.

### Before you start (5 minutes)

Two terminals in the repository, both with the project environment:

```bash
cd ~/…/yoctotui                      # the Bitloom checkout
source .venv/bin/activate             # fresh checkout: ./setup-demo.sh --dev --no-launch first
export PATH="$PWD/.venv/bin:$PATH"    # kas-container lives in the venv
bitloom --state .validation --service-stop   # only if a service from an older Bitloom is still running
```

The profiles file `.validation/profiles.json` already contains the two built workspaces:

| Profile | Release | Work directory |
| --- | --- | --- |
| `kas-scarthgap` | Scarthgap 5.0 LTS (poky) | `~/bitloom-kas-validation` |
| `kas-wrynose` | Wrynose 6.0 LTS (split repositories, sbom-cve-check enabled) | `~/bitloom-kas-wrynose` |

If the file is missing, recreate it without building: `python tools/prepare_validation.py --release both --work ~/bitloom-kas-validation --wrynose-work ~/bitloom-kas-wrynose`.

Terminal A, the TUI:

```bash
COLORTERM=truecolor bitloom --config .validation/profiles.json --state .validation
```

Terminal B, the web dashboard (same service, same history):

```bash
bitloom --web --config .validation/profiles.json --state .validation --port 9000
```

Open the printed `http://127.0.0.1:9000/#token=…` in a browser. Keep both side by side for the rest of the tour.

### Stage 1 — Find your way around (no builds, 5 minutes)

| # | Do | You should see |
| --- | --- | --- |
| 1.1 | TUI: press `?`, scroll, `Esc`. | The keyboard reference: global keys, every section's letters, nano keys for editors. |
| 1.2 | Press `1` … `9`, `0`, then `[` and `]`. | Each section opens; the rail marks it; the footer shows the section's own letters. |
| 1.3 | Press `P`, choose `kas-scarthgap`, then `P` again and `kas-wrynose`. | The top bar shows *scarthgap 5.0 LTS* then *wrynose 6.0 LTS* within a second. |
| 1.4 | Web: press `1` … `6`, then `?`. | The six views fade in; the help lists the web keys. |
| 1.5 | Web: `Ctrl+K`, type `scarth`, Enter; then `Ctrl+K`, `wry`, Enter. | The palette switches profile; the release chip changes. |
| 1.6 | TUI: `F7`, try *Linen* and *High Contrast*, `Esc`. | The palette previews live; `Esc` restores yours. |

### Stage 2 — Inspect the real workspace (no builds, 10 minutes, profile `kas-wrynose`)

| # | Do | You should see |
| --- | --- | --- |
| 2.1 | `2` Recipes. Type `busybox` in the search, Enter on the recipe. | About 1300 entries (layers, recipes, appends, classes, kas files only); the preview shows the recipe; Enter opens it read-only in the editor (`^X` closes). |
| 2.2 | `t` (tree), expand `meta`. | Layers with their recipes; no BitBake test fixtures, no CI YAML. |
| 2.3 | `3` Task logs, filter `do_compile`, open one. | Thousands of task logs; the log opens with search (`^W`). |
| 2.4 | `5` Caches, `s` (scan), then `w` (tmp/work). | Downloads: about 1000 files and 14 GiB, `.done` markers hidden and counted. tmp/work: about 60 GiB per recipe, largest first, with rm_work advice (≈7 s). |
| 2.5 | `6` Artifacts, then `m`, `s`, `i`. | Image matrix per MACHINE; SBOM quality (SPDX 3.0.1, 37 installed packages, PURL/licence 100%); rootfs inventory of the newest image. |
| 2.6 | `1` Builds, `c` (console builds). | Every BitBake run of this build directory, also those started outside Bitloom, each marked success, failed or interrupted. Enter opens one in Builds. |
| 2.7 | Web: `2` Recipes, `3` Task logs, `4` Image, `5` SBOM & CRA. | The same data in the browser; the SBOM gauges animate. |

### Stage 3 — First real jobs, followed in both interfaces (≈1 minute of builds)

| # | Do | You should see |
| --- | --- | --- |
| 3.1 | `9`, `o` (notifications): tick *success* and *failed*, set the minimum to `0`, `^O`. | Saved; from now on every job end raises a desktop notification (a Windows notification on WSL). |
| 3.2 | TUI: `t`, type `busybox`, Enter. | *Build target · busybox* queued and done in ≈10 s (nothing to rebuild); toast/notification *Completed*. The web history shows the same job at once. |
| 3.3 | `F2`, type `force`, choose *Force compile*, Enter (target `busybox`). | ≈45 s: live output, task count `N/M`, active BitBake tasks, ETA once enough tasks ran; the web progress bar is striped and moving. |
| 3.4 | When it ends: `1`, select it, `d` (compare). | Comparison with the previous force compile, if any; otherwise with the closest earlier run. Run 3.3 again and press `d`: durations and task counts side by side. |
| 3.5 | `e` (errors only), `/` search `busybox`, `x` (export), `i` (summary). | Filtered views of the same log; the export lands in `.validation/exports`. |
| 3.6 | Web: select the job, tabs *Summary*, *Sstate reuse*, *Warnings*, *Timings*, *Compare* (`u o w m d`). | Toaster-style reports computed from the log. |

### Stage 4 — Failures and their diagnosis (≈10 seconds; optional real story ≈9 minutes)

| # | Do | You should see |
| --- | --- | --- |
| 4.1 | `t`, type `no-such-recipe`, Enter. | Fails in ≈5 s; toast *Build failed*; the web raises the same failure toast. |
| 4.2 | `7` Analysis, type *Failure diagnosis*, `a`. | Category *metadata*, the root-cause lines (*Nothing PROVIDES*) and the next step. |
| 4.3 | `t`, type `a; id`, Enter. | Refused before queueing: *Not a BitBake target*. |
| 4.4 | Optional, Wrynose with sbom-cve-check: after 3.3, build `core-image-minimal` (`t`, Enter). | ≈4.5 min, then `do_sbom_cve_check` fails. `f` opens the failed task log; Analysis → *Failure diagnosis* says *stale SBOM* and gives the fix. |
| 4.5 | Optional fix: `F2`, *Custom command*, `bitbake core-image-minimal -C create_image_sbom_spdx`, Enter. | ≈3.5 min, success. `6`, `v` then shows the new CVE report. |

### Stage 5 — Stop, retry, detach (≈1 minute)

| # | Do | You should see |
| --- | --- | --- |
| 5.1 | Start the force compile again (3.3); while it runs press `s`. | The stop dialog: *Graceful stop* is disabled with the reason (kas runtimes expose no BitBake client to signal); *Let finish* leaves it running. |
| 5.2 | Choose *Force + recovery*. | The job's own container is stopped and the job ends *cancelled*; recovery offers `bitbake -c clean busybox` for the recipe that was running. Accept or skip it. |
| 5.3 | `r` (retry). | The same command queued again with its original profile. |
| 5.4 | While it runs: `Ctrl+Q`, then launch the TUI again (terminal A command). | The job kept running in the service; the TUI reconnects to it and its output. |
| 5.5 | Web: on a running job, hover *Graceful*, then press `s`. | *Graceful* is disabled with the same reason; `s` asks for confirmation and stops the job. |

### Stage 6 — Developer workbench (≈2 minutes of probes in the container)

`8` Developer. Choose the view with `v`, set the field, press `i` (Inspect). Each probe runs inside the kas container.

| # | View and input | You should see |
| --- | --- | --- |
| 6.1 | *Variable history*, recipe `busybox`, variable `SUMMARY`. | ≈8 s: every assignment of SUMMARY with file and line (`/work/openembedded-core/…`). |
| 6.2 | *Recipe context*. | ≈13 s: PN, PV, FILE, DL_DIR and the rest of the evaluated recipe. |
| 6.3 | *Runtime capabilities*. | ≈25 s: bitbake, devtool, runqemu… found or unavailable in the container. |
| 6.4 | *Image regressions*, field blank. | ≈20 s: the build target's installed packages and sizes from buildhistory. `c` captures a baseline; after a rebuild `d` compares. |
| 6.5 | *Build performance*. | The slowest tasks of the latest real build (sbom-cve-check database fetches first). |
| 6.6 | *Kernel fragments* with the field blank. | A clear message asking for a `.cfg` path (no traceback). |
| 6.7 | *Runtime browser*, Enter on `build`, then on a file. | Directory listing inside the container; files open in the runtime editor. |

### Stage 7 — Studio: your own layer and recipe (≈1 minute of build)

| # | Do | You should see |
| --- | --- | --- |
| 7.1 | `2`, `c` (Studio), choose *Application recipe*. Layer *new layer…* `meta-tour`, name `tour-hello`, build system `make`. | The preview lists every file: layer.conf, licence, Makefile, `tour-hello_1.0.bb`. |
| 7.2 | `^O` (create, use for this profile). | Files written; `kas-studio-meta-tour.yml` appended to the profile's kas files; target set to `tour-hello`. |
| 7.3 | `b`. | ≈45 s on Wrynose (≈75 s on Scarthgap): the recipe builds; the new layer appears in Recipes. |
| 7.4 | Web: `6` Studio, *Distribution*. | Live preview of `conf/distro/acme.conf`; nothing is written until *Create files*. |
| 7.5 | Clean up when done: `F4`, remove `:kas-studio-meta-tour.yml` from `kas_file`, `^O`; delete `meta-tour/` and the overlay. | The profile builds the plain image again. |

### Stage 8 — SBOM, CVE and CRA (no builds)

| # | Do | You should see |
| --- | --- | --- |
| 8.1 | `6`, `v`. | ≈1800 unpatched of ≈21500 assessed, critical first; detail with CVSS vector and link. |
| 8.2 | `/` type `openssl`; `r` on a row: owner, reason, expiry `^O`. | Filtered list; the review appears in the *Review* column. |
| 8.3 | `x`, choose *Markdown report*; repeat with *HTML*, *SARIF*. | Files in `.validation/exports`: the Markdown links every CVE to NVD, CVE.org and OSV; open the HTML in a browser and print it to PDF. |
| 8.4 | `9`, `c` (CRA readiness). | Every check from real evidence; *Unpatched vulnerabilities* warns; dispositions now count your review. |
| 8.5 | `9`, `s` (SBOM settings). Move through the options; `Esc` (do not apply). | Each option explains itself; *Generate SPDX SBOMs* shows *on (default)* on Wrynose; on `kas-scarthgap` the Wrynose-only options show *n/a*. |
| 8.6 | `P` → `kas-scarthgap`, `F2`, type `sbom-cve`. | *(not in this release)* with the Scarthgap alternative (cve-check). |
| 8.7 | Web: `5`, Export menu → *Markdown report*. | The same report downloads. |

### Stage 8b — The image, file by file, and what each release can do (no builds)

| # | Do | You should see |
| --- | --- | --- |
| 8b.1 | Web on `kas-wrynose`: `4` (Image). | *core-image-minimal · qemux86-64* from its `tar.bz2`: ≈29 MiB on the device, ≈370 files, ≈34 packages; biggest package the kernel image (≈13 MiB), then `libcrypto3 · openssl`, `libc6 · glibc`; biggest folders `/boot`, `/usr`, `/lib`. |
| 8b.2 | Open `etc`, select `motd`. | `base-files 3.0.14`, layer *meta · upstream*, in *core-image-minimal (pulled in by packagegroup-core-boot)*, the existing appends in meta-poky and meta-selftest, the text of the file, and the advice to add a `base-files_%.bbappend` to your layer. |
| 8b.3 | *Change it with an append*. `Esc` at the end without creating. | Studio opens a *Recipe append* already filled in: `base-files`, `recipes-core`, file `motd`; the planned `files/motd` holds the current device text (toast *Starting from the device's file*). |
| 8b.4 | Type `libc6` in *Which recipe installs…*, Enter; then select `/etc/passwd`. | `libc6` is the renamed `glibc` package, pulled in by busybox, eudev, kmod…; `/etc/passwd` is in no package, with the explanation (useradd, `EXTRA_USERS_PARAMS`). |
| 8b.4b | Image: *Services*. Select `syslog`. Then `bitloom --config .validation/profiles.json --state .validation --services`. | *sysvinit · 20 started at boot*; init scripts in boot order (`banner.sh S02`, `sysfs.sh S02`, `mountall.sh S03`, `udev S04`…), then shutdown (`halt`, `reboot`) and helpers; udev rules from eudev with `80-net-name-slot.rules` *disabled in /etc*. `syslog` opens `/etc/init.d/syslog` (owner root, `busybox-syslog · busybox`). The CLI prints the same list. |
| 8b.4c | Demo (`bitloom --web --demo`), profile `demo-wrynose`: Image → *Device tree*; select `spi@50000`; search `serial`, `Enter`. Then `bitloom --demo --devicetree demo-board.dtb --format dts`. On `kas-wrynose` (qemux86-64): *Device tree*. | The demo board: model *Demo sample board*, 11 enabled and 3 disabled devices; `spi@50000` scrolls the DTS to its node; *1 of 4* matches. The CLI prints DTS starting with `/dts-v1/;`. On qemux86-64: *No device tree deployed* with the reason (x86 machines have none). |
| 8b.4d | Image → *Insights* on `kas-wrynose`, both themes (OS setting). Hover *linux-yocto*; select *openssl*. Then `bitloom --config .validation/profiles.json --state .validation --insights --format json`. | Tiles (≈29 MiB, ≈370 files, 37 packages, 20 started at boot, 0 ports, 3 setuid); one layer bar (*meta* 99%); kinds led by *Kernel and modules*; licences sorted by packages (GPL-2.0-only first); *update-alternatives-opkg* needed by 7; *Nothing listens on the network*; *root password: locked*; 3 setuid files (`busybox.suid`, `halt.sysvinit`, `shutdown.sysvinit`). The tooltip reads *linux-yocto · 13.7 MiB · 47% · 5 files*; *openssl* opens Files with its packages. The JSON has the same numbers. |
| 8b.5 | TUI: `7`, choose *Which recipe installs…*, type `/etc/inittab`, `a`. Then in a shell: `bitloom --config .validation/profiles.json --state .validation --who-installs /etc/inittab`. | Both answer `sysvinit-inittab`, its recipe file, layer, image, and *add recipes-core/sysvinit-inittab/sysvinit-inittab_%.bbappend to your layer*. |
| 8b.6 | Web `8`: *What this release can do*, on `kas-wrynose` then `kas-scarthgap`. | Wrynose: ✔ SPDX 3.0, sbom-cve-check, VEX, configuration fragments; ✖ cve-check (*use sbom-cve-check*), bitbake-setup (*not set up with bitbake-setup*). Scarthgap: ✔ SPDX 2.2, cve-check, debug-tweaks; ✖ VEX (*vex.bbclass is not in this project's layers*), fragments (*bitbake-config-build is not in this project's BitBake*). |
| 8b.7 | On `kas-scarthgap`: `q`, *Generate VEX metadata*, target `busybox`. | Refused before queueing, with the same reason; nothing enters the history. |

### Stage 8c — Best practices (no builds)

| # | Do | You should see |
| --- | --- | --- |
| 8c.1 | Web on `kas-wrynose`: `7` (Practices). | A score around 80 %, *Needs attention* grouped by area; *LAYERSERIES_COMPAT includes the release you build* fails on `meta-acme/conf/layer.conf` (*scarthgap*, the project builds wrynose) if the Studio test layer is still there; upstream layers are not judged. |
| 8c.2 | *All rules*: switch off *Each layer has a SECURITY.md*, set *rm_work keeps tmp/work small* to *error*. | The rule moves to *Switched off*, the score changes; `bitloom-practices.json` at the project root holds `"disabled": ["layer-security-policy"]` and the severity. |
| 8c.3 | *Add a company rule*. *Next* without choosing; then the example *Products build our distribution*; open the **?** of each field; *Try it on this project*. | The wizard refuses to go on without a kind of check. The example fills step 2; the plain-words line reads *An error unless DISTRO is exactly acme…*; *Try it* reports `DISTRO is “poky”, expected “acme”` (the `acme.conf` in meta-acme does not count: the build selects poky). Nothing is saved yet. |
| 8c.3b | Step 3: the id follows the title; *Save rule*. Then add a rule with id `layer-name`, and one with pattern `(`. | The rule appears under *Company*. The others are refused (*already used*, *not a valid regular expression*). |
| 8c.4 | *Export* → Markdown. In a shell: `bitloom --config .validation/profiles.json --practices --profile kas-wrynose; echo "exit $?"`, then with `--fail-on never`. | The report downloads; the CLI prints the same review and exits 2 with errors, 0 with `--fail-on never`. |
| 8c.5 | Delete the rule and the file (`rm bitloom-practices.json`). | The defaults are back. |

### Stage 8d — Your own keys (no builds)

| # | Do | You should see |
| --- | --- | --- |
| 8d.1 | TUI: `0`, `c`. Enter on *Builds · Stop*, press `S`. Enter on *Retry*, press `e`; then `1`. | *✔ Stop: S · saved*; `e` refused (*already does “Errors”*), `1` refused (*reserved*). The table marks `S *`. |
| 8d.2 | `Esc`, `Ctrl+Q`, start `bitloom` again; `1`, then `S` on a running job; `?`. Then `bitloom --keys`. | `S` stops the job; the Stop button and `?` show `S`; `--keys` lists `S (default s)`. |
| 8d.3 | Edit `~/.config/bitloom/keys.json` to `{"builds": {"Stop": "j"}}`, start `bitloom`. Then `0`, `c`, `R`. | A warning at start (*reserved*), default keys kept; `R` restores every default and removes the file. |

### Stage 8e — BitBake assistant (no builds)

| # | Do | You should see |
| --- | --- | --- |
| 8e.1 | Web on `kas-wrynose`: `6` Studio → *Image*, switch on *edit before creating*, click at the end of the file. Type `IMAGE_FEA`; `↓`; `Enter`. Then a new line `inherit sys`, `Ctrl+Space`. | Suggestions under the cursor with V badges and *FEA* in bold; the documentation of the selected one below the list; Enter inserts `EXTRA_IMAGE_FEATURES`. `inherit sys` offers `syslinux`, `systemd`…, each a C (class). |
| 8e.2 | Type `IMAGE_INSTALL:append = "htop"`, a new line `DEPENDS_append = " zlib"`, a new line `EXTRA_IMAGE_FEATURES = "debug-tweak"`. Click a problem. | Below the editor: ▲ *adds no space* with the fix, ✖ *old override syntax*, ▲ *not an image feature of this release* (on Scarthgap: *did you mean “debug-tweaks”?*); the line numbers turn red/yellow; clicking selects the line. |
| 8e.3 | TUI: `2`, open a recipe with `o` from your layer (or `n` *New file* with a `.bb` path); type `inherit sys`, `Ctrl+Space`, `Enter`; move onto a variable, `Alt+D`. | A list of classes; Enter inserts `systemd`; the line under the editor lists problems or *✔ no problems found*; Alt+D shows the variable's documentation. |
| 8e.4 | `bitloom --config .validation/profiles.json --lint meta-acme; echo $?`; then on a folder with a `DEPENDS_append`; `bitloom --config .validation/profiles.json --explain IMAGE_INSTAL; echo $?` | Clean layer: exit 0; with the error: the file:line, the fix and exit 2. `--explain` suggests `IMAGE_INSTALL` and exits 1. |

### Stage 8f — Migrate Scarthgap → Wrynose (no builds; a build at the end is optional)

| # | Do | You should see |
| --- | --- | --- |
| 8f.1 | Web on `kas-scarthgap`: `9`. | *scarthgap 5.0 LTS → wrynose 6.0 LTS*; the path 5.1 → 5.2 → 5.3 → 6.0 with the guides linked; *2 break the build* (the poky repository in `tests/integration/kas-minimal.yml`, `LAYERSERIES_COMPAT_acme`) and *1 with a safe fix* (when the Studio test layer meta-acme is still there). |
| 8f.2 | *Preview the selected fixes*, *Apply*; then *Undo*. | The diff `LAYERSERIES_COMPAT_acme = "scarthgap"` → `"wrynose"`; after Apply the count drops; Undo restores the file (check `meta-acme/conf/layer.conf`). |
| 8f.3 | Step 3: read the diff; *Write kas-minimal-wrynose.yml and the profile*. | The new file next to `kas-minimal.yml` with bitbake, openembedded-core and meta-yocto at yocto-6.0.2 (the same as `kas-wrynose.yml`); the profile `kas-scarthgap-wrynose` with `KAS_WORK_DIR` `…/bitloom-kas-validation-wrynose`; the old file and profile unchanged. |
| 8f.4 | Optional (≈30 min, downloads): step 4, *Switch*, *Parse metadata*, *Build the image*. | The new profile parses and builds core-image-minimal on Wrynose in its own work directory; `kas-scarthgap` still builds as before. Remove the profile and `tests/integration/kas-minimal-wrynose.yml` afterwards. |
| 8f.5 | On `kas-wrynose`: `9`. TUI on `kas-scarthgap`: `7`, *Migration check*, `a`. CLI: `bitloom --config .validation/profiles.json --migrate --to wrynose; echo $?` | Wrynose: *on the newest release Bitloom covers*. TUI and CLI: the same report as the web; exit 2 while something breaks the build. |

### Stage 8g — Add a layer (network; nothing is built)

| # | Do | You should see |
| --- | --- | --- |
| 8g.1 | Web on `kas-wrynose`: `2`, *+ Add*, type `virtual`, choose *meta-virtualization*. | openembedded-core *already in the project*; meta-oe, meta-python, meta-networking, meta-filesystems and meta-virtualization to add, each *✔ wrynose*; the diff adds `meta-openembedded` (four layers) and `meta-virtualization` to `tests/integration/kas-wrynose.yml`. Do not press *Add* (or press it and use *Migrate → Undo*). |
| 8g.2 | Mirror `https://git.example.invalid/m`. | The URLs change to the mirror; the branch checks fail (*no wrynose branch* or *not checked*) and *Add* is disabled with the reason. |
| 8g.3 | *From a Git URL*: `https://git.yoctoproject.org/meta-security`, branch `nonexistent`, *Check*. | *✖ no nonexistent branch*; *Add* disabled. |
| 8g.4 | `bitloom --config .validation/profiles.json --add-layer meta-virtualization` (active profile kas-scarthgap). | The same plan on Scarthgap (branch scarthgap) and the kas diff; nothing written without `--apply`. |

### Stage 9 — Projects, setup and notifications (no builds)

| # | Do | You should see |
| --- | --- | --- |
| 9.1 | `9`, `w` (projects). | Recent projects; the active one marked *active*. |
| 9.2 | `o`, Enter on the project folder (the Bitloom checkout). Then `o` again with `~/bitloom-kas-wrynose`. | The checkout: kas proposals for `kas-minimal.yml` and `kas-wrynose.yml` with evidence. The work directory: only a host proposal, marked as the kas work directory of `kas-wrynose` with a warning to switch with `P` instead. `Esc` without saving. Web: `8` → *Set up a project* shows the same. |
| 9.3b | Web `8` → *New project*: release Scarthgap, open *Set up with*; then Wrynose, *bitbake-setup*, MACHINE `qemuarm64`, folder `~/bitloom-bbsetup-try`, runtime *container*, *Create project*. | Scarthgap: *bitbake-setup: not available for this release (BitBake 2.16+)*. Wrynose: the machine list becomes the template's five machines, the preview shows the `bitbake-setup … init --non-interactive … poky-wrynose poky machine/qemuarm64 distro/poky` command. Create: a job in Builds (≈30 s with network) ending with *setup ready*; the profile `my-product` (container, kas image) becomes active; `bitbake-getvar MACHINE` via *Resolve one BitBake variable* answers `qemuarm64`. Remove the folder and the profile afterwards. |
| 9.3 | `n` (new project). | Release, MACHINE, image and runtime fields with a live preview; `Esc` without creating. |
| 9.4 | `9`, `o`, `^T`. | A test notification arrives. |

### Stage 10 — Web extras (no builds)

| # | Do | You should see |
| --- | --- | --- |
| 10.1 | The bell button, allow notifications; switch to another tab and run a short build from the TUI. | A browser notification when it ends. |
| 10.2 | Narrow the window to phone width (or the browser's device mode). | One column; the navigation becomes a scrolling bar; nothing scrolls sideways. |
| 10.3 | Switch the operating system to light theme. | The dashboard follows it. |

### Stage 10b — Themes (no builds)

| # | Do | You should see |
| --- | --- | --- |
| 10b.1 | Web: the round button in the top bar; pick *Nord*, *Catppuccin Latte*, *High contrast*; reload the page. | The whole dashboard changes at once, menu and toasts included; after the reload the last choice is applied without a flash of the default. Image → *Insights* stays readable in each. |
| 10b.2 | Ctrl+K, type `theme`, pick *Theme: System*. | Back to the operating system's light or dark. |
| 10b.3 | TUI: `F7`, preview *Catppuccin Latte* and *Solarized Light*, `^O`. | Both light palettes apply live; saved for the next start. |

### Stage 11 — Command line and CI (≈30 seconds)

```bash
bitloom --state .validation --service-stop        # after closing the TUI and the web server
bitloom --config .validation/profiles.json --state .validation --ci build:busybox --profile kas-wrynose \
  --junit /tmp/results.xml --summary /tmp/summary.json        # ≈10 s, PASS line, JUnit and JSON written
bitloom --config .validation/profiles.json --state .validation --vulns --min-cvss 9 --fail-on-unpatched; echo "exit $?"   # exit 2
bitloom --config .validation/profiles.json --state .validation --vulns --format md -o /tmp/vulns.md
bitloom --config .validation/profiles.json --cra; bitloom --config .validation/profiles.json --doctor --network
```

`--ci` runs its own serial queue on the state directory, so first close the web server (`Ctrl+C`) and the TUI (`Ctrl+Q`) and stop the idle service: `bitloom --state .validation --service-stop`. The other commands only read and work at any time.

### Stage 11b — Build server (≈1 minute, systemd user session)

| # | Do | You should see |
| --- | --- | --- |
| 11b.1 | Close the TUI and the web server. `bitloom --state /tmp/bl-svc --config /tmp/bl-svc.json --service-install --web --port 18765 --service-name bitloom-try` | Two units written and started, the dashboard URL with its token, the `loginctl enable-linger` hint when lingering is off. |
| 11b.2 | Open the URL. `systemctl --user restart bitloom-try-web`, reload the page. `bitloom --state /tmp/bl-svc --service-status --service-name bitloom-try` | The dashboard works with the same URL after the restart; status shows both units *active · enabled* and the service JSON. |
| 11b.3 | `bitloom --service-uninstall --service-name bitloom-try` | *stopped, disabled and removed …*; `~/.config/systemd/user` has no `bitloom-try` units. |

### Stage 12 — Finish

If they are still open, close the web server with `Ctrl+C` and the TUI with `Ctrl+Q`, then `bitloom --state .validation --service-stop`. Builds already done stay in the work directories; nothing else needs cleaning except the Studio files of step 7.5.

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

Press `P`: the switcher lists `demo`, `demo-scarthgap` and `demo-wrynose`. Select each: the top bar shows *release unknown*, *scarthgap 5.0 LTS* and *wrynose 6.0 LTS* respectively. The workspaces live in `.bitloom/demo`, `.bitloom/demo-scarthgap` and `.bitloom/demo-wrynose`; every SBOM/CVE sample names itself a demo sample.

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

F4 provides both a JSON editor and Clone. Clone chooses a unique name and distinct absolute build directory; it preserves the original profile. Developer also provides Clone through F10.

Expected: kas-integration profile, kas-container runtime, qemux86-64/poky. The helper preserves history and takes KAS_WORK_DIR from the recorded result. With Docker Snap the daemon's /tmp can differ from host /tmp. Use runtime file operations with `/work/build`; an empty host directory does not prove the container build is missing.

Use this path for read-only inspection or routine rebuilds. A saved result does not prove the temporary work mount still exists: use F10 Runtime browser to check `/work/build`. If it was removed, use K02 or K04 for a fresh workspace. Use an isolated profile for tests that change configuration, devtool state or caches.

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

Before the first checkout, open F10 → Runtime capabilities → Prepare new kas workspace → Run. This prepares the dedicated empty container work directory if its daemon-side ownership differs. For Podman change KAS_CONTAINER_ENGINE and use podman info. This dedicated workspace may require a cold build. Existing edits to the base integration YAML are included; record its Git diff before testing.

### K03 — Checkout and validate configuration

F2 → Checkout kas repositories; then Dump resolved kas configuration. Expected: checked-out pinned Poky revision and the merged machine/distro/target. In Analysis run Build preflight on `/work/build`; missing build configuration before the first build is a prerequisite finding, not a fake PASS. Build busybox, then core-image-minimal to populate pkgdata, artifacts and reports needed below. Run Generate kas lock file and inspect its actual output; kas release support determines the result.

### K04 — Automated real Developer fixture setup

For a new isolated real workspace, after installing the official wrapper above:

```bash
python tools/validate_developer.py --build
COLORTERM=truecolor bitloom --config .developer-validation/profiles.json \
  --state .developer-validation/manual
```

Docker is the default. `--engine podman` selects Podman; `--work /absolute/new/workspace` selects another work mount. `--image` additionally builds core-image-minimal with the generated package. The helper probes actual metadata, creates a uniquely named local layer/YAML, builds a small data-only CLOSED recipe, prepares sources, verifies fetch and recipe build with BB_NO_NETWORK, introduces/restores a controlled do_install failure, and saves result.json plus actual logs. The fixture deliberately keeps the initial build smaller than the complete image; TUI templates are separate MIT-licensed source examples. Repeating retains older evidence and creates new unique overlays/layers.

Expected: every successful operation has a log/exit result. Missing image/buildhistory artifacts before `--image` remain unavailable. In F10 set recipe to `bitloom-validation-hello`, inspect Recipe context and SUMMARY, browse `/work`, then create your own fixture for chapter 13. Use a new state directory for manual work so automated history remains separate. This can take several minutes and download/build native dependencies on a cold workspace.

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

Force + recovery must show observed active recipes and only offer recovery when shutdown is confirmed. Owned kas-container jobs record the exact container stop result before recovery. With native kas wrappers/external servers verify remaining work before manually cleaning; termination of the wrapper is not proof that BitBake stopped. Recovery uses recipe clean, not editing .bb files. An observed active recipe is not proof of corruption. Rebuild afterward and preserve interruption logs.

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
| CMD070 / `sbom-cve-recipe` | Recipe CVE analysis from its SBOM (sbom-cve-check) | target=busybox | V01 on kas-wrynose | Wrynose: report in DEPLOY_DIR_IMAGE. Scarthgap: refused, naming the cve-check alternative. | TODO |
| CMD071 / `recipe-sbom` | Create recipe SBOM (SPDX 3) | target=busybox | V01 on kas-wrynose | Recipe SBOM task runs on Wrynose; refused on Scarthgap. | TODO |
| CMD072 / `vex` | Generate VEX metadata | target=busybox | V03 (vex class enabled) | do_generate_vex runs when the class is inherited; otherwise the probe explains it is unavailable. | TODO |
| CMD073 / `sbom-cve-enable` | Enable sbom-cve-check for image builds | none | V03 on kas-wrynose | bitbake-config-build enables the fragment; the next image build writes sbom-cve-check reports. | TODO |
| CMD074 / `sbom-cve-disable` | Disable sbom-cve-check fragment | none | after CMD073 | The fragment is disabled again. | TODO |
| CMD075 / `fragments` | List configuration fragments | none | kas-wrynose | bitbake-config-build lists the fragments and the enabled ones. On kas-scarthgap: refused, "bitbake-config-build is not in this project's BitBake". | TODO |
| CMD076 / `fragment-enable` | Enable a configuration fragment | fragment=core/yocto/sstate-mirror-cdn | kas-wrynose | OE_FRAGMENTS in build/conf/toolcfg.conf gains the fragment; `rm -rf` as fragment is refused before queueing. | TODO |
| CMD077 / `fragment-disable` | Disable a configuration fragment | fragment=core/yocto/sstate-mirror-cdn | after CMD076 | The fragment is removed from OE_FRAGMENTS. | TODO |
| CMD078 / `setup-status` | bitbake-setup: compare with upstream | none | a bitbake-setup workspace (see the guided setup case) | Shows the differences with the template; on a kas profile refused with "not set up with bitbake-setup"; on Scarthgap refused because its BitBake has no bitbake-setup. | TODO |
| CMD079 / `setup-update` | bitbake-setup: update layers and configuration | none | a bitbake-setup workspace | Interactive: updates the layer checkouts and asks before changing the build configuration. | TODO |
| CMD080 / `kernel-savedefconfig` | Save kernel defconfig | none | a profile with a kernel built (for example after building core-image-minimal) | `${B}/defconfig` appears in the kernel's build folder; on a runtime without the task the action is refused with the probed reason. | TODO |
| CMD081 / `uboot-menuconfig` | U-Boot menuconfig | none | a machine with a bootloader (for example `qemuarm64` with u-boot; qemux86-64 has none) | Interactive menuconfig of virtual/bootloader in a terminal; on qemux86-64 refused before running (no do_menuconfig for the bootloader). | TODO |
| CMD082 / `uboot-diffconfig` | Export U-Boot config changes | none | after CMD081 | `fragment.cfg` with the changes in the bootloader's work folder. | TODO |

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

## 13. Developer acceptance

All fourteen researched workflows are implemented in **F10 Developer**, across sixteen views. This chapter is a manual checklist; implementation does not imply you have already tested the feature. Record PASS/FAIL/N/A with evidence for each case. The [Developer guide](https://padovanl.github.io/bitloom/developer.html) gives exact field meanings and limits; the [research map](https://padovanl.github.io/bitloom/roadmap.html) retains sources. No hardware/SDK/security report is fabricated to fill a missing prerequisite.

### Shared procedure

Use K02 or K04, keep the queue idle while inspecting, and record the selected profile. F10 opens Developer; Tab selects controls, arrows select rows, Enter/Open follows a runtime path. The first field changes meaning with the view; read its placeholder. Capture writes a timestamped private JSON export and fills the baseline input once. After a change/build, Inspect again and Compare; later Capture preserves the original baseline. Choose another JSON path to change it. Save the comparison export as evidence.

| Case | View or control | Required fixture | Manual result |
| --- | --- | --- | --- |
| P01 | Variable history | Parsed recipe plus matching append | TODO |
| P02 | Recipe context + Runtime browser | Real runtime layer | TODO |
| P03 | Rebuild evidence | Before/after signatures | TODO |
| P04 | Failure investigation | Controlled failed task | TODO |
| P05 | New layer | Writable new runtime destination | TODO |
| P06 | IDE / SDK bridge | Supported release/build system and SDK | TODO or N/A with reason |
| P07 | Image regressions | Two actual images with buildhistory/pkgdata | TODO |
| P08 | Build performance | Actual buildstats; cgroup-v2 if applicable | TODO |
| P09 | Clone + Resolved kas / multiconfig | Independent profile; optional multiconfig | TODO |
| P10 | Downloads / offline | Local source fixture and populated downloads | TODO |
| P11 | CVE / SBOM review | Actual supported JSON reports | TODO or N/A with reason |
| P12 | Kernel fragments + Upgrade baseline | Kernel .config/fragment; upgrade fixture | TODO or N/A with reason |
| P13 | Board laboratory | Dedicated real SSH/serial/labgrid equipment | TODO or N/A with reason |
| P14 | Runtime capabilities + Shutdown evidence | Optional task probes; stoppable owned job | TODO |

### P01 — Follow a variable to its source

Set the Developer recipe to your fixture (`bitloom-hello` after P05, or chapter 5's recipe). Select Variable history, first field `SUMMARY`, Inspect. Select assignment-origin rows: Enter opens the actual runtime file at its line. Capture. In a matching append add `SUMMARY:append = " (experiment)"`, Inspect again and verify the final value and both origins. Query PACKAGECONFIG and OVERRIDES to inspect override context; an inactive override must not be presented as winning. Edit the origin externally while idle, wait for STALE (up to fifteen seconds), and verify Capture/Compare requires a fresh Inspect. Restore your append after recording evidence. Clear the recipe for a global variable; with configured multiconfig, repeat using `mc:debug:RECIPE` and verify that datastore identity is preserved.

### P02 — Navigate real runtime files

Choose Recipe context for the fixture, Inspect, and inspect FILE/PV/appends/S/B/T/sysroots. Select S and Enter: Runtime browser opens the evaluated directory. Arrow/Enter through source files; open a file, save a greeting change with backup, then close and Inspect. Enter `/work/meta-bitloom-dev` in the browser's first field and `.bb` in its second field for a bounded recursive filename search. Create a file through Analysis/New file or chapter 5, refresh and verify it appears; delete your own test file externally, refresh and verify it disappears. Symlinks are labelled; edits through symlinks are refused. Repeat at 80×24 and 60×20: controls scroll, table/report remain reachable and return after resizing.

### P03 — Investigate a rebuild

Build your fixture, choose Rebuild evidence and Run Dump signatures. When the queue finishes, Inspect and Capture. Edit its installed greeting/source, build again and dump signatures again. Inspect, open a signature row, and save actual diffsigs/printdiff evidence. Compare the capture. Potential dependency paths are labelled as evidence, not promised rebuild totals. Repeat without changing metadata: record the real result, which may reuse tasks and may still retain the last available historical signature pair. If paired sigdata is absent, record incomplete evidence rather than claiming no change or an invented cache-miss cause.

### P04 — Connect the failed task, script and log

Use A01's deliberate `bbfatal` or create a matching append containing `do_install:append() { bbfatal "Bitloom controlled task failure"; }`. Force install and verify a genuinely failed history row. Select it in Builds, F10 → Failure investigation, leave the first field blank and Inspect. Open log.do_install and run.do_install rows; read the diagnostic context and Capture. Switch the active profile and inspect that selected old failure again: it must keep the original job/profile. Restore the append and rebuild successfully. The historical failure stays failed, and its captured evidence stays attached to that original job. Use an explicit runtime log path for a standalone investigation.

### P05 — Create and register a licensed fixture from the TUI

F10 → New layer. Enter `/work/meta-bitloom-dev`, `bitloom-hello`, collection `bitloomdev`, your copyright owner, series `scarthgap`, new host YAML `kas-bitloom-dev.yml`, and CMake. Preview: check layer.conf, MIT text/checksum, main.c, CMakeLists.txt, recipe and kas registration. Cancel first and verify nothing was created. Repeat Preview → Create + register. A new derived profile selects the new overlay; original YAML/profile remain intact. F2 → Show configured layers, Show recipe appends and Build target `bitloom-hello`: successful parsing/build verifies registration. Build core-image-minimal and inspect its manifest for the package. Runtime browser → files/source/main.c → edit greeting → save → rebuild recipe/image. Existing destinations must be refused. Repeat with unique layer/name/YAML for Meson, Make, Python and Rust; inspect each complete source/license and build it on a release with the corresponding class/toolchain. SDK/compiler dependencies can make these real builds slow.

### P06 — IDE source iteration

Choose IDE / SDK bridge for the CMake fixture, first field `core-image-minimal`, Inspect. Record S/B/compiler/sysroots/architecture and actual ide-sdk help. Configure F4 source_mappings only if the runtime source is truly host-visible. Run Export IDE mappings/database; inspect the export and mapped compile_commands.json if available, including -I/sysroot arguments. Generate IDE SDK queues release-native devtool ide-sdk after the probe. In the supported IDE/container context, change and build the greeting with the generated cross-toolchain; verify binary architecture and deployed image/debug symbols match. An unavailable IDE command, missing compile database or inaccessible Docker-private source is a prerequisite finding. Mark the interactive SDK/debug portion N/A until its requirements are supplied.

### P07 — Compare images and trace a package

In an isolated kas overlay enable `INHERIT += "buildhistory"` and build the image. F10 → Image regressions, recipe `core-image-minimal`, Inspect → Capture. Record that package sizes identify their source (exact pkgdata bytes or normalized buildhistory KiB). Add your fixture with IMAGE_INSTALL, rebuild the same image/machine/distro/libc/multiconfig, Inspect → Compare. Expect an added package with recipe owner, installed file additions and byte deltas. Select that package → Trace selected package inclusion → Run. Change a fixture-installed file mode, rebuild and compare against a new deliberate baseline; record permission/owner/link differences from buildhistory. A different-machine/image baseline must be rejected. Missing buildhistory is unavailable, not an empty successful comparison.

### P08 — Find measured bottlenecks

Enable buildstats in your test configuration, run a real build, then Build performance → Inspect with a blank first field for the latest session. Record slow tasks, timeline, measured task span and runtime cgroup/pressure/disk evidence. Capture, repeat a comparable build and Compare durations. Parallel durations must not be added to claim elapsed wall time. To test limits, configure a dedicated container with known cgroup-v2 CPU/memory limits and verify them separately from the host cards. Unavailable pressure/cgroup-v1 files or absent buildstats must be labelled. The probe measures its current runtime; it does not reconstruct old container usage.

### P09 — Clone profiles and inspect multiconfig

F10 → Clone (also F4 → Clone). Choose a unique name and a separate absolute build directory, for example `/tmp/bitloom-debug-work/build`. For kas verify KAS_WORK_DIR still points to the original source workspace and KAS_BUILD_DIR is the new absolute directory; local layers remain available and the external build mount appears as /build. Select Resolved kas / multiconfig → Inspect → Capture; change a copied composition, re-inspect and Compare the real merged dump. Check the resolved machine/distro: profile hints do not rewrite a base YAML. Run Generate kas lock and inspect the release-native result. With actual BBMULTICONFIG configured, query `mc:debug:RECIPE` in Variable history and Recipe context and build the target through F2. Capture the context. Different profiles keep original job identity; one build directory cannot be owned by two cooperating builders, and the current service queue remains serial. Preserve the original profile/settings.

### P10 — Diagnose downloads and verify offline readiness

Choose Downloads / offline, recipe your fixture, Inspect. Record mirror/cache/network variables and URI DNS observations. Induce a missing URI and separately a bad checksum in an isolated tiny source recipe (save its original metadata first); fetch and inspect the failed log through the first field or selected log. Expect distinct evidence categories; restore each change. Run Prepare source mirrors and wait for success; Run Verify fetch offline and separately Verify full build offline. Each job must record the actual result with BB_NO_NETWORK in its temporary BitBake configuration. A successful fetch check is not a claim that kas bootstrap or the full build needs no network. Restore the recipe and save original logs.

### P11 — Review actual CVE/SPDX evidence

Run supported CVE/SPDX actions after Runtime capabilities identifies their tasks. Locate the real JSON report with Runtime browser. In CVE / SBOM review enter its absolute runtime path, Inspect → Capture. Record package/version/license, upstream issue status and available report/database dates. Build/import a second actual report and Compare for new/changed statuses. Select an issue → Record selected issue review → Run; enter owner/reason/future YYYY-MM-DD expiry. Inspect again: original status is retained and the separate review appears. Missing/unsupported reports must be unavailable; a review is not a patch or proof of non-exploitability. Expired saved reviews must be visibly labelled. Record N/A without suitable reports/configuration.

### P12 — Check kernel fragments and recipe upgrades

For a kernel fixture, use Kernel fragments with recipe `virtual/kernel`, first field the fragment and second field final .config (or blank for evaluated B/.config). Inspect requested enabled/disabled values against actual values. Run Kernel config check, Export kernel diff and Menuconfig where actual listtasks supports them. Record mismatches and release tool results; no automatic fix is implied. Separately clone the profile, choose Upgrade baseline for a small recipe, Inspect → Capture before change; perform a controlled version/revision or devtool upgrade, parse/build, re-inspect and Compare. Versions may change while machine/distro/libc/multiconfig must remain compatible. Check active appends, patches, layer commits and dirty status; retain original kas pins and source edits. Mark unavailable kernel/upgrade operations N/A with prerequisites.

### P13 — Use a real board and retain evidence

F10 → Devices; configure actual SSH/serial or labgrid equipment using the Developer guide schema. Board laboratory → Inspect; Enter selects a device. Run Device status and verify actual output; disconnect it and record the failed/unavailable result. Export the artifact to a local path (Analysis Export runtime artifact), put that path in the second field, and use a real devtool workspace recipe for Deploy recipe. Inspect the evidence JSON: hash/device/job/result are recorded; deploy transfers recipe outputs and must not claim that the referenced image was flashed. Run your explicit test_argv and verify its actual exit code/log. Console uses the real terminal and records transcript/exit status. For labgrid, verify show/acquire/release and use power cycle only on your dedicated place. N/A without actual equipment; there is no simulated board PASS.

### P14 — Probe optional tasks and verify stopping

Runtime capabilities → Inspect your fixture and an image: record installed tools, task names, release and device/terminal prerequisites. In F2 choose an optional task absent from that probe; the recent result disables it with the missing task, or a fresh pre-submission probe refuses it before queueing. Refresh after configuration changes. Test missing ide-sdk/device tools similarly.

On an expendable owned kas-container build, F5 → Let finish first; then in a separate run use Force + recovery. Record the unique Bitloom container name and Shutdown evidence observations: exact container stop result, client result and recovery eligibility. Confirm its container is gone/stopped using the same engine. Recipe recovery is offered only after confirmed termination; observed active tasks are at risk, not proof of corruption. Native kas wrappers/existing containers remain guarded when shutdown is unconfirmed. A new kas shell sees a separate namespace and must not be used as proof that an old server exited. Restart an old persistent service only after its queue is idle when installing the new version.

### Developer evidence ledger

Save P01–P14 results with profile/release, inputs, baseline/current captures, comparison files and job IDs/logs. Optional N/A entries must name the missing hardware, task, report or SDK. Automated reproduction complements this book:

```bash
python tools/validate_developer.py --build
python tools/capture_developer.py
python -m pytest -q
python tools/check_testbook.py
python tools/build_docs.py
```

The validation helper's `--image` opt-in builds a full fresh image; its default `--build` validates a small recipe and offline/failure recovery paths. Read result.json rather than treating executable probe PASS as proof of missing image artifacts. Restore your experimental changes and keep the original state/history as described in chapter 12.

## 14. Keyboard, web, compliance, Studio and teams

Run on the demo first (`bitloom --demo`), then on the real `kas-scarthgap`/`kas-wrynose` profiles from `python tools/prepare_validation.py --release both` where a case says so.

### U01 — Keyboard-only session

Do not touch the mouse. Expected for each step:

1. `1`…`0` open each section and focus its list; `[`/`]` cycle; the rail highlight follows.
2. In Builds the footer and buttons show `s r e p x i f c`; `e` toggles errors only; typing `/err` puts the letters in the search field without toggling; `Esc` returns focus to History.
3. `2` then `j`/`k` move in the metadata table; `t` (Recipes uses `t` for the tree) focuses the layer tree.
4. `1`, `t`, type a target (several separated by spaces), Enter: the build is queued at once, as with `b` and *Build*; a target such as `a; id` is refused and the field keeps focus. `F2` opens the command center: `↓`/`↑` change the operation from the filter, `Tab Tab` reaches the inputs, Enter queues.
5. `P` opens the profile switcher (`j`/`k`, Enter); `?`, `F1` and `Ctrl+G` open the keyboard reference; `Ctrl+X` closes it.
6. `Ctrl+P` lists sections, Studio, console builds and every operation.

### U02 — nano keys in editors

`9`, `l` opens local.conf. `^K ^K` cuts two lines, `^U` pastes them back, `^W` searches (Enter selects the match, `Alt+W` finds the next), `^X` refuses once while the buffer is modified, `^O` writes a timestamped `.bak-` backup, `^X` closes. The same keys work in the profile editor (`F4`), runtime files and the new-file dialog; forms confirm with `^O`.

### W01 — Start the web dashboard securely

```bash
bitloom --web --no-browser --port 8765 --config .validation/profiles.json --state .validation
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/api/state              # 401: token required
curl -s -o /dev/null -w '%{http_code}\n' -H 'X-Bitloom-Token: wrong' http://127.0.0.1:8765/api/state   # 401
```

Expected: the printed URL carries `#token=…`; opening it shows *Connected* and the service pid. The token disappears from the address bar after load. A TUI on the same `--state` shows the same history.

### W02 — Follow, stop and retry from the browser

Queue a build with `b` (or Operations, `q`). Expected: a *Build started* toast; the progress bar is indeterminate, then striped with `task N of M`; output streams; the TUI shows the same job with a spinner. Open Summary/Sstate reuse/Warnings/Timings with `u`, `o`, `w`, `m`. Search with `/`, toggle errors with `e`. `g` (graceful) or `s` (force, confirm) stops it with a toast; `r` retries. A failure raises an error toast whose *Open summary* button jumps to the summary.

### W03 — Palette, phone and light theme

`Ctrl+K`, type `sbom`: the palette lists the SBOM section and operations. Resize the browser below 900 px or open it on a phone: one column, scrolling navigation, toasts at the bottom. With the system light theme the page switches palettes; with *reduce motion* animations stop.

### V01 — Release awareness

On `demo-scarthgap` (or `kas-scarthgap`): `F2`, type `sbom`, `↓` to *Recipe CVE analysis from its SBOM*. Expected: *(not in this release)*, a disabled Queue button and “use Run recipe CVE check (cve-check) instead”. On `demo-wrynose` (or `kas-wrynose`) the same operation is offered and `cve` is refused the other way round. In the web dashboard the Operations dialog shows the same refusal. `bitloom --ci sbom-cve-recipe:busybox --profile kas-scarthgap` prints a skip warning and writes `<skipped>` in JUnit.

### V02 — SBOM quality

`6`, `s` (or `bitloom --sbom`). On `demo-wrynose`: SPDX 3.0.1, PURL 67%, supplier 67%, VEX affected 1 · fixed 1 · not affected 1, affected CVE-0000-0001. On `demo-scarthgap`: SPDX 2.2 with CPE coverage. On a real Scarthgap build: the image appears as `…rootfs-<timestamp>.manifest` (the SPDX 2.2 archive is read through the manifest and `tmp/deploy/spdx`), supplier 0% because of the OpenEmbedded placeholder, and *CVEs recorded fixed by recipes*.

### V03 — SBOM settings

`9`, `s`. Move with `j`/`k`; the right pane explains each option, its CRA relevance and release window. On Scarthgap, *sbom-cve-check on image builds* shows n/a and Space refuses it; *Supplier, SPDX 2.2* accepts a name. Toggle *Generate SPDX SBOMs* and *Build history*, `^O`. Expected: a managed block in `build/conf/local.conf` plus a `.bak-` backup (host/container), or `bitloom-sbom.yml` appended to the kas profile's `kas_file`. Reopen: the states persist. `v` queues `bitbake-getvar` for the selected variable.

### V04 — CRA readiness

`9`, `c` and `bitloom --cra --config … --state …`. Expected: the release support line, SBOM/identifier/licence/VEX/analysis/traceability/disposition/reproducibility checks, the 2026-09-11 and 2027-12-11 milestones and the EN 40000-1-3 note; `--cra` exits 2 when any check warns. The web SBOM & CRA section (`5`) shows the same checks with gauges.

### N01 — Studio: your own distribution

`2`, `c`. Expected: kinds on the left; *Distribution* selected. On the demo, the target layer is `meta-demo`; change the id to `demo-os` and watch the preview. `^O` creates `meta-demo/conf/distro/demo-os.conf`; the profile's DISTRO becomes `demo-os` (top bar). Repeat: Studio refuses to overwrite. Try *Image recipe* on Wrynose: `debug-tweaks` is not offered; on Scarthgap it is.

### N02 — Studio on a kas profile and in the browser

On `kas-scarthgap`, create a *Product layer* `meta-acme`, then an *Image recipe* in it. Expected: `kas-studio-meta-acme.yml` appended to `kas_file` with the layer as a repository and `target: acme-image`; `b` builds it after a kas build registers the layer. In the web Studio (`6`) the same forms preview live; *Create files* raises a toast with a *Build* button.

### T01 — Headless CI matrix

```bash
bitloom --config .validation/profiles.json --state .ci --ci kas-build --profile kas-scarthgap \
  --junit results.xml --summary summary.json --annotations github
```

Expected: `::group::` sections around the build output, error/warning annotations, `results.xml` with one test case per job, `summary.json` with status, sstate hit rate, warnings, failed tasks and new images; exit code 0 on success. Ctrl+C stops the running job cleanly (exit 130).

### T02 — Team profiles

Create `/tmp/team.json` with `{"profiles": [{"name": "team-demo", "root": "<demo root>"}]}` and add `"include": ["/tmp/team.json", "/tmp/missing.json"]` to your profiles file. Expected: `P` lists `team-demo` marked *team*; F4 shows only your own profiles plus the include list; Configuration warns about `/tmp/missing.json`; saving profiles keeps the include.

### T03 — Setup, filesystem and network checks

`9` and `bitloom --doctor` (`--network` to probe). Expected: host rows (cores, memory, Python, locale, inotify, open files, engines, WSL hint), filesystem rows for the build directory, TMPDIR, DL_DIR and SSTATE_DIR, and `n` probing configured mirrors/hash equivalence/PR servers without downloading.

### T04 — Images, fleet and console builds

`6`, `m` lists every image per MACHINE with sizes and package counts. Developer → Board view → *Fleet status* (or `bitloom --fleet`) probes all configured devices at once and writes `fleet-status.json`. Run a build directly in a kas shell, outside Bitloom; then `1`, `c`: the console build appears classified, Enter opens it with search and errors-only, and the web dashboard lists it under *Console builds*.

### T05 — Project launcher script

Create a script that accepts kas subcommands and `shell -c CMD`, for example:

```bash
cat > /tmp/launcher.sh <<'SH'
#!/bin/bash
# Configuration chosen by $YML; kas subcommand as arguments.
if [ "$1" = "shell" ] && [ "$2" = "-c" ]; then exec kas-container shell "$YML" -c "$3"; fi
exec kas-container "$@" "$YML"
SH
chmod +x /tmp/launcher.sh
```

Add a profile with `"mode": "wrapper"`, `"launcher": ["/tmp/launcher.sh"]`, `"environment": {"YML": "tests/integration/kas-minimal.yml", "KAS_WORK_DIR": "<work dir>"}`. Expected: Configuration shows the launcher as OK; *Build kas configuration* runs `/tmp/launcher.sh build`; *Resolve recipe environment* runs `/tmp/launcher.sh shell -c 'bitbake -e …'`.

### J01 — Guided setup of an existing project

Create a folder with a kas file and a launcher script (the T05 script works), or use one of your projects. **Configuration → `w` → `o`**, type the folder, Enter. Expected: proposals with evidence (launcher script reading `$YML`, kas file with MACHINE, Poky checkout if present); ↑/↓ fills the form; checks show ✔/▲/✖ live and block saving on ✖ (for example an empty `KAS_WORK_DIR` for kas-container); `^O` makes the profile active and the top bar, Recipes and Configuration reload. Opening the same folder again switches to its profile. Start Bitloom in an empty directory with a new `--config`: the guided setup opens by itself. Repeat in the web dashboard (`8` → *Set up a project*).

### J02 — New project

`w` → `n`. Choose Wrynose, `qemuarm64`, `core-image-base`, product layer on. Expected: the preview shows `kas.yml` with bitbake/openembedded-core/meta-yocto pinned to yocto-6.0.2 and `meta-<name>`; `^O` creates the folder with README, `.gitignore`, `.git` and the layer; the profile is active; `b` starts the first kas build. A non-empty folder or an invalid name is refused. In the web dashboard: `8` → *New project*, live preview, *Create project*, toast with *Build it*.

### J03 — Clone from Git

`w` → `g`, enter an HTTPS or SSH URL of a project (or `file:///path/to/repo`). Expected: the destination is suggested until you edit it; `^O` starts a *Clone* job visible in Builds; on success the guided setup opens on the clone. An existing destination or an option-like URL is refused. Web: *Clone from Git*, then the *Set it up* toast.

### V05 — Vulnerabilities

On `demo-wrynose`: `6`, `v`. Expected: 3 unpatched findings ordered critical (CVE-0000-0002, 9.8), high, medium; `/openssh` filters; the detail shows source, detail and summary; `r` opens the review dialog and, after saving, the Review column shows owner and expiry; `x` opens the export menu: each format (Markdown, HTML, CSV, JSON, SARIF) writes `<state>/exports/vulnerabilities-<profile>-<time>.<ext>` with the findings shown; the Markdown and HTML reports link every CVE to NVD, CVE.org and OSV and end with the Yocto remediation steps; `g` scans the newest SPDX SBOM with Grype when installed (otherwise it explains). `bitloom --vulns --min-cvss 9 --fail-on-unpatched` exits 2; with `--min-cvss 9.9` it exits 0. On a real Wrynose build with the sbom-cve-check fragment enabled, the report from `tmp/deploy/images` appears as source. `bitloom --vulns --format md -o report.md` (also `html`, `csv`, `json`, `sarif`, `--all-statuses`) writes the same reports. Web: `5` → *Vulnerabilities* with chips, filters and the *Export* menu (download in the chosen format); CRA readiness shows *Unpatched vulnerabilities*.

### H01 — Build notifications

`9`, `o`: tick *failed* and *success*, set the minimum to `0`, keep *desktop* on and enter an ntfy topic (`https://ntfy.sh/<random-topic>`, subscribed on your phone) as webhook; `^T`. Expected: a desktop notification (on WSL a Windows notification), the terminal bell and a push on the phone. Run a short failing command (F2 → custom `python3 -c 'exit(1)'`), close the TUI before it ends in persistent mode: the notification still arrives (sent by the service). Set the minimum to 600: short jobs stay quiet. In the web dashboard enable the bell button, switch to another tab and let a build end: a browser notification appears.

### H02 — ETA, comparison and tmp/work

Run the same build twice. Expected: during the second run the Tasks card and the web progress line show `ETA ~…` with its basis (task rate, previous runs); after it, `1`, `d` (web: *Compare* tab) compares durations, executed vs setscene tasks, sstate hit rate and warnings. `5`, `w` (or `bitloom --work-usage`) lists the largest recipe work directories, says whether rm_work is enabled and suggests clean commands.

### B04 — GitHub release workflow

In GitHub → Actions → *Release Bitloom* → *Run workflow*, enter a new version (for example `0.2.0`) and optionally tick *draft* or *prerelease*. Expected: tests pass, the job builds `bitloom-<version>.tar.gz`, the wheel, `bitloom_<version>_all.deb` and `SHA256SUMS`, installs the `.deb` and smoke-tests it, attaches the assets to the workflow run and creates the `v<version>` release. An existing tag is refused. Locally, `python tools/build_release.py 0.2.0 --output /tmp/release` produces the same files.


### E01 — Damaged files and odd inputs

Run each step in a scratch copy (`cp -r .bitloom /tmp/bl`, then `--config /tmp/bl/profiles.json --state /tmp/bl`). Expected: a one-line message naming the file, never a Python traceback.

1. Write `{nope` into `profiles.json` and run `bitloom --cra`: exit 2, `…profiles.json is not valid JSON`. An empty `profiles.json` behaves like a first start; a file without `"active"` uses its first profile; `"active": "ghost"` lists the defined profiles.
2. Write `not a database` into `history.sqlite3` and run `bitloom --ci parse`: exit 2, `history.sqlite3 cannot be used … move it away`.
3. Write `[1, 2]` into `security-reviews.json`: CRA readiness shows *Vulnerability dispositions* as WARN with the reason, Vulnerabilities lists it, and recording a review (`r`) is refused without changing the file.
4. Put a truncated `*.spdx.json` and a `*.sbom-cve-check.yocto.json` containing `{"package": "nope"}` next to the image: `--sbom` and `--vulns` report each file's problem and keep analysing the others.
5. Build target `core-image-minimal busybox` queues one BitBake command with both targets; `a; id`, `$(id)` or a task `compile; id` are refused with *Not a BitBake target* / *Not a task name*, in the TUI, in the web dashboard and in `--ci build:…`.
6. Web API: `POST /api/jobs` with `"values": "x"` answers 400 with a JSON error; `DELETE /api/state` answers 405.

### D01 — Documentation site

`python tools/serve_docs.py --port 8000`, open `http://127.0.0.1:8000`. Expected: the landing page with feature filter, runtime tabs and screenshot lightbox. Open the *User guide*: a sidebar lists every page (the current one highlighted), *On this page* follows the scroll, each page ends with *Previous* / *Next*. Press `/` (or Ctrl+K), type `sbom-cve-check`: results from several pages with highlighted terms; ↓ and Enter open the section. The ☾/☀ button switches theme and is remembered after a reload; without a choice the site follows the system theme. Code blocks show *Copy* on hover. At phone width, ☰ opens the page list and nothing scrolls sideways.
