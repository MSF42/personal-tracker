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
        "name": "rename_exercise_routines_to_workout_routines",
        "sql": """
               ALTER TABLE exercise_routines RENAME TO workout_routines;
               """,
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
]


async def run_migrations(db_path: str):
    async with aiosqlite.connect(db_path) as db:
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

        print("Migrations complete")
