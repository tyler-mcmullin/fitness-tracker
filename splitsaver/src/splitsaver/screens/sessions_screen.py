import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import create_session, get_sessions, delete_session, get_variants


class SessionsScreen:
    """Shows the sessions under one split. Lets the user add, delete, and open a session."""

    def __init__(self, conn, window, split_id, split_name, on_back, on_open_session):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow, needed for dialogs
        split_id, split_name: the split whose sessions this screen shows
        on_back: callback() -> called to return to the Splits screen
        on_open_session: callback(session_id, session_name) -> called when a session is activated
        """
        self.conn = conn
        self.window = window
        self.split_id = split_id
        self.split_name = split_name
        self.on_back = on_back
        self.on_open_session = on_open_session
        self.selected_session_id = None

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        back_button = toga.Button(
            "< Splits", on_press=lambda widget: self.on_back(), style=Pack(margin=(0, 0, 10, 0))
        )

        title = toga.Label(
            self.split_name,
            style=Pack(margin=(0, 0, 10, 0), font_size=18, font_weight="bold"),
        )

        self.table = toga.Table(
            columns=["Name", "Variants"],
            style=Pack(flex=1, margin=(0, 0, 10, 0)),
            on_select=self._on_select,
            on_activate=self._on_activate,
        )

        add_row = toga.Box(style=Pack(direction=ROW, margin=(0, 0, 10, 0)))
        self.new_session_input = toga.TextInput(
            placeholder="e.g. Legs",
            style=Pack(flex=1, margin=(0, 5, 0, 0)),
        )
        add_button = toga.Button("Add Session", on_press=self._on_add, style=Pack(margin=0))
        add_row.add(self.new_session_input)
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

        box.add(back_button)
        box.add(title)
        box.add(self.table)
        box.add(add_row)
        box.add(self.open_button)
        box.add(self.delete_button)
        return box

    def refresh(self):
        """Re-reads sessions for this split and repopulates the table."""
        sessions = get_sessions(self.conn, self.split_id)  # list of (id, name)
        self._ids_by_row = [s[0] for s in sessions]

        rows = []
        for session_id, name in sessions:
            variant_count = len(get_variants(self.conn, session_id))
            dots = "\u25cf" * variant_count  # one dot per variant; blank if none yet
            rows.append((name, dots))
        self.table.data = rows

        self.selected_session_id = None
        self.delete_button.enabled = False
        self.open_button.enabled = False

    # -----------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------

    def _on_add(self, widget):
        name = self.new_session_input.value.strip()
        if not name:
            self.window.info_dialog("Missing name", "Enter a name for the session first.")
            return

        create_session(self.conn, self.split_id, name)
        self.new_session_input.value = ""
        self.refresh()

    def _on_select(self, widget):
        if widget.selection is None:
            self.selected_session_id = None
            self.delete_button.enabled = False
            self.open_button.enabled = False
            return

        row_index = self.table.data.index(widget.selection)
        self.selected_session_id = self._ids_by_row[row_index]
        self.delete_button.enabled = True
        self.open_button.enabled = True

    def _on_open_pressed(self, widget):
        if self.selected_session_id is None:
            return
        row_index = self._ids_by_row.index(self.selected_session_id)
        session_name = self.table.data[row_index].name
        self.on_open_session(self.selected_session_id, session_name)

    def _on_activate(self, widget, row):
        row_index = self.table.data.index(row)
        session_id = self._ids_by_row[row_index]
        session_name = row.name
        self.on_open_session(session_id, session_name)

    def _on_delete(self, widget):
        if self.selected_session_id is None:
            return

        def confirm_and_delete(window, dialog_result):
            if dialog_result:
                delete_session(self.conn, self.selected_session_id)
                self.refresh()

        self.window.confirm_dialog(
            "Delete session",
            "This will permanently delete this session, its variants, and its exercise plans. Workout history stays intact. Continue?",
            on_result=confirm_and_delete,
        )