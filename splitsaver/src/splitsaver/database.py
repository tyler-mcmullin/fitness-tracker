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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logged_sets (
            id INTEGER PRIMARY KEY,
            workout_log_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            set_number INTEGER,
            reps INTEGER,
            weight REAL,
            FOREIGN KEY (workout_log_id) REFERENCES workout_logs(id)
        )
    """)
    conn.commit()
    return conn

# History Functions - log workout data
def log_workout(conn, variant_id, exercise_entries):
    """Saves workout history."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workout_logs (variant_id, date) VALUES (?, DATE('now'))",
        (variant_id,)
    )
    workout_log_id = cur.lastrowid

    for exercise in exercise_entries:
        for i, s in enumerate(exercise["sets"], start=1):
            cur.execute(
                """INSERT INTO logged_sets
                   (workout_log_id, exercise_name, set_number, reps, weight)
                   VALUES (?, ?, ?, ?, ?)""",
                (workout_log_id, exercise["name"], i, s["reps"], s["weight"])
            )
    conn.commit()


def update_exercises(conn, variant_id, exercise_name, sets, reps, weight):
    """Updates an individual exercise."""
    conn.execute(
        """UPDATE exercises
           SET current_sets = ?, current_reps = ?, current_weight = ?
           WHERE variant_id = ? AND name = ?""",
        (sets, reps, weight, variant_id, exercise_name)
    )
    conn.commit()