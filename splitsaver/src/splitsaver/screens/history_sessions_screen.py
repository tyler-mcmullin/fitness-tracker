import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from splitsaver.database import get_sessions
from splitsaver.screens.styles import SPACE_MD, SCREEN_PADDING, FONT_SIZE_TITLE, margin_bottom


class HistorySessionsScreen:
    """Read-only list of sessions under a split, for browsing history."""

    def __init__(self, conn, window, split_id, split_name, on_open_session, on_back):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow
        split_id, split_name: the split whose sessions this screen shows
        on_open_session: callback(session_id, session_name) -> called when a session is tapped
        on_back: callback() -> called to return to the history splits list
        """
        self.conn = conn
        self.window = window
        self.split_id = split_id
        self.split_name = split_name
        self.on_open_session = on_open_session
        self.on_back = on_back

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=SCREEN_PADDING))

        back_button = toga.Button(
            "< History", on_press=lambda widget: self.on_back(), style=Pack(margin=margin_bottom(SPACE_MD))
        )

        title = toga.Label(
            self.split_name, style=Pack(margin=margin_bottom(SPACE_MD), font_size=FONT_SIZE_TITLE, font_weight="bold")
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
        sessions = get_sessions(self.conn, self.split_id)  # list of (id, name)
        self._ids_by_row = [s[0] for s in sessions]
        self.list_view.data = [{"title": s[1], "subtitle": ""} for s in sessions]

    def _on_select(self, widget):
        if widget.selection is None:
            return
        row_index = self.list_view.data.index(widget.selection)
        session_id = self._ids_by_row[row_index]
        session_name = widget.selection.title
        self.on_open_session(session_id, session_name)