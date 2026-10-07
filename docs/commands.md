# Command reference

All actions use the selected profile/runtime. Required inputs appear in the command dialog.
Commands may require classes or options supplied by your selected Yocto release.

| ID | Group | Operation | Required input | Tool / arguments |
| --- | --- | --- | --- | --- |
| `build` | Build | Build target | target | `bitbake` |
| `dry-run` | Build | Dry run | target | `bitbake -n` |
| `parse` | Build | Parse metadata | — | `bitbake -p` |
| `fetch` | Downloads | Fetch recipe sources | target | `bitbake -c fetch` |
| `fetch-all` | Downloads | Fetch all target dependencies | target | `bitbake --runall=fetch` |
| `unpack` | Build | Unpack recipe | target | `bitbake -c unpack` |
| `patch` | Build | Apply recipe patches | target | `bitbake -c patch` |
| `configure` | Build | Configure recipe | target | `bitbake -c configure` |
| `compile` | Build | Compile recipe | target | `bitbake -c compile` |
| `force-compile` | Build | Force compile | target | `bitbake -f -c compile` |
| `install` | Build | Install recipe | target | `bitbake -c install` |
| `package` | Build | Package recipe | target | `bitbake -c package` |
| `rootfs` | Build | Build root filesystem | target | `bitbake -c rootfs` |
| `sdk` | Build | Build SDK | target | `bitbake -c populate_sdk` |
| `esdk` | Build | Build extensible SDK | target | `bitbake -c populate_sdk_ext` |
| `task` | Build | Run custom task | target, task | `bitbake` |
| `clean` | Maintenance | Clean recipe work directory | target | `bitbake -c clean` |
| `cleansstate` | Maintenance | Clean recipe + sstate | target | `bitbake -c cleansstate` |
| `cleanall` | Maintenance | Clean recipe + sstate + downloads | target | `bitbake -c cleanall` |
| `environment` | Inspect | Resolve recipe environment | target | `bitbake -e` |
| `tasks` | Inspect | List recipe tasks | target | `bitbake -c listtasks` |
| `graph` | Inspect | Generate dependency graph | target | `bitbake -g` |
| `signatures` | Inspect | Dump signatures | target | `bitbake -S none` |
| `sig-diff` | Inspect | Explain sstate differences | target | `bitbake -S printdiff` |
| `layers` | Layers | Show layers and priorities | — | `bitbake-layers show-layers` |
| `recipes` | Layers | Show recipes | — | `bitbake-layers show-recipes` |
| `appends` | Layers | Show recipe appends | — | `bitbake-layers show-appends` |
| `overlay` | Layers | Show overlaid recipes | — | `bitbake-layers show-overlayed` |
| `layer-add` | Layers | Add layer | path | `bitbake-layers add-layer` |
| `layer-remove` | Layers | Remove layer | path | `bitbake-layers remove-layer` |
| `layer-create` | Layers | Create layer | path | `bitbake-layers create-layer` |
| `layer-depends` | Layers | Show cross-layer dependencies | — | `bitbake-layers show-cross-depends` |
| `dev-status` | Devtool | Workspace status | — | `devtool status` |
| `dev-modify` | Devtool | Modify recipe | target | `devtool modify` |
| `dev-add` | Devtool | Add source as recipe | target, path | `devtool add` |
| `dev-build` | Devtool | Build workspace recipe | target | `devtool build` |
| `dev-image` | Devtool | Build image with workspace recipes | target | `devtool build-image` |
| `dev-reset` | Devtool | Reset workspace recipe | target | `devtool reset` |
| `dev-finish` | Devtool | Finish recipe into layer | target, path | `devtool finish` |
| `dev-update` | Devtool | Update recipe from source | target | `devtool update-recipe` |
| `dev-upgrade` | Devtool | Upgrade recipe | target | `devtool upgrade` |
| `dev-latest` | Devtool | Check upstream version | target | `devtool latest-version` |
| `dev-deploy` | Devtool | Deploy to device | target, device | `devtool deploy-target` |
| `dev-undeploy` | Devtool | Undeploy from device | target, device | `devtool undeploy-target` |
| `dev-config` | Devtool | Configure help | target | `devtool configure-help` |
| `dev-upgrade-status` | Devtool | Check recipe upgrade status | target | `devtool check-upgrade-status` |
| `recipe-create` | Recipes | Create recipe from URL/source | source | `recipetool create` |
| `packages` | Packages | List built packages | — | `oe-pkgdata-util list-pkgs` |
| `package-files` | Packages | List package files | target | `oe-pkgdata-util list-pkg-files` |
| `find-path` | Packages | Find package owning a path | path | `oe-pkgdata-util find-path` |
| `package-recipe` | Packages | Find recipe for package | target | `oe-pkgdata-util lookup-recipe` |
| `license` | Inspect | Generate SPDX SBOM | target | `bitbake -c create_spdx` |
| `testimage` | Testing | Run image tests | target | `bitbake -c testimage` |
| `ptest` | Testing | Build ptest packages | target | `bitbake -c compile_ptest_base` |
| `devshell` | Terminal | Open recipe development shell | target | `bitbake -c devshell` |
| `menuconfig` | Terminal | Kernel menuconfig | target | `bitbake -c menuconfig` |
| `qemu` | Terminal | Boot image with QEMU | target | `runqemu` |
| `kas-build` | Kas | Build kas configuration | — | `kas build` |
| `kas-checkout` | Kas | Checkout kas repositories | — | `kas checkout` |
| `kas-dump` | Kas | Dump resolved kas configuration | — | `kas dump` |
| `kas-shell` | Kas | Open kas shell | — | `kas shell` |
| `custom` | Utility | Custom command (argument list) | command | `custom argv` |
| `getvar` | Inspect | Resolve one BitBake variable | variable | `bitbake-getvar` |
| `dumpsig` | Inspect | Read signature file | path | `bitbake-dumpsig` |
| `diffsigs` | Inspect | Compare signature files | path, path2 | `bitbake-diffsigs` |
| `kernel-diff` | Kernel | Export kernel config changes | target | `bitbake -c diffconfig` |
| `kernel-fragments` | Kernel | Validate kernel config fragments | target | `bitbake -c kernel_configcheck` |
| `cve` | Security | Run recipe CVE check | target | `bitbake -c cve_check` |
| `kas-lock` | Kas | Generate kas lock file | — | `kas lock` |

Interactive commands hand off to a real terminal and are not stored as queued build logs.
Custom task adds `-c TASK` after the target. kas commands append the selected kas_file.

## Action-specific requirements

- **Clean recipe + sstate:** Removes this recipe's local shared state. Avoid with shared caches in active use.
- **Clean recipe + sstate + downloads:** Removes recipe sources and local shared state.
- **Generate SPDX SBOM:** Requires create-spdx in your image configuration.
- **Run image tests:** Requires testimage configuration and suitable target runner.
- **Build ptest packages:** Recipe must inherit ptest and ptest must be enabled.
- **Custom command (argument list):** Parsed as argv. Shell operators are not interpreted.
- **Run recipe CVE check:** Requires the cve-check class and CVE database.
