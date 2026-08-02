import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import create_session, get_sessions, delete_session, get_variants
from splitsaver.screens.styles import (
    SPACE_SM, SPACE_MD, SCREEN_PADDING, FONT_SIZE_TITLE, margin_bottom, margin_right,
)

DOT_FILLED = "\u25cf"  # ●


class SessionsScreen:
    """Shows the sessions under one split. Tap a row to open it, swipe to delete,
    or use the field below to add one. Each row's subtitle shows a dot per variant."""

    def __init__(self, conn, window, split_id, split_name, on_back, on_open_session):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow, needed for dialogs
        split_id, split_name: the split whose sessions this screen shows
        on_back: callback() -> called to return to the Splits screen
        on_open_session: callback(session_id, session_name) -> called when a session is tapped
        """
        self.conn = conn
        self.window = window
        self.split_id = split_id
        self.split_name = split_name
        self.on_back = on_back
        self.on_open_session = on_open_session

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=SCREEN_PADDING))

        back_button = toga.Button(
            "< Splits", on_press=lambda widget: self.on_back(), style=Pack(margin=margin_bottom(SPACE_MD))
        )

        title = toga.Label(
            self.split_name,
            style=Pack(margin=margin_bottom(SPACE_MD), font_size=FONT_SIZE_TITLE, font_weight="bold"),
        )

        self.list_view = toga.DetailedList(
            style=Pack(flex=1, margin=margin_bottom(SPACE_MD)),
            on_select=self._on_select,
            on_primary_action=self._on_swipe_delete,
        )

        # "Add Session" starts as a single button; tapping it reveals a small
        # inline form (name field + Save/Cancel) rather than an always-visible field.
        self.show_add_form_button = toga.Button(
            "Add Session", on_press=self._on_show_add_form, style=Pack(margin=0)
        )
        self.show_add_button_container = toga.Box(style=Pack(direction=COLUMN))
        self.show_add_button_container.add(self.show_add_form_button)

        self.add_form_container = toga.Box(style=Pack(direction=COLUMN))
        self.new_session_input = toga.TextInput(
            placeholder="ex: Legs", style=Pack(margin=margin_bottom(SPACE_SM))
        )
        self.add_form_buttons_row = toga.Box(style=Pack(direction=ROW))
        save_button = toga.Button("Save", on_press=self._on_add, style=Pack(margin=margin_right(SPACE_SM)))
        cancel_button = toga.Button("Cancel", on_press=self._on_cancel_add, style=Pack(margin=0))
        self.add_form_buttons_row.add(save_button)
        self.add_form_buttons_row.add(cancel_button)

        box.add(back_button)
        box.add(title)
        box.add(self.list_view)
        box.add(self.show_add_button_container)
        box.add(self.add_form_container)
        return box

    def refresh(self):
        """Re-reads sessions for this split and repopulates the list."""
        sessions = get_sessions(self.conn, self.split_id)  # list of (id, name)
        self._ids_by_row = [s[0] for s in sessions]

        rows = []
        for session_id, name in sessions:
            variant_count = len(get_variants(self.conn, session_id))
            dots = DOT_FILLED * variant_count
            rows.append({"title": name, "subtitle": dots})
        self.list_view.data = rows

    # -----------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------

    def _on_show_add_form(self, widget):
        """Reveals the inline 'new session' form and hides the trigger button."""
        self.new_session_input.value = ""

        while len(self.show_add_button_container.children) > 0:
            self.show_add_button_container.remove(self.show_add_button_container.children[0])

        while len(self.add_form_container.children) > 0:
            self.add_form_container.remove(self.add_form_container.children[0])
        self.add_form_container.add(self.new_session_input)
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
        name = self.new_session_input.value.strip()
        if not name:
            await self.window.dialog(toga.InfoDialog("Missing name", "Enter a name for the session first."))
            return

        create_session(self.conn, self.split_id, name)
        self._hide_add_form()
        self.refresh()

    def _on_select(self, widget):
        """Single tap on a row -> open it immediately."""
        if widget.selection is None:
            return
        row_index = self.list_view.data.index(widget.selection)
        session_id = self._ids_by_row[row_index]
        session_name = widget.selection.title
        self.on_open_session(session_id, session_name)

    async def _on_swipe_delete(self, widget, row):
        """Fires when the user swipes a row and taps the revealed 'Delete' action."""
        row_index = self.list_view.data.index(row)
        session_id = self._ids_by_row[row_index]

        confirmed = await self.window.dialog(
            toga.ConfirmDialog(
                "Delete session",
                "This will permanently delete this session, its variants, and its exercise plans. Workout history stays intact. Continue?",
            )
        )
        if confirmed:
            delete_session(self.conn, session_id)
            self.refresh()