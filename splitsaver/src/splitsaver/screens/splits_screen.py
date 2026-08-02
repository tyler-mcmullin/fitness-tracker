import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import create_split, get_splits, delete_split
from splitsaver.screens.styles import (
    SPACE_SM, SPACE_MD, SCREEN_PADDING, FONT_SIZE_TITLE, margin_bottom, margin_right,
)


class SplitsScreen:
    """Shows the list of splits. Tap a row to open it, swipe to delete, or use the field below to add one."""

    def __init__(self, conn, window, on_open_split, on_view_history):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow, needed for dialogs
        on_open_split: callback(split_id, split_name) -> called when a split is tapped
        on_view_history: callback() -> called when "View History" is tapped
        """
        self.conn = conn
        self.window = window
        self.on_open_split = on_open_split
        self.on_view_history = on_view_history

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=SCREEN_PADDING))

        title = toga.Label(
            "My Splits",
            style=Pack(margin=margin_bottom(SPACE_MD), font_size=FONT_SIZE_TITLE, font_weight="bold"),
        )

        self.list_view = toga.DetailedList(
            style=Pack(flex=1, margin=margin_bottom(SPACE_MD)),
            on_select=self._on_select,
            on_primary_action=self._on_swipe_delete,
        )

        # "Add Split" starts as a single button; tapping it reveals a small
        # inline form (name field + Save/Cancel) rather than an always-visible field.
        self.show_add_form_button = toga.Button(
            "Add Split", on_press=self._on_show_add_form, style=Pack(margin=margin_bottom(SPACE_MD))
        )
        self.show_add_button_container = toga.Box(style=Pack(direction=COLUMN))
        self.show_add_button_container.add(self.show_add_form_button)

        self.add_form_container = toga.Box(style=Pack(direction=COLUMN))
        self.new_split_input = toga.TextInput(
            placeholder="ex: Push Pull Legs", style=Pack(margin=margin_bottom(SPACE_SM))
        )
        self.add_form_buttons_row = toga.Box(style=Pack(direction=ROW, margin=margin_bottom(SPACE_MD)))
        save_button = toga.Button("Save", on_press=self._on_add, style=Pack(margin=margin_right(SPACE_SM)))
        cancel_button = toga.Button("Cancel", on_press=self._on_cancel_add, style=Pack(margin=0))
        self.add_form_buttons_row.add(save_button)
        self.add_form_buttons_row.add(cancel_button)

        history_button = toga.Button(
            "View History", on_press=lambda widget: self.on_view_history(), style=Pack(margin=margin_bottom(SPACE_MD))
        )

        box.add(title)
        box.add(self.list_view)
        box.add(self.show_add_button_container)
        box.add(self.add_form_container)
        box.add(history_button)
        return box

    def refresh(self):
        """Re-reads splits from the database and repopulates the list."""
        splits = get_splits(self.conn)  # list of (id, name, notes)
        self._ids_by_row = [s[0] for s in splits]
        self.list_view.data = [{"title": s[1], "subtitle": s[2] or ""} for s in splits]

    # -----------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------

    def _on_show_add_form(self, widget):
        """Reveals the inline 'new split' form and hides the trigger button."""
        self.new_split_input.value = ""

        while len(self.show_add_button_container.children) > 0:
            self.show_add_button_container.remove(self.show_add_button_container.children[0])

        while len(self.add_form_container.children) > 0:
            self.add_form_container.remove(self.add_form_container.children[0])
        self.add_form_container.add(self.new_split_input)
        self.add_form_container.add(self.add_form_buttons_row)

    def _hide_add_form(self):
        """Collapses the form back down to just the trigger button."""
        while len(self.add_form_container.children) > 0:
            self.add_form_container.remove(self.add_form_container.children[0])

        while len(self.show_add_button_container.children) > 0:
            self.show_add_button_container.remove(self.show_add_button_container.children[0])
        self.show_add_button_container.add(self.show_add_form_button)

    def _on_cancel_add(self, widget):
        self._hide_add_form()

    async def _on_add(self, widget):
        name = self.new_split_input.value.strip()
        if not name:
            await self.window.dialog(toga.InfoDialog("Missing name", "Enter a name for the split first."))
            return

        create_split(self.conn, name)
        self._hide_add_form()
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