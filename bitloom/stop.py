from textual import on
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, SelectionList


class StopScreen(ModalScreen):
    DEFAULT_CSS = """
    StopScreen, RecoveryScreen { align: center middle; }
    StopScreen > Vertical, RecoveryScreen > Vertical { width: 90; height: auto; max-height: 85%; padding: 1 2; border: round $warning; border-title-color: $warning; border-title-style: bold; background: $surface; }
    StopScreen Horizontal, RecoveryScreen Horizontal { height: 3; margin-top: 1; }
    RecoveryScreen SelectionList { height: 12; }
    """
    BINDINGS = [("escape", "dismiss", "Close"), ("ctrl+x", "dismiss", "Close"), ("f", "choose_key('finish')", "Let finish"),
                ("g", "choose_key('graceful')", "Graceful"), ("k", "choose_key('force')", "Force")]

    def __init__(self, job):
        super().__init__()
        self.job = job

    def compose(self):
        with Vertical():
            yield Label(self.job.title, markup=False)
            yield Label("Finish: leave this build running. Graceful: send one SIGINT to the BitBake client, wait without escalation. Force: terminate the process group and offer recovery.")
            yield Label("Recipe metadata is not normally changed by a build. Interrupted work directories may need cleaning; this is not proof of corruption.")
            if self.job.at_risk:
                yield Label("Observed active recipes: " + ", ".join(sorted(self.job.at_risk)), markup=False)
            supported = (self.job.profile.mode == "host" or (self.job.profile.mode == "container" and bool(self.job.managed_container))) and self.job.command[0] == "bitbake"
            if not supported:
                yield Label("Graceful client signalling is unavailable. Force stops the named owned container when present; external server shutdown otherwise remains unconfirmed.")
            with Horizontal():
                yield Button("f Let finish", variant="primary", id="finish")
                yield Button("g Graceful stop", id="graceful", disabled=not supported)
                yield Button("k Force + recovery", variant="warning", id="force")
                yield Button("Esc Close", id="close")

    def on_mount(self):
        self.query_one(Vertical).border_title = "Build interruption"
        self.query_one("#finish", Button).focus()

    def action_choose_key(self, ident):
        button = self.query_one(f"#{ident}", Button)
        if not button.disabled:
            self.dismiss(ident)

    @on(Button.Pressed)
    def choose(self, event):
        self.dismiss(None if event.button.id == "close" else event.button.id)


class RecoveryScreen(ModalScreen):
    DEFAULT_CSS = StopScreen.DEFAULT_CSS
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, recipes):
        super().__init__()
        self.recipes = recipes

    def compose(self):
        with Vertical():
            yield Label("Select recipes to queue bitbake -c clean. This removes work files; save uncommitted edits in WORKDIR first. Downloads and shared state are retained.")
            yield SelectionList(*[(r, r, True) for r in self.recipes], id="recipes")
            with Horizontal():
                yield Button("Queue selected clean", variant="warning", id="clean")
                yield Button("Keep work files", id="keep")

    def on_mount(self):
        self.query_one(Vertical).border_title = "Recipe recovery"
        self.query_one("#recipes", SelectionList).focus()

    @on(Button.Pressed)
    def choose(self, event):
        self.dismiss(self.query_one("#recipes", SelectionList).selected if event.button.id == "clean" else [])
