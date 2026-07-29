import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from splitsaver.database import create_variant, get_variants, delete_variant


class VariantsScreen:
    """Shows the variants (e.g. 'A', 'B') under one session, as tabs.
    Each tab has a button to open that variant's exercises and a button to delete it."""

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

        self.tab_container = toga.OptionContainer(style=Pack(flex=1, margin=(0, 0, 10, 0)))

        add_row = toga.Box(style=Pack(direction=ROW))
        self.new_variant_input = toga.TextInput(
            placeholder="e.g. A",
            style=Pack(flex=1, margin=(0, 5, 0, 0)),
        )
        add_button = toga.Button("Add Variant", on_press=self._on_add, style=Pack(margin=0))
        add_row.add(self.new_variant_input)
        add_row.add(add_button)

        box.add(back_button)
        box.add(title)
        box.add(self.tab_container)
        box.add(add_row)
        return box

    def refresh(self):
        """Re-reads variants for this session and rebuilds the tabs."""
        variants = get_variants(self.conn, self.session_id)  # list of (id, name)

        # Clear existing tabs before rebuilding
        while len(self.tab_container.content) > 0:
            self.tab_container.content.remove(self.tab_container.content[0])

        for variant_id, name in variants:
            tab_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

            open_button = toga.Button(
                "Open Exercises",
                on_press=lambda widget, vid=variant_id, vname=name: self.on_open_variant(vid, vname),
                style=Pack(margin=(0, 0, 10, 0)),
            )
            delete_button = toga.Button(
                "Delete This Variant",
                on_press=lambda widget, vid=variant_id: self._on_delete(vid),
                style=Pack(margin=0),
            )

            tab_box.add(open_button)
            tab_box.add(delete_button)
            self.tab_container.content.append(text=name, content=tab_box)

    # -----------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------

    def _on_add(self, widget):
        name = self.new_variant_input.value.strip()
        if not name:
            self.window.info_dialog("Missing name", "Enter a name for the variant first (e.g. 'A').")
            return

        create_variant(self.conn, self.session_id, name)
        self.new_variant_input.value = ""
        self.refresh()

    def _on_delete(self, variant_id):
        def confirm_and_delete(window, dialog_result):
            if dialog_result:
                delete_variant(self.conn, variant_id)
                self.refresh()

        self.window.confirm_dialog(
            "Delete variant",
            "This will permanently delete this variant and its exercise plan. Workout history stays intact. Continue?",
            on_result=confirm_and_delete,
        )