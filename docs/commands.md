# Command reference

All actions use the selected profile/runtime. Required inputs appear in the command dialog.
Commands may require classes or options supplied by your selected Yocto release. The Release column shows the Yocto series window; outside it the TUI, web dashboard and `--ci` explain what is missing and suggest the alternative.

| ID | Group | Operation | Required input | Tool / arguments | Release |
| --- | --- | --- | --- | --- | --- |
| `build` | Build | Build target | target | `bitbake` | any |
| `dry-run` | Build | Dry run | target | `bitbake -n` | any |
| `parse` | Build | Parse metadata | — | `bitbake -p` | any |
| `fetch` | Downloads | Fetch recipe sources | target | `bitbake -c fetch` | any |
| `fetch-all` | Downloads | Fetch all target dependencies | target | `bitbake --runall=fetch` | any |
| `unpack` | Build | Unpack recipe | target | `bitbake -c unpack` | any |
| `patch` | Build | Apply recipe patches | target | `bitbake -c patch` | any |
| `configure` | Build | Configure recipe | target | `bitbake -c configure` | any |
| `compile` | Build | Compile recipe | target | `bitbake -c compile` | any |
| `force-compile` | Build | Force compile | target | `bitbake -f -c compile` | any |
| `install` | Build | Install recipe | target | `bitbake -c install` | any |
| `package` | Build | Package recipe | target | `bitbake -c package` | any |
| `rootfs` | Build | Build root filesystem | target | `bitbake -c rootfs` | any |
| `sdk` | Build | Build SDK | target | `bitbake -c populate_sdk` | any |
| `esdk` | Build | Build extensible SDK | target | `bitbake -c populate_sdk_ext` | any |
| `task` | Build | Run custom task | target, task | `bitbake` | any |
| `clean` | Maintenance | Clean recipe work directory | target | `bitbake -c clean` | any |
| `cleansstate` | Maintenance | Clean recipe + sstate | target | `bitbake -c cleansstate` | any |
| `cleanall` | Maintenance | Clean recipe + sstate + downloads | target | `bitbake -c cleanall` | any |
| `environment` | Inspect | Resolve recipe environment | target | `bitbake -e` | any |
| `tasks` | Inspect | List recipe tasks | target | `bitbake -c listtasks` | any |
| `graph` | Inspect | Generate dependency graph | target | `bitbake -g` | any |
| `signatures` | Inspect | Dump signatures | target | `bitbake -S none` | any |
| `sig-diff` | Inspect | Explain sstate differences | target | `bitbake -S printdiff` | any |
| `layers` | Layers | Show layers and priorities | — | `bitbake-layers show-layers` | any |
| `recipes` | Layers | Show recipes | — | `bitbake-layers show-recipes` | any |
| `appends` | Layers | Show recipe appends | — | `bitbake-layers show-appends` | any |
| `overlay` | Layers | Show overlaid recipes | — | `bitbake-layers show-overlayed` | any |
| `layer-add` | Layers | Add layer | path | `bitbake-layers add-layer` | any |
| `layer-remove` | Layers | Remove layer | path | `bitbake-layers remove-layer` | any |
| `layer-create` | Layers | Create layer | path | `bitbake-layers create-layer` | any |
| `layer-depends` | Layers | Show cross-layer dependencies | — | `bitbake-layers show-cross-depends` | any |
| `dev-status` | Devtool | Workspace status | — | `devtool status` | any |
| `dev-modify` | Devtool | Modify recipe | target | `devtool modify` | any |
| `dev-add` | Devtool | Add source as recipe | target, path | `devtool add` | any |
| `dev-build` | Devtool | Build workspace recipe | target | `devtool build` | any |
| `dev-image` | Devtool | Build image with workspace recipes | target | `devtool build-image` | any |
| `dev-reset` | Devtool | Reset workspace recipe | target | `devtool reset` | any |
| `dev-finish` | Devtool | Finish recipe into layer | target, path | `devtool finish` | any |
| `dev-update` | Devtool | Update recipe from source | target | `devtool update-recipe` | any |
| `dev-upgrade` | Devtool | Upgrade recipe | target | `devtool upgrade` | any |
| `dev-latest` | Devtool | Check upstream version | target | `devtool latest-version` | any |
| `dev-deploy` | Devtool | Deploy to device | target, device | `devtool deploy-target` | any |
| `dev-undeploy` | Devtool | Undeploy from device | target, device | `devtool undeploy-target` | any |
| `dev-config` | Devtool | Configure help | target | `devtool configure-help` | any |
| `dev-upgrade-status` | Devtool | Check recipe upgrade status | target | `devtool check-upgrade-status` | any |
| `recipe-create` | Recipes | Create recipe from URL/source | source | `recipetool create` | any |
| `packages` | Packages | List built packages | — | `oe-pkgdata-util list-pkgs` | any |
| `package-files` | Packages | List package files | target | `oe-pkgdata-util list-pkg-files` | any |
| `find-path` | Packages | Find package owning a path | path | `oe-pkgdata-util find-path` | any |
| `package-recipe` | Packages | Find recipe for package | target | `oe-pkgdata-util lookup-recipe` | any |
| `license` | Inspect | Generate SPDX SBOM | target | `bitbake -c create_spdx` | any |
| `testimage` | Testing | Run image tests | target | `bitbake -c testimage` | any |
| `ptest` | Testing | Build ptest packages | target | `bitbake -c compile_ptest_base` | any |
| `devshell` | Terminal | Open recipe development shell | target | `bitbake -c devshell` | any |
| `menuconfig` | Terminal | Kernel menuconfig | target | `bitbake -c menuconfig` | any |
| `qemu` | Terminal | Boot image with QEMU | target | `runqemu` | any |
| `kas-build` | Kas | Build kas configuration | — | `kas build` | any |
| `kas-checkout` | Kas | Checkout kas repositories | — | `kas checkout` | any |
| `kas-dump` | Kas | Dump resolved kas configuration | — | `kas dump` | any |
| `kas-shell` | Kas | Open kas shell | — | `kas shell` | any |
| `custom` | Utility | Custom command (argument list) | command | `custom argv` | any |
| `getvar` | Inspect | Resolve one BitBake variable | variable | `bitbake-getvar` | any |
| `dumpsig` | Inspect | Read signature file | path | `bitbake-dumpsig` | any |
| `diffsigs` | Inspect | Compare signature files | path, path2 | `bitbake-diffsigs` | any |
| `kernel-diff` | Kernel | Export kernel config changes | target | `bitbake -c diffconfig` | any |
| `kernel-fragments` | Kernel | Validate kernel config fragments | target | `bitbake -c kernel_configcheck` | any |
| `cve` | Security | Run recipe CVE check (cve-check) | target | `bitbake -c cve_check` | …whinlatter |
| `kas-lock` | Kas | Generate kas lock file | — | `kas lock` | any |
| `sbom-cve-recipe` | Security | Recipe CVE analysis from its SBOM (sbom-cve-check) | target | `bitbake -c sbom_cve_check_recipe` | wrynose+ |
| `recipe-sbom` | Security | Create recipe SBOM (SPDX 3) | target | `bitbake -c create_recipe_sbom` | wrynose+ |
| `vex` | Security | Generate VEX metadata | target | `bitbake -c generate_vex` | any |
| `sbom-cve-enable` | Security | Enable sbom-cve-check for image builds | — | `bitbake-config-build enable-fragment core/yocto/sbom-cve-check` | wrynose+ |
| `sbom-cve-disable` | Security | Disable sbom-cve-check fragment | — | `bitbake-config-build disable-fragment core/yocto/sbom-cve-check` | wrynose+ |

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
