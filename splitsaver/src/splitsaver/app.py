import toga

from splitsaver.database import init_db
from splitsaver.screens.splits_screen import SplitsScreen
from splitsaver.screens.sessions_screen import SessionsScreen
from splitsaver.screens.variants_screen import VariantsScreen


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
        self.current_split_id = split_id
        self.current_split_name = split_name
        screen = SessionsScreen(
            self.conn,
            self.main_window,
            split_id,
            split_name,
            on_back=self.show_splits_screen,
            on_open_session=self.show_variants_screen,
        )
        self.main_window.content = screen.box

    def show_variants_screen(self, session_id, session_name):
        screen = VariantsScreen(
            self.conn,
            self.main_window,
            session_id,
            session_name,
            on_back=lambda: self.show_sessions_screen(self.current_split_id, self.current_split_name),
        )
        self.main_window.content = screen.box


def main():
    return SplitSaver()