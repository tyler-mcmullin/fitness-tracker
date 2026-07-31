import toga

from splitsaver.database import init_db
from splitsaver.screens.splits_screen import SplitsScreen
from splitsaver.screens.sessions_screen import SessionsScreen
from splitsaver.screens.variants_screen import VariantsScreen
from splitsaver.screens.history_splits_screen import HistorySplitsScreen
from splitsaver.screens.history_sessions_screen import HistorySessionsScreen
from splitsaver.screens.history_variants_screen import HistoryVariantsScreen
from splitsaver.screens.history_exercises_screen import HistoryExercisesScreen
from splitsaver.screens.history_exercise_detail_screen import HistoryExerciseDetailScreen


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
            on_view_history=self.show_history_splits_screen,
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

    # -----------------------------------------------------------------
    # Navigation — history browsing (read-only mirror of the flow above)
    # -----------------------------------------------------------------

    def show_history_splits_screen(self):
        screen = HistorySplitsScreen(
            self.conn,
            self.main_window,
            on_open_split=self.show_history_sessions_screen,
            on_back=self.show_splits_screen,
        )
        self.main_window.content = screen.box

    def show_history_sessions_screen(self, split_id, split_name):
        screen = HistorySessionsScreen(
            self.conn,
            self.main_window,
            split_id,
            split_name,
            on_open_session=lambda session_id, session_name: self.show_history_variants_screen(
                split_id, split_name, session_id, session_name
            ),
            on_back=self.show_history_splits_screen,
        )
        self.main_window.content = screen.box

    def show_history_variants_screen(self, split_id, split_name, session_id, session_name):
        screen = HistoryVariantsScreen(
            self.conn,
            self.main_window,
            session_id,
            session_name,
            on_open_variant=lambda variant_id, variant_name: self.show_history_exercises_screen(
                split_id, split_name, session_id, session_name, variant_id, variant_name
            ),
            on_back=lambda: self.show_history_sessions_screen(split_id, split_name),
        )
        self.main_window.content = screen.box

    def show_history_exercises_screen(
        self, split_id, split_name, session_id, session_name, variant_id, variant_name
    ):
        screen = HistoryExercisesScreen(
            self.conn,
            self.main_window,
            variant_id,
            variant_name,
            on_open_exercise=lambda exercise_name: self.show_history_exercise_detail_screen(
                split_id, split_name, session_id, session_name, variant_id, variant_name, exercise_name
            ),
            on_back=lambda: self.show_history_variants_screen(split_id, split_name, session_id, session_name),
        )
        self.main_window.content = screen.box

    def show_history_exercise_detail_screen(
        self, split_id, split_name, session_id, session_name, variant_id, variant_name, exercise_name
    ):
        screen = HistoryExerciseDetailScreen(
            self.conn,
            self.main_window,
            variant_id,
            variant_name,
            exercise_name,
            on_back=lambda: self.show_history_exercises_screen(
                split_id, split_name, session_id, session_name, variant_id, variant_name
            ),
        )
        self.main_window.content = screen.box


def main():
    return SplitSaver()