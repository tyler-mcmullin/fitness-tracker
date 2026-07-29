import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import create_variant, get_variants, delete_variant

DOT_FILLED = "\u25cf"   # ●
DOT_EMPTY = "\u25cb"    # ○


class VariantsScreen:
    """Shows the variants (e.g. 'A', 'B') under one session, one at a time,
    with left/right arrow buttons and a dot indicator to page between them."""

    def __init__(self, conn, window, session_id, session_name, on_back, on_open_variant):
        """
        conn: sqlite3 connection
        window: the toga.MainWindow, needed for dialogs
        session_id, session_name: the session whose variants this screen shows
        on_back: callback() -> called to return to the Sessions screen
        on_open_variant: callback(variant_id, variant_name) -> called when "Open Exercises" is pressed
        """
        self.conn = conn
        self.window = window
        self.session_id = session_id
        self.session_name = session_name
        self.on_back = on_back
        self.on_open_variant = on_open_variant

        self.variants = []       # list of (id, name), refreshed from the db
        self.current_index = 0

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

        # Pager: [ < ]  Variant Name  [ > ]
        pager_row = toga.Box(style=Pack(direction=ROW, margin=(0, 0, 5, 0), align_items="center"))
        self.left_arrow = toga.Button("<", on_press=self._on_prev, style=Pack(width=40), enabled=False)
        self.variant_name_label = toga.Label(
            "", style=Pack(flex=1, text_align="center", font_size=16, font_weight="bold")
        )
        self.right_arrow = toga.Button(">", on_press=self._on_next, style=Pack(width=40), enabled=False)
        pager_row.add(self.left_arrow)
        pager_row.add(self.variant_name_label)
        pager_row.add(self.right_arrow)

        self.dots_label = toga.Label(
            "", style=Pack(margin=(0, 0, 10, 0), text_align="center")
        )

        self.open_button = toga.Button(
            "Open Exercises", on_press=self._on_open, style=Pack(margin=(0, 0, 5, 0)), enabled=False
        )
        self.delete_button = toga.Button(
            "Delete This Variant", on_press=self._on_delete, style=Pack(margin=(0, 0, 10, 0)), enabled=False
        )

        add_row = toga.Box(style=Pack(direction=ROW))
        self.new_variant_input = toga.TextInput(
            placeholder="e.g. A", style=Pack(flex=1, margin=(0, 5, 0, 0))
        )
        add_button = toga.Button("Add Variant", on_press=self._on_add, style=Pack(margin=0))
        add_row.add(self.new_variant_input)
        add_row.add(add_button)

        box.add(back_button)
        box.add(title)
        box.add(pager_row)
        box.add(self.dots_label)
        box.add(self.open_button)
        box.add(self.delete_button)
        box.add(add_row)
        return box

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
            self.open_button.enabled = False
            self.delete_button.enabled = False
            return

        variant_id, name = self.variants[self.current_index]
        self.variant_name_label.text = name
        self.dots_label.text = " ".join(
            DOT_FILLED if i == self.current_index else DOT_EMPTY for i in range(count)
        )
        self.left_arrow.enabled = self.current_index > 0
        self.right_arrow.enabled = self.current_index < count - 1
        self.open_button.enabled = True
        self.delete_button.enabled = True

    # -----------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------

    def _on_prev(self, widget):
        if self.current_index > 0:
            self.current_index -= 1
            self._render_current_page()

    def _on_next(self, widget):
        if self.current_index < len(self.variants) - 1:
            self.current_index += 1
            self._render_current_page()

    async def _on_add(self, widget):
        name = self.new_variant_input.value.strip()
        if not name:
            await self.window.dialog(toga.InfoDialog("Missing name", "Enter a name for the variant first (e.g. 'A')."))
            return

        create_variant(self.conn, self.session_id, name)
        self.new_variant_input.value = ""
        # Jump to the newly added variant (it's appended at the end)
        self.current_index = len(self.variants)  # will be clamped/set correctly in refresh
        self.refresh(keep_index=True)

    async def _on_open(self, widget):
        if not self.variants:
            return
        variant_id, name = self.variants[self.current_index]
        await self.on_open_variant(variant_id, name)

    async def _on_delete(self, widget):
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
            # Step back a page if we just deleted the last one
            if self.current_index > 0:
                self.current_index -= 1
            self.refresh(keep_index=True)