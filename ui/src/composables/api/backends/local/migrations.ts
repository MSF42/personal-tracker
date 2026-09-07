export const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    due_date TEXT,
    completed INTEGER NOT NULL DEFAULT 0,
    repeat_type TEXT,
    repeat_interval INTEGER,
    repeat_days TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    link_type TEXT,
    link_routine_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed);

CREATE TABLE IF NOT EXISTS running_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    distance_km REAL NOT NULL,
    notes TEXT,
    has_gpx INTEGER NOT NULL DEFAULT 0,
    title TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    import_sha256 TEXT,
    source_uuid TEXT,
    start_time TEXT,
    elapsed_seconds INTEGER,
    is_indoor INTEGER NOT NULL DEFAULT 0,
    avg_hr INTEGER,
    max_hr INTEGER,
    avg_cadence INTEGER,
    max_cadence INTEGER,
    calories INTEGER,
    total_ascent_m REAL,
    total_descent_m REAL,
    avg_power INTEGER,
    max_power INTEGER,
    avg_temperature_c REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_running_date ON running_activities(date);
CREATE INDEX IF NOT EXISTS idx_running_distance ON running_activities(distance_km);

CREATE TABLE IF NOT EXISTS gpx_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    running_activity_id INTEGER NOT NULL,
    segment_name TEXT NOT NULL,
    distance_km REAL NOT NULL,
    duration_seconds INTEGER NOT NULL,
    pace REAL NOT NULL,
    pace_formatted TEXT NOT NULL,
    FOREIGN KEY (running_activity_id) REFERENCES running_activities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_gpx_segments_activity ON gpx_segments(running_activity_id);

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
CREATE INDEX IF NOT EXISTS idx_exercise_muscle_group ON exercises(muscle_group);

CREATE TABLE IF NOT EXISTS workout_routines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routine_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    routine_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    sets INTEGER NOT NULL DEFAULT 3,
    reps INTEGER NOT NULL DEFAULT 10,
    order_index INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (routine_id) REFERENCES workout_routines(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
    UNIQUE (routine_id, exercise_id)
);

CREATE TABLE IF NOT EXISTS workout_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    routine_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (routine_id) REFERENCES workout_routines(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS set_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_log_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    reps INTEGER NOT NULL,
    weight REAL,
    FOREIGN KEY (workout_log_id) REFERENCES workout_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    unit TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS measurement_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    measurement_id INTEGER NOT NULL REFERENCES measurements(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    value REAL NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_measurement_entries_lookup
    ON measurement_entries(measurement_id, date DESC);

CREATE TABLE IF NOT EXISTS run_laps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    running_activity_id INTEGER NOT NULL REFERENCES running_activities(id) ON DELETE CASCADE,
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
    trigger TEXT
);
CREATE INDEX IF NOT EXISTS idx_run_laps_activity ON run_laps(running_activity_id, lap_index);

CREATE TABLE IF NOT EXISTS run_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    running_activity_id INTEGER NOT NULL REFERENCES running_activities(id) ON DELETE CASCADE,
    t_seconds REAL NOT NULL,
    distance_km REAL,
    heart_rate INTEGER,
    cadence INTEGER,
    speed_mps REAL,
    altitude_m REAL,
    power INTEGER,
    lat REAL,
    lon REAL
);
CREATE INDEX IF NOT EXISTS idx_run_samples_activity ON run_samples(running_activity_id, t_seconds);

CREATE TABLE IF NOT EXISTS countdowns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_countdowns_date ON countdowns(date);
`;

export const SCHEMA_VERSION = 1;

export const SEED_SQL = `
INSERT OR IGNORE INTO measurements (name, unit, sort_order, created_at, updated_at)
VALUES ('Weight', 'lbs', 0, datetime('now'), datetime('now'));
`;
