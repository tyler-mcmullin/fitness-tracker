import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import get_exercise_history


class HistoryExerciseDetailScreen:
    """Shows every logged set for one exercise, grouped by workout date,
    most recent first."""

    def __init__(self, conn, window, variant_id, variant_name, exercise_name, on_back):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow
        variant_id, variant_name: the variant this exercise's history belongs to
        exercise_name: the exercise whose history this screen shows
        on_back: callback() -> called to return to the history exercises list
        """
        self.conn = conn
        self.window = window
        self.variant_id = variant_id
        self.variant_name = variant_name
        self.exercise_name = exercise_name
        self.on_back = on_back

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        back_button = toga.Button(
            "< Exercises", on_press=lambda widget: self.on_back(), style=Pack(margin=(0, 0, 10, 0))
        )

        title = toga.Label(
            self.exercise_name, style=Pack(margin=(0, 0, 3, 0), font_size=18, font_weight="bold")
        )
        subtitle = toga.Label(
            self.variant_name, style=Pack(margin=(0, 0, 10, 0), font_size=13)
        )

        self.entries_box = toga.Box(style=Pack(direction=COLUMN))
        entries_scroll = toga.ScrollContainer(
            content=self.entries_box, style=Pack(flex=1), horizontal=False
        )

        box.add(back_button)
        box.add(title)
        box.add(subtitle)
        box.add(entries_scroll)
        return box

    def refresh(self):
        """Re-reads history for this exercise and rebuilds the grouped display."""
        while len(self.entries_box.children) > 0:
            self.entries_box.remove(self.entries_box.children[0])

        rows = get_exercise_history(self.conn, self.variant_id, self.exercise_name)
        # rows: (date, set_number, reps, weight, unit), ordered oldest first

        if not rows:
            self.entries_box.add(
                toga.Label("No history logged for this exercise yet.", style=Pack(margin=(0, 0, 10, 0)))
            )
            return

        # Group by date, preserving set order, then display most recent date first
        by_date = {}
        for date, set_number, reps, weight, unit in rows:
            by_date.setdefault(date, []).append((set_number, reps, weight, unit))

        for date in sorted(by_date.keys(), reverse=True):
            date_box = toga.Box(style=Pack(direction=COLUMN, margin=(0, 0, 12, 0)))
            date_label = toga.Label(date, style=Pack(margin=(0, 0, 4, 0), font_weight="bold"))
            date_box.add(date_label)

            for set_number, reps, weight, unit in by_date[date]:
                set_label = toga.Label(
                    f"Set {set_number}: {reps} reps @ {_format_number(weight)} {unit}",
                    style=Pack(margin=(0, 0, 2, 10)),
                )
                date_box.add(set_label)

            self.entries_box.add(date_box)


def _format_number(value):
    """Formats a number for display: whole numbers show with no decimal (25),
    anything with a fractional part keeps it (22.5)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if f == int(f):
        return str(int(f))
    return str(f)