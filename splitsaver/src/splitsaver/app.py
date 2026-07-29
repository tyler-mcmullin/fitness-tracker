import toga

from splitsaver.database import init_db
from splitsaver.screens.splits_screen import SplitsScreen
from splitsaver.screens.sessions_screen import SessionsScreen


class SplitSaver(toga.App):
    def startup(self):
        self.conn = init_db(str(self.paths.data / "workouts.db"))

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.show_splits_screen()
        self.main_window.show()

    # -----------------------------------------------------------------
    # Navigation — each method builds a screen and shows it
    # -----------------------------------------------------------------

    def show_splits_screen(self):
        screen = SplitsScreen(
            self.conn,
            self.main_window,
            on_open_split=self.show_sessions_screen,
        )
        self.main_window.content = screen.box

    def show_sessions_screen(self, split_id, split_name):
        screen = SessionsScreen(
            self.conn,
            self.main_window,
            split_id,
            split_name,
            on_back=self.show_splits_screen,
            on_open_session=self.show_variants_screen_stub,
        )
        self.main_window.content = screen.box

    def show_variants_screen_stub(self, session_id, session_name):
        """Placeholder until the Variants screen exists."""
        self.main_window.info_dialog(
            "Open session",
            f"Opening '{session_name}' (id={session_id}) — Variants screen not built yet.",
        )


def main():
    return SplitSaver()