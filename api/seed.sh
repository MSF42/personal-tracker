#!/bin/bash
# Seed data script for Personal Tracker
# Requires the API server running on localhost:8000

BASE="http://localhost:8000/api/v1"

echo "=== Creating Exercises ==="

# Back exercises
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Barbell Row","muscle_group":"back","equipment":"barbell"}' | echo "1: Barbell Row"
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Pull Up","muscle_group":"back","equipment":"pull-up bar"}' | echo "2: Pull Up"

# Chest exercises
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Bench Press","muscle_group":"chest","equipment":"barbell"}' | echo "3: Bench Press"
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Incline Dumbbell Press","muscle_group":"chest","equipment":"dumbbells"}' | echo "4: Incline DB Press"

# Biceps
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Barbell Curl","muscle_group":"biceps","equipment":"barbell"}' | echo "5: Barbell Curl"
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Hammer Curl","muscle_group":"biceps","equipment":"dumbbells"}' | echo "6: Hammer Curl"

# Triceps
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Tricep Pushdown","muscle_group":"triceps","equipment":"cable machine"}' | echo "7: Tricep Pushdown"
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Overhead Extension","muscle_group":"triceps","equipment":"dumbbell"}' | echo "8: Overhead Extension"

# Shoulders
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Overhead Press","muscle_group":"shoulders","equipment":"barbell"}' | echo "9: Overhead Press"
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Lateral Raise","muscle_group":"shoulders","equipment":"dumbbells"}' | echo "10: Lateral Raise"

# Legs
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Barbell Squat","muscle_group":"legs","equipment":"barbell"}' | echo "11: Barbell Squat"
curl -s -X POST "$BASE/exercises" -H "Content-Type: application/json" \
  -d '{"name":"Romanian Deadlift","muscle_group":"legs","equipment":"barbell"}' | echo "12: Romanian Deadlift"

echo ""
echo "=== Creating Workout Routines ==="

curl -s -X POST "$BASE/workout-routines" -H "Content-Type: application/json" \
  -d '{"name":"Upper Body Push","description":"Chest, shoulders, and triceps"}' | echo "1: Upper Body Push"
curl -s -X POST "$BASE/workout-routines" -H "Content-Type: application/json" \
  -d '{"name":"Upper Body Pull","description":"Back and biceps"}' | echo "2: Upper Body Pull"
curl -s -X POST "$BASE/workout-routines" -H "Content-Type: application/json" \
  -d '{"name":"Leg Day","description":"Quads, hamstrings, and glutes"}' | echo "3: Leg Day"
curl -s -X POST "$BASE/workout-routines" -H "Content-Type: application/json" \
  -d '{"name":"Full Body","description":"Compound movements for full body"}' | echo "4: Full Body"

echo ""
echo "=== Assigning Exercises to Routines ==="

# Upper Body Push (routine 1): Bench Press(3), Incline DB Press(4), Overhead Press(9), Lateral Raise(10), Tricep Pushdown(7)
curl -s -X POST "$BASE/workout-routines/1/exercises?exercise_id=3&sets=4&reps=8" > /dev/null
curl -s -X POST "$BASE/workout-routines/1/exercises?exercise_id=4&sets=3&reps=10" > /dev/null
curl -s -X POST "$BASE/workout-routines/1/exercises?exercise_id=9&sets=3&reps=8" > /dev/null
curl -s -X POST "$BASE/workout-routines/1/exercises?exercise_id=10&sets=3&reps=12" > /dev/null
curl -s -X POST "$BASE/workout-routines/1/exercises?exercise_id=7&sets=3&reps=12" > /dev/null
echo "Upper Body Push: 5 exercises assigned"

# Upper Body Pull (routine 2): Barbell Row(1), Pull Up(2), Barbell Curl(5), Hammer Curl(6)
curl -s -X POST "$BASE/workout-routines/2/exercises?exercise_id=1&sets=4&reps=8" > /dev/null
curl -s -X POST "$BASE/workout-routines/2/exercises?exercise_id=2&sets=3&reps=10" > /dev/null
curl -s -X POST "$BASE/workout-routines/2/exercises?exercise_id=5&sets=3&reps=10" > /dev/null
curl -s -X POST "$BASE/workout-routines/2/exercises?exercise_id=6&sets=3&reps=12" > /dev/null
echo "Upper Body Pull: 4 exercises assigned"

# Leg Day (routine 3): Squat(11), RDL(12)
curl -s -X POST "$BASE/workout-routines/3/exercises?exercise_id=11&sets=4&reps=8" > /dev/null
curl -s -X POST "$BASE/workout-routines/3/exercises?exercise_id=12&sets=3&reps=10" > /dev/null
echo "Leg Day: 2 exercises assigned"

# Full Body (routine 4): Squat(11), Bench(3), Row(1), Overhead Press(9)
curl -s -X POST "$BASE/workout-routines/4/exercises?exercise_id=11&sets=3&reps=8" > /dev/null
curl -s -X POST "$BASE/workout-routines/4/exercises?exercise_id=3&sets=3&reps=8" > /dev/null
curl -s -X POST "$BASE/workout-routines/4/exercises?exercise_id=1&sets=3&reps=8" > /dev/null
curl -s -X POST "$BASE/workout-routines/4/exercises?exercise_id=9&sets=3&reps=8" > /dev/null
echo "Full Body: 4 exercises assigned"

echo ""
echo "=== Creating Workout Logs ==="

curl -s -X POST "$BASE/workout-logs?routine_id=1&date=2026-02-10&notes=Good%20session" > /dev/null && echo "1: Upper Body Push - Feb 10"
curl -s -X POST "$BASE/workout-logs?routine_id=2&date=2026-02-12&notes=Heavy%20pulls" > /dev/null && echo "2: Upper Body Pull - Feb 12"
curl -s -X POST "$BASE/workout-logs?routine_id=3&date=2026-02-17&notes=Leg%20day%20planned" > /dev/null && echo "3: Leg Day - Feb 17"

echo ""
echo "=== Creating Running Activities ==="

curl -s -X POST "$BASE/runs" -H "Content-Type: application/json" \
  -d '{"date":"2026-01-20","duration_seconds":1800,"distance_km":5.0,"notes":"Easy run"}' > /dev/null && echo "1: Jan 20 - 5km"
curl -s -X POST "$BASE/runs" -H "Content-Type: application/json" \
  -d '{"date":"2026-01-28","duration_seconds":2400,"distance_km":7.5,"notes":"Tempo run"}' > /dev/null && echo "2: Jan 28 - 7.5km"
curl -s -X POST "$BASE/runs" -H "Content-Type: application/json" \
  -d '{"date":"2026-02-03","duration_seconds":1500,"distance_km":3.2,"notes":"Recovery jog"}' > /dev/null && echo "3: Feb 3 - 3.2km"
curl -s -X POST "$BASE/runs" -H "Content-Type: application/json" \
  -d '{"date":"2026-02-08","duration_seconds":2700,"distance_km":8.0,"notes":"Long run"}' > /dev/null && echo "4: Feb 8 - 8km"
curl -s -X POST "$BASE/runs" -H "Content-Type: application/json" \
  -d '{"date":"2026-02-11","duration_seconds":1920,"distance_km":5.5}' > /dev/null && echo "5: Feb 11 - 5.5km"
curl -s -X POST "$BASE/runs" -H "Content-Type: application/json" \
  -d '{"date":"2026-02-14","duration_seconds":2100,"distance_km":6.0,"notes":"Valentine run"}' > /dev/null && echo "6: Feb 14 - 6km"
curl -s -X POST "$BASE/runs" -H "Content-Type: application/json" \
  -d '{"date":"2026-02-16","duration_seconds":1680,"distance_km":4.5}' > /dev/null && echo "7: Feb 16 - 4.5km"
curl -s -X POST "$BASE/runs" -H "Content-Type: application/json" \
  -d '{"date":"2026-02-20","duration_seconds":3000,"distance_km":10.0,"notes":"Planned long run"}' > /dev/null && echo "8: Feb 20 - 10km"

echo ""
echo "=== Creating Tasks ==="

curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Buy groceries","category":"personal","due_date":"2026-02-14","completed":true}' > /dev/null && echo "1: Buy groceries (done)"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Update resume","category":"career","due_date":"2026-02-18"}' > /dev/null && echo "2: Update resume"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Schedule dentist appointment","category":"health","due_date":"2026-02-10"}' > /dev/null && echo "3: Dentist (overdue)"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Read 30 pages","category":"personal","due_date":"2026-02-15","repeat_type":"daily","repeat_interval":1}' > /dev/null && echo "4: Read 30 pages (daily)"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Weekly meal prep","category":"health","due_date":"2026-02-16","repeat_type":"weekly","repeat_interval":1}' > /dev/null && echo "5: Meal prep (weekly)"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Pay rent","category":"finance","due_date":"2026-03-01","repeat_type":"monthly","repeat_interval":1}' > /dev/null && echo "6: Pay rent (monthly)"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Clean apartment","category":"personal","due_date":"2026-02-15","completed":true}' > /dev/null && echo "7: Clean apartment (done)"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Review PR #42","category":"work","due_date":"2026-02-13"}' > /dev/null && echo "8: Review PR (overdue)"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Plan weekend hike","category":"personal","due_date":"2026-02-22"}' > /dev/null && echo "9: Plan hike"
curl -s -X POST "$BASE/tasks" -H "Content-Type: application/json" \
  -d '{"title":"Write blog post","category":"career"}' > /dev/null && echo "10: Write blog post (no date)"

echo ""
echo "=== Seed data complete! ==="
