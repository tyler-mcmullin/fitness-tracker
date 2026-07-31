import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from splitsaver.database import get_logged_exercise_names


class HistoryExercisesScreen:
    """Read-only list of exercises that have logged history for a variant.
    Shows every exercise name ever logged, even ones since deleted or renamed
    in the current plan, since history is decoupled from the plan on purpose."""

    def __init__(self, conn, window, variant_id, variant_name, on_open_exercise, on_back):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow
        variant_id, variant_name: the variant whose logged exercises this screen shows
        on_open_exercise: callback(exercise_name) -> called when an exercise is tapped
        on_back: callback() -> called to return to the history variants list
        """
        self.conn = conn
        self.window = window
        self.variant_id = variant_id
        self.variant_name = variant_name
        self.on_open_exercise = on_open_exercise
        self.on_back = on_back

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        back_button = toga.Button(
            "< Variants", on_press=lambda widget: self.on_back(), style=Pack(margin=(0, 0, 10, 0))
        )

        title = toga.Label(
            self.variant_name, style=Pack(margin=(0, 0, 10, 0), font_size=18, font_weight="bold")
        )

        # Placeholder that holds the "no history yet" message, toggled on refresh
        self.empty_container = toga.Box(style=Pack(direction=COLUMN))

        self.list_view = toga.DetailedList(
            style=Pack(flex=1),
            on_select=self._on_select,
        )

        box.add(back_button)
        box.add(title)
        box.add(self.empty_container)
        box.add(self.list_view)
        return box

    def refresh(self):
        names = get_logged_exercise_names(self.conn, self.variant_id)
        self._names_by_row = names
        self.list_view.data = [{"title": name, "subtitle": ""} for name in names]

        while len(self.empty_container.children) > 0:
            self.empty_container.remove(self.empty_container.children[0])
        if not names:
            self.empty_container.add(
                toga.Label("No workouts logged for this variant yet.", style=Pack(margin=(0, 0, 10, 0)))
            )

    def _on_select(self, widget):
        if widget.selection is None:
            return
        row_index = self.list_view.data.index(widget.selection)
        exercise_name = self._names_by_row[row_index]
        self.on_open_exercise(exercise_name)