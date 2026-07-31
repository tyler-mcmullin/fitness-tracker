import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from splitsaver.database import get_splits


class HistorySplitsScreen:
    """Read-only list of splits, for browsing history. Tap a row to see its sessions."""

    def __init__(self, conn, window, on_open_split, on_back):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow, needed for dialogs
        on_open_split: callback(split_id, split_name) -> called when a split is tapped
        on_back: callback() -> called to leave history browsing entirely
        """
        self.conn = conn
        self.window = window
        self.on_open_split = on_open_split
        self.on_back = on_back

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        back_button = toga.Button(
            "< Back", on_press=lambda widget: self.on_back(), style=Pack(margin=(0, 0, 10, 0))
        )

        title = toga.Label(
            "History", style=Pack(margin=(0, 0, 10, 0), font_size=18, font_weight="bold")
        )

        self.list_view = toga.DetailedList(
            style=Pack(flex=1),
            on_select=self._on_select,
        )

        box.add(back_button)
        box.add(title)
        box.add(self.list_view)
        return box

    def refresh(self):
        splits = get_splits(self.conn)  # list of (id, name, notes)
        self._ids_by_row = [s[0] for s in splits]
        self.list_view.data = [{"title": s[1], "subtitle": s[2] or ""} for s in splits]

    def _on_select(self, widget):
        if widget.selection is None:
            return
        row_index = self.list_view.data.index(widget.selection)
        split_id = self._ids_by_row[row_index]
        split_name = widget.selection.title
        self.on_open_split(split_id, split_name)