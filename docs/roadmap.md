# Research and implementation map

Research reviewed on **2026-10-10**. All fourteen workflows below now have implemented controls in F10 Developer. See the [Developer guide](developer.md) for inputs/operations and [chapter 13 of the manual testbook](testbook.html#13-developer-acceptance) for concrete acceptance cases. Implementation status and validation coverage are separate: hardware, complete SDK debugging and release-specific reports still require their real prerequisites.

## What developers are struggling with

Public discussions describe opaque configuration, confusing errors and lengthy feedback loops. A developer learning Yocto describes difficulty understanding variables and locating the actual failure in an [August 2026 discussion](https://www.reddit.com/r/embedded/comments/1vdlik5/is_yocto_hard_or_am_i_dumb/). Another describes spending working days chasing configuration changes across projects in an [August 2023 discussion](https://www.reddit.com/r/embedded/comments/1661ico/my_job_has_become_editing_yocto_and_other_config/). A [March 2025 beginner discussion](https://www.reddit.com/r/embedded/comments/1jqre2y/) highlights friction between an intended image change and the resulting system.

These are individual experiences, not a representative developer survey. They identify problems worth investigating; they do not establish demand percentages or prove which feature is most popular. The priorities below are Bitloom's assessment of daily value, considering what the application already provides. Technical foundations are checked against upstream documentation, rather than community advice alone.

## Answering the criticisms of earlier Yocto interfaces

Research reviewed on **2026-10-12**. Earlier graphical front ends were criticised and some were retired; Bitloom is designed around those lessons. The left column records documented problems, the right column how Bitloom responds. It is a design rationale, not a claim that Bitloom replaces these tools.

| Documented problem | Bitloom's response |
| --- | --- |
| **Hob** was tightly woven into BitBake internals, fragile, needed constant QA, was tied to GTK+ 2 and was removed in 2016 ([removal discussion](https://docs.yoctoproject.org/pipermail/yocto/2016-March/028921.html)). | Uses only public command-line interfaces and their output (`bitbake`, `bitbake-layers`, `devtool`, `kas`, `bitbake-getvar`, logs and deploy files); no imports of BitBake internals. A terminal UI plus a standard-library web page, nothing to keep in sync with a GUI toolkit. |
| **Toaster** must be running before a build to record it, needs its own Django setup and database, struggles with non-Poky layouts, and the project lists it among components with little maintainer time ([Toaster manual](https://docs.yoctoproject.org/toaster-manual/intro.html), [2025 status reports](https://wiki.yoctoproject.org/wiki/2025_Yocto_Project_Weekly_Status_Archive)). | Reads evidence after the fact: console builds from `tmp/log/cooker` (builds started anywhere), task logs, deploy directories, SPDX documents and buildstats. One `pip`/`.deb` install, SQLite history only for its own queue, kas and split-repository (Wrynose) layouts, containers and project launcher scripts. |
| **knotty** output floods beginners; finding the failing task and its cause is hard, and messages labelled ERROR are not always the root cause ([user report](https://docs.yoctoproject.org/pipermail/yocto/2011-November/003477.html), [BitBake discussion](https://www.openembedded.org/pipermail/bitbake-devel/2013-April/013176.html)). | Errors-only filter with context, failed task logs from BitBake's own paths, Toaster-style summaries, grouped warnings and a root-cause diagnosis with next steps, verified on a real perl build failure. |
| A steep learning curve: months to become productive, release differences make advice stale ([DornerWorks](https://www.dornerworks.com/?p=1658)). | Every operation previews the exact command; Studio and SBOM settings explain every field; the detected release decides defaults and explains what a release lacks with the alternative it offers. |
| **taskexp** and graphical dependency explorers need a desktop toolkit. | Dependency edges, "why this task" and environment diffs in the terminal and over SSH. |
| Remote and shared build machines: sessions die with the terminal. | A reconnectable build service, a web dashboard on loopback with a token (tunnel it over SSH), headless CI runs with JUnit/JSON, read-only team profiles. |

## Implemented workflow map

| Case | Implemented interaction | Evidence and practical boundary |
| --- | --- | --- |
| P01 | Variable history with origin Enter-to-edit | Actual getvar/evaluated datastore, OVERRIDES, file/line history and stale fingerprints; global/recipe/multiconfig identity remains explicit. |
| P02 | Recipe context and selectable Runtime browser | Evaluated provider/appends/source/build/temp/sysroot paths plus bounded recursive filename search; logs/scripts remain read-only. |
| P03 | Rebuild evidence | Paired sigdata/diffsigs, printdiff and potential reverse task dependencies; missing pairs/cache proof is incomplete evidence, not a guessed causal count. |
| P04 | Failure investigation | Original job/profile, reported task log/script and diagnostic context; relative source locations are not guessed. |
| P05 | New layer preview and registration | Complete MIT-licensed CMake/Meson/Make/Python/Rust fixtures, checksum, source and layer.conf; new kas overlay/profile or queued add-layer. Existing destinations refused; parse/build establishes successful registration. |
| P06 | IDE / SDK bridge | Actual ide-sdk probe/queue, source/sysroot/compiler identity and explicit mapping/compile-database exports; SDK generation/debugging depends on installed release, build system and accessible sources. |
| P07 | Image regressions and provenance | Actual buildhistory/pkgdata packages, normalized byte sizes, file metadata and baseline deltas; reject incompatible contexts, expose missing reports. |
| P08 | Build performance | Measured buildstats timeline/trends plus cgroup-v2/pressure/disk evidence; parallel durations are not summed as elapsed time, old job resource use is not reconstructed. |
| P09 | Clone and Resolved kas / multiconfig | Separate absolute build directory and real kas dump comparisons, multiconfig queries and job identity; service scheduling remains serial. |
| P10 | Downloads / offline | Log evidence categories, URI DNS and mirror configuration, source mirror preparation and separate BB_NO_NETWORK fetch/full-build verification; kas bootstrap is a separate network concern. |
| P11 | CVE / SBOM review | Supported CVE/SPDX JSON, baseline status changes, owner/reason/expiry dispositions; upstream status retained, missing reports unavailable. |
| P12 | Kernel fragments and Upgrade baseline | Requested/final CONFIG checks and actual kernel commands, version/appends/patches/layer comparisons; does not guarantee compatibility or overwrite developer edits. |
| P13 | Board laboratory | Explicit SSH/console/test profiles and labgrid adapter, real job/transcript evidence and artifact references; devtool deploy transfers recipe outputs, image hash is not proof of flashing. |
| P14 | Runtime capabilities and Shutdown evidence | Actual task/tool probes gate optional actions, owned kas-container naming/stop confirmation, distinct client/container/server observations; external wrappers retain unconfirmed-server guards. |

## Upstream foundations

Variable assignment histories, recipe/task datastores, task logs and signature differences use the installed release's tools described in [Yocto debugging documentation](https://docs.yoctoproject.org/dev/dev-manual/debugging.html). Runtime file/line navigation and connected captures are Bitloom's interface design. The [Technical FAQ](https://wiki.yoctoproject.org/wiki/Technical_FAQ) explains checks such as selected recipe versions when changes appear ineffective.

The IDE bridge follows release-supported devtool ide-sdk behavior in the [Scarthgap SDK manual](https://docs.yoctoproject.org/5.0.12/sdk-manual/extensible.html). It probes the installed command before submitting; it does not promise every IDE/language or a host-visible Docker-private source tree.

Image comparisons consume the package/file metadata described in [buildhistory documentation](https://docs.yoctoproject.org/5.0.12/dev-manual/build-quality.html). Performance uses [buildstats](https://docs.yoctoproject.org/5.0.12/ref-manual/classes.html#buildstats) and reports observable limits alongside measurements discussed in [build-speed guidance](https://docs.yoctoproject.org/dev/dev-manual/speeding-up-build.html). There is no automatic tuning or invented time-saved forecast.

Profile isolation and configuration-specific targets are grounded in [BitBake multiconfig documentation](https://docs.yoctoproject.org/dev/dev-manual/multiconfig.html); profile cloning and a multiconfig datastore remain separate concepts. Fetch classification, mirrors and network-disabled checks use [BitBake fetching behavior](https://docs.yoctoproject.org/bitbake/bitbake-user-manual/bitbake-user-manual-fetching.html). Source readiness and complete build readiness have separate recorded outcomes.

Security review retains original findings and separate local dispositions. [Scarthgap vulnerability guidance](https://docs.yoctoproject.org/5.0.12/dev-manual/vulnerabilities.html) describes mapping limitations; [current security documentation](https://docs.yoctoproject.org/security-manual/vulnerabilities.html) describes newer SBOM-based workflows. A newer class/report format is never assumed present in the Scarthgap fixture. Supported JSON formats are parsed with explicit missing/unsupported results.

Board operations use configured tools and actual equipment, following [labgrid resource and driver abstractions](https://labgrid.readthedocs.io/en/latest/overview.html). Bitloom does not implement an imaginary universal flashing protocol. Commands, device ownership, logs and artifact references are recorded together.

## Validation and remaining experiments

The [validation report](validation.md) separates the earlier verified 4,064-task minimal-image build from new Developer probes and small-recipe/offline/controlled-failure validation. Parser fixtures verify deltas, cgroup/buildstats handling, CVE reviews and kernel fragment comparisons; UI tests verify runtime editing, preview/cancel, captures/staleness and compact layout. Executable probes can pass while an optional artifact remains unavailable.

Run P01–P14 in the [testbook](testbook.html#13-developer-acceptance) and keep actual captures/logs. Device deployment/console, complete interactive IDE cross-build/debugging, new CVE database scans, full kernel compilation and an end-to-end Podman build need the corresponding environment. The implemented controls expose these prerequisites rather than marking them successful. This research map records shipped behavior; it is not a delivery-date or community-demand survey.
