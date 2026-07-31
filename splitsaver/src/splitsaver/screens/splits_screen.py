import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import create_split, get_splits, delete_split


class SplitsScreen:
    """Shows the list of splits. Tap a row to open it, swipe to delete, or use the field below to add one."""

    def __init__(self, conn, window, on_open_split):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow, needed for dialogs
        on_open_split: callback(split_id, split_name) -> called when a split is tapped
        """
        self.conn = conn
        self.window = window
        self.on_open_split = on_open_split

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        title = toga.Label(
            "My Splits",
            style=Pack(margin=(0, 0, 10, 0), font_size=18, font_weight="bold"),
        )

        self.list_view = toga.DetailedList(
            style=Pack(flex=1, margin=(0, 0, 10, 0)),
            on_select=self._on_select,
            on_primary_action=self._on_swipe_delete,
        )

        add_row = toga.Box(style=Pack(direction=ROW))
        self.new_split_input = toga.TextInput(
            placeholder="ex: Push Pull Legs",
            style=Pack(flex=1, margin=(0, 5, 0, 0)),
        )
        add_button = toga.Button("Add Split", on_press=self._on_add, style=Pack(margin=0))
        add_row.add(self.new_split_input)
        add_row.add(add_button)

        box.add(title)
        box.add(self.list_view)
        box.add(add_row)
        return box

    def refresh(self):
        """Re-reads splits from the database and repopulates the list."""
        splits = get_splits(self.conn)  # list of (id, name, notes)
        self._ids_by_row = [s[0] for s in splits]
        self.list_view.data = [{"title": s[1], "subtitle": s[2] or ""} for s in splits]

    # -----------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------

    async def _on_add(self, widget):
        name = self.new_split_input.value.strip()
        if not name:
            await self.window.dialog(toga.InfoDialog("Missing name", "Enter a name for the split first."))
            return

        create_split(self.conn, name)
        self.new_split_input.value = ""
        self.refresh()

    def _on_select(self, widget):
        """Single tap on a row -> open it immediately."""
        if widget.selection is None:
            return
        row_index = self.list_view.data.index(widget.selection)
        split_id = self._ids_by_row[row_index]
        split_name = widget.selection.title
        self.on_open_split(split_id, split_name)

    async def _on_swipe_delete(self, widget, row):
        """Fires when the user swipes a row and taps the revealed 'Delete' action."""
        row_index = self.list_view.data.index(row)
        split_id = self._ids_by_row[row_index]

        confirmed = await self.window.dialog(
            toga.ConfirmDialog(
                "Delete split",
                "This will permanently delete this split, its sessions, and its exercise plans. Workout history stays intact. Continue?",
            )
        )
        if confirmed:
            delete_split(self.conn, split_id)
            self.refresh()