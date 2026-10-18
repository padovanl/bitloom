# Command reference

All actions use the selected profile/runtime. Required inputs appear in the command dialog.
Some operations need a capability of the project's Yocto release (see [Release capabilities](#release-capabilities)). Bitloom checks it in the project itself (the class in its layers, the tool in its BitBake) and falls back to the release number; where it is missing the TUI, the web dashboard and `--ci` refuse the operation, say why and name the one to use instead.

| ID | Group | Operation | Required input | Tool / arguments | Needs |
| --- | --- | --- | --- | --- | --- |
| `build` | Build | Build target | target | `bitbake` | any release |
| `dry-run` | Build | Dry run | target | `bitbake -n` | any release |
| `parse` | Build | Parse metadata | — | `bitbake -p` | any release |
| `fetch` | Downloads | Fetch recipe sources | target | `bitbake -c fetch` | any release |
| `fetch-all` | Downloads | Fetch all target dependencies | target | `bitbake --runall=fetch` | any release |
| `unpack` | Build | Unpack recipe | target | `bitbake -c unpack` | any release |
| `patch` | Build | Apply recipe patches | target | `bitbake -c patch` | any release |
| `configure` | Build | Configure recipe | target | `bitbake -c configure` | any release |
| `compile` | Build | Compile recipe | target | `bitbake -c compile` | any release |
| `force-compile` | Build | Force compile | target | `bitbake -f -c compile` | any release |
| `install` | Build | Install recipe | target | `bitbake -c install` | any release |
| `package` | Build | Package recipe | target | `bitbake -c package` | any release |
| `rootfs` | Build | Build root filesystem | target | `bitbake -c rootfs` | any release |
| `sdk` | Build | Build SDK | target | `bitbake -c populate_sdk` | any release |
| `esdk` | Build | Build extensible SDK | target | `bitbake -c populate_sdk_ext` | any release |
| `task` | Build | Run custom task | target, task | `bitbake` | any release |
| `clean` | Maintenance | Clean recipe work directory | target | `bitbake -c clean` | any release |
| `cleansstate` | Maintenance | Clean recipe + sstate | target | `bitbake -c cleansstate` | any release |
| `cleanall` | Maintenance | Clean recipe + sstate + downloads | target | `bitbake -c cleanall` | any release |
| `environment` | Inspect | Resolve recipe environment | target | `bitbake -e` | any release |
| `tasks` | Inspect | List recipe tasks | target | `bitbake -c listtasks` | any release |
| `graph` | Inspect | Generate dependency graph | target | `bitbake -g` | any release |
| `signatures` | Inspect | Dump signatures | target | `bitbake -S none` | any release |
| `sig-diff` | Inspect | Explain sstate differences | target | `bitbake -S printdiff` | any release |
| `layers` | Layers | Show layers and priorities | — | `bitbake-layers show-layers` | any release |
| `recipes` | Layers | Show recipes | — | `bitbake-layers show-recipes` | any release |
| `appends` | Layers | Show recipe appends | — | `bitbake-layers show-appends` | any release |
| `overlay` | Layers | Show overlaid recipes | — | `bitbake-layers show-overlayed` | any release |
| `layer-add` | Layers | Add layer | path | `bitbake-layers add-layer` | any release |
| `layer-remove` | Layers | Remove layer | path | `bitbake-layers remove-layer` | any release |
| `layer-create` | Layers | Create layer | path | `bitbake-layers create-layer` | any release |
| `layer-depends` | Layers | Show cross-layer dependencies | — | `bitbake-layers show-cross-depends` | any release |
| `dev-status` | Devtool | Workspace status | — | `devtool status` | any release |
| `dev-modify` | Devtool | Modify recipe | target | `devtool modify` | any release |
| `dev-add` | Devtool | Add source as recipe | target, path | `devtool add` | any release |
| `dev-build` | Devtool | Build workspace recipe | target | `devtool build` | any release |
| `dev-image` | Devtool | Build image with workspace recipes | target | `devtool build-image` | any release |
| `dev-reset` | Devtool | Reset workspace recipe | target | `devtool reset` | any release |
| `dev-finish` | Devtool | Finish recipe into layer | target, path | `devtool finish` | any release |
| `dev-update` | Devtool | Update recipe from source | target | `devtool update-recipe` | any release |
| `dev-upgrade` | Devtool | Upgrade recipe | target | `devtool upgrade` | any release |
| `dev-latest` | Devtool | Check upstream version | target | `devtool latest-version` | any release |
| `dev-deploy` | Devtool | Deploy to device | target, device | `devtool deploy-target` | any release |
| `dev-undeploy` | Devtool | Undeploy from device | target, device | `devtool undeploy-target` | any release |
| `dev-config` | Devtool | Configure help | target | `devtool configure-help` | any release |
| `dev-upgrade-status` | Devtool | Check recipe upgrade status | target | `devtool check-upgrade-status` | any release |
| `recipe-create` | Recipes | Create recipe from URL/source | source | `recipetool create` | any release |
| `packages` | Packages | List built packages | — | `oe-pkgdata-util list-pkgs` | any release |
| `package-files` | Packages | List package files | target | `oe-pkgdata-util list-pkg-files` | any release |
| `find-path` | Packages | Find package owning a path | path | `oe-pkgdata-util find-path` | any release |
| `package-recipe` | Packages | Find recipe for package | target | `oe-pkgdata-util lookup-recipe` | any release |
| `license` | Inspect | Generate SPDX SBOM | target | `bitbake -c create_spdx` | any release |
| `testimage` | Testing | Run image tests | target | `bitbake -c testimage` | any release |
| `ptest` | Testing | Build ptest packages | target | `bitbake -c compile_ptest_base` | any release |
| `devshell` | Terminal | Open recipe development shell | target | `bitbake -c devshell` | any release |
| `menuconfig` | Terminal | Kernel menuconfig | target | `bitbake -c menuconfig` | any release |
| `qemu` | Terminal | Boot image with QEMU | target | `runqemu` | any release |
| `kas-build` | Kas | Build kas configuration | — | `kas build` | any release |
| `kas-checkout` | Kas | Checkout kas repositories | — | `kas checkout` | any release |
| `kas-dump` | Kas | Dump resolved kas configuration | — | `kas dump` | any release |
| `kas-shell` | Kas | Open kas shell | — | `kas shell` | any release |
| `custom` | Utility | Custom command (argument list) | command | `custom argv` | any release |
| `getvar` | Inspect | Resolve one BitBake variable | variable | `bitbake-getvar` | any release |
| `dumpsig` | Inspect | Read signature file | path | `bitbake-dumpsig` | any release |
| `diffsigs` | Inspect | Compare signature files | path, path2 | `bitbake-diffsigs` | any release |
| `kernel-diff` | Kernel | Export kernel config changes | target | `bitbake -c diffconfig` | any release |
| `kernel-fragments` | Kernel | Validate kernel config fragments | target | `bitbake -c kernel_configcheck` | any release |
| `cve` | Security | Run recipe CVE check (cve-check) | target | `bitbake -c cve_check` | [cve-check](#release-capabilities) |
| `kas-lock` | Kas | Generate kas lock file | — | `kas lock` | any release |
| `sbom-cve-recipe` | Security | Recipe CVE analysis from its SBOM (sbom-cve-check) | target | `bitbake -c sbom_cve_check_recipe` | [sbom-cve-check-recipe](#release-capabilities) |
| `recipe-sbom` | Security | Create recipe SBOM (SPDX 3) | target | `bitbake -c create_recipe_sbom` | [recipe-sbom](#release-capabilities) |
| `vex` | Security | Generate VEX metadata | target | `bitbake -c generate_vex` | [vex](#release-capabilities) |
| `sbom-cve-enable` | Security | Enable sbom-cve-check for image builds | — | `bitbake-config-build enable-fragment core/yocto/sbom-cve-check` | [sbom-cve-check](#release-capabilities), [fragments](#release-capabilities) |
| `sbom-cve-disable` | Security | Disable sbom-cve-check fragment | — | `bitbake-config-build disable-fragment core/yocto/sbom-cve-check` | [sbom-cve-check](#release-capabilities), [fragments](#release-capabilities) |
| `fragments` | Setup | List configuration fragments | — | `bitbake-config-build list-fragments` | [fragments](#release-capabilities) |
| `fragment-enable` | Setup | Enable a configuration fragment | fragment | `bitbake-config-build enable-fragment` | [fragments](#release-capabilities) |
| `fragment-disable` | Setup | Disable a configuration fragment | fragment | `bitbake-config-build disable-fragment` | [fragments](#release-capabilities) |
| `setup-status` | Setup | bitbake-setup: compare with upstream | — | `bitbake-setup status` | [bitbake-setup](#release-capabilities) |
| `setup-update` | Setup | bitbake-setup: update layers and configuration | — | `bitbake-setup update` | [bitbake-setup](#release-capabilities) |

Interactive commands hand off to a real terminal and are not stored as queued build logs.
Custom task adds `-c TASK` after the target. kas commands append the selected kas_file.

## Action-specific requirements

- **Clean recipe + sstate:** Removes this recipe's local shared state. Avoid with shared caches in active use.
- **Clean recipe + sstate + downloads:** Removes recipe sources and local shared state.
- **Generate SPDX SBOM:** Requires create-spdx in your image configuration.
- **Run image tests:** Requires testimage configuration and suitable target runner.
- **Build ptest packages:** Recipe must inherit ptest and ptest must be enabled.
- **Custom command (argument list):** Parsed as argv. Shell operators are not interpreted.
- **Run recipe CVE check (cve-check):** Requires the cve-check class and CVE database. Removed in 6.0 Wrynose: use sbom-cve-check.
- **Recipe CVE analysis from its SBOM (sbom-cve-check):** Analyses the recipe SBOM without building the software. The recipe must inherit sbom-cve-check-recipe; reports go to DEPLOY_DIR_IMAGE.
- **Create recipe SBOM (SPDX 3):** Recipe-level SBOM used by sbom-cve-check-recipe.
- **Generate VEX metadata:** Requires INHERIT += "vex". Produces per-recipe and image VEX reports in DEPLOY_DIR_IMAGE.
- **Enable sbom-cve-check for image builds:** Every image build then analyses its SPDX 3 SBOM for CVEs. Reports go to DEPLOY_DIR_IMAGE.
- **List configuration fragments:** Fragments are named pieces of configuration (machine/…, distro/…, core/yocto/…) enabled in conf/toolcfg.conf.
- **Enable a configuration fragment:** Appends the fragment to OE_FRAGMENTS in build/conf/toolcfg.conf, for example core/yocto/sstate-mirror-cdn.
- **bitbake-setup: compare with upstream:** Shows how this bitbake-setup workspace differs from its configuration template and upstream layers.
- **bitbake-setup: update layers and configuration:** Brings the workspace to its template: updates layer checkouts and, after asking, the build configuration.

## Release capabilities

One registry (`bitloom/capabilities.py`) decides what the project's Yocto release can do. Operations, SBOM and CRA settings, the CRA checks and Studio all ask it. **Evidence** is looked for in the project first; the release window is used only when the layers or BitBake are not visible from Bitloom. Configuration shows the answer for the active project (web: *What this release can do*).

| Capability | What it is | Releases | Evidence in the project | Otherwise use |
| --- | --- | --- | --- | --- |
| `spdx2` | SPDX 2.2 SBOMs (create-spdx-2.2) | up to whinlatter 5.3 | `create-spdx-2.2.bbclass` in its layers | `spdx3` |
| `spdx3` | SPDX 3.0 SBOMs (create-spdx-3.0) | styhead 5.1+ | `create-spdx-3.0.bbclass` in its layers | `spdx2` |
| `spdx-supplier-3` | SBOM supplier variables SPDX_PACKAGE_SUPPLIER / SPDX_IMAGE_SUPPLIER | styhead 5.1+ | `create-spdx-3.0.bbclass` in its layers | — |
| `cve-check` | cve-check class | up to whinlatter 5.3 | `cve-check.bbclass` in its layers | `sbom-cve-check` |
| `sbom-cve-check` | sbom-cve-check on image SBOMs | wrynose 6.0+ | `sbom-cve-check.bbclass` in its layers | `cve-check` |
| `sbom-cve-check-recipe` | sbom-cve-check for one recipe | wrynose 6.0+ | `sbom-cve-check-recipe.bbclass` in its layers | `cve-check` |
| `recipe-sbom` | Recipe SBOM task (do_create_recipe_sbom) | wrynose 6.0+ | `sbom-cve-check-recipe.bbclass` in its layers | — |
| `vex` | VEX metadata class | styhead 5.1+ | `vex.bbclass` in its layers | — |
| `fragments` | Configuration fragments (bitbake-config-build) | walnascar 5.2+ | `bitbake-config-build` in its BitBake | — |
| `bitbake-setup` | bitbake-setup workspaces | where the tool exists | `bitbake-setup` in its BitBake; a bitbake-setup workspace | — |
| `unpackdir` | Sources unpacked in UNPACKDIR (before 5.1 recipes read files from WORKDIR) | styhead 5.1+ | release only | — |
| `image-access-split` | allow-empty-password, empty-root-password, allow-root-login (before 5.1 a single debug-tweaks feature) | styhead 5.1+ | release only | — |
| `debug-tweaks` | debug-tweaks image feature | up to scarthgap 5.0 | release only | `image-access-split` |
| `systemd-default` | systemd as the default init manager | wrynose 6.0+ | release only | — |
