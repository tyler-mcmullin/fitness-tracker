import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import (
    create_variant,
    get_variants,
    delete_variant,
    add_exercise,
    get_current_state,
    delete_exercise,
    update_exercises,
    log_workout,
)

DOT_FILLED = "\u25cf"   # ●
DOT_EMPTY = "\u25cb"    # ○


def _format_weight(value):
    """Formats a weight for display: whole numbers show with no decimal (25),
    anything with a fractional part keeps it (22.5)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "0"
    if f == int(f):
        return str(int(f))
    return str(f)


def _parse_weight(text):
    """Parses a weight field's text back into a float. Falls back to 0 on bad input."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


class VariantsScreen:
    """Shows the variants (e.g. 'A', 'B') under one session, one at a time.
    Every session starts with a single auto-created default variant, shown
    plainly with no pager controls. Once the user adds a second variant,
    left/right arrows and a dot indicator appear to page between them, and
    a 'Delete This Variant' button becomes available. Each variant's
    exercises are listed inline below, with sets/reps/weight editable
    directly, plus a button to log the workout to history."""

    def __init__(self, conn, window, session_id, session_name, on_back):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow, needed for dialogs
        session_id, session_name: the session whose variants this screen shows
        on_back: callback() -> called to return to the Sessions screen
        """
        self.conn = conn
        self.window = window
        self.session_id = session_id
        self.session_name = session_name
        self.on_back = on_back

        self.variants = []       # list of (id, name), refreshed from the db
        self.current_index = 0
        self._exercise_inputs = {}  # exercise_id -> {"weight": widget, "reps": widget}

        self.box = self._build()
        self.refresh()

    def _build(self):
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        back_button = toga.Button(
            "< Sessions", on_press=lambda widget: self.on_back(), style=Pack(margin=(0, 0, 10, 0))
        )

        title = toga.Label(
            self.session_name,
            style=Pack(margin=(0, 0, 10, 0), font_size=18, font_weight="bold"),
        )

        # Pager: [ < ]  Variant Name  [ > ]  — only shown once there's more than one variant
        self.pager_row = toga.Box(style=Pack(direction=ROW, margin=(0, 0, 5, 0), align_items="center"))
        self.left_arrow = toga.Button("<", on_press=self._on_prev, style=Pack(width=40), enabled=False)
        self.variant_name_label = toga.Label(
            "", style=Pack(flex=1, text_align="center", font_size=16, font_weight="bold")
        )
        self.right_arrow = toga.Button(">", on_press=self._on_next, style=Pack(width=40), enabled=False)
        self.pager_row.add(self.left_arrow)
        self.pager_row.add(self.variant_name_label)
        self.pager_row.add(self.right_arrow)

        self.dots_label = toga.Label("", style=Pack(margin=(0, 0, 10, 0), text_align="center"))

        # Placeholder that holds pager_row + dots_label when there's more than one variant
        self.pager_container = toga.Box(style=Pack(direction=COLUMN))

        # Exercise list for the current variant
        self.exercise_list_box = toga.Box(style=Pack(direction=COLUMN, margin=(0, 0, 10, 0)))
        exercise_scroll = toga.ScrollContainer(
            content=self.exercise_list_box, style=Pack(flex=1, margin=(0, 0, 10, 0)), horizontal=False
        )

        add_exercise_row = toga.Box(style=Pack(direction=ROW, margin=(0, 0, 10, 0)))
        self.new_exercise_input = toga.TextInput(
            placeholder="e.g. Squat", style=Pack(flex=1, margin=(0, 5, 0, 0))
        )
        add_exercise_button = toga.Button(
            "Add Exercise", on_press=self._on_add_exercise, style=Pack(margin=0)
        )
        add_exercise_row.add(self.new_exercise_input)
        add_exercise_row.add(add_exercise_button)

        self.log_button = toga.Button(
            "Log Workout", on_press=self._on_log_workout, style=Pack(margin=(0, 0, 10, 0)), enabled=False
        )
        self.delete_variant_button = toga.Button(
            "Delete This Variant", on_press=self._on_delete_variant, style=Pack(margin=(0, 0, 10, 0)),
            enabled=False,
        )
        # Placeholder that holds delete_variant_button when there's more than one variant —
        # deleting the sole default variant isn't offered, since every session needs at least one
        self.delete_variant_container = toga.Box(style=Pack(direction=COLUMN))

        add_variant_row = toga.Box(style=Pack(direction=ROW))
        self.new_variant_input = toga.TextInput(
            placeholder="e.g. A", style=Pack(flex=1, margin=(0, 5, 0, 0))
        )
        add_variant_button = toga.Button("Add Variant", on_press=self._on_add_variant, style=Pack(margin=0))
        add_variant_row.add(self.new_variant_input)
        add_variant_row.add(add_variant_button)

        box.add(back_button)
        box.add(title)
        box.add(self.pager_container)
        box.add(exercise_scroll)
        box.add(add_exercise_row)
        box.add(self.log_button)
        box.add(self.delete_variant_container)
        box.add(add_variant_row)
        return box

    # -----------------------------------------------------------------
    # Rendering
    # -----------------------------------------------------------------

    def refresh(self, keep_index=False):
        """Re-reads variants for this session and redraws the current page."""
        self.variants = get_variants(self.conn, self.session_id)  # list of (id, name)

        if not keep_index or self.current_index >= len(self.variants):
            self.current_index = 0

        self._render_current_page()

    def _render_current_page(self):
        count = len(self.variants)

        if count == 0:
            self.variant_name_label.text = "No variants yet"
            self.dots_label.text = ""
            self.left_arrow.enabled = False
            self.right_arrow.enabled = False
            self.log_button.enabled = False
            self.delete_variant_button.enabled = False
            self._set_multi_variant_controls_visible(False)
            self._render_exercises(variant_id=None)
            return

        variant_id, name = self.variants[self.current_index]
        self.variant_name_label.text = name
        self.dots_label.text = " ".join(
            DOT_FILLED if i == self.current_index else DOT_EMPTY for i in range(count)
        )
        self.left_arrow.enabled = self.current_index > 0
        self.right_arrow.enabled = self.current_index < count - 1
        self.log_button.enabled = True
        self.delete_variant_button.enabled = True

        # Only show the pager/dots/delete-variant controls once there's more than
        # one variant — a single (likely auto-created) variant is shown plainly.
        self._set_multi_variant_controls_visible(count > 1)

        self._render_exercises(variant_id)

    def _set_multi_variant_controls_visible(self, visible):
        """Adds or removes the pager/dots and delete-variant button from the layout."""
        pager_should_be_shown = self.pager_row in self.pager_container.children
        if visible and not pager_should_be_shown:
            self.pager_container.add(self.pager_row)
            self.pager_container.add(self.dots_label)
        elif not visible and pager_should_be_shown:
            self.pager_container.remove(self.pager_row)
            self.pager_container.remove(self.dots_label)

        delete_should_be_shown = self.delete_variant_button in self.delete_variant_container.children
        if visible and not delete_should_be_shown:
            self.delete_variant_container.add(self.delete_variant_button)
        elif not visible and delete_should_be_shown:
            self.delete_variant_container.remove(self.delete_variant_button)

    def _render_exercises(self, variant_id):
        """Rebuilds the inline exercise list for the given variant."""
        # Clear existing rows
        while len(self.exercise_list_box.children) > 0:
            self.exercise_list_box.remove(self.exercise_list_box.children[0])
        self._exercise_inputs = {}

        if variant_id is None:
            return

        exercises = get_current_state(self.conn, variant_id)  # (id, name, sets, reps, weight)
        for exercise_id, name, sets, reps, weight in exercises:
            row = toga.Box(style=Pack(direction=ROW, margin=(0, 0, 8, 0), align_items="center"))

            name_label = toga.Label(name, style=Pack(flex=1))

            sets_input = toga.NumberInput(
                value=sets, min=1, step=1, style=Pack(width=50, margin=(0, 5, 0, 0))
            )
            weight_input = toga.TextInput(
                value=_format_weight(weight), style=Pack(width=70, margin=(0, 5, 0, 0))
            )
            reps_input = toga.NumberInput(
                value=reps, min=0, step=1, style=Pack(width=60, margin=(0, 5, 0, 0))
            )

            on_change = self._make_on_field_change(variant_id, exercise_id, name)
            sets_input.on_change = on_change
            weight_input.on_change = on_change
            reps_input.on_change = on_change

            remove_button = toga.Button(
                "Remove",
                on_press=self._make_on_remove_exercise(exercise_id),
                style=Pack(margin=0),
            )

            row.add(name_label)
            row.add(sets_input)
            row.add(toga.Label("sets", style=Pack(margin=(0, 10, 0, 0))))
            row.add(reps_input)
            row.add(toga.Label("reps", style=Pack(margin=(0, 10, 0, 0))))
            row.add(weight_input)
            row.add(toga.Label("lb", style=Pack(margin=(0, 10, 0, 0))))
            row.add(remove_button)

            self.exercise_list_box.add(row)
            self._exercise_inputs[exercise_id] = {
                "weight": weight_input, "reps": reps_input, "sets": sets_input, "name": name,
            }

    # -----------------------------------------------------------------
    # Event handlers — pager
    # -----------------------------------------------------------------

    def _on_prev(self, widget):
        if self.current_index > 0:
            self.current_index -= 1
            self._render_current_page()

    def _on_next(self, widget):
        if self.current_index < len(self.variants) - 1:
            self.current_index += 1
            self._render_current_page()

    # -----------------------------------------------------------------
    # Event handlers — exercises
    # -----------------------------------------------------------------

    def _make_on_field_change(self, variant_id, exercise_id, name):
        """Returns an on_change handler that saves this exercise's plan
        whenever sets, weight, or reps is edited directly in the list."""
        def handler(widget):
            inputs = self._exercise_inputs.get(exercise_id)
            if inputs is None:
                return
            sets = int(inputs["sets"].value or 1)
            weight = _parse_weight(inputs["weight"].value)
            reps = int(inputs["reps"].value or 0)
            update_exercises(self.conn, variant_id, name, sets=sets, reps=reps, weight=weight)
        return handler

    def _make_on_remove_exercise(self, exercise_id):
        async def handler(widget):
            confirmed = await self.window.dialog(
                toga.ConfirmDialog("Remove exercise", "Remove this exercise from the plan?")
            )
            if confirmed:
                delete_exercise(self.conn, exercise_id)
                self._render_current_page()
        return handler

    async def _on_add_exercise(self, widget):
        name = self.new_exercise_input.value.strip()
        if not name:
            await self.window.dialog(toga.InfoDialog("Missing name", "Enter a name for the exercise first."))
            return
        if not self.variants:
            await self.window.dialog(toga.InfoDialog("No variant", "Add a variant before adding exercises."))
            return

        variant_id, _ = self.variants[self.current_index]
        add_exercise(self.conn, variant_id, name)
        self.new_exercise_input.value = ""
        self._render_current_page()

    async def _on_log_workout(self, widget):
        if not self.variants:
            return
        variant_id, name = self.variants[self.current_index]

        exercise_entries = []
        for exercise_id, inputs in self._exercise_inputs.items():
            weight = _parse_weight(inputs["weight"].value)
            reps = int(inputs["reps"].value or 0)
            sets = int(inputs["sets"].value or 1)
            exercise_entries.append({
                "name": inputs["name"],
                "sets": [{"reps": reps, "weight": weight} for _ in range(sets)],
            })

        if not exercise_entries:
            await self.window.dialog(toga.InfoDialog("Nothing to log", "Add an exercise first."))
            return

        log_workout(self.conn, variant_id, exercise_entries)
        await self.window.dialog(toga.InfoDialog("Logged", f"Workout logged for '{name}'."))

    # -----------------------------------------------------------------
    # Event handlers — variants
    # -----------------------------------------------------------------

    async def _on_add_variant(self, widget):
        name = self.new_variant_input.value.strip()
        if not name:
            await self.window.dialog(toga.InfoDialog("Missing name", "Enter a name for the variant first (e.g. 'A')."))
            return

        create_variant(self.conn, self.session_id, name)
        self.new_variant_input.value = ""
        self.current_index = len(self.variants)  # jump to the newly added variant
        self.refresh(keep_index=True)

    async def _on_delete_variant(self, widget):
        if not self.variants:
            return
        variant_id, name = self.variants[self.current_index]

        confirmed = await self.window.dialog(
            toga.ConfirmDialog(
                "Delete variant",
                f"This will permanently delete '{name}' and its exercise plan. Workout history stays intact. Continue?",
            )
        )
        if confirmed:
            delete_variant(self.conn, variant_id)
            if self.current_index > 0:
                self.current_index -= 1
            self.refresh(keep_index=True)