import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from splitsaver.database import get_variants
from splitsaver.screens.styles import SPACE_MD, SCREEN_PADDING, FONT_SIZE_TITLE, margin_bottom


class HistoryVariantsScreen:
    """Read-only list of variants under a session, for browsing history.
    Unlike the editing screen, this shows every variant plainly in a list —
    there's no hide-until-second-variant behavior here, since any variant
    that exists might have logged history worth viewing."""

    def __init__(self, conn, window, session_id, session_name, on_open_variant, on_back):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow
        session_id, session_name: the session whose variants this screen shows
        on_open_variant: callback(variant_id, variant_name) -> called when a variant is tapped
        on_back: callback() -> called to return to the history sessions list
        """
        self.conn = conn
        self.window = window
        self.session_id = session_id
        self.session_name = session_name
        self.on_open_variant = on_open_variant
        self.on_back = on_back

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=SCREEN_PADDING))

        back_button = toga.Button(
            "< Sessions", on_press=lambda widget: self.on_back(), style=Pack(margin=margin_bottom(SPACE_MD))
        )

        title = toga.Label(
            self.session_name, style=Pack(margin=margin_bottom(SPACE_MD), font_size=FONT_SIZE_TITLE, font_weight="bold")
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
        variants = get_variants(self.conn, self.session_id)  # list of (id, name)
        self._ids_by_row = [v[0] for v in variants]
        self.list_view.data = [{"title": v[1], "subtitle": ""} for v in variants]

    def _on_select(self, widget):
        if widget.selection is None:
            return
        row_index = self.list_view.data.index(widget.selection)
        variant_id = self._ids_by_row[row_index]
        variant_name = widget.selection.title
        self.on_open_variant(variant_id, variant_name)