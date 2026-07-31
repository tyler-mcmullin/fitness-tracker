import sqlite3

def init_db(path):
    """Database initialization logic that creates Splits, sessions, session_variants, and exercises"""

    conn = sqlite3.connect(path)

    # Main Workout Tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS splits (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            notes TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            split_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            order_index INTEGER,
            FOREIGN KEY (split_id) REFERENCES splits(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_variants (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            name TEXT NOT NULL,          -- 'A', 'B', or 'Default'
            order_index INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY,
        variant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        order_index INTEGER,
        current_sets INTEGER,
        current_reps INTEGER,
        current_weight REAL,
        unit TEXT NOT NULL DEFAULT 'lb',   -- 'lb', 'kg', 'sec', or 'min'
        FOREIGN KEY (variant_id) REFERENCES session_variants(id)
    )
    """)


    # Logged History
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY,
            variant_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (variant_id) REFERENCES session_variants(id)
        )
    """)
    # One row per exercise per workout (not per individual set) — sets is a
    # count, reps/weight/unit apply to all sets of that exercise that day.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logged_exercises (
            id INTEGER PRIMARY KEY,
            workout_log_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            sets INTEGER,
            reps INTEGER,
            weight REAL,
            unit TEXT NOT NULL DEFAULT 'lb',   -- preserved as of when it was logged
            FOREIGN KEY (workout_log_id) REFERENCES workout_logs(id)
        )
    """)

    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------

def create_split(conn, name, notes=None):
    """Creates a new split (e.g. 'Push Pull Legs') and returns its id."""
    cur = conn.execute(
        "INSERT INTO splits (name, notes) VALUES (?, ?)",
        (name, notes)
    )
    conn.commit()
    return cur.lastrowid


def get_splits(conn):
    """Returns all splits as a list of (id, name, notes)."""
    cur = conn.execute("SELECT id, name, notes FROM splits ORDER BY id")
    return cur.fetchall()


def delete_split(conn, split_id):
    """Deletes a split. Does NOT cascade automatically (no ON DELETE CASCADE),
    so sessions/variants/exercises under it are deleted explicitly first."""
    session_ids = [row[0] for row in conn.execute(
        "SELECT id FROM sessions WHERE split_id = ?", (split_id,)
    )]
    for session_id in session_ids:
        variant_ids = [row[0] for row in conn.execute(
            "SELECT id FROM session_variants WHERE session_id = ?", (session_id,)
        )]
        for variant_id in variant_ids:
            conn.execute("DELETE FROM exercises WHERE variant_id = ?", (variant_id,))
        conn.execute("DELETE FROM session_variants WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE split_id = ?", (split_id,))
    conn.execute("DELETE FROM splits WHERE id = ?", (split_id,))
    conn.commit()


def rename_split(conn, split_id, new_name):
    """Renames a split. Sessions/variants/exercises underneath are unaffected."""
    conn.execute(
        "UPDATE splits SET name = ? WHERE id = ?",
        (new_name, split_id)
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def create_session(conn, split_id, name):
    """Creates a new session (e.g. 'Legs') under a split and returns its id.
    Also creates a default variant automatically, named '{session name} 1'
    (e.g. 'Legs 1'), since every session needs at least one place to hold
    exercises. This default variant stays hidden in the UI until the user
    explicitly adds a second variant — at which point they read naturally
    as a pair, e.g. 'Legs 1' / 'Legs 2'."""
    cur = conn.execute(
        "INSERT INTO sessions (split_id, name, order_index) VALUES (?, ?, "
        "(SELECT COALESCE(MAX(order_index), -1) + 1 FROM sessions WHERE split_id = ?))",
        (split_id, name, split_id)
    )
    session_id = cur.lastrowid
    create_variant(conn, session_id, f"{name} 1")
    conn.commit()
    return session_id


def get_sessions(conn, split_id):
    """Returns all sessions for a split as a list of (id, name)."""
    cur = conn.execute(
        "SELECT id, name FROM sessions WHERE split_id = ? ORDER BY order_index",
        (split_id,)
    )
    return cur.fetchall()


def rename_session(conn, session_id, new_name):
    """Renames a session (e.g. 'Legs' -> 'Lower Body'). Variants/exercises underneath are unaffected."""
    conn.execute(
        "UPDATE sessions SET name = ? WHERE id = ?",
        (new_name, session_id)
    )
    conn.commit()


def delete_session(conn, session_id):
    """Deletes a session and everything under it (variants, exercises).
    Does NOT cascade automatically (no ON DELETE CASCADE), so variants/exercises
    are deleted explicitly first. Workout history is untouched."""
    variant_ids = [row[0] for row in conn.execute(
        "SELECT id FROM session_variants WHERE session_id = ?", (session_id,)
    )]
    for variant_id in variant_ids:
        conn.execute("DELETE FROM exercises WHERE variant_id = ?", (variant_id,))
    conn.execute("DELETE FROM session_variants WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Session variants (e.g. Legs A / Legs B)
# ---------------------------------------------------------------------------

def create_variant(conn, session_id, name):
    """Creates a new variant (e.g. 'A') under a session and returns its id."""
    cur = conn.execute(
        "INSERT INTO session_variants (session_id, name, order_index) VALUES (?, ?, "
        "(SELECT COALESCE(MAX(order_index), -1) + 1 FROM session_variants WHERE session_id = ?))",
        (session_id, name, session_id)
    )
    conn.commit()
    return cur.lastrowid


def get_variants(conn, session_id):
    """Returns all variants for a session as a list of (id, name)."""
    cur = conn.execute(
        "SELECT id, name FROM session_variants WHERE session_id = ? ORDER BY order_index",
        (session_id,)
    )
    return cur.fetchall()


def rename_variant(conn, variant_id, new_name):
    """Renames a variant (e.g. 'A' -> 'Heavy Day'). Exercises underneath are unaffected."""
    conn.execute(
        "UPDATE session_variants SET name = ? WHERE id = ?",
        (new_name, variant_id)
    )
    conn.commit()


def delete_variant(conn, variant_id):
    """Deletes a variant and its exercise plan. Workout history is untouched,
    since workout_logs/logged_exercises reference variant_id but are never cleaned up
    here — history for a deleted variant remains queryable by id if needed."""
    conn.execute("DELETE FROM exercises WHERE variant_id = ?", (variant_id,))
    conn.execute("DELETE FROM session_variants WHERE id = ?", (variant_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Exercises (current plan for a variant)
# ---------------------------------------------------------------------------

def add_exercise(conn, variant_id, name, sets=3, reps=8, weight=0, unit="lb"):
    """Adds a new exercise to a variant's plan and returns its id.
    unit is one of 'lb', 'kg', 'sec', or 'min'."""
    cur = conn.execute(
        """INSERT INTO exercises
           (variant_id, name, order_index, current_sets, current_reps, current_weight, unit)
           VALUES (?, ?, (SELECT COALESCE(MAX(order_index), -1) + 1 FROM exercises WHERE variant_id = ?), ?, ?, ?, ?)""",
        (variant_id, name, variant_id, sets, reps, weight, unit)
    )
    conn.commit()
    return cur.lastrowid


def duplicate_exercises(conn, source_variant_id, target_variant_id):
    """Copies every exercise from one variant's plan into another, preserving
    sets/reps/weight/unit and order. Used when creating a new variant as a
    starting point copied from an existing one (e.g. 'Push 2' starting as
    a copy of 'Push 1', ready to tweak). Does not touch history."""
    exercises = get_current_state(conn, source_variant_id)  # (id, name, sets, reps, weight, unit)
    for _id, name, sets, reps, weight, unit in exercises:
        add_exercise(conn, target_variant_id, name, sets=sets, reps=reps, weight=weight, unit=unit)


def get_current_state(conn, variant_id):
    """Returns the current plan (last known sets/reps/weight/unit) for each exercise in a variant.
    Each row is (id, name, current_sets, current_reps, current_weight, unit)."""
    cur = conn.execute(
        """SELECT id, name, current_sets, current_reps, current_weight, unit
           FROM exercises
           WHERE variant_id = ? ORDER BY order_index""",
        (variant_id,)
    )
    return cur.fetchall()


def delete_exercise(conn, exercise_id):
    """Removes an exercise from the plan. Does not affect past logged_exercises history,
    since logged_exercises stores exercise_name as free text, decoupled from this table."""
    conn.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
    conn.commit()


def rename_exercise(conn, exercise_id, new_name):
    """Renames an exercise in the plan (e.g. 'Squat' -> 'Front Squat').
    Past logged_exercises keep the OLD name, since exercise_name there is free text —
    your history stays accurate to what it was actually called at the time."""
    conn.execute(
        "UPDATE exercises SET name = ? WHERE id = ?",
        (new_name, exercise_id)
    )
    conn.commit()


# ---------------------------------------------------------------------------
# History Functions - log workout data
# ---------------------------------------------------------------------------

def log_workout(conn, variant_id, exercise_entries):
    """Saves workout history — one row per exercise, not per individual set.

    exercise_entries: list of dicts, e.g.
        [{"name": "Squat", "unit": "lb", "sets": 3, "reps": 8, "weight": 25}]
    "unit" is optional per entry and defaults to 'lb' if omitted.
    """
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workout_logs (variant_id, date) VALUES (?, DATE('now'))",
        (variant_id,)
    )
    workout_log_id = cur.lastrowid

    for exercise in exercise_entries:
        cur.execute(
            """INSERT INTO logged_exercises
               (workout_log_id, exercise_name, sets, reps, weight, unit)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                workout_log_id,
                exercise["name"],
                exercise["sets"],
                exercise["reps"],
                exercise["weight"],
                exercise.get("unit", "lb"),
            )
        )
    conn.commit()
    return workout_log_id


def get_workout_history(conn, variant_id):
    """Returns all past workout_logs for a variant, most recent first.
    Each row is (id, date, notes)."""
    cur = conn.execute(
        """SELECT id, date, notes FROM workout_logs
           WHERE variant_id = ? ORDER BY date DESC, id DESC""",
        (variant_id,)
    )
    return cur.fetchall()


def get_logged_exercises(conn, workout_log_id):
    """Returns all exercises recorded for a specific past workout — one row
    per exercise, not per individual set.
    Each row is (exercise_name, sets, reps, weight, unit)."""
    cur = conn.execute(
        """SELECT exercise_name, sets, reps, weight, unit
           FROM logged_exercises
           WHERE workout_log_id = ? ORDER BY exercise_name""",
        (workout_log_id,)
    )
    return cur.fetchall()


def get_logged_exercise_names(conn, variant_id):
    """Returns the distinct exercise names ever logged for this variant, alphabetically.
    Useful for a history browser, since a deleted or renamed exercise can still
    have history worth viewing even though it's no longer in the current plan."""
    cur = conn.execute(
        """SELECT DISTINCT le.exercise_name
           FROM logged_exercises le
           JOIN workout_logs wl ON wl.id = le.workout_log_id
           WHERE wl.variant_id = ?
           ORDER BY le.exercise_name""",
        (variant_id,)
    )
    return [row[0] for row in cur.fetchall()]


def get_exercise_history(conn, variant_id, exercise_name):
    """Returns every logged entry for one specific exercise across all past workouts —
    one row per workout (not per set) — useful for a progress-over-time view.
    Each row is (date, sets, reps, weight, unit)."""
    cur = conn.execute(
        """SELECT wl.date, le.sets, le.reps, le.weight, le.unit
           FROM logged_exercises le
           JOIN workout_logs wl ON wl.id = le.workout_log_id
           WHERE wl.variant_id = ? AND le.exercise_name = ?
           ORDER BY wl.date ASC""",
        (variant_id, exercise_name)
    )
    return cur.fetchall()


def update_exercises(conn, variant_id, exercise_name, sets, reps, weight, unit="lb"):
    """Updates an individual exercise, including its unit."""
    conn.execute(
        """UPDATE exercises
           SET current_sets = ?, current_reps = ?, current_weight = ?, unit = ?
           WHERE variant_id = ? AND name = ?""",
        (sets, reps, weight, unit, variant_id, exercise_name)
    )
    conn.commit()