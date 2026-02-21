# Remove Trivial Converter Functions Design

**Date:** 2026-02-21
**Status:** Approved

## Problem

Four domains have structurally identical `*InDB` and `*Response` Pydantic model pairs.
Their converter functions do nothing except pass data through:

```python
def exercise_from_db(row: ExerciseInDB) -> ExerciseResponse:
    return ExerciseResponse(**row.model_dump())  # no-op
```

This indirection adds cognitive load without providing any value.
Affected domains: Exercise, WorkoutRoutine, Measurement, MeasurementEntry.

## Chosen Approach: Remove InDB models + converters entirely

Delete all 4 `*InDB` classes and all 4 converter functions.
Repositories construct the `*Response` model directly from DB rows.

## Changes

### Model files

| File | Remove |
|------|--------|
| `api/src/models/exercise.py` | `ExerciseInDB` class, `exercise_from_db` function |
| `api/src/models/workout_routine.py` | `WorkoutRoutineInDB` class, `workout_routine_from_db` function |
| `api/src/models/measurement.py` | `MeasurementInDB` class, `measurement_from_db` function, `MeasurementEntryInDB` class, `entry_from_db` function |

### Repository files

Each repository stops constructing an intermediate InDB object and calls the
Response constructor directly from the DB row dict:

```python
# Before
exercise_in_db = ExerciseInDB(**dict(row))
return exercise_from_db(exercise_in_db)

# After
return ExerciseResponse(**dict(row))
```

List comprehensions follow the same simplification:

```python
# Before
return [exercise_from_db(ExerciseInDB(**dict(row))) for row in rows]

# After
return [ExerciseResponse(**dict(row)) for row in rows]
```

Affected repositories: `exercise_repository.py`, `workout_routine_repository.py`,
`measurement_repository.py`.

## Scope

No routes, tests, or other files reference these InDB models or converter functions.
Only the 3 model files and 3 repository files are touched.

## Alternatives Considered

**Type alias (`ExerciseInDB = ExerciseResponse`)** — Keeps two names for the same
thing. Confusing without adding value. Rejected.

**Leave as-is** — Harmless but adds cognitive load. Rejected (YAGNI).
