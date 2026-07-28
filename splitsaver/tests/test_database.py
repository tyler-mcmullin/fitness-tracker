"""
Tests for splittracker.database

Run with: briefcase dev --test   (or plain `pytest` in your venv)
"""
import pytest

from splitsaver.database import (
    init_db,
    log_workout,
    update_exercises,
)


@pytest.fixture
def conn():
    """Fresh in-memory database for each test — nothing touches your real data."""
    return init_db(":memory:")


@pytest.fixture
def variant_with_exercise(conn):
    """
    Manually inserts a split -> session -> variant -> exercise chain,
    since there's no create_split/create_session/create_variant/add_exercise yet.
    Returns the variant_id.
    """
    cur = conn.cursor()
    cur.execute("INSERT INTO splits (name, notes) VALUES (?, ?)", ("Push Pull Legs", None))
    split_id = cur.lastrowid

    cur.execute(
        "INSERT INTO sessions (split_id, name, order_index) VALUES (?, ?, ?)",
        (split_id, "Legs", 0)
    )
    session_id = cur.lastrowid

    cur.execute(
        "INSERT INTO session_variants (session_id, name, order_index) VALUES (?, ?, ?)",
        (session_id, "A", 0)
    )
    variant_id = cur.lastrowid

    cur.execute(
        """INSERT INTO exercises
           (variant_id, name, order_index, current_sets, current_reps, current_weight)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (variant_id, "Squat", 0, 3, 8, 20)
    )
    conn.commit()
    return variant_id


def test_init_db_creates_all_tables(conn):
    """Confirms every table exists and is queryable without error."""
    tables = ["splits", "sessions", "session_variants", "exercises", "workout_logs", "logged_sets"]
    for table in tables:
        # Will raise sqlite3.OperationalError if the table doesn't exist
        conn.execute(f"SELECT * FROM {table}")


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
    """Logging a workout should not touch the `exercises` plan table."""
    variant_id = variant_with_exercise

    log_workout(conn, variant_id, [
        {"name": "Squat", "sets": [{"reps": 8, "weight": 25}] * 3}  # did MORE than planned
    ])

    row = conn.execute(
        "SELECT current_weight FROM exercises WHERE variant_id = ? AND name = ?",
        (variant_id, "Squat")
    ).fetchone()
    assert row[0] == 20  # still the original planned weight, untouched


def test_update_exercises_changes_the_plan(conn, variant_with_exercise):
    variant_id = variant_with_exercise

    update_exercises(conn, variant_id, "Squat", sets=3, reps=8, weight=25)

    row = conn.execute(
        "SELECT current_sets, current_reps, current_weight FROM exercises WHERE variant_id = ? AND name = ?",
        (variant_id, "Squat")
    ).fetchone()
    assert row == (3, 8, 25)


def test_update_exercises_only_affects_matching_variant_and_name(conn, variant_with_exercise):
    """Sanity check: update_exercises shouldn't leak into other rows."""
    variant_id = variant_with_exercise

    # Add a second exercise on the same variant
    conn.execute(
        """INSERT INTO exercises
           (variant_id, name, order_index, current_sets, current_reps, current_weight)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (variant_id, "Leg Press", 1, 3, 10, 90)
    )
    conn.commit()

    update_exercises(conn, variant_id, "Squat", sets=3, reps=8, weight=25)

    leg_press = conn.execute(
        "SELECT current_weight FROM exercises WHERE variant_id = ? AND name = ?",
        (variant_id, "Leg Press")
    ).fetchone()
    assert leg_press[0] == 90  # untouched