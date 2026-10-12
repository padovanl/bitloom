"""Rows of section controls that wrap into several lines when the terminal is narrow."""
from __future__ import annotations

from textual.containers import Horizontal
from textual.widgets import Button, Static


class ToolBar(Horizontal):
    """A row of controls that becomes a grid of several rows when they do not fit, so no
    control is cut off or squeezed to zero width (Textual rows do not wrap by themselves).
    Buttons and labels take one cell; inputs and selects take as many cells as 24 columns."""

    DEFAULT_CSS = """
    ToolBar { scrollbar-size-horizontal: 0; }
    ToolBar.wrapped { grid-gutter: 0 1; grid-rows: 1; }
    ToolBar.wrapped Button { margin-right: 0; }
    """

    def __init__(self, *children, max_rows: int = 4, **kwargs):
        super().__init__(*children, **kwargs)
        self.max_rows = max_rows

    def on_resize(self) -> None:
        self.reflow()

    def reflow(self) -> None:
        width = self.size.width
        children = [child for child in self.children if child.display]
        if not width or not children:
            return
        fixed = [isinstance(child, Button) or type(child) is Static for child in children]
        # label + 1 space each side (Button pads it) + padding 0 1 + margin 1
        natural = [child.label.cell_len + 5 if isinstance(child, Button)
                   else len(str(child.renderable)) + 1 if type(child) is Static
                   else max(24, child.styles.width.cells or 0) if child.styles.width and child.styles.width.cells else 24
                   for child in children]
        height = self.app.size.height
        limit = 1 if height < 22 else min(self.max_rows, 3 if height < 30 else 4)
        # Tiny terminals keep one row that scrolls to the focused control instead of wrapping.
        self.styles.overflow_x = "auto" if limit == 1 else "hidden"
        if sum(natural) <= width or limit == 1:
            if self.has_class("wrapped"):
                self.remove_class("wrapped")
                self.styles.layout = "horizontal"
                self.styles.height = None
                for child in children:
                    child.styles.width = None
                    child.styles.column_span = None
            return
        cell = max([n for n, f in zip(natural, fixed) if f] or [24])
        columns = max(1, (width + 1) // (cell + 1))  # one column of gutter between cells
        spans = [1 if f else min(columns, -(-n // cell)) for n, f in zip(natural, fixed)]
        rows, position = 1, 0
        for index, (child, span) in enumerate(zip(children, spans)):
            # A label stays on the row of the field it describes.
            keep = span + (spans[index + 1] if type(child) is Static and index + 1 < len(spans) else 0)
            if position and position + min(keep, columns) > columns:
                # The grid fills free cells in order: widen the previous control to end the row.
                spans[index - 1] += columns - position
                rows, position = rows + 1, 0
            position += span
        for child, span in zip(children, spans):
            child.styles.column_span = span
            child.styles.width = "100%"
        self.add_class("wrapped")
        self.styles.layout = "grid"
        self.styles.grid_size_columns = columns
        # Short terminals keep room for content: extra rows stay reachable through their keys.
        self.styles.height = min(rows, limit)
