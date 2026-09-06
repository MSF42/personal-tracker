import aiosqlite

MIGRATIONS = [
    {
        "version": 1,
        "name": "create_schema_migrations",
        "sql": """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """,
    },
    {
        "version": 2,
        "name": "create_tasks_table",
        "sql": """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                due_date TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                repeat_type TEXT,
                repeat_interval INTEGER,               
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """,
    },
    {
        "version": 3,
        "name": "create_tasks_indexes",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
            CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
            CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed);
        """,
    },
    {
        "version": 4,
        "name": "create_running_activities_table",
        "sql": """
               CREATE TABLE IF NOT EXISTS running_activities
               (
                   id               INTEGER PRIMARY KEY AUTOINCREMENT,
                   date             TEXT    NOT NULL,
                   duration_seconds INTEGER NOT NULL,
                   distance_km      REAL    NOT NULL,
                   notes            TEXT,
                   created_at       TEXT    NOT NULL,
                   updated_at       TEXT    NOT NULL
               )
               """,
    },
    {
        "version": 5,
        "name": "create_running_activities_indexes",
        "sql": """
               CREATE INDEX IF NOT EXISTS idx_running_date ON running_activities (date);
               CREATE INDEX IF NOT EXISTS idx_running_distance ON running_activities (distance_km);
               """,
    },
    {
        "version": 6,
        "name": "create_exercise_table",
        "sql": """
                  CREATE TABLE IF NOT EXISTS exercises (                                                  
                  id INTEGER PRIMARY KEY AUTOINCREMENT,                                               
                  name TEXT NOT NULL UNIQUE,                                                          
                  description TEXT,                                                                   
                  muscle_group TEXT NOT NULL,                                                         
                  equipment TEXT,                                                                     
                  instructions TEXT,                                                                  
                  created_at TEXT NOT NULL,                                                           
                  updated_at TEXT NOT NULL                                                            
                  ); 
                """,
    },
    {
        "version": 7,
        "name": "create_exercise_muscle_group_index",
        "sql": "CREATE INDEX IF NOT EXISTS idx_exercise_muscle_group ON exercises(muscle_group);",
    },
    {
        "version": 8,
        "name": "create_exercise_routines",
        "sql": """
                  CREATE TABLE IF NOT EXISTS workout_routines (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,                     
                  name TEXT NOT NULL,                                       
                  description TEXT,                                         
                  created_at TEXT NOT NULL,                                 
                  updated_at TEXT NOT NULL 
                  );
        """,
    },
    {
        "version": 9,
        "name": "create_routine_exercises_table",
        "sql": """
               CREATE TABLE IF NOT EXISTS routine_exercises
               (
                   id          INTEGER PRIMARY KEY AUTOINCREMENT,
                   routine_id  INTEGER NOT NULL,
                   exercise_id INTEGER NOT NULL,
                   sets        INTEGER NOT NULL DEFAULT 3,
                   reps        INTEGER NOT NULL DEFAULT 10,
                   order_index INTEGER NOT NULL DEFAULT 0,
                   FOREIGN KEY (routine_id) REFERENCES workout_routines (id) ON DELETE CASCADE,
                   FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE,
                   UNIQUE (routine_id, exercise_id)
               );
               """,
    },
    {
        "version": 10,
        "name": "create_workout_logs_table",
        "sql": """
               CREATE TABLE IF NOT EXISTS workout_logs
               (
                   id         INTEGER PRIMARY KEY AUTOINCREMENT,
                   routine_id INTEGER NOT NULL,
                   date       TEXT    NOT NULL,
                   notes      TEXT,
                   created_at TEXT    NOT NULL,
                   FOREIGN KEY (routine_id) REFERENCES workout_routines (id) ON DELETE CASCADE
               );
               """,
    },
    {
        "version": 11,
        "name": "create_set_logs_table",
        "sql": """
               CREATE TABLE IF NOT EXISTS set_logs
               (
                   id             INTEGER PRIMARY KEY AUTOINCREMENT,
                   workout_log_id INTEGER NOT NULL,
                   exercise_id    INTEGER NOT NULL,
                   set_number     INTEGER NOT NULL,
                   reps           INTEGER NOT NULL,
                   weight         REAL,
                   FOREIGN KEY (workout_log_id) REFERENCES workout_logs (id) ON DELETE CASCADE,
                   FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
               );
               """,
    },
    {
        "version": 12,
        "name": "no_op_rename_exercise_routines",  # was broken; workout_routines already existed in migration 8
        "sql": "SELECT 1;",  # no-op: workout_routines already created correctly in migration 8
    },
    {
        "version": 13,
        "name": "create_gpx_segments_table",
        "sql": """
               CREATE TABLE IF NOT EXISTS gpx_segments (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   running_activity_id INTEGER NOT NULL,
                   segment_name TEXT NOT NULL,
                   distance_km REAL NOT NULL,
                   duration_seconds INTEGER NOT NULL,
                   pace REAL NOT NULL,
                   pace_formatted TEXT NOT NULL,
                   FOREIGN KEY (running_activity_id) REFERENCES running_activities (id) ON DELETE CASCADE
               );
               CREATE INDEX IF NOT EXISTS idx_gpx_segments_activity ON gpx_segments (running_activity_id);
               """,
    },
    {
        "version": 14,
        "name": "add_has_gpx_to_running_activities",
        "sql": """
               ALTER TABLE running_activities ADD COLUMN has_gpx INTEGER NOT NULL DEFAULT 0;
               """,
    },
    {
        "version": 15,
        "name": "add_title_to_running_activities",
        "sql": """
               ALTER TABLE running_activities ADD COLUMN title TEXT;
               """,
    },
    {
        "version": 16,
        "name": "create_user_settings_table",
        "sql": """
               CREATE TABLE IF NOT EXISTS user_settings (
                   key TEXT PRIMARY KEY,
                   value TEXT NOT NULL
               );
               """,
    },
    {
        "version": 17,
        "name": "add_repeat_days_to_tasks",
        "sql": """
               ALTER TABLE tasks ADD COLUMN repeat_days TEXT;
               """,
    },
    # Versions 18, 23 and 25 built the notes outliner (notes table, its due-date
    # columns and the node_links backlink index). The feature was removed in
    # favour of the companion Outboard2 app; the numbers stay retired so an
    # existing database's schema_migrations rows keep their meaning. Databases
    # created before the removal still carry those tables and their data.
    {
        "version": 19,
        "name": "create_measurements_tables",
        "sql": """
               CREATE TABLE measurements (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL UNIQUE,
                   unit TEXT NOT NULL DEFAULT '',
                   sort_order INTEGER NOT NULL DEFAULT 0,
                   created_at TEXT NOT NULL,
                   updated_at TEXT NOT NULL
               );

               CREATE TABLE measurement_entries (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   measurement_id INTEGER NOT NULL REFERENCES measurements(id) ON DELETE CASCADE,
                   date TEXT NOT NULL,
                   value REAL NOT NULL,
                   notes TEXT,
                   created_at TEXT NOT NULL,
                   updated_at TEXT NOT NULL
               );

               CREATE INDEX idx_measurement_entries_lookup
                   ON measurement_entries (measurement_id, date DESC);

               INSERT INTO measurements (name, unit, sort_order, created_at, updated_at)
               VALUES ('Weight', 'lbs', 0, datetime('now'), datetime('now'))
               ON CONFLICT(name) DO NOTHING;
               """,
    },
    {
        "version": 20,
        "name": "create_habits_tables",
        "sql": """
               CREATE TABLE IF NOT EXISTS habits (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL,
                   description TEXT,
                   frequency TEXT NOT NULL DEFAULT 'daily',
                   frequency_days TEXT,
                   color TEXT NOT NULL DEFAULT '#3b82f6',
                   archived INTEGER NOT NULL DEFAULT 0,
                   created_at TEXT NOT NULL,
                   updated_at TEXT NOT NULL
               );
               CREATE TABLE IF NOT EXISTS habit_completions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   habit_id INTEGER NOT NULL,
                   date TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
                   UNIQUE (habit_id, date)
               );
               CREATE INDEX IF NOT EXISTS idx_habit_completions_habit_date ON habit_completions (habit_id, date DESC);
               """,
    },
    {
        "version": 21,
        "name": "add_priority_to_tasks",
        "sql": "ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'",
    },
    {
        "version": 22,
        "name": "add_fk_indices",
        "sql": """
               CREATE INDEX IF NOT EXISTS idx_routine_exercises_routine_id ON routine_exercises (routine_id);
               CREATE INDEX IF NOT EXISTS idx_set_logs_workout_log_id ON set_logs (workout_log_id);
               """,
    },
    {
        "version": 24,
        "name": "create_search_index_fts5",
        "sql": """
               CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                   kind UNINDEXED,
                   entity_id UNINDEXED,
                   parent_id UNINDEXED,
                   title,
                   body,
                   tokenize = 'porter unicode61'
               );
               """,
    },
    {
        "version": 26,
        "name": "create_countdowns",
        "sql": """
               CREATE TABLE IF NOT EXISTS countdowns (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   date TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   updated_at TEXT NOT NULL
               );
               CREATE INDEX IF NOT EXISTS idx_countdowns_date ON countdowns (date);
               """,
    },
    {
        "version": 27,
        "name": "add_gpx_sha256_to_running_activities",
        "sql": """
               ALTER TABLE running_activities ADD COLUMN gpx_sha256 TEXT;
               CREATE UNIQUE INDEX IF NOT EXISTS idx_running_activities_gpx_sha256
                   ON running_activities (gpx_sha256) WHERE gpx_sha256 IS NOT NULL;
               """,
    },
    {
        "version": 28,
        "name": "fit_import_metrics_laps_samples",
        "sql": """
               ALTER TABLE running_activities RENAME COLUMN gpx_sha256 TO import_sha256;
               ALTER TABLE running_activities ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';
               UPDATE running_activities SET source = 'gpx' WHERE has_gpx = 1;
               ALTER TABLE running_activities ADD COLUMN source_uuid TEXT;
               ALTER TABLE running_activities ADD COLUMN start_time TEXT;
               ALTER TABLE running_activities ADD COLUMN elapsed_seconds INTEGER;
               ALTER TABLE running_activities ADD COLUMN is_indoor INTEGER NOT NULL DEFAULT 0;
               ALTER TABLE running_activities ADD COLUMN avg_hr INTEGER;
               ALTER TABLE running_activities ADD COLUMN max_hr INTEGER;
               ALTER TABLE running_activities ADD COLUMN avg_cadence INTEGER;
               ALTER TABLE running_activities ADD COLUMN max_cadence INTEGER;
               ALTER TABLE running_activities ADD COLUMN calories INTEGER;
               ALTER TABLE running_activities ADD COLUMN total_ascent_m REAL;
               ALTER TABLE running_activities ADD COLUMN total_descent_m REAL;
               ALTER TABLE running_activities ADD COLUMN avg_power INTEGER;
               ALTER TABLE running_activities ADD COLUMN max_power INTEGER;
               ALTER TABLE running_activities ADD COLUMN avg_temperature_c REAL;
               CREATE UNIQUE INDEX IF NOT EXISTS idx_running_activities_source_uuid
                   ON running_activities (source_uuid) WHERE source_uuid IS NOT NULL;

               CREATE TABLE IF NOT EXISTS run_laps (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   running_activity_id INTEGER NOT NULL,
                   lap_index INTEGER NOT NULL,
                   start_time TEXT,
                   timer_seconds INTEGER NOT NULL,
                   elapsed_seconds INTEGER,
                   distance_km REAL NOT NULL,
                   pace REAL,
                   avg_hr INTEGER,
                   max_hr INTEGER,
                   avg_cadence INTEGER,
                   avg_power INTEGER,
                   total_ascent_m REAL,
                   trigger TEXT,
                   FOREIGN KEY (running_activity_id) REFERENCES running_activities (id) ON DELETE CASCADE
               );
               CREATE INDEX IF NOT EXISTS idx_run_laps_activity ON run_laps (running_activity_id, lap_index);

               CREATE TABLE IF NOT EXISTS run_samples (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   running_activity_id INTEGER NOT NULL,
                   t_seconds REAL NOT NULL,
                   distance_km REAL,
                   heart_rate INTEGER,
                   cadence INTEGER,
                   speed_mps REAL,
                   altitude_m REAL,
                   power INTEGER,
                   lat REAL,
                   lon REAL,
                   FOREIGN KEY (running_activity_id) REFERENCES running_activities (id) ON DELETE CASCADE
               );
               CREATE INDEX IF NOT EXISTS idx_run_samples_activity ON run_samples (running_activity_id, t_seconds);
               """,
    },
    {
        "version": 29,
        "name": "gpx_segments_start_end_offsets",
        "sql": """
               ALTER TABLE gpx_segments ADD COLUMN start_seconds REAL;
               ALTER TABLE gpx_segments ADD COLUMN end_seconds REAL;
               """,
    },
]


async def run_migrations(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Step 1: Always create schema_migrations first (version 1)
        await db.executescript(MIGRATIONS[0]["sql"])
        await db.commit()

        # Step 2: Get list of already-applied versions
        cursor = await db.execute("SELECT version FROM schema_migrations")
        rows = await cursor.fetchall()
        applied_versions = {row[0] for row in rows}

        # Step 3: Loop through migrations, skip if already applied
        for migration in MIGRATIONS:
            version = migration["version"]
            if version in applied_versions:
                continue

            # Step 4: Run the migration
            print(f"Applying migration {version}: {migration['name']}")
            await db.executescript(migration["sql"])

            # Step 5: Record that we applied it
            await db.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, datetime('now'))",
                (version, migration["name"]),
            )
            await db.commit()

        # Post-migration: idempotent seed steps that need Python logic
        await _backfill_search_index(db)
        await backfill_segment_bounds(db)

        print("Migrations complete")


async def _backfill_search_index(db: aiosqlite.Connection) -> None:
    """Populate search_index from existing rows if the index is empty.

    Runs on every startup but only does work when the index contains nothing,
    which happens immediately after the FTS5 migration applies or after a
    restore that didn't carry the FTS table across.
    """
    cursor = await db.execute("SELECT COUNT(*) AS c FROM search_index")
    row = await cursor.fetchone()
    if row and row["c"] > 0:
        return

    # Tasks
    cursor = await db.execute("SELECT id, title, description FROM tasks")
    for t in await cursor.fetchall():
        body = f"{t['title']}\n{t['description'] or ''}"
        await db.execute(
            "INSERT INTO search_index (kind, entity_id, parent_id, title, body) "
            "VALUES ('task', ?, NULL, ?, ?)",
            (t["id"], t["title"], body),
        )

    # Habits
    cursor = await db.execute("SELECT id, name, description FROM habits")
    for h in await cursor.fetchall():
        body = f"{h['name']}\n{h['description'] or ''}"
        await db.execute(
            "INSERT INTO search_index (kind, entity_id, parent_id, title, body) "
            "VALUES ('habit', ?, NULL, ?, ?)",
            (h["id"], h["name"], body),
        )

    # Exercises
    cursor = await db.execute("SELECT id, name, description FROM exercises")
    for e in await cursor.fetchall():
        body = f"{e['name']}\n{e['description'] or ''}"
        await db.execute(
            "INSERT INTO search_index (kind, entity_id, parent_id, title, body) "
            "VALUES ('exercise', ?, NULL, ?, ?)",
            (e["id"], e["name"], body),
        )

    # Workout routines
    cursor = await db.execute("SELECT id, name, description FROM workout_routines")
    for r in await cursor.fetchall():
        body = f"{r['name']}\n{r['description'] or ''}"
        await db.execute(
            "INSERT INTO search_index (kind, entity_id, parent_id, title, body) "
            "VALUES ('routine', ?, NULL, ?, ?)",
            (r["id"], r["name"], body),
        )

    await db.commit()


async def backfill_segment_bounds(db: aiosqlite.Connection) -> int:
    """Recompute best-effort segments (now with start/end offsets) for runs that
    have per-second samples but segments recorded before offsets existed.

    Returns the number of runs updated. Runs without samples are left alone.
    """
    from src.services.track_segments import compute_best_segments

    cursor = await db.execute(
        """
        SELECT DISTINCT g.running_activity_id AS id
        FROM gpx_segments g
        JOIN run_samples s ON s.running_activity_id = g.running_activity_id
        WHERE g.start_seconds IS NULL
        """
    )
    activity_ids = [row["id"] for row in await cursor.fetchall()]
    for activity_id in activity_ids:
        cursor = await db.execute(
            """
            SELECT t_seconds, distance_km FROM run_samples
            WHERE running_activity_id = ? AND distance_km IS NOT NULL
            ORDER BY t_seconds ASC
            """,
            (activity_id,),
        )
        cum_dist: list[float] = []
        cum_time: list[float] = []
        for row in await cursor.fetchall():
            d = float(row["distance_km"])
            if cum_dist and d < cum_dist[-1]:
                continue
            cum_dist.append(d)
            cum_time.append(float(row["t_seconds"]))
        if len(cum_dist) < 2:
            continue
        segments = compute_best_segments(cum_dist, cum_time, cum_dist[-1])
        await db.execute("DELETE FROM gpx_segments WHERE running_activity_id = ?", (activity_id,))
        await db.executemany(
            """
            INSERT INTO gpx_segments (running_activity_id, segment_name, distance_km,
                                      duration_seconds, pace, pace_formatted,
                                      start_seconds, end_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    activity_id,
                    seg.name,
                    seg.distance_km,
                    seg.duration_seconds,
                    seg.pace,
                    seg.pace_formatted,
                    seg.start_seconds,
                    seg.end_seconds,
                )
                for seg in segments
            ],
        )
    if activity_ids:
        await db.commit()
    return len(activity_ids)
