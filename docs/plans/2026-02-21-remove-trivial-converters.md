# Remove Trivial Converter Functions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Delete 4 trivial `*_from_db()` converter functions and their paired `*InDB` models, replacing repository call sites with direct `*Response(**dict(row))` construction.

**Architecture:** Pure deletion refactor — no behavior change. Each task targets one domain: edit the model file to remove the InDB class and converter function, then edit the repository to remove the now-dead imports and inline the Response constructor. Verified by ruff lint and a grep confirming no stray references remain.

**Tech Stack:** Python 3.14, Pydantic v2, aiosqlite

**Test runner:** `/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/py.test api/tests/test_utils.py -v`
**Linter:** `/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check <file>`
**Repo root:** `/Users/stevefurches/Documents/Steve/personal-tracker`

> **Note:** The existing integration tests (`test_tasks.py`, `test_running.py`) fail at startup due to a missing `data/uploads` directory — pre-existing, unrelated to this refactor. Only run `test_utils.py`.

---

### Task 1: Exercise domain

**Files:**
- Modify: `api/src/models/exercise.py`
- Modify: `api/src/repositories/exercise_repository.py`

---

**Step 1: Remove `ExerciseInDB` and `exercise_from_db` from `exercise.py`**

Delete the entire `ExerciseInDB` class (currently lines 15–23) and the `exercise_from_db` function (currently lines 53–54). The file should end after `UpdateExerciseRequest`.

Final state of `api/src/models/exercise.py`:

```python
from enum import Enum

from pydantic import BaseModel, Field


class MuscleGroup(str, Enum):
    back = "back"
    chest = "chest"
    biceps = "biceps"
    triceps = "triceps"
    shoulders = "shoulders"
    legs = "legs"


class ExerciseResponse(BaseModel):
    id: int
    name: str
    description: str | None
    muscle_group: MuscleGroup
    equipment: str | None
    instructions: str | None
    created_at: str
    updated_at: str


class CreateExerciseRequest(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    description: str | None = None
    muscle_group: MuscleGroup
    equipment: str | None = None
    instructions: str | None = None


class UpdateExerciseRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    muscle_group: MuscleGroup | None = None
    equipment: str | None = None
    instructions: str | None = None
```

**Step 2: Update `exercise_repository.py` imports**

Current import block:
```python
from src.models.exercise import (
    CreateExerciseRequest,
    ExerciseInDB,
    ExerciseResponse,
    UpdateExerciseRequest,
    exercise_from_db,
)
```

Replace with:
```python
from src.models.exercise import (
    CreateExerciseRequest,
    ExerciseResponse,
    UpdateExerciseRequest,
)
```

**Step 3: Update `find_by_id()` in `exercise_repository.py`**

Current (near line 53):
```python
        exercise_in_db = ExerciseInDB(**dict(row))
        return exercise_from_db(exercise_in_db)
```

Replace with:
```python
        return ExerciseResponse(**dict(row))
```

**Step 4: Update `find_all()` in `exercise_repository.py`**

Current (near line 61):
```python
        return [exercise_from_db(ExerciseInDB(**dict(row))) for row in rows]
```

Replace with:
```python
        return [ExerciseResponse(**dict(row)) for row in rows]
```

**Step 5: Lint both files**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/models/exercise.py \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/exercise_repository.py
```

Expected: No errors

**Step 6: Verify no stray references remain**

```bash
grep -r "ExerciseInDB\|exercise_from_db" \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/
```

Expected: No output

**Step 7: Run tests**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/py.test \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/tests/test_utils.py -v
```

Expected: 4 tests PASS

**Step 8: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/models/exercise.py api/src/repositories/exercise_repository.py && \
git commit -m "refactor: remove ExerciseInDB and exercise_from_db, use Response directly"
```

---

### Task 2: WorkoutRoutine domain

**Files:**
- Modify: `api/src/models/workout_routine.py`
- Modify: `api/src/repositories/workout_routine_repository.py`

---

**Step 1: Remove `WorkoutRoutineInDB` and `workout_routine_from_db` from `workout_routine.py`**

Delete the `WorkoutRoutineInDB` class (currently lines 4–9) and `workout_routine_from_db` function (currently lines 30–31).

Final state of `api/src/models/workout_routine.py`:

```python
from pydantic import BaseModel


class WorkoutRoutineResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: str
    updated_at: str


class CreateWorkoutRoutineRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateWorkoutRoutineRequest(BaseModel):
    name: str | None = None
    description: str | None = None
```

**Step 2: Update `workout_routine_repository.py` imports**

Current import block:
```python
from src.models.workout_routine import (
    CreateWorkoutRoutineRequest,
    UpdateWorkoutRoutineRequest,
    WorkoutRoutineInDB,
    WorkoutRoutineResponse,
    workout_routine_from_db,
)
```

Replace with:
```python
from src.models.workout_routine import (
    CreateWorkoutRoutineRequest,
    UpdateWorkoutRoutineRequest,
    WorkoutRoutineResponse,
)
```

**Step 3: Update `find_by_id()` in `workout_routine_repository.py`**

Current (near line 48):
```python
        routine_in_db = WorkoutRoutineInDB(**dict(row))
        return workout_routine_from_db(routine_in_db)
```

Replace with:
```python
        return WorkoutRoutineResponse(**dict(row))
```

**Step 4: Update `find_all()` in `workout_routine_repository.py`**

Current (near line 56):
```python
        return [workout_routine_from_db(WorkoutRoutineInDB(**dict(row))) for row in rows]
```

Replace with:
```python
        return [WorkoutRoutineResponse(**dict(row)) for row in rows]
```

**Step 5: Lint both files**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/models/workout_routine.py \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/workout_routine_repository.py
```

Expected: No errors

**Step 6: Verify no stray references remain**

```bash
grep -r "WorkoutRoutineInDB\|workout_routine_from_db" \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/
```

Expected: No output

**Step 7: Run tests**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/py.test \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/tests/test_utils.py -v
```

Expected: 4 tests PASS

**Step 8: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/models/workout_routine.py api/src/repositories/workout_routine_repository.py && \
git commit -m "refactor: remove WorkoutRoutineInDB and workout_routine_from_db, use Response directly"
```

---

### Task 3: Measurement domain (two model pairs)

**Files:**
- Modify: `api/src/models/measurement.py`
- Modify: `api/src/repositories/measurement_repository.py`

---

**Step 1: Remove all four deleted items from `measurement.py`**

Delete: `MeasurementInDB` class, `measurement_from_db` function, `MeasurementEntryInDB` class, `entry_from_db` function.

Final state of `api/src/models/measurement.py`:

```python
from pydantic import BaseModel, Field


class MeasurementResponse(BaseModel):
    id: int
    name: str
    unit: str
    sort_order: int
    created_at: str
    updated_at: str


class CreateMeasurementRequest(BaseModel):
    name: str = Field(min_length=1)
    unit: str = ""


class UpdateMeasurementRequest(BaseModel):
    name: str | None = None
    unit: str | None = None


class MeasurementEntryResponse(BaseModel):
    id: int
    measurement_id: int
    date: str
    value: float
    notes: str | None = None
    created_at: str
    updated_at: str


class CreateMeasurementEntryRequest(BaseModel):
    date: str
    value: float
    notes: str | None = None


class UpdateMeasurementEntryRequest(BaseModel):
    date: str | None = None
    value: float | None = None
    notes: str | None = None
```

**Step 2: Update `measurement_repository.py` imports**

Current import block:
```python
from src.models.measurement import (
    CreateMeasurementEntryRequest,
    CreateMeasurementRequest,
    MeasurementEntryInDB,
    MeasurementEntryResponse,
    MeasurementInDB,
    MeasurementResponse,
    UpdateMeasurementEntryRequest,
    UpdateMeasurementRequest,
    entry_from_db,
    measurement_from_db,
)
```

Replace with:
```python
from src.models.measurement import (
    CreateMeasurementEntryRequest,
    CreateMeasurementRequest,
    MeasurementEntryResponse,
    MeasurementResponse,
    UpdateMeasurementEntryRequest,
    UpdateMeasurementRequest,
)
```

**Step 3: Update `find_measurement_by_id()` in `measurement_repository.py`**

Current (near line 50):
```python
        return measurement_from_db(MeasurementInDB(**dict(row)))
```

Replace with:
```python
        return MeasurementResponse(**dict(row))
```

**Step 4: Update `find_all_measurements()` in `measurement_repository.py`**

Current (near line 55):
```python
        return [measurement_from_db(MeasurementInDB(**dict(row))) for row in rows]
```

Replace with:
```python
        return [MeasurementResponse(**dict(row)) for row in rows]
```

**Step 5: Update `find_entry_by_id()` in `measurement_repository.py`**

Current (near line 113):
```python
        return entry_from_db(MeasurementEntryInDB(**dict(row)))
```

Replace with:
```python
        return MeasurementEntryResponse(**dict(row))
```

**Step 6: Update `find_entries()` in `measurement_repository.py`**

Current (near line 121):
```python
        return [entry_from_db(MeasurementEntryInDB(**dict(row))) for row in rows]
```

Replace with:
```python
        return [MeasurementEntryResponse(**dict(row)) for row in rows]
```

**Step 7: Lint both files**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/models/measurement.py \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/measurement_repository.py
```

Expected: No errors

**Step 8: Verify no stray references remain**

```bash
grep -r "MeasurementInDB\|MeasurementEntryInDB\|measurement_from_db\|entry_from_db" \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/
```

Expected: No output

**Step 9: Run tests**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/py.test \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/tests/test_utils.py -v
```

Expected: 4 tests PASS

**Step 10: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/models/measurement.py api/src/repositories/measurement_repository.py && \
git commit -m "refactor: remove MeasurementInDB, MeasurementEntryInDB, and trivial converters"
```

---

## Done

After all 3 tasks: 4 InDB classes and 4 converter functions deleted. Repositories construct Response models directly from DB rows — same behavior, half the indirection.
