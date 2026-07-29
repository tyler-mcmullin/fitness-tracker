"""
Tests for splittracker.database

Covers every function currently in database.py.

To use in your Briefcase project:
  1. Copy this file to tests/test_database.py (replacing the old one)
  2. Adjust the import below if your package name differs
  3. Run with: briefcase dev --test   (or plain `pytest` in your venv)
"""
import pytest

from splitsaver.database import (
    init_db,
    create_split,
    get_splits,
    delete_split,
    rename_split,
    create_session,
    get_sessions,
    rename_session,
    delete_session,
    create_variant,
    get_variants,
    rename_variant,
    delete_variant,
    add_exercise,
    get_current_state,
    delete_exercise,
    rename_exercise,
    log_workout,
    get_workout_history,
    get_logged_sets,
    get_exercise_history,
    update_exercises,
)


@pytest.fixture
def conn():
    """Fresh in-memory database for each test — nothing touches your real data."""
    return init_db(":memory:")


@pytest.fixture
def variant_with_exercise(conn):
    """Builds split -> session -> exercise using the real create_* functions.
    create_session auto-creates a default variant ('A'), so we use that
    rather than creating a second one. Returns the variant_id."""
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")
    variant_id = get_variants(conn, session_id)[0][0]  # the auto-created default variant
    add_exercise(conn, variant_id, "Squat", sets=3, reps=8, weight=20)
    return variant_id


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

def test_init_db_creates_all_tables(conn):
    tables = ["splits", "sessions", "session_variants", "exercises", "workout_logs", "logged_sets"]
    for table in tables:
        conn.execute(f"SELECT * FROM {table}")  # raises if missing


# ---------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------

def test_create_and_get_split(conn):
    split_id = create_split(conn, "Push Pull Legs", notes="3x/week")
    splits = get_splits(conn)
    assert len(splits) == 1
    assert splits[0] == (split_id, "Push Pull Legs", "3x/week")


def test_get_splits_returns_multiple_in_order(conn):
    create_split(conn, "Push Pull Legs")
    create_split(conn, "Upper Lower")
    splits = get_splits(conn)
    assert [s[1] for s in splits] == ["Push Pull Legs", "Upper Lower"]


def test_delete_split_removes_split_and_everything_under_it(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")  # auto-creates "A"
    variant_id = get_variants(conn, session_id)[0][0]
    add_exercise(conn, variant_id, "Squat", sets=3, reps=8, weight=20)

    delete_split(conn, split_id)

    assert get_splits(conn) == []
    assert conn.execute("SELECT * FROM sessions WHERE split_id = ?", (split_id,)).fetchall() == []
    assert conn.execute("SELECT * FROM session_variants WHERE session_id = ?", (session_id,)).fetchall() == []
    assert conn.execute("SELECT * FROM exercises WHERE variant_id = ?", (variant_id,)).fetchall() == []


def test_rename_split(conn):
    split_id = create_split(conn, "Push Pull Legs")
    rename_split(conn, split_id, "PPL v2")

    splits = get_splits(conn)
    assert splits[0][1] == "PPL v2"


def test_rename_split_does_not_affect_sessions_underneath(conn):
    split_id = create_split(conn, "Push Pull Legs")
    create_session(conn, split_id, "Legs")

    rename_split(conn, split_id, "PPL v2")

    sessions = get_sessions(conn, split_id)
    assert sessions[0][1] == "Legs"  # untouched


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def test_create_and_get_sessions(conn):
    split_id = create_split(conn, "Push Pull Legs")
    create_session(conn, split_id, "Push")
    create_session(conn, split_id, "Pull")
    create_session(conn, split_id, "Legs")

    sessions = get_sessions(conn, split_id)
    assert [s[1] for s in sessions] == ["Push", "Pull", "Legs"]


def test_get_sessions_only_returns_matching_split(conn):
    split_a = create_split(conn, "Push Pull Legs")
    split_b = create_split(conn, "Upper Lower")
    create_session(conn, split_a, "Legs")
    create_session(conn, split_b, "Upper")

    sessions_a = get_sessions(conn, split_a)
    assert [s[1] for s in sessions_a] == ["Legs"]


def test_rename_session(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")

    rename_session(conn, session_id, "Lower Body")

    sessions = get_sessions(conn, split_id)
    assert sessions[0][1] == "Lower Body"


def test_delete_session_removes_session_and_everything_under_it(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")  # auto-creates "A"
    variant_id = get_variants(conn, session_id)[0][0]
    add_exercise(conn, variant_id, "Squat", sets=3, reps=8, weight=20)

    delete_session(conn, session_id)

    assert get_sessions(conn, split_id) == []
    assert conn.execute("SELECT * FROM session_variants WHERE session_id = ?", (session_id,)).fetchall() == []
    assert conn.execute("SELECT * FROM exercises WHERE variant_id = ?", (variant_id,)).fetchall() == []


def test_delete_session_does_not_affect_other_sessions(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id_legs = create_session(conn, split_id, "Legs")
    session_id_push = create_session(conn, split_id, "Push")

    delete_session(conn, session_id_legs)

    remaining = get_sessions(conn, split_id)
    assert [s[1] for s in remaining] == ["Push"]


# ---------------------------------------------------------------------------
# Session variants
# ---------------------------------------------------------------------------

def test_create_session_auto_creates_default_variant(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")

    variants = get_variants(conn, session_id)
    assert [v[1] for v in variants] == ["A"]


def test_create_and_get_variants(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")  # auto-creates "A"
    create_variant(conn, session_id, "B")

    variants = get_variants(conn, session_id)
    assert [v[1] for v in variants] == ["A", "B"]


def test_rename_variant(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")  # auto-creates "A"
    variant_id = get_variants(conn, session_id)[0][0]

    rename_variant(conn, variant_id, "Heavy Day")

    variants = get_variants(conn, session_id)
    assert variants[0][1] == "Heavy Day"


def test_delete_variant_removes_variant_and_its_exercises(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")  # auto-creates "A"
    variant_id = get_variants(conn, session_id)[0][0]
    add_exercise(conn, variant_id, "Squat", sets=3, reps=8, weight=20)

    delete_variant(conn, variant_id)

    assert get_variants(conn, session_id) == []
    assert conn.execute("SELECT * FROM exercises WHERE variant_id = ?", (variant_id,)).fetchall() == []


def test_delete_variant_does_not_affect_sibling_variants(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")  # auto-creates "A"
    variant_a = get_variants(conn, session_id)[0][0]
    variant_b = create_variant(conn, session_id, "B")

    delete_variant(conn, variant_a)

    remaining = get_variants(conn, session_id)
    assert [v[1] for v in remaining] == ["B"]


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------

def test_add_exercise_and_get_current_state(conn, variant_with_exercise):
    variant_id = variant_with_exercise
    state = get_current_state(conn, variant_id)
    assert len(state) == 1
    _, name, sets, reps, weight = state[0]
    assert (name, sets, reps, weight) == ("Squat", 3, 8, 20)


def test_add_exercise_preserves_order(conn):
    split_id = create_split(conn, "Push Pull Legs")
    session_id = create_session(conn, split_id, "Legs")
    variant_id = create_variant(conn, session_id, "A")
    add_exercise(conn, variant_id, "Squat")
    add_exercise(conn, variant_id, "Leg Press")
    add_exercise(conn, variant_id, "Calf Raise")

    state = get_current_state(conn, variant_id)
    assert [row[1] for row in state] == ["Squat", "Leg Press", "Calf Raise"]


def test_delete_exercise_removes_from_plan_only(conn, variant_with_exercise):
    variant_id = variant_with_exercise
    exercise_id = get_current_state(conn, variant_id)[0][0]

    # Log a workout first so history exists
    log_workout(conn, variant_id, [
        {"name": "Squat", "sets": [{"reps": 8, "weight": 20}]}
    ])

    delete_exercise(conn, exercise_id)

    assert get_current_state(conn, variant_id) == []
    # History should be untouched since logged_sets stores exercise_name as free text
    history = get_workout_history(conn, variant_id)
    assert len(history) == 1
    assert len(get_logged_sets(conn, history[0][0])) == 1


def test_rename_exercise_changes_the_plan(conn, variant_with_exercise):
    variant_id = variant_with_exercise
    exercise_id = get_current_state(conn, variant_id)[0][0]

    rename_exercise(conn, exercise_id, "Front Squat")

    state = get_current_state(conn, variant_id)
    assert state[0][1] == "Front Squat"


def test_rename_exercise_does_not_change_past_history(conn, variant_with_exercise):
    """History should keep the OLD name — it's free text, decoupled from the plan."""
    variant_id = variant_with_exercise
    exercise_id = get_current_state(conn, variant_id)[0][0]

    log_workout(conn, variant_id, [
        {"name": "Squat", "sets": [{"reps": 8, "weight": 20}]}
    ])

    rename_exercise(conn, exercise_id, "Front Squat")

    history = get_workout_history(conn, variant_id)
    logged = get_logged_sets(conn, history[0][0])
    assert logged[0][0] == "Squat"  # old name preserved in history

    # And querying exercise history under the NEW name finds nothing,
    # since it was logged under the old name before the rename
    assert get_exercise_history(conn, variant_id, "Front Squat") == []
    assert len(get_exercise_history(conn, variant_id, "Squat")) == 1


# ---------------------------------------------------------------------------
# Logging workouts / history
# ---------------------------------------------------------------------------

def test_log_workout_inserts_workout_log_and_sets(conn, variant_with_exercise):
    variant_id = variant_with_exercise

    log_workout(conn, variant_id, [
        {"name": "Squat", "sets": [{"reps": 8, "weight": 20}] * 3}
    ])

    logs = conn.execute("SELECT * FROM workout_logs WHERE variant_id = ?", (variant_id,)).fetchall()
    assert len(logs) == 1

    sets = conn.execute(
        "SELECT * FROM logged_sets WHERE workout_log_id = ?", (logs[0][0],)
    ).fetchall()
    assert len(sets) == 3
    assert all(row[5] == 20 for row in sets)  # weight column


def test_log_workout_does_not_change_exercises_table(conn, variant_with_exercise):
    variant_id = variant_with_exercise

    log_workout(conn, variant_id, [
        {"name": "Squat", "sets": [{"reps": 8, "weight": 25}] * 3}  # did MORE than planned
    ])

    row = conn.execute(
        "SELECT current_weight FROM exercises WHERE variant_id = ? AND name = ?",
        (variant_id, "Squat")
    ).fetchone()
    assert row[0] == 20  # still the original planned weight, untouched


def test_get_workout_history_orders_most_recent_first(conn, variant_with_exercise):
    variant_id = variant_with_exercise
    log_workout(conn, variant_id, [{"name": "Squat", "sets": [{"reps": 8, "weight": 20}]}])
    log_workout(conn, variant_id, [{"name": "Squat", "sets": [{"reps": 8, "weight": 25}]}])

    history = get_workout_history(conn, variant_id)
    assert len(history) == 2  # both logged, same date is fine — id DESC breaks the tie


def test_get_logged_sets_returns_correct_rows(conn, variant_with_exercise):
    variant_id = variant_with_exercise
    log_id = log_workout(conn, variant_id, [
        {"name": "Squat", "sets": [{"reps": 8, "weight": 20}, {"reps": 6, "weight": 22}]}
    ])

    sets = get_logged_sets(conn, log_id)
    assert sets == [
        ("Squat", 1, 8, 20),
        ("Squat", 2, 6, 22),
    ]


def test_get_exercise_history_across_multiple_workouts(conn, variant_with_exercise):
    variant_id = variant_with_exercise
    log_workout(conn, variant_id, [{"name": "Squat", "sets": [{"reps": 8, "weight": 20}] * 3}])
    log_workout(conn, variant_id, [{"name": "Squat", "sets": [{"reps": 8, "weight": 25}] * 3}])

    history = get_exercise_history(conn, variant_id, "Squat")
    weights_used = {row[3] for row in history}
    assert weights_used == {20, 25}


def test_get_exercise_history_ignores_other_exercises(conn, variant_with_exercise):
    variant_id = variant_with_exercise
    log_workout(conn, variant_id, [
        {"name": "Squat", "sets": [{"reps": 8, "weight": 20}]},
        {"name": "Leg Press", "sets": [{"reps": 10, "weight": 90}]},
    ])

    squat_history = get_exercise_history(conn, variant_id, "Squat")
    assert len(squat_history) == 1
    assert squat_history[0][3] == 20  # weight column, not leg press's 90


# ---------------------------------------------------------------------------
# update_exercises
# ---------------------------------------------------------------------------

def test_update_exercises_changes_the_plan(conn, variant_with_exercise):
    variant_id = variant_with_exercise

    update_exercises(conn, variant_id, "Squat", sets=3, reps=8, weight=25)

    row = conn.execute(
        "SELECT current_sets, current_reps, current_weight FROM exercises WHERE variant_id = ? AND name = ?",
        (variant_id, "Squat")
    ).fetchone()
    assert row == (3, 8, 25)


def test_update_exercises_only_affects_matching_variant_and_name(conn, variant_with_exercise):
    variant_id = variant_with_exercise
    add_exercise(conn, variant_id, "Leg Press", sets=3, reps=10, weight=90)

    update_exercises(conn, variant_id, "Squat", sets=3, reps=8, weight=25)

    leg_press = conn.execute(
        "SELECT current_weight FROM exercises WHERE variant_id = ? AND name = ?",
        (variant_id, "Leg Press")
    ).fetchone()
    assert leg_press[0] == 90  # untouched