# Where your build runs

Bitloom does not change how you build. Whatever your project uses (BitBake on the machine, kas, kas-container, a Docker or Podman image, or your own script that starts a container), you describe it once in a **profile**, and from then on **every feature works the same way**: builds and the queue, logs and diagnosis, recipes, the image explorer, SBOM and CRA checks, Studio, best practices, the BitBake assistant, the migration assistant, devtool and the developer workbench.

The guided setup (Configuration → *Set up a project*, or the first start in a project folder) recognises these setups and proposes the profile with its evidence; you can also write it by hand in `.bitloom/profiles.json`.

## Supported setups

| Your setup | Profile `mode` | What Bitloom runs for `bitbake core-image-minimal` |
| --- | --- | --- |
| BitBake on the machine (a Poky checkout, the split repositories, a bitbake-setup workspace) | `host` | `bash -c 'cd <project> && source <init script> <build> && exec bitbake core-image-minimal'` |
| kas installed on the machine | `kas` | `kas shell kas.yml -c 'bitbake core-image-minimal'` |
| kas in its container | `kas-container` | `kas-container shell kas.yml -c 'bitbake core-image-minimal'` |
| Your own build image, a new container per command | `container` + `image` | `docker run --rm -i -v <project>:/work -w /work --user <you> <image> bash -c '… bitbake core-image-minimal'` |
| A build container that is already running | `container` + `container_name` | `docker exec -i -w /work <container> bash -c '… bitbake core-image-minimal'` |
| Your own launcher script (`YML=board.yml ./run_build.sh build`) | `wrapper` | `./run_build.sh shell -c 'bitbake core-image-minimal'` |

kas operations (*Build kas configuration*, checkout, dump, lock) run as `kas build kas.yml`, `kas-container build kas.yml` or `./run_build.sh build`. Docker and Podman are interchangeable (`engine`). With kas, several files can be combined (`kas_file: "kas.yml:overlay.yml"`), and Bitloom follows their includes and overlays: MACHINE, DISTRO and the targets come from them.

## One rule for every setup

Bitloom runs commands **through** your setup, and it reads results (logs, `tmp/deploy`, `pkgdata`, the root filesystem, SBOMs, `buildhistory`) **from the build folder**. So the build folder must be visible from where Bitloom runs:

* `host`, `kas`: it is on the machine;
* `kas-container`: set `KAS_WORK_DIR` (or `KAS_BUILD_DIR`) in the profile, as kas-container itself needs;
* `container`: the project is mounted at `container_root` (default `/work`), and the build folder lives in it;
* `wrapper`: your script keeps the build folder on the machine (a bind mount) and the profile knows where (`KAS_WORK_DIR`, or the folder Bitloom reads from the script).

Configuration → *Health* shows the checks for the active profile; the guided setup refuses a profile it cannot use and says why.

With kas, `local.conf` and `bblayers.conf` are written again from the kas files on every run. Bitloom treats the kas files as the source: MACHINE and DISTRO are read from them (an overlay's distribution applies), best-practice findings point at `local_conf_header`, Studio adds overlays, SBOM settings and the migration assistant change the kas files, and the TUI's `local.conf` editor opens the kas file.

## Launcher scripts

Many products build with a script that selects the configuration and starts the build environment, for example `YML=boards/board-a.yml ./run_build.sh build`. Bitloom uses it as it is, with four requirements:

1. **Forward a command into the build environment.** Bitloom calls `./run_build.sh shell -c "<command>"` for every BitBake command, query and probe (`launcher_shell` in the profile changes the form if your script uses another one).
2. **Keep standard input open, and use a terminal only when there is one.** Bitloom reads the output through a pipe: `docker run -i`, and `-t` only when `[ -t 0 ]`. A script that always passes `-t` fails with *the input device is not a TTY*.
3. **Return the command's exit status** (`exec docker run …`), so a failed build is a failed job.
4. **Keep the build folder on the machine** (a bind mount), and export or document where (`KAS_WORK_DIR`).

Interactive tools (devshell, menuconfig, `kas shell`) run in a real terminal from the TUI; for those the script may use `-t`, which is why the test is on `[ -t 0 ]`.

A typical script, and what changes:

```diff
 #!/bin/bash
-YML=$1
-docker run -it --rm -v $PWD:/repo -v $HOME/work:/work ghcr.io/siemens/kas/kas:4.8.1 build /repo/$YML
+# YML=<config>.yml ./run_build.sh build|checkout|dump|lock|shell [-c CMD]
+set -e
+cd "$(dirname "$0")"
+YML=${YML:?set YML to the kas file of the product}
+export KAS_WORK_DIR=${KAS_WORK_DIR:-$HOME/work/$(basename "$YML" .yml)}
+mkdir -p "$KAS_WORK_DIR"
+TTY=; [ -t 0 ] && TTY=-t                 # a terminal only when there is one
+run() {
+  exec docker run -i $TTY --rm --user root -e USER_ID="$(id -u)" -e GROUP_ID="$(id -g)" -e KAS_WORK_DIR=/work \
+       -v "$PWD":/repo:ro -v "$KAS_WORK_DIR":/work -w /work ghcr.io/siemens/kas/kas:4.8.1 "$@"
+}
+case "$1" in
+  shell) if [ "$2" = "-c" ]; then run shell "/repo/$YML" -c "$3"; else run shell "/repo/$YML"; fi ;;
+  build|checkout|dump|lock) run "$1" "/repo/$YML" ;;
+  *) echo "usage: YML=<config>.yml $0 build|checkout|dump|lock|shell [-c CMD]" >&2; exit 2 ;;
+esac
```

The configuration moves from an argument to the `YML` variable, so one script builds every product and Bitloom proposes one profile per product (each kas file that is not only included by others). `--user root` with `USER_ID`/`GROUP_ID` is how the kas image switches to your user: the build files belong to you. This script, with the build folder inside the project, was run by hand and through a Bitloom `wrapper` profile against the Wrynose reference build (`bitbake-getvar` through `shell -c`, every setup check passing). If your script calls `kas-container` instead of `docker run`, the same applies: `kas-container shell "$YML" -c "$3"` for `shell -c`.

The matching profile (the guided setup writes it for you):

```json
{
  "name": "board-a",
  "root": "/home/me/src/product",
  "mode": "wrapper",
  "launcher": ["./run_build.sh"],
  "launcher_shell": ["shell", "-c", "{command}"],
  "environment": {"YML": "boards/board-a.yml", "KAS_WORK_DIR": "/home/me/work/board-a"}
}
```

## Bitloom next to the build, or inside it

**Next to it (the default).** One Bitloom on the machine (or the build server) talks to every setup above. Its queue, history, dashboard and notifications live outside the build containers, which matters with kas-container and `container` + `image`: they start a fresh container for every command.

**Inside it.** If your team works in a long-lived build container, or a build server is that container, Bitloom can run in it like on any machine: there it uses `kas` or `host` profiles. Nothing needs rebuilding: every release has **`bitloom-<version>.pyz`**, Bitloom and its dependencies in one file (pure Python, any `python3` 3.10 or newer, as in the kas image).

```console
# the official kas image, unchanged; the project and Bitloom mounted
$ docker run -d --name build-dash --entrypoint "" --user "$(id -u):$(id -g)" -e HOME=/work/.home \
    -v "$PWD":/work -v "$PWD/bitloom.pyz":/opt/bitloom.pyz:ro -w /work -p 127.0.0.1:8765:8765 \
    ghcr.io/siemens/kas/kas:4.8.1 \
    python3 /opt/bitloom.pyz --web --host 0.0.0.0 --port 8765 --no-browser --persistent-token \
      --config /work/.bitloom/profiles.json --state /work/.bitloom/state
$ cat .bitloom/state/web.token        # the dashboard: http://127.0.0.1:8765/#token=<token>
```

with a `kas` profile in `.bitloom/profiles.json`:

```json
{"active": "board", "profiles": [{"name": "board", "root": "/work", "mode": "kas", "kas_file": "kas.yml"}]}
```

Keep the state folder on the mounted project (or a volume) so history and settings survive the container. To bake it into your own image instead, one line is enough: `COPY bitloom.pyz /opt/` (or install the `.deb`). This was checked with the official kas 4.8.1 image: the dashboard and the build service started from the mounted file, a kas checkout and `bitbake-getvar` ran from it.

Which to choose: next to the build when you use kas-container, fresh containers per command or several kinds of project; inside when the build environment is one long-lived container you already work in.
