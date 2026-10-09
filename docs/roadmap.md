# Developer workflow roadmap

Research reviewed on **2026-10-10**. Everything below is **proposed**, with no delivery date or claim of implementation. The [command reference](commands.md), [user guide](guide.md) and [manual testbook](testbook.html) describe the current application.

## What developers are struggling with

Public discussions describe opaque configuration, confusing errors and lengthy feedback loops. A developer learning Yocto describes difficulty understanding variables and locating the actual failure in an [August 2026 discussion](https://www.reddit.com/r/embedded/comments/1vdlik5/is_yocto_hard_or_am_i_dumb/). Another describes spending working days chasing configuration changes across projects in an [August 2023 discussion](https://www.reddit.com/r/embedded/comments/1661ico/my_job_has_become_editing_yocto_and_other_config/). A [March 2025 beginner discussion](https://www.reddit.com/r/embedded/comments/1jqre2y/) highlights friction between an intended image change and the resulting system.

These are individual experiences, not a representative developer survey. They identify problems worth investigating; they do not establish demand percentages or prove which feature is most popular. The priorities below are Bitloom's assessment of daily value, considering what the application already provides. Technical foundations are checked against upstream documentation, rather than community advice alone.

## Proposed priorities and current boundaries

| Proposal | Priority | Proposed workflow | What Bitloom already provides / remaining gap |
| --- | --- | --- | --- |
| P01 | First | Explain a variable's value and winning overrides, with file/line navigation | Environment filtering/diffs and raw getvar output exist; assignment history is not a navigable view. |
| P02 | First | A recipe context view and selectable runtime file tree | Host metadata browser and runtime list/read/edit/create exist; container listings are text reports. |
| P03 | First | Explain rebuilds and cache misses across recorded builds | Signatures, printdiff, dependency context and sstate summaries exist; no unified before/after causal view exists. |
| P04 | First | Connect a failed task to its script, log and source diagnostic | Search, task-log retrieval and textual diagnosis exist; no structured investigation workspace exists. |
| P05 | Next | Create and register a complete layer/recipe with previewed changes | File templates, layer commands and devtool add exist; kas registration and license checks remain separate steps. |
| P06 | Next | Set up an IDE and cross-development environment from a recipe | devtool and SDK/eSDK commands exist; ide-sdk integration and path mapping are not built in. |
| P07 | Next | Compare image size, files, packages and permissions between builds | Manifest diff, rootfs inventory, provenance and snapshots exist; no unified regression dashboard exists. |
| P08 | Next | Explain build bottlenecks using buildstats and runtime limits | Host resource sampling and timestamped task reports exist; cgroup limits and buildstats aggregation are absent. |
| P09 | Next | Clone profiles, compare resolved kas settings and manage multiconfig contexts | Named profiles, kas dump/lock and a serial queue exist; there is no profile wizard or multiconfig workspace. |
| P10 | Next | Diagnose fetch failures and prepare verified offline inputs | Fetch, download audit, inventory and diagnosis exist; no mirror connectivity or offline-readiness report exists. |
| P11 | Later | Review image CVE/SBOM changes and recorded dispositions | CVE/SPDX commands and artifact discovery exist; there is no vulnerability review dashboard. |
| P12 | Later | Review kernel fragments and recipe/layer upgrades together | Kernel diff/check and devtool upgrade commands exist; there is no guided migration comparison. |
| P13 | Later | Track deployment, serial console and board test evidence per image | devtool deploy/undeploy and testimage entry points exist; there is no board inventory or lab automation adapter. |
| P14 | Foundation | Probe runtime capabilities and strengthen interruption evidence | Diagnostics, preflight and stop/recovery guards exist; optional tasks are not dynamically gated and kas server shutdown can remain unconfirmed. |

## Proposed interactions and upstream foundations

### P01 — Variable explanation

Select a recipe and variable, then inspect its effective value, assignment chain, override context and source location. Keep global, recipe and task contexts explicit. Open the originating file through the selected runtime. Mark a capture stale after metadata changes. Upstream [debugging documentation](https://docs.yoctoproject.org/dev/dev-manual/debugging.html) explains that getvar exposes assignment history and that recipe/task datastores differ. The proposed interactive presentation is Bitloom's design.

### P02 — Recipe and runtime navigation

Provide one keyboard-driven context for the selected provider/version, active .bbappend files, source and build directories, sysroot, task logs and editable metadata. Resolve paths from BitBake rather than assuming the checkout layout. A container-only layer should be searchable and navigable with Enter just like a local layer. The upstream [Technical FAQ](https://wiki.yoctoproject.org/wiki/Technical_FAQ) recommends checking selected recipe versions when changes appear ineffective. Bitloom would connect that evidence to its editors.

### P03 — Rebuild explanation

Associate a metadata edit with captured signature differences and affected task dependencies. Distinguish observed changes from an incomplete forecast; display missing comparison evidence explicitly. Explain cache misses only when metadata, logs or mirror checks support the cause. Upstream [signature debugging](https://docs.yoctoproject.org/dev/dev-manual/debugging.html) documents diffsigs and printdiff for unexpected task execution. This would organize their output, not invent a guaranteed rebuild count or saved-time estimate.

### P04 — Failed-task investigation

Open the failed task's log, executed script and earliest relevant diagnostic together. Navigate source locations through runtime paths, retain the original job/profile and export the investigation. Avoid treating the first generic ERROR as a proven root cause. Upstream [task-log guidance](https://docs.yoctoproject.org/dev/dev-manual/debugging.html) identifies log.do_TASK and run.do_TASK as complementary evidence. Add structured categories for fetch, patch, compiler, packaging QA and rootfs failures around the existing diagnosis.

### P05 — Layer and recipe scaffolding

Offer build-system templates, source location, license and checksum fields, layer destination and kas composition. Show a diff of every generated file and configuration change before saving. Evaluate registration and matching appends after creation. Use installed release tools instead of recreating BitBake parsing. This extends the existing New file editor and layer commands; a draft recipe alone must not be presented as a registered, buildable component.

### P06 — IDE and faster source iteration

Integrate devtool ide-sdk for releases and recipes that support it, including SDK configuration, IDE project location and host/container source mapping. Keep debugging symbols associated with the deployed image. Upstream [Scarthgap SDK documentation](https://docs.yoctoproject.org/5.0.12/sdk-manual/extensible.html) describes native IDE build-tool integration and its faster iteration for supported build systems. Probe installed capabilities; do not promise support for every language, IDE or Yocto release.

### P07 — Image regression comparison

Compare a chosen successful baseline with a new image: package size changes, added/removed files, permissions, owners and links. Connect a package to its recipe and recorded inclusion chain. Require matching machine/configuration or flag incomparable inputs. Upstream [buildhistory documentation](https://docs.yoctoproject.org/5.0.12/dev-manual/build-quality.html) describes package size and image file metadata. The dashboard would consume that evidence, with unavailable fields labelled explicitly.

### P08 — Performance investigation

Aggregate buildstats into a task timeline and duration trends; identify overlapping work without summing it into a false wall-clock duration. Show container memory/CPU limits alongside host measurements, disk/inode headroom and observable resource pressure. Suggestions for parallelism should name their evidence and tradeoffs. Upstream [buildstats](https://docs.yoctoproject.org/5.0.12/ref-manual/classes.html#buildstats) and [build-speed guidance](https://docs.yoctoproject.org/dev/dev-manual/speeding-up-build.html) provide the measurements and configuration controls; no automatic tuning is proposed for the first version.

### P09 — Profiles and multiconfig

Clone a profile with a distinct build directory, compare resolved kas configuration and record debug/release or machine variants together. Expose the selected multiconfig context in every recipe query and job. Preserve serialization within one build directory; independent scheduling would require additional ownership and cache coordination. Upstream [multiconfig documentation](https://docs.yoctoproject.org/dev/dev-manual/multiconfig.html) explains configuration-specific builds. A profile matrix and BitBake multiconfig are separate concepts and should remain distinguishable.

### P10 — Downloads and offline preparation

Show each failing URI with evidence for DNS, proxy, TLS, access, missing source or checksum failure. Suggest concrete mirror/configuration changes without silently weakening verification. For offline preparation, connect fetch-all with release-supported source mirror generation and a recorded network-disabled check. Upstream [fetching documentation](https://docs.yoctoproject.org/bitbake/bitbake-user-manual/bitbake-user-manual-fetching.html) describes mirrors and fetcher behavior. Successful source fetching alone is not proof that a complete build needs no network.

### P11 — CVE and SBOM review

Import reports for the actual built image; show package/recipe identity, vulnerability status, report/database date and changes against a baseline. Preserve evidence for reviewed exceptions and their owner/expiry separately from an upstream patch status. Upstream [Scarthgap vulnerability guidance](https://docs.yoctoproject.org/5.0.12/dev-manual/vulnerabilities.html) notes product mapping can cause false positives and negatives. Detect the installed release's report format: current development documentation uses [SBOM-based checks](https://docs.yoctoproject.org/security-manual/vulnerabilities.html), which must not be assumed available in the Scarthgap test profile.

### P12 — Kernel and upgrade review

Connect requested kernel fragment settings to the final evaluated configuration and the existing kernel_configcheck output. For recipe/layer upgrades, compare selected versions, active appends, source patches and parse/build results against a recorded baseline. Preserve kas revisions and developer source changes. This is a proposed review workflow around current commands; it cannot automatically guarantee compatibility with a new release or board.

### P13 — Board feedback loop

Store device profiles with deployment location, serial access and test commands. Associate logs and results with an exported image hash. Integrate a labgrid adapter for configured equipment instead of inventing board-specific flash/power protocols. Upstream [labgrid documentation](https://labgrid.readthedocs.io/en/latest/overview.html) describes resource/driver abstractions, console access and power control. Keep hardware experiments optional and expose device ownership before a deployment.

### P14 — Capabilities and interruption evidence

Probe tools, release, task availability, runtime paths and terminal/device prerequisites. Explain unavailable operations before queue submission. After interruption, record client/container/server observations separately and enable recipe recovery only when shutdown is established. A wrapper exiting is insufficient evidence. Capability probes must share the queue's build-directory ownership and remain read-only; they must not race a running BitBake invocation.

## Validation approach

The [testbook proposal section](testbook.html#13-feature-assessment) defines P01–P14 experiments for future implementations. Their status is **PLANNED**, separate from the 69 implemented command cases. Until a proposal ships, use the current actions identified in the table to collect baseline evidence. The first implementation batch should connect variable history, recipe navigation, rebuild evidence and task failure context; P14 capability/lifetime work supports those flows.

Every shipped addition should include an English workflow guide, a command/capability description, manual cases with prerequisites and expected artifacts, and screenshots from the actual running TUI when the interaction changes. Capture host and kas-container evidence, including a small terminal. Move a proposal into implemented documentation only after its behavior and limitations can be demonstrated.
