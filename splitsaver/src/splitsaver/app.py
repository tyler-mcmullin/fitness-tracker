import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import (
    init_db,
    create_split,
    get_splits,
    delete_split,
)


class SplitSaver(toga.App):
    def startup(self):
        self.conn = init_db(str(self.paths.data / "workouts.db"))
        self.selected_split_id = None

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = self.build_splits_screen()
        self.main_window.show()

    # -----------------------------------------------------------------
    # Splits screen
    # -----------------------------------------------------------------

    def build_splits_screen(self):
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        title = toga.Label(
            "My Splits",
            style=Pack(padding=(0, 0, 10, 0), font_size=18, font_weight="bold"),
        )

        self.splits_table = toga.Table(
            headings=["Name"],
            style=Pack(flex=1, padding=(0, 0, 10, 0)),
            on_select=self.on_split_selected,
            on_activate=self.on_split_activated,
        )

        add_row = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))
        self.new_split_input = toga.TextInput(
            placeholder="e.g. Push Pull Legs",
            style=Pack(flex=1, padding=(0, 5, 0, 0)),
        )
        add_button = toga.Button(
            "Add Split",
            on_press=self.on_add_split,
            style=Pack(padding=0),
        )
        add_row.add(self.new_split_input)
        add_row.add(add_button)

        self.delete_button = toga.Button(
            "Delete Selected",
            on_press=self.on_delete_split,
            style=Pack(padding=(0, 0, 0, 0)),
            enabled=False,
        )

        box.add(title)
        box.add(self.splits_table)
        box.add(add_row)
        box.add(self.delete_button)

        self.refresh_splits_table()
        return box

    def refresh_splits_table(self):
        """Re-reads splits from the database and repopulates the table."""
        splits = get_splits(self.conn)  # list of (id, name, notes)
        self._split_ids_by_row = [s[0] for s in splits]
        self.splits_table.data = [(s[1],) for s in splits]
        self.selected_split_id = None
        self.delete_button.enabled = False

    # -----------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------

    def on_add_split(self, widget):
        name = self.new_split_input.value.strip()
        if not name:
            self.main_window.info_dialog("Missing name", "Enter a name for the split first.")
            return

        create_split(self.conn, name)
        self.new_split_input.value = ""
        self.refresh_splits_table()

    def on_split_selected(self, widget):
        if widget.selection is None:
            self.selected_split_id = None
            self.delete_button.enabled = False
            return

        row_index = self.splits_table.data.index(widget.selection)
        self.selected_split_id = self._split_ids_by_row[row_index]
        self.delete_button.enabled = True

    def on_split_activated(self, widget, row):
        """Fires on double-click / tap-to-open. Placeholder until the
        Sessions screen exists — will navigate there next."""
        row_index = self.splits_table.data.index(row)
        split_id = self._split_ids_by_row[row_index]
        split_name = row.name
        self.main_window.info_dialog(
            "Open split",
            f"Opening '{split_name}' (id={split_id}) — Sessions screen not built yet.",
        )

    def on_delete_split(self, widget):
        if self.selected_split_id is None:
            return

        def confirm_and_delete(window, dialog_result):
            if dialog_result:
                delete_split(self.conn, self.selected_split_id)
                self.refresh_splits_table()

        self.main_window.confirm_dialog(
            "Delete split",
            "This will permanently delete this split, its sessions, and its exercise plans. Workout history will stay intact. Continue?",
            on_result=confirm_and_delete,
        )


def main():
    return SplitSaver()
