import shutil
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from aiosqlite import Connection

from src.config.settings import get_settings


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def _days_from_now(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


today = date.today().isoformat()
now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


async def seed_sample_data(db: Connection) -> None:
    # Disable FK checks for the duration of the seed — we insert in correct
    # parent-before-child order, so there are no real violations.  The check
    # must be disabled before any DML begins (it cannot be changed mid-tx).
    await db.execute("PRAGMA foreign_keys = OFF")

    settings = get_settings()
    uploads_path = Path(settings.uploads_path)
    uploads_path.mkdir(parents=True, exist_ok=True)

    # ── Profile picture ───────────────────────────────────────────────────────
    steve_pic = Path.home() / "Pictures" / "steve.png"
    profile_pic_url = None
    if steve_pic.exists():
        filename = f"{uuid.uuid4()}.png"
        shutil.copy2(steve_pic, uploads_path / filename)
        profile_pic_url = f"/uploads/{filename}"

    # ── Settings ──────────────────────────────────────────────────────────────
    await db.execute(
        "INSERT INTO user_settings (key, value) VALUES ('user_name', 'Steve') "
        "ON CONFLICT(key) DO UPDATE SET value = 'Steve'"
    )
    if profile_pic_url:
        await db.execute(
            "INSERT INTO user_settings (key, value) VALUES ('profile_picture', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = ?",
            (profile_pic_url, profile_pic_url),
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────
    tasks = [
        ("Buy groceries", None, "Errands", _days_from_now(1), 0, None, None, None, "low"),
        ("Complete quarterly report", "Q1 numbers due EOD", "Work", _days_ago(1), 0, None, None, None, "high"),
        ("Call dentist", "Schedule 6-month cleaning", "Health", None, 0, None, None, None, "medium"),
        ("Read 'Atomic Habits'", None, "Personal", _days_ago(5), 1, None, None, None, "low"),
        ("Fix leaky faucet", None, "Home", today, 0, None, None, None, "high"),
        ("Plan team offsite", "Book venue, catering, agenda", "Work", _days_from_now(14), 0, None, None, None, "medium"),
        ("Organize garage", None, "Home", None, 0, None, None, None, "low"),
        ("Review pull requests", None, "Work", today, 0, "daily", 1, "1,2,3,4,5", "medium"),
        ("Take vitamins", None, "Health", None, 1, "daily", 1, None, "low"),
        ("Weekly review", "Review goals and plan next week", "Personal", _days_from_now(3), 0, "weekly", 1, "6", "medium"),
    ]
    for t in tasks:
        await db.execute(
            """INSERT INTO tasks
               (title, description, category, due_date, completed,
                repeat_type, repeat_interval, repeat_days, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*t, now_iso, now_iso),
        )

    # ── Habits ────────────────────────────────────────────────────────────────
    habits_data = [
        ("Morning Run", "Start the day strong", "daily", None, "#ef4444"),
        ("Meditate", "10 minutes of mindfulness", "daily", None, "#8b5cf6"),
        ("Read 30 min", None, "daily", None, "#f59e0b"),
        ("Drink 8 glasses", "Stay hydrated", "daily", None, "#06b6d4"),
        ("No sugar", None, "weekdays", "1,2,3,4,5", "#22c55e"),
    ]
    habit_ids = []
    for h in habits_data:
        cursor = await db.execute(
            """INSERT INTO habits (name, description, frequency, frequency_days, color, archived, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
            (*h, now_iso, now_iso),
        )
        habit_ids.append(cursor.lastrowid)

    # Completion patterns (days ago → completed): realistic streaks
    # Morning Run: 14-day streak
    run_days = set(range(0, 14))
    # Meditate: 5-day streak, missed 2, then 10 before that
    meditate_days = set(range(0, 5)) | set(range(7, 17))
    # Read: 21-day streak
    read_days = set(range(0, 21))
    # Drink water: most days (24/28)
    water_days = set(range(0, 28)) - {4, 9, 16, 22}
    # No sugar: weekdays only in last 28 days
    no_sugar_days = {
        i for i in range(0, 28) if (date.today() - timedelta(days=i)).weekday() < 5
    }

    completion_patterns = [run_days, meditate_days, read_days, water_days, no_sugar_days]
    for habit_id, days_set in zip(habit_ids, completion_patterns):
        for days_ago in days_set:
            d = _days_ago(days_ago)
            await db.execute(
                "INSERT OR IGNORE INTO habit_completions (habit_id, date, created_at) VALUES (?, ?, ?)",
                (habit_id, d, now_iso),
            )

    # ── Exercises ─────────────────────────────────────────────────────────────
    exercises_data = [
        ("Bench Press", "Horizontal push", "chest", "Barbell", None),
        ("Squat", "King of leg exercises", "legs", "Barbell", None),
        ("Deadlift", "Full-body pull", "back", "Barbell", None),
        ("Overhead Press", "Vertical push", "shoulders", "Barbell", None),
        ("Pull-Up", "Bodyweight vertical pull", "back", "Pull-up bar", None),
        ("Bicep Curl", None, "biceps", "Dumbbell", None),
        ("Tricep Dip", None, "triceps", "Parallel bars", None),
        ("Romanian Deadlift", "Hamstring-focused hinge", "legs", "Barbell", None),
        ("Lateral Raise", None, "shoulders", "Dumbbell", None),
        ("Row", "Horizontal pull", "back", "Barbell", None),
    ]
    exercise_ids = []
    for e in exercises_data:
        cursor = await db.execute(
            """INSERT OR IGNORE INTO exercises (name, description, muscle_group, equipment, instructions, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (*e, now_iso, now_iso),
        )
        if cursor.lastrowid:
            exercise_ids.append(cursor.lastrowid)
        else:
            # Already exists — fetch its id
            c2 = await db.execute("SELECT id FROM exercises WHERE name = ?", (e[0],))
            row = await c2.fetchone()
            if row:
                exercise_ids.append(row[0])

    # Map by name for easy reference
    ex = {name: eid for name, eid in zip([e[0] for e in exercises_data], exercise_ids)}

    # ── Workout Routines ──────────────────────────────────────────────────────
    routines_data = [
        ("Push Day", "Chest, shoulders, triceps"),
        ("Pull Day", "Back and biceps"),
        ("Leg Day", "Quads, hamstrings, glutes"),
    ]
    routine_ids = []
    for r in routines_data:
        cursor = await db.execute(
            "INSERT INTO workout_routines (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (*r, now_iso, now_iso),
        )
        routine_ids.append(cursor.lastrowid)

    push_id, pull_id, leg_id = routine_ids

    # Routine exercises
    routine_exercises = [
        (push_id, ex["Bench Press"], 4, 8, 0),
        (push_id, ex["Overhead Press"], 3, 10, 1),
        (push_id, ex["Tricep Dip"], 3, 12, 2),
        (pull_id, ex["Deadlift"], 4, 5, 0),
        (pull_id, ex["Pull-Up"], 3, 8, 1),
        (pull_id, ex["Row"], 3, 10, 2),
        (pull_id, ex["Bicep Curl"], 3, 12, 3),
        (leg_id, ex["Squat"], 4, 8, 0),
        (leg_id, ex["Romanian Deadlift"], 3, 10, 1),
        (leg_id, ex["Lateral Raise"], 3, 15, 2),
    ]
    for re in routine_exercises:
        await db.execute(
            "INSERT OR IGNORE INTO routine_exercises (routine_id, exercise_id, sets, reps, order_index) VALUES (?, ?, ?, ?, ?)",
            re,
        )

    # ── Workout Logs ──────────────────────────────────────────────────────────
    logs_data = [
        (push_id, _days_ago(14), "Felt strong today"),
        (pull_id, _days_ago(12), None),
        (leg_id, _days_ago(10), "Legs were sore from the run"),
        (push_id, _days_ago(7), None),
        (pull_id, _days_ago(5), "Good session"),
        (leg_id, _days_ago(3), None),
        (push_id, _days_ago(1), "New bench PR: 90kg"),
    ]
    for log in logs_data:
        cursor = await db.execute(
            "INSERT INTO workout_logs (routine_id, date, notes, created_at) VALUES (?, ?, ?, ?)",
            (*log, now_iso),
        )
        log_id = cursor.lastrowid
        routine_id = log[0]

        # Add sets for each log based on its routine
        if routine_id == push_id:
            sets = [
                (ex["Bench Press"], 1, 8, 85.0),
                (ex["Bench Press"], 2, 8, 87.5),
                (ex["Bench Press"], 3, 6, 90.0),
                (ex["Overhead Press"], 1, 10, 55.0),
                (ex["Overhead Press"], 2, 10, 57.5),
                (ex["Tricep Dip"], 1, 12, None),
                (ex["Tricep Dip"], 2, 10, None),
            ]
        elif routine_id == pull_id:
            sets = [
                (ex["Deadlift"], 1, 5, 120.0),
                (ex["Deadlift"], 2, 5, 125.0),
                (ex["Deadlift"], 3, 4, 130.0),
                (ex["Pull-Up"], 1, 8, None),
                (ex["Pull-Up"], 2, 7, None),
                (ex["Row"], 1, 10, 70.0),
                (ex["Row"], 2, 10, 72.5),
                (ex["Bicep Curl"], 1, 12, 15.0),
                (ex["Bicep Curl"], 2, 12, 15.0),
            ]
        else:  # leg
            sets = [
                (ex["Squat"], 1, 8, 100.0),
                (ex["Squat"], 2, 8, 102.5),
                (ex["Squat"], 3, 6, 105.0),
                (ex["Romanian Deadlift"], 1, 10, 80.0),
                (ex["Romanian Deadlift"], 2, 10, 82.5),
                (ex["Lateral Raise"], 1, 15, 10.0),
            ]

        for exercise_id, set_num, reps, weight in sets:
            await db.execute(
                "INSERT INTO set_logs (workout_log_id, exercise_id, set_number, reps, weight) VALUES (?, ?, ?, ?, ?)",
                (log_id, exercise_id, set_num, reps, weight),
            )

    # ── Running Activities ────────────────────────────────────────────────────
    runs = [
        (_days_ago(25), 1980, 5.02, "Easy morning jog", "Easy 5k"),
        (_days_ago(22), 2340, 6.15, None, "Morning run"),
        (_days_ago(19), 1800, 5.0, "Felt tired", "5k"),
        (_days_ago(16), 3120, 8.3, "Long run Sunday", "Long run"),
        (_days_ago(13), 2160, 5.8, None, "Tempo run"),
        (_days_ago(10), 2520, 7.1, "Windy today", "7k"),
        (_days_ago(7), 3600, 10.05, "First 10k in a while!", "10k milestone"),
        (_days_ago(4), 1920, 5.0, None, "5k recovery"),
        (_days_ago(2), 2280, 6.4, "Felt great", "6k morning"),
        (today, 1740, 4.8, "Short but fast", "Speed session"),
    ]
    for r in runs:
        await db.execute(
            """INSERT INTO running_activities (date, duration_seconds, distance_km, notes, title, has_gpx, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
            (*r, now_iso, now_iso),
        )

    # ── Notes ─────────────────────────────────────────────────────────────────
    async def insert_note(parent_id, content, sort_order=0):
        cursor = await db.execute(
            "INSERT INTO notes (parent_id, content, sort_order, collapsed, created_at, updated_at) VALUES (?, ?, ?, 0, ?, ?)",
            (parent_id, content, sort_order, now_iso, now_iso),
        )
        return cursor.lastrowid

    # ── Fitness ──
    fitness = await insert_note(None, "Fitness", 0)

    running_node = await insert_note(fitness, "Running", 0)
    await insert_note(running_node, "Goal: 10k under 50 min by June", 0)
    await insert_note(running_node, "Weekly target: 40km", 1)
    races = await insert_note(running_node, "Race calendar", 2)
    await insert_note(races, "10k — June 2026", 0)
    await insert_note(races, "Half marathon — October 2026", 1)

    strength_node = await insert_note(fitness, "Strength", 1)
    await insert_note(strength_node, "Bench PR: 90kg × 3 (Mar 2026)", 0)
    await insert_note(strength_node, "Squat target: 120kg by end of Q2", 1)
    await insert_note(strength_node, "Current program: 5/3/1", 2)

    # ── 2026 Goals ──
    goals = await insert_note(None, "2026 Goals", 1)

    fitness_goals = await insert_note(goals, "Fitness", 0)
    await insert_note(fitness_goals, "Run 500km total", 0)
    await insert_note(fitness_goals, "Meditate every day for 90 days straight", 1)

    personal_goals = await insert_note(goals, "Personal", 1)
    await insert_note(personal_goals, "Read 24 books", 0)
    book_list = await insert_note(personal_goals, "Book list", 1)
    await insert_note(book_list, "Atomic Habits — James Clear ✓", 0)
    await insert_note(book_list, "Deep Work — Cal Newport", 1)
    await insert_note(book_list, "The Pragmatic Programmer", 2)

    work_goals = await insert_note(goals, "Work", 2)
    await insert_note(work_goals, "Launch side project", 0)
    await insert_note(work_goals, "Complete cloud certification", 1)

    # ── Ideas ──
    ideas = await insert_note(None, "Ideas", 2)

    app_ideas = await insert_note(ideas, "Apps", 0)
    await insert_note(app_ideas, "Habit tracker with social accountability", 0)
    await insert_note(app_ideas, "Workout logger with AI coaching feedback", 1)

    writing_ideas = await insert_note(ideas, "Writing", 1)
    await insert_note(writing_ideas, "Blog: lessons from 6 months of consistent exercise", 0)
    await insert_note(writing_ideas, "Newsletter: weekly fitness + productivity roundup", 1)

    # ── Recipes ──
    recipes = await insert_note(None, "Recipes", 3)

    breakfast = await insert_note(recipes, "Breakfast", 0)
    await insert_note(breakfast, "High-protein overnight oats: oats + greek yogurt + protein powder + berries", 0)
    await insert_note(breakfast, "Green smoothie: spinach + banana + almond milk + chia seeds", 1)

    post_workout = await insert_note(recipes, "Post-workout", 1)
    await insert_note(post_workout, "Shake: banana + spinach + protein powder + almond milk", 0)
    await insert_note(post_workout, "Rice bowl: 200g rice + 180g chicken + roasted veg", 1)

    # ── Measurements ─────────────────────────────────────────────────────────
    # Update the default Weight measurement (already inserted by migration 19, unit 'lbs')
    # Add body fat and update weight unit to kg
    await db.execute("UPDATE measurements SET unit = 'kg' WHERE name = 'Weight'")
    weight_cursor = await db.execute("SELECT id FROM measurements WHERE name = 'Weight'")
    weight_row = await weight_cursor.fetchone()
    weight_id = weight_row[0] if weight_row else None

    bf_cursor = await db.execute(
        "INSERT OR IGNORE INTO measurements (name, unit, sort_order, created_at, updated_at) VALUES ('Body Fat', '%', 1, ?, ?)",
        (now_iso, now_iso),
    )
    bf_id = bf_cursor.lastrowid
    if not bf_id:
        c = await db.execute("SELECT id FROM measurements WHERE name = 'Body Fat'")
        row = await c.fetchone()
        bf_id = row[0] if row else None

    # Weight entries: gradual downward trend over 6 months
    weight_entries = [
        (_days_ago(180), 84.5), (_days_ago(165), 84.0), (_days_ago(150), 83.2),
        (_days_ago(135), 82.8), (_days_ago(120), 82.0), (_days_ago(105), 81.5),
        (_days_ago(90), 81.0),  (_days_ago(75), 80.3),  (_days_ago(60), 79.8),
        (_days_ago(45), 79.2),  (_days_ago(30), 78.9),  (_days_ago(15), 78.4),
        (today, 78.1),
    ]
    if weight_id:
        for d, v in weight_entries:
            await db.execute(
                "INSERT OR IGNORE INTO measurement_entries (measurement_id, date, value, notes, created_at, updated_at) VALUES (?, ?, ?, NULL, ?, ?)",
                (weight_id, d, v, now_iso, now_iso),
            )

    bf_entries = [
        (_days_ago(180), 22.1), (_days_ago(150), 21.5), (_days_ago(120), 20.8),
        (_days_ago(90), 20.1),  (_days_ago(60), 19.4),  (_days_ago(30), 18.9),
        (today, 18.3),
    ]
    if bf_id:
        for d, v in bf_entries:
            await db.execute(
                "INSERT OR IGNORE INTO measurement_entries (measurement_id, date, value, notes, created_at, updated_at) VALUES (?, ?, ?, NULL, ?, ?)",
                (bf_id, d, v, now_iso, now_iso),
            )

    await db.commit()
    await db.execute("PRAGMA foreign_keys = ON")
