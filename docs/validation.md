# Validation report

## Status

Development validation on **2026-10-10**. The full container image build is running; this report will be updated from the observed result before the final verification commit. This is not a success claim.

## Automated checks

The initial expanded suite passed **20 unit and UI tests** on Python 3.10.12 and Textual 1.0.0. It covers argument construction, shell quoting, host/kas/container routing, profile persistence, serial jobs, failure exit codes, cancellation, single-signal graceful stop, cache deletion boundaries, full-file log search, report parsing and TUI navigation.

The sandbox's Python thread-pool shutdown hung even for a minimal asyncio.to_thread example. The same tests passed when executed outside that sandbox. This restriction is separate from application behavior.

## Genuine Yocto image build

| Setting | Value |
| --- | --- |
| Target | core-image-minimal |
| Machine | qemux86-64 |
| Distro | poky |
| Release | yocto-5.0.8 (Scarthgap) |
| Poky revision | dc4827b3660bc1a03a2bc3b0672615b50e9137ff |
| kas wrapper / image | 4.8.1 |
| Image digest observed | sha256:fef6f850106a6823e65e133ed8157a847431dea4aa2de3a636c11f65e9977476 |
| Runtime | Docker, through kas-container |
| Engine integration | YoctoTUI Runner, SQLite history, persistent streamed log |
| Work | Dedicated /tmp/yoctotui-kas-validation mount in the Docker daemon namespace |
| Output format | root filesystem tar.bz2 |
| Threads | BB_NUMBER_THREADS=8, PARALLEL_MAKE=-j8 |

No Yocto build toolchain was installed on the host. The official kas image provides those dependencies. The project venv contains TUI/test/documentation tools and the kas-container wrapper. Build data and the downloaded image consume disk space; they are isolated, not nonexistent.

Docker Snap exposed a private /tmp mount initially owned by root. Only that dedicated work mount was assigned the builder UID/GID. Docker socket permissions were not modified. A failed initial attempt and the later real build logs are retained locally under .validation.

The configuration pins the fetched Poky commit for reproducibility. Standard upstream source fetches and mirrors are used; network warnings are not treated as successful fetch evidence.

## Screenshots and GIF

Media in assets/ was captured from the actual Textual app with Pilot. The sample workspace and controlled failure are clearly labelled demo data. SVG is exported by Textual; PNG is rendered from the exported SVG; GIF sequences those actual captures. No generated image or invented successful build screen is used.

## Coverage boundaries

A passing minimal image build does not validate every board, old release, devtool operation, existing-container lifecycle, shared-cache topology, external device or optional testing/security class. Podman command construction is tested; a Docker execution does not prove an end-to-end Podman build. Graceful stop uses documented BitBake client behavior and single-signal unit verification; interrupting the full validation build was not used as a shortcut.

Reference behavior: [BitBake knotty UI shutdown handling](https://github.com/openembedded/bitbake/blob/master/lib/bb/ui/knotty.py), [kas container guide](https://kas.readthedocs.io/en/4.8.1/userguide/kas-container.html).
