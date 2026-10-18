"""The build progress line of the TUI, drawn like the web dashboard's: task count, a bar with a live head,
percentage and ETA on one row, coloured by the job's state."""
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

EIGHTHS = " ▏▎▍▌▋▊▉"


class TaskProgress(Static):
    DEFAULT_CSS = """
    TaskProgress { height: 1; }
    """

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self.status, self.done, self.total, self.eta, self.tick = "", 0, 0, None, 0
        self.timer = None

    def on_mount(self):
        self.timer = self.set_interval(.14, self.step, pause=True)

    def on_resize(self):
        self.refresh()

    def show(self, status: str, progress=None, eta: str | None = None) -> None:
        """status of the job; progress = (task N, of M) as BitBake reports it; eta as text or None."""
        done, total = (progress or (0, 0))[:2]
        new = (status, done, total, eta)
        if new == (self.status, self.done, self.total, self.eta):
            return
        self.status, self.done, self.total, self.eta = new
        if self.timer:
            self.timer.resume() if status == "running" else self.timer.pause()
        self.refresh()

    def step(self):
        self.tick += 1
        self.refresh()

    def fraction(self) -> float | None:
        if self.status == "success":
            return 1.0
        if not self.total:
            return None
        # BitBake's "task N of M" reaches M when the last task starts: only success is 100%.
        return min(self.done / self.total, .99)

    def render(self):
        theme = self.app.current_theme
        color = {"running": theme.accent, "success": theme.success, "failed": theme.error, "cancelling": theme.warning}.get(self.status, theme.foreground or "white")
        muted = "dim"
        width = max(10, self.size.width)
        fraction = self.fraction()
        # Label: "252 / 420 tasks", then percentage and ETA; the bar takes what is left.
        label = Text()
        if self.status == "success":
            label.append("done", style="bold")
            if self.total:
                label.append(f" · {self.total:,} tasks", style=muted)
        elif self.total:
            label.append(f"{self.done:,}", style="bold")
            label.append(f" / {self.total:,} tasks", style=muted)
        elif self.status == "running":
            label.append("waiting for task counts", style=muted)
        right = Text()
        if fraction is not None:
            right.append(f"{100 * fraction:.0f}%" if fraction in (0, 1) or fraction >= .995 else f"{100 * fraction:.1f}%", style=f"bold {color}")
        if self.eta:
            right.append(f"  ETA ~{self.eta}", style=muted)
        if self.status == "running" and self.total and self.done >= self.total:
            right.append("  last task running", style=muted)
        room = width - label.cell_len - right.cell_len - 4
        if room < 12:                      # narrow panel: the bar and the percentage matter most
            label = Text()
            room = width - right.cell_len - 2
        bar = self.bar(max(6, room), fraction, color)
        line = Text.assemble(label, " " if label.plain else "", bar, " ", right)
        line.no_wrap = True
        return line

    def bar(self, cells: int, fraction: float | None, color: str) -> Text:
        track = "─"
        text = Text()
        if fraction is None:
            if self.status != "running":
                return Text(track * cells, style="dim")
            # Indeterminate: a short segment gliding along the track.
            span = max(3, cells // 6)
            position = self.tick % (cells + span) - span
            for index in range(cells):
                text.append("━" if position <= index < position + span else track, style=color if position <= index < position + span else "dim")
            return text
        exact = fraction * cells
        full = int(exact)
        text.append("━" * full, style=f"bold {color}")
        if full < cells:
            if self.status == "running":
                # The head pulses where BitBake is now.
                text.append("●" if self.tick // 4 % 2 == 0 else "◉", style=f"bold {color}")
            elif self.status == "failed":
                text.append("✖", style=f"bold {color}")
            else:
                partial = EIGHTHS[int((exact - full) * 8)]
                text.append(partial if partial.strip() else track, style=color if partial.strip() else "dim")
            text.append(track * (cells - full - 1), style="dim")
        return text
