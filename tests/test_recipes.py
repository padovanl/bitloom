"""Image recipes for the target field, recipes organised by layer and folder, steady history."""
import json
import threading
import urllib.error
import urllib.request

from bitloom.inspectors import images, is_image, metadata, organize, recipe_name
from bitloom.models import Profile


def layer(root, name, files):
    (root / name / "conf").mkdir(parents=True)
    (root / name / "conf/layer.conf").write_text(f'LAYERSERIES_COMPAT_{name} = "wrynose"\n')
    for path, text in files.items():
        (root / name / path).parent.mkdir(parents=True, exist_ok=True)
        (root / name / path).write_text(text)


def workspace(tmp_path):
    layer(tmp_path, "meta", {
        "recipes-core/images/core-image-minimal.bb": 'SUMMARY = "A small image"\ninherit core-image\n',
        "recipes-core/images/core-image-minimal-dev.bb": 'require recipes-core/images/core-image-minimal.bb\n',
        "recipes-core/busybox/busybox_1.37.0.bb": 'SUMMARY = "Tiny utilities"\n',
        "recipes-kernel/linux/linux-yocto-fitimage.bb": 'inherit kernel-fit-image\n',      # a kernel, not an image
        "recipes-sato/images/core-image-sato.bb": 'SUMMARY = "${DISTRO} image with Sato"\nIMAGE_INSTALL += "x"\ninherit core-image\n',
        "classes-recipe/image.bbclass": "# image class\n",
    })
    layer(tmp_path, "meta-selftest", {"recipes-test/images/test-empty-image.bb": "inherit image\n"})
    layer(tmp_path, "meta-mine", {"recipes-core/busybox/busybox_%.bbappend": 'FILESEXTRAPATHS:prepend := "x"\n'})
    deploy = tmp_path / "build/tmp/deploy/images/qemux86-64"
    deploy.mkdir(parents=True)
    (deploy / "core-image-sato-qemux86-64.rootfs.manifest").write_text("busybox 1.37.0\n")
    return Profile(name="p", root=str(tmp_path), targets=["core-image-minimal"])


def test_organize_by_layer_and_folder(tmp_path):
    profile = workspace(tmp_path)
    entries = {e.name: e for e in organize(metadata(profile))}
    assert (entries["busybox_1.37.0.bb"].layer, entries["busybox_1.37.0.bb"].group) == ("meta", "recipes-core")
    assert (entries["busybox_%.bbappend"].layer, entries["image.bbclass"].group) == ("meta-mine", "classes-recipe")
    assert recipe_name(entries["busybox_1.37.0.bb"]) == ("busybox", "1.37.0") and recipe_name(entries["busybox_%.bbappend"]) == ("busybox", "%")
    assert not is_image(entries["linux-yocto-fitimage.bb"]) and not is_image(entries["busybox_1.37.0.bb"])


def test_images_ranked_for_the_target_field(tmp_path):
    rows = images(workspace(tmp_path))
    names = [r["name"] for r in rows]
    # Configured target first, then what was built, then the layers' images, examples last.
    assert names == ["core-image-minimal", "core-image-sato", "core-image-minimal-dev", "test-empty-image"]
    sato = rows[1]
    assert sato["built"] and not sato["configured"] and sato["summary"] == "image with Sato"   # ${DISTRO} is not shown raw
    assert rows[-1]["example"] and rows[0]["configured"] and rows[0]["summary"] == "A small image"


def test_web_images_and_organised_metadata(tmp_path):
    from bitloom.daemon import rpc
    from bitloom.models import Settings
    from bitloom.web import Dashboard, create_server
    profile = workspace(tmp_path / "ws")
    config = tmp_path / "profiles.json"
    settings = Settings(config)
    settings.profiles, settings.active = [profile], "p"
    settings.save()
    board = Dashboard(config, tmp_path / "state", token="t")
    server = create_server(board, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def get(path):
        return json.loads(urllib.request.urlopen(urllib.request.Request(base + path, headers={"X-Bitloom-Token": "t"})).read())
    try:
        assert [r["name"] for r in get("/api/images?profile=p")["rows"]][:2] == ["core-image-minimal", "core-image-sato"]
        rows = {r["name"]: r for r in get("/api/metadata?profile=p")["rows"]}
        assert rows["core-image-sato.bb"]["image"] and rows["core-image-sato.bb"]["group"] == "recipes-sato"
        assert (rows["busybox_1.37.0.bb"]["recipe"], rows["busybox_1.37.0.bb"]["version"], rows["busybox_1.37.0.bb"]["layer"]) == ("busybox", "1.37.0", "meta")
        assert sorted(r["kind"] for r in get("/api/metadata?profile=p&q=meta-mine")["rows"]) == ["bbappend", "layer"]
        # Studio: the preview lists what Create will do; a bad value names the field to fix.
        def post(path, body):
            request = urllib.request.Request(base + path, json.dumps(body).encode(), {"X-Bitloom-Token": "t", "Content-Type": "application/json"})
            try:
                return json.loads(urllib.request.urlopen(request).read())
            except urllib.error.HTTPError as error:
                return json.loads(error.read())
        fields = get("/api/studio/fields?profile=p&kind=distro")
        assert fields["sections"]["where"] and fields["fields"][0]["section"] == "where"
        values = {f["id"]: f["default"] for f in fields["fields"]}
        preview = post("/api/studio/preview", {"profile": "p", "kind": "distro", "values": values})
        assert preview["main"].startswith("conf/distro/") and preview["steps"][0].startswith("Write ")
        assert post("/api/studio/preview", {"profile": "p", "kind": "distro", "values": {**values, "name": "Bad"}})["field"] == "name"
    finally:
        server.shutdown()
        try:
            rpc(board.state, {"op": "stop"})
        except (OSError, ValueError):
            pass


async def test_tui_image_picker_and_steady_history(tmp_path):
    import sys
    from textual.widgets import DataTable, Input, Tree
    from bitloom.app import BitloomApp
    from bitloom.cli import make_demo
    from bitloom.screens import ImagePickerScreen
    app = BitloomApp(make_demo(tmp_path / "demo"), tmp_path / "state")
    async with app.run_test(size=(150, 46)) as pilot:
        for _ in range(50):
            if app.image_rows:
                break
            await pilot.pause(.1)
        assert [r["name"] for r in app.image_rows] == ["demo-image"]
        target = app.query_one("#target", Input)
        await pilot.press("t")
        target.value = ""
        await pilot.press("down")
        await pilot.pause(.2)
        assert isinstance(app.screen, ImagePickerScreen)
        await pilot.press("enter")
        await pilot.pause(.2)
        assert target.value == "demo-image" and not isinstance(app.screen, ImagePickerScreen)
        # The layer tree goes layer -> folder -> file.
        tree = app.query_one("#layer-tree", Tree)
        demo = next(node for node in tree.root.children if node.data and node.data.name == "meta-demo")
        assert {child.data.group for child in demo.children} == {"recipes-core", "recipes-apps"}
        # History refreshes update cells in place: rows are not rebuilt while a job ticks.
        job = app.runner.submit(app.profile, "tick", [sys.executable, "-c", "import time; time.sleep(1.5)"])
        await pilot.pause(.4)
        table = app.query_one("#history", DataTable)
        cleared = []
        original = table.clear
        table.clear = lambda *a, **k: (cleared.append(1), original(*a, **k))[1]
        app.refresh_history()
        app.refresh_history()
        assert not cleared and job.id in [key.value for key in table.rows]
        await app.runner.consumer
    app.store.close()
