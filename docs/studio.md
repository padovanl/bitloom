# Studio

Studio creates the metadata of your own product: a product layer, your distribution instead of Poky, machines, images, recipes and appends. Every field explains itself, defaults follow the detected Yocto release, and you see every file before anything is written.

Open it with **Recipes → `c`** in the TUI, **Ctrl+P → Studio**, or section **5** of the [web dashboard](web.md).

![Studio creating a distribution on Wrynose](assets/studio.png)

## What you can create

| Kind | Files | Notes |
| --- | --- | --- |
| Product layer | `conf/layer.conf`, `README.md`, `COPYING.MIT` | Collection, priority, `LAYERDEPENDS`, `LAYERSERIES_COMPAT` from the detected release |
| Distribution | `conf/distro/<id>.conf` | Based on Poky (`require conf/distro/poky.conf`) or standalone OE-Core defaults; `DISTRO_NAME`/`VERSION`, `MAINTAINER`, vendors, `INIT_MANAGER`, `DISTRO_FEATURES` to add and remove, package format, `security_flags.inc`, SBOM policy with the supplier |
| Machine | `conf/machine/<id>.conf` | Derived from a reference machine (`require` + `MACHINEOVERRIDES`), `MACHINE_FEATURES`, `SERIAL_CONSOLES`, preferred kernel |
| Image | `recipes-core/images/<name>.bb` | `inherit core-image` or extend an existing image, `IMAGE_FEATURES`, packages, `IMAGE_FSTYPES`, extra space |
| Application recipe | `recipes-example/<name>/…` | Licensed sample with CMake, Meson, Make, Python or Rust sources |
| Recipe append | `recipes-*/<recipe>/<recipe>_%.bbappend` | `FILESEXTRAPATHS`, an installed file, extra assignments |

Release-dependent choices are applied for you:

* `INIT_MANAGER` defaults to systemd on Wrynose, which made it the default.
* The image developer-access features follow 5.1: `debug-tweaks` was split into `allow-empty-password`, `empty-root-password` and `allow-root-login`; Studio refuses `debug-tweaks` on 5.1 and later.
* Appends read files from `UNPACKDIR` on 5.1 and later, `WORKDIR` before.
* The SBOM supplier uses `SPDX_PACKAGE_SUPPLIER`/`SPDX_IMAGE_SUPPLIER` on SPDX 3 releases and `SPDX_SUPPLIER` on SPDX 2.2 releases.

## Where files go

Choose an existing product layer (upstream layers such as `meta`, `meta-poky` and fetched repositories are never offered) or *new layer…*. Studio writes only inside the project root or `KAS_WORK_DIR`, refuses any file that already exists and writes all files or none.

## Registration

| Profile | After creation |
| --- | --- |
| host, container | A new layer is registered with a queued `bitbake-layers add-layer`. For a distribution or machine, *Use for this profile* sets the profile's `DISTRO`/`MACHINE`. |
| kas, kas-container | Studio writes `kas-studio-<layer>.yml` (the new layer as a repository plus `distro:`, `machine:` or `target:`) and appends it to the profile's `kas_file`. Team profiles are not modified: clone them first. |
| wrapper | The overlay is written; add it to the configuration your launcher passes to kas. |

Images and recipes set the build target, so `b` builds them next.

## Keyboard

`↑`/`↓` choose the kind, `Tab` moves through the fields, `Space` toggles list entries, `^O` creates, `Esc` closes.
