import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import create_split, get_splits, delete_split


class SplitsScreen:
    """Shows the list of splits. Lets the user add, delete, and open a split."""

    def __init__(self, conn, window, on_open_split):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow, needed for dialogs
        on_open_split: callback(split_id, split_name) -> called when a split is activated
        """
        self.conn = conn
        self.window = window
        self.on_open_split = on_open_split
        self.selected_split_id = None

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        title = toga.Label(
            "My Splits",
            style=Pack(margin=(0, 0, 10, 0), font_size=18, font_weight="bold"),
        )

        self.table = toga.Table(
            columns=["Name"],
            style=Pack(flex=1, margin=(0, 0, 10, 0)),
            on_select=self._on_select,
            on_activate=self._on_activate,
        )

        add_row = toga.Box(style=Pack(direction=ROW, margin=(0, 0, 10, 0)))
        self.new_split_input = toga.TextInput(
            placeholder="e.g. Push Pull Legs",
            style=Pack(flex=1, margin=(0, 5, 0, 0)),
        )
        add_button = toga.Button("Add Split", on_press=self._on_add, style=Pack(margin=0))
        add_row.add(self.new_split_input)
        add_row.add(add_button)

        self.delete_button = toga.Button(
            "Delete Selected",
            on_press=self._on_delete,
            style=Pack(margin=0),
            enabled=False,
        )

        self.open_button = toga.Button(
            "Open Selected",
            on_press=self._on_open_pressed,
            style=Pack(margin=(0, 0, 10, 0)),
            enabled=False,
        )

        box.add(title)
        box.add(self.table)
        box.add(add_row)
        box.add(self.open_button)
        box.add(self.delete_button)
        return box

    def refresh(self):
        """Re-reads splits from the database and repopulates the table."""
        splits = get_splits(self.conn)  # list of (id, name, notes)
        self._ids_by_row = [s[0] for s in splits]
        self.table.data = [(s[1],) for s in splits]
        self.selected_split_id = None
        self.delete_button.enabled = False
        self.open_button.enabled = False

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
        if widget.selection is None:
            self.selected_split_id = None
            self.delete_button.enabled = False
            self.open_button.enabled = False
            return

        row_index = self.table.data.index(widget.selection)
        self.selected_split_id = self._ids_by_row[row_index]
        self.delete_button.enabled = True
        self.open_button.enabled = True

    def _on_open_pressed(self, widget):
        if self.selected_split_id is None:
            return
        row_index = self._ids_by_row.index(self.selected_split_id)
        split_name = self.table.data[row_index].name
        self.on_open_split(self.selected_split_id, split_name)

    def _on_activate(self, widget, row):
        row_index = self.table.data.index(row)
        split_id = self._ids_by_row[row_index]
        split_name = row.name
        self.on_open_split(split_id, split_name)

    async def _on_delete(self, widget):
        if self.selected_split_id is None:
            return

        confirmed = await self.window.dialog(
            toga.ConfirmDialog(
                "Delete split",
                "This will permanently delete this split, its sessions, and its exercise plans. Workout history stays intact. Continue?",
            )
        )
        if confirmed:
            delete_split(self.conn, self.selected_split_id)
            self.refresh()