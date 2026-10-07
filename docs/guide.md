# User guide

## Profiles and paths

Profiles are local JSON stored at `.yoctotui/profiles.json` by default. State is stored at `.yoctotui/`; both paths can be set on the command line. The file is atomically replaced with mode 0600. Profile names must be unique; queued jobs retain a copy of the original profile.

| Field | Meaning |
| --- | --- |
| `name` | Unique profile identifier |
| `root` | Absolute or relative project root (resolved on the host) |
| `build_dir` | Build directory, relative to root or absolute on host |
| `mode` | `host`, `kas`, `container`, or `kas-container` |
| `init_script` | Host/container init script; autodetects oe-init-build-env or poky/oe-init-build-env |
| `kas_file` | kas configuration path(s), including colon-separated composition |
| `engine` | Docker or Podman for generic container mode |
| `image` | Builder image for a fresh container |
| `container_name` | Existing container name; empty starts a fresh temporary container |
| `container_root` | Project mount path inside a generic container; default `/work` |
| `machine`, `distro` | Environment overrides passed through BitBake's allow-list |
| `downloads`, `sstate` | Host paths used by cache inventory; these do not modify BitBake configuration |
| `environment` | String environment variables; kas variables control kas paths/runtime |
| `container_args` | Array of additional Docker/Podman arguments |
| `targets` | Suggested targets; the first fills the toolbar |

`DL_DIR`/`SSTATE_DIR` in local.conf are read as literal hints. `${TOPDIR}` is expanded; other expressions require a profile path override. Runtime paths, especially kas container paths, may differ from host paths. Use **Resolve env** to inspect the authoritative result.

### Host

Set root to your checkout. The TUI sources the init script in bash and executes a quoted argument list. You can also start from an already initialized shell and leave init_script empty. No shell operators in target fields are executed.

### kas

Set mode to `kas` and point kas_file to your YAML. BitBake/devtool commands execute with `kas shell FILE -c COMMAND`; kas actions call the appropriate subcommand directly. Install kas in your preferred environment.

### kas-container

Install the official kas-container wrapper and a functioning Docker or Podman runtime. Set `KAS_CONTAINER_ENGINE`, `KAS_WORK_DIR` and optionally `KAS_BUILD_DIR` in environment. Use a dedicated work directory distinct from the Git source repository. The wrapper supplies containerized kas and Yocto dependencies.

kas-container does not forward every arbitrary host environment variable into its container. Put Yocto overrides in kas YAML or use officially supported kas environment variables. Set `KAS_MACHINE`/`KAS_DISTRO` for kas overrides. Set container engine through `KAS_CONTAINER_ENGINE`, not the generic engine field.

### Generic Docker / Podman

Set mode to `container`, engine and image. New containers bind root at container_root, use the current UID/GID and have a unique name. The image must contain bash and your build dependencies. BitBake should be the final exec process for graceful signalling.

Existing container_name uses `exec` instead; that container must already mount the project at container_root. build_dir must be inside root. External caches require explicit mounts plus matching paths in your build configuration. Runtime args must be JSON strings, such as `["--network", "host"]`; review privileged options yourself.

## Build and development workflows

Enter one target or recipe in the toolbar and press Build or F2. Filter the command list by group/name. Required inputs appear dynamically. Review the exact invocation and queue it. Builds and utilities share a serial queue to avoid two servers modifying one build directory.

The Build pane persists operation, profile, status, timestamps, exit code and log path. Enter on a row loads its log. Retry uses original command and profile even if you have switched profiles. Live progress comes from standard `Running task N of M` messages. History timestamps are stored in UTC.

Use recipe browsing to locate metadata, open files, build or start devtool modify. The metadata browser indexes local files, including inactive layers; `Show layers`, `Show recipes`, `Show appends` and `Show overlaid recipes` ask BitBake for evaluated state.

Interactive actions suspend Textual and give the real terminal to devshell, menuconfig, QEMU or kas shell. They require a real terminal and cannot start while a queued/running job occupies the runner. Their output is not persisted as a queued build log.

## Errors and log search

Failures generate a notification and refresh the task-log browser. Search selected logs case-insensitively with three surrounding lines, or toggle errors-only. The live view keeps 5,000 lines; searches inspect the complete file and cap the rendered result. Export copies the original complete log to `.yoctotui/exports`.

Task logs are discovered under the standard `tmp/work/ARCH/RECIPE/VERSION/temp` hierarchy and ordered by modification time. Custom TMPDIR layouts currently require setting build_dir to match the expected layout or opening logs externally. Symlink aliases are skipped to avoid duplicate entries.

The Workbench build report extracts warnings, errors, task summaries, failed tasks and shared-state summaries. It does not invent diagnoses. Use the task's own log to determine the cause.

## Workbench

**Environment:** Resolve env for the chosen target, wait for success, then Load. Filter both variable names and values. Capturing two environments for the same target/profile enables Env diff. Literal exported values are compared; function bodies and assignment provenance remain in the original log.

**Dependencies:** Generate graph for a target and wait for success. Choose Dependencies and Load to read task-depends.dot from the configured host-visible build directory. Filter nodes to explore task relationships. The first 20,000 edges are indexed.

**Build history:** Enable buildhistory and BUILDHISTORY_COMMIT in local.conf, build an image, then open Build history diff. The report shows recent Git commits and changes between the newest two commits.

**Signatures:** Use Dump signatures, Explain sstate differences, Read signature file or Compare signature files. Signature commands use BitBake tools from the selected release rather than decoding undocumented binary formats.

## Cache and download maintenance

Scan either Downloads or Shared state to view names, size, age and relative paths. Inventory is capped at 20,000 files. The scan total is the indexed total, not necessarily the entire cache. Set an age of at least one day and open Prune plan. It lists concrete files and estimated bytes; nothing is removed before Execute plan.

Pruning excludes symlinks, `.lock`/`.done` markers, Git checkout internals and files whose sibling lock exists. Each file's path, size and modification time is checked again at deletion. Only files inside the selected root can be deleted. The TUI refuses a plan while its own jobs are active/queued. Other machines/builders cannot be detected.

Age is not proof that an artifact is unused. Keep shared caches and offline source requirements in mind. Recipe clean keeps downloads/sstate; cleansstate removes local recipe shared state; cleanall also deletes recipe downloads. Remote sstate mirrors are unaffected by local inventory pruning.

Download audit reports possible partial files, lock files and orphan completion markers. For actual source integrity checking, use the recipe fetch task and its SRC_URI checksums.

## Releases and compatibility

Versions reports local repository branches, commit IDs, Git descriptions, dirty status and literal LAYERSERIES_COMPAT declarations against locally detected LAYERSERIES_CORENAMES. Dynamic expressions can require manual review. Metadata parse is authoritative.

Use one profile/build directory per release. The TUI does not switch active Git branches underneath a running build, silently migrate local.conf syntax or mix caches without your configuration.

## Configuration editing

local.conf, bblayers.conf and metadata are editable. Save creates a timestamped backup, refuses to overwrite a file changed externally, and atomically replaces the contents. Files above 2 MB and binary files are not opened in the editor. Close without saving discards in-editor changes. Review changes with your usual Git tooling.

Example snippets cover buildhistory/buildstats, mirrors, shared caches, offline builds, mirror tarballs, thread limits and optional image/security classes.

## Troubleshooting

- **bitbake not found:** configure an init script or launch from a sourced environment.
- **Docker permission denied:** the user running YoctoTUI must have permission to the Docker socket; the app never changes daemon permissions.
- **Docker Snap and /tmp:** Snap's daemon can see a different `/tmp` from the host. A bind mount may be created as root in the daemon namespace. Prefer a dedicated Linux directory visible to both namespaces, or initialize only the dedicated mount ownership inside a container. Never apply broad permissions to Docker or the project root.
- **Windows/NTFS build paths:** store Yocto work directories on a Linux filesystem. The TUI source can live under /mnt/c; BitBake source/build caches should not rely on NTFS semantics.
- **kas custom machine override:** use KAS_MACHINE/KAS_DISTRO or kas YAML; arbitrary environment variables may not be forwarded by the wrapper.
- **Stop left an external build running:** wrapper/pre-existing-container modes cannot guarantee server termination. Verify processes in that runtime before recovery.
- **Missing task/class:** check your release and INHERIT configuration. CVE, SPDX, testimage and ptest entry points require appropriate metadata.
- **Too little space/RAM:** check Health, reduce thread counts, and inspect cache plans before removal.
- **Small terminal:** use keyboard shortcuts and Tab, or increase to 140×42 for the complete layout.

## Documentation and verification

`python tools/capture_docs.py` captures the real Textual interface with Pilot and exports SVG/PNG/GIF. It uses labelled demo data. `python tools/validate_kas.py` executes a real image build through Runner and records a JSON result. Read validation.md for evidence from the current development session.
