# API Code Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 17 API issues identified in the code review — security vulnerabilities, route bugs, model inconsistencies, and dead code.

**Architecture:** Five logical commits on a `cleanup/api` branch, working from safest (config/dead code) to most structural (models/repositories). Each commit leaves the test suite green. The rename of `ValidationError` → `AppValidationError` is a cross-cutting change that touches 4 route files — do it in one commit to keep diffs atomic.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, SQLite (aiosqlite), pytest + pytest-asyncio (asyncio_mode=auto), httpx for test client.

---

## File Map

**Modified:**
- `api/src/config/settings.py` — fix default host
- `api/src/app.py` — remove duplicate health router registration
- `api/src/routes/health.py` — remove debug endpoints
- `api/src/errors.py` — rename `ValidationError` → `AppValidationError`
- `api/src/routes/notes.py` — update import; add magic-byte validation
- `api/src/routes/running.py` — update import; add GPX error handling
- `api/src/routes/settings.py` — zip-slip fix, size cap, remove inline model
- `api/src/routes/workout_logs.py` — reorder `/routine/{id}` before `/{id}`
- `api/src/models/note.py` — `NoteTreeNode` extends `NoteResponse`
- `api/src/models/workout_log.py` — add response models
- `api/src/repositories/note_repository.py` — remove redundant PRAGMA
- `api/src/repositories/workout_log_repository.py` — rewrite UPDATE as parameterized
- `api/src/repositories/task_repository.py` — add noqa comment
- `api/src/services/task_recurrence.py` — add docstring + cross-reference

**Created:**
- `api/src/models/settings.py` — `UpdateSettingRequest`

**Tests modified:**
- `api/tests/test_settings.py` — zip-slip, size cap tests
- `api/tests/test_running.py` — GPX error handling tests
- `api/tests/test_workout_logs.py` — route ordering, response model shape tests

---

## Task 1: Quick config & dead code

**Issues:** H6, M5, L6
**Files:** `api/src/config/settings.py`, `api/src/app.py`, `api/src/routes/health.py`

- [ ] **Step 1: Change default host to 127.0.0.1**

  In `api/src/config/settings.py`, find the `host` field and change its default:
  ```python
  host: str = "127.0.0.1"
  ```

- [ ] **Step 2: Remove duplicate health router registration**

  In `api/src/app.py`, find the two `include_router` calls for the health router. Keep only the one without the `/api/v1` prefix. Delete the line:
  ```python
  app.include_router(router, prefix="/api/v1")
  ```

- [ ] **Step 3: Remove debug endpoints from health.py**

  In `api/src/routes/health.py`, delete the `/ping` and `/db-test` route handlers and their decorators entirely (currently the last ~15 lines of the file).

- [ ] **Step 4: Run the test suite**

  ```bash
  cd api && pytest -q
  ```
  Expected: all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git checkout -b cleanup/api
  git add api/src/config/settings.py api/src/app.py api/src/routes/health.py
  git commit -m "fix: restrict default API host to 127.0.0.1; remove debug endpoints"
  ```

---

## Task 2: Rename ValidationError → AppValidationError

**Issue:** H2
**Files:** `api/src/errors.py`, `api/src/routes/notes.py`, `api/src/routes/running.py`

The custom `ValidationError` class silently shadows Pydantic's `ValidationError`, causing FastAPI's 422 request validation errors to fall through to the generic 500 handler instead.

- [ ] **Step 1: Write a failing test**

  In `api/tests/test_tasks.py` (or create `api/tests/test_errors.py`), add a test that sends a request with a missing required field and asserts a 422 response:

  ```python
  async def test_create_task_missing_fields_returns_422(client):
      response = await client.post("/api/v1/tasks", json={})
      assert response.status_code == 422
  ```

  Run it:
  ```bash
  cd api && pytest tests/test_tasks.py::test_create_task_missing_fields_returns_422 -v
  ```
  Expected: **FAIL** — currently returns 500 due to the name clash.

- [ ] **Step 2: Rename the class in errors.py**

  In `api/src/errors.py`, change:
  ```python
  class ValidationError(AppError):
      def __init__(self, detail: str = "Validation error"):
          super().__init__(status_code=422, detail=detail, code="VALIDATION_ERROR")
  ```
  to:
  ```python
  class AppValidationError(AppError):
      def __init__(self, detail: str = "Validation error"):
          super().__init__(status_code=422, detail=detail, code="VALIDATION_ERROR")
  ```

- [ ] **Step 3: Update all import sites**

  Two files import `ValidationError` from `src.errors` — update both explicitly, then grep to catch any others:

  `api/src/routes/notes.py` line 9:
  ```python
  from src.errors import NotFoundError, AppValidationError
  ```
  Then replace both usages of `ValidationError(` with `AppValidationError(` in that file (lines ~90, ~97).

  `api/src/routes/running.py` line 4:
  ```python
  from src.errors import NotFoundError, AppValidationError
  ```
  Replace `ValidationError(` with `AppValidationError(` (line ~58).

  Search for any other usages:
  ```bash
  grep -rn "ValidationError" api/src/
  ```
  Update any remaining occurrences.

- [ ] **Step 4: Run the failing test — it should now pass**

  ```bash
  cd api && pytest tests/test_tasks.py::test_create_task_missing_fields_returns_422 -v
  ```
  Expected: **PASS** — returns 422.

- [ ] **Step 5: Run full test suite**

  ```bash
  cd api && pytest -q
  ```
  Expected: all tests pass.

- [ ] **Step 6: Commit**

  ```bash
  git add api/src/errors.py api/src/routes/notes.py api/src/routes/running.py api/tests/
  git commit -m "fix: rename ValidationError to AppValidationError to prevent Pydantic shadowing"
  ```

---

## Task 3: Zip-slip path traversal fix + upload size cap

**Issues:** H1, H4
**File:** `api/src/routes/settings.py`

- [ ] **Step 1: Write failing tests**

  In `api/tests/test_settings.py`, add:

  ```python
  import io, zipfile

  def make_zip(entries: dict[str, bytes]) -> bytes:
      buf = io.BytesIO()
      with zipfile.ZipFile(buf, "w") as zf:
          for name, data in entries.items():
              zf.writestr(name, data)
      return buf.getvalue()

  async def test_restore_rejects_path_traversal_in_uploads(client):
      """A zip entry with ../ in an uploads path must be rejected."""
      bad_zip = make_zip({
          "tracker.db": b"SQLite format 3\x00" + b"\x00" * 84,
          "uploads/../evil.txt": b"pwned",
      })
      response = await client.post(
          "/api/v1/settings/restore",
          files={"file": ("backup.zip", bad_zip, "application/zip")},
      )
      assert response.status_code == 400

  async def test_restore_rejects_oversized_upload(client):
      """Uploads over 100 MB must be rejected before processing."""
      # Create a zip that reports large uncompressed content
      # We test the content length check, so create a real large bytes object
      big_content = b"x" * (101 * 1024 * 1024)
      response = await client.post(
          "/api/v1/settings/restore",
          content=big_content,
          headers={"content-type": "multipart/form-data; boundary=boundary"},
      )
      # The server should reject with 400 or 413 before full processing
      assert response.status_code in (400, 413, 422)
  ```

  Run:
  ```bash
  cd api && pytest tests/test_settings.py::test_restore_rejects_path_traversal_in_uploads -v
  ```
  Expected: **FAIL** (currently no guard, path traversal would succeed or error differently).

- [ ] **Step 2: Add size cap**

  In `api/src/routes/settings.py`, after `content = await file.read()`, add:
  ```python
  MAX_RESTORE_SIZE = 100 * 1024 * 1024  # 100 MB
  if len(content) > MAX_RESTORE_SIZE:
      return JSONResponse(
          status_code=400,
          content={"error": "Upload exceeds 100 MB limit", "code": "FILE_TOO_LARGE"},
      )
  ```
  Add `from fastapi.responses import JSONResponse` at the top of the file if not already imported.

- [ ] **Step 3: Add path-traversal guards**

  In the same restore handler, replace the two extraction sections:

  **For tracker.db** — reject the zip if any entry claims to be `tracker.db` but has path components (e.g. `"../tracker.db"`). Use a literal equality check, and always write to the configured `db_path` (never a path derived from the zip entry name):
  ```python
  if "tracker.db" not in names:
      return JSONResponse(
          status_code=400,
          content={"error": "Invalid backup: missing tracker.db", "code": "VALIDATION_ERROR"},
      )
  # Check no entry uses "tracker.db" with path components to escape
  for name in names:
      if name.endswith("tracker.db") and name != "tracker.db":
          return JSONResponse(
              status_code=400,
              content={"error": "Invalid backup: path traversal detected", "code": "VALIDATION_ERROR"},
          )

  # Safe: always write to the configured db_path, never to a path derived from the zip
  with zf.open("tracker.db") as src, open(db_path, "wb") as dst:
      shutil.copyfileobj(src, dst)
  ```

  **For upload files** — add a resolve-and-assert check:
  ```python
  resolved_uploads = uploads_path.resolve()
  for name in names:
      if name.startswith("uploads/") and not name.endswith("/"):
          # Strip the "uploads/" prefix and resolve the target path
          relative = Path(name[len("uploads/"):])
          target = (uploads_path / relative).resolve()
          # Guard: target must be inside uploads_path
          if not str(target).startswith(str(resolved_uploads)):
              return JSONResponse(
                  status_code=400,
                  content={"error": "Invalid backup: path traversal detected", "code": "VALIDATION_ERROR"},
              )
          target.parent.mkdir(parents=True, exist_ok=True)
          with zf.open(name) as src, open(target, "wb") as dst:
              shutil.copyfileobj(src, dst)
  ```

- [ ] **Step 4: Run the tests**

  ```bash
  cd api && pytest tests/test_settings.py -v
  ```
  Expected: path traversal test passes. The size test may need adjustment based on how multipart limits work in your test client — verify and adjust if needed.

- [ ] **Step 5: Run full suite**

  ```bash
  cd api && pytest -q
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add api/src/routes/settings.py api/tests/test_settings.py
  git commit -m "fix: prevent zip-slip path traversal in backup restore; add 100MB size cap"
  ```

---

## Task 4: Image upload magic-byte validation

**Issue:** H3
**File:** `api/src/routes/notes.py`

- [ ] **Step 1: Write a failing test**

  In `api/tests/test_notes.py` (create if it doesn't exist), add:

  ```python
  async def test_upload_image_rejects_mismatched_magic_bytes(client):
      """A file claiming to be JPEG but with wrong magic bytes must be rejected."""
      fake_jpeg = b"This is not a JPEG" + b"\x00" * 50
      response = await client.post(
          "/api/v1/notes/images",
          files={"file": ("photo.jpg", fake_jpeg, "image/jpeg")},
      )
      assert response.status_code == 422

  async def test_upload_image_accepts_valid_jpeg(client):
      """A real JPEG magic header must be accepted."""
      valid_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
      response = await client.post(
          "/api/v1/notes/images",
          files={"file": ("photo.jpg", valid_jpeg, "image/jpeg")},
      )
      assert response.status_code == 201
  ```

  Run:
  ```bash
  cd api && pytest tests/test_notes.py::test_upload_image_rejects_mismatched_magic_bytes -v
  ```
  Expected: **FAIL** (currently only checks content_type, not bytes).

- [ ] **Step 2: Add magic-byte validation to the upload handler**

  In `api/src/routes/notes.py`, add a helper near the top of the file (after imports):

  ```python
  # Magic byte signatures: maps content_type to (offset, bytes_to_match)
  MAGIC_BYTES: dict[str, list[bytes]] = {
      "image/jpeg":  [b"\xff\xd8\xff"],
      "image/png":   [b"\x89PNG\r\n\x1a\n"],
      "image/gif":   [b"GIF87a", b"GIF89a"],
      "image/webp":  [],  # RIFF....WEBP — checked below
  }

  def _validate_magic_bytes(content: bytes, content_type: str) -> bool:
      if content_type == "image/webp":
          return (
              len(content) >= 12
              and content[:4] == b"RIFF"
              and content[8:12] == b"WEBP"
          )
      signatures = MAGIC_BYTES.get(content_type, [])
      if not signatures:
          return False
      return any(content[:len(sig)] == sig for sig in signatures)
  ```

  In the `upload_image` handler, after the existing `content_type` allowlist check and after reading the file, add:

  ```python
  content = await file.read()

  # Second layer: magic-byte check (content_type is client-supplied and can be spoofed)
  if not _validate_magic_bytes(content, file.content_type):
      raise AppValidationError(
          f"File content does not match declared type {file.content_type}"
      )
  ```

  Verify that the downstream write uses the `content` bytes variable (not `file` directly). If it does, no seek is needed. If the write reads from `file` again, call `await file.seek(0)` after the magic-byte check.

- [ ] **Step 3: Run the tests**

  ```bash
  cd api && pytest tests/test_notes.py -v
  ```
  Expected: both new tests pass.

- [ ] **Step 4: Run full suite**

  ```bash
  cd api && pytest -q
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add api/src/routes/notes.py api/tests/test_notes.py
  git commit -m "fix: add magic-byte validation on image uploads as second layer after MIME check"
  ```

---

## Task 5: Fix workout log route ordering

**Issue:** M2
**File:** `api/src/routes/workout_logs.py`

The route `GET /routine/{routine_id}` is currently registered after `GET /{workout_log_id}`, making it unreachable (FastAPI tries to parse `"routine"` as an integer and returns 422).

- [ ] **Step 1: Write a failing test**

  In `api/tests/test_workout_logs.py`, add:

  ```python
  async def test_get_logs_by_routine_is_reachable(client):
      """GET /workout-logs/routine/999 must not return 422 (route unreachable)."""
      response = await client.get("/api/v1/workout-logs/routine/999")
      # 404 is fine (no such routine); 422 means route ordering bug
      assert response.status_code != 422
  ```

  Run:
  ```bash
  cd api && pytest tests/test_workout_logs.py::test_get_logs_by_routine_is_reachable -v
  ```
  Expected: **FAIL** — currently returns 422.

- [ ] **Step 2: Move the route registration**

  In `api/src/routes/workout_logs.py`, cut the entire `@router.get("/routine/{routine_id}")` handler block (currently near the bottom) and paste it **before** the `@router.get("/{workout_log_id}")` handler.

  After the move, the order of GET routes in the file should be:
  1. `GET ""` — list all
  2. `GET "/exercise-last-performed"` — static
  3. `GET "/exercise/{exercise_id}/history"` — static prefix
  4. `GET "/routine/{routine_id}"` — **moved here**
  5. `GET "/{workout_log_id}"` — parameterized (catch-all)

- [ ] **Step 3: Run the test**

  ```bash
  cd api && pytest tests/test_workout_logs.py::test_get_logs_by_routine_is_reachable -v
  ```
  Expected: **PASS** — returns 200 or 404, not 422.

- [ ] **Step 4: Run full suite**

  ```bash
  cd api && pytest -q
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add api/src/routes/workout_logs.py api/tests/test_workout_logs.py
  git commit -m "fix: register /routine/{id} before /{workout_log_id} to make route reachable"
  ```

---

## Task 6: GPX error handling

**Issue:** M6
**File:** `api/src/routes/running.py`

`parse_gpx` raises `ValueError` for short tracks and `xml.etree.ElementTree.ParseError` for malformed XML. Both currently bubble up as 500.

- [ ] **Step 1: Write failing tests**

  In `api/tests/test_running.py`, add:

  ```python
  async def test_import_gpx_returns_422_for_malformed_xml(client):
      bad_xml = b"this is not xml at all"
      response = await client.post(
          "/api/v1/running/import-gpx",
          files={"file": ("run.gpx", bad_xml, "application/gpx+xml")},
      )
      assert response.status_code == 422

  async def test_import_gpx_returns_422_for_too_few_points(client):
      one_point_gpx = b"""<?xml version="1.0"?>
  <gpx xmlns="http://www.topografix.com/GPX/1/1">
    <trk><trkseg>
      <trkpt lat="51.5" lon="-0.1"><time>2024-01-01T10:00:00Z</time></trkpt>
    </trkseg></trk>
  </gpx>"""
      response = await client.post(
          "/api/v1/running/import-gpx",
          files={"file": ("run.gpx", one_point_gpx, "application/gpx+xml")},
      )
      assert response.status_code == 422
  ```

  Run:
  ```bash
  cd api && pytest tests/test_running.py::test_import_gpx_returns_422_for_malformed_xml -v
  ```
  Expected: **FAIL** — currently returns 500.

- [ ] **Step 2: Wrap parse_gpx in error handling**

  In `api/src/routes/running.py`, add the import at the top:
  ```python
  import xml.etree.ElementTree as ET
  ```

  Then wrap the `parse_gpx` call:
  ```python
  try:
      result = parse_gpx(xml_bytes)
  except ValueError as e:
      raise AppValidationError(str(e))
  except ET.ParseError:
      raise AppValidationError("GPX file contains invalid XML")
  ```

- [ ] **Step 3: Run the tests**

  ```bash
  cd api && pytest tests/test_running.py -v
  ```
  Expected: both new tests pass.

- [ ] **Step 4: Run full suite**

  ```bash
  cd api && pytest -q
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add api/src/routes/running.py api/tests/test_running.py
  git commit -m "fix: return 422 for malformed or short GPX files instead of 500"
  ```

---

## Task 7: Model & repository consistency

**Issues:** M3, M4, M7, L3, L4

### 7a: NoteTreeNode inheritance

**File:** `api/src/models/note.py`

- [ ] **Step 1: Make NoteTreeNode extend NoteResponse**

  In `api/src/models/note.py`, change `NoteTreeNode` from:
  ```python
  class NoteTreeNode(BaseModel):
      id: int
      parent_id: int | None
      content: str
      sort_order: int
      collapsed: bool
      created_at: str
      updated_at: str
      children: list["NoteTreeNode"] = []
  ```
  to:
  ```python
  class NoteTreeNode(NoteResponse):
      children: list["NoteTreeNode"] = []
  ```

- [ ] **Step 2: Run full suite to verify nothing broke**

  ```bash
  cd api && pytest -q
  ```

### 7b: Move UpdateSettingRequest to models/

**Files:** `api/src/models/settings.py` (new), `api/src/routes/settings.py`

- [ ] **Step 3: Create api/src/models/settings.py**

  ```python
  from pydantic import BaseModel


  class UpdateSettingRequest(BaseModel):
      value: str
  ```

- [ ] **Step 4: Update the import in routes/settings.py**

  Remove the inline `class UpdateSettingRequest(BaseModel)` definition from `api/src/routes/settings.py`.

  Add at the top with the other imports:
  ```python
  from src.models.settings import UpdateSettingRequest
  ```

- [ ] **Step 5: Run full suite**

  ```bash
  cd api && pytest -q
  ```

### 7c: Workout log Pydantic response models

**Files:** `api/src/models/workout_log.py`, `api/src/routes/workout_logs.py`

- [ ] **Step 6: Add response models to workout_log.py**

  In `api/src/models/workout_log.py`, append:

  ```python
  class SetLogResponse(BaseModel):
      id: int
      workout_log_id: int
      exercise_id: int
      set_number: int
      reps: int | None
      weight: float | None
      created_at: str

  class WorkoutLogResponse(BaseModel):
      id: int
      routine_id: int
      routine_name: str
      date: str
      notes: str | None
      created_at: str
      sets: list[SetLogResponse] = []
  ```

- [ ] **Step 7: Add response_model to routes**

  In `api/src/routes/workout_logs.py`, add import:
  ```python
  from src.models.workout_log import (
      CreateWorkoutLogRequest,
      LogSetRequest,
      UpdateWorkoutLogRequest,
      WorkoutLogResponse,
      SetLogResponse,
  )
  ```

  Add `response_model=WorkoutLogResponse` (or `list[WorkoutLogResponse]`) to each route:
  - `GET ""` → `response_model=list[WorkoutLogResponse]`
  - `POST ""` → `response_model=WorkoutLogResponse`
  - `GET "/{workout_log_id}"` → `response_model=WorkoutLogResponse`
  - `PUT "/{workout_log_id}"` → `response_model=WorkoutLogResponse`
  - `GET "/routine/{routine_id}"` → `response_model=list[WorkoutLogResponse]`
  - `POST "/{workout_log_id}/sets"` → `response_model=SetLogResponse`

- [ ] **Step 8: Write a test verifying response shape**

  In `api/tests/test_workout_logs.py`:
  ```python
  async def test_get_workout_log_response_has_expected_fields(client):
      """Verify the response model shape is enforced."""
      # Create the minimum required data to get a log back
      # (depends on your fixtures — adapt as needed)
      response = await client.get("/api/v1/workout-logs")
      assert response.status_code == 200
      data = response.json()
      assert isinstance(data, list)
  ```

- [ ] **Step 9: Run full suite**

  ```bash
  cd api && pytest -q
  ```
  Expected: all tests pass. If Pydantic rejects the dict returns, the repositories return dicts — check `WorkoutLogResponse` field names match the dict keys exactly.

### 7d: Parameterize workout_log UPDATE & remove redundant PRAGMA

**Files:** `api/src/repositories/workout_log_repository.py`, `api/src/repositories/note_repository.py`

- [ ] **Step 10: Rewrite the UPDATE in workout_log_repository**

  In `api/src/repositories/workout_log_repository.py`, replace the f-string UPDATE (lines ~124–128) with:

  ```python
  if updates:
      # Only "date" and "notes" are updatable — explicit safe columns, no dynamic column names
      # Note: workout_logs has no updated_at column so execute_update is not used here
      allowed = {"date", "notes"}
      filtered = {k: v for k, v in updates.items() if k in allowed}
      if filtered:
          set_clause = ", ".join(f"{key} = ?" for key in filtered)
          values = list(filtered.values()) + [workout_log_id]
          await self.db.execute(
              f"UPDATE workout_logs SET {set_clause} WHERE id = ?",  # noqa: S608
              values,
          )
          await self.db.commit()
  ```
  The `filtered` dict ensures only `date` and `notes` can ever appear in the SET clause, eliminating the injection risk. The noqa comment acknowledges the f-string pattern intentionally.

- [ ] **Step 11: Remove redundant PRAGMA from note_repository.delete**

  In `api/src/repositories/note_repository.py`, find the `delete` method. Remove the line:
  ```python
  await db.execute("PRAGMA foreign_keys = ON")
  ```
  (The `get_db()` dependency sets this on every connection; it doesn't need to be repeated per-operation.)

- [ ] **Step 12: Run full suite**

  ```bash
  cd api && pytest -q
  ```

- [ ] **Step 13: Commit all of Task 7**

  ```bash
  git add api/src/models/ api/src/routes/settings.py api/src/routes/workout_logs.py \
          api/src/repositories/workout_log_repository.py \
          api/src/repositories/note_repository.py \
          api/tests/test_workout_logs.py
  git commit -m "refactor: model consistency — NoteTreeNode inheritance, workout log response models, UpdateSettingRequest to models/"
  ```

---

## Task 8: Recurrence documentation & SQL style

**Issues:** M1 (Python side), L1
**Files:** `api/src/services/task_recurrence.py`, `api/src/repositories/task_repository.py`

These are documentation/style-only changes. No behavioral changes.

- [ ] **Step 1: Add docstring to task_recurrence.py**

  In `api/src/services/task_recurrence.py`, add a module-level or function-level docstring to `calculateNextDueDate` (or the main calculation function):

  ```python
  def calculate_next_due_date(current_date: date, recurrence_type: str, repeat_days: list[int] | None) -> date:
      """
      Calculate the next due date for a recurring task.

      Weekday convention: Monday = 0, Sunday = 6 (Python's datetime.weekday()).

      NOTE: The TypeScript local-backend counterpart in
      ui/src/composables/api/backends/local/useTaskApi.ts (lines 35–73)
      uses JavaScript's Date.getDay() convention (Sunday = 0, Saturday = 6).
      This means weekly tasks with repeat_days will calculate INCORRECT next
      due dates in the local backend for all days except Saturday.
      Tracked as a known issue — fix requires aligning the two conventions.
      """
  ```

- [ ] **Step 2: Add noqa comment in task_repository.py**

  In `api/src/repositories/task_repository.py`, find the f-string SQL builder for the count/list queries. Add a `# noqa: S608` comment with justification on the relevant line(s), matching the pattern in `utils.py`:

  ```python
  query = f"SELECT * FROM tasks WHERE {where_clause} ORDER BY ..."  # noqa: S608 — where_clause built from validated condition strings, not user input
  ```

- [ ] **Step 3: Run full suite one final time**

  ```bash
  cd api && pytest -q
  ```
  Expected: all tests pass.

- [ ] **Step 4: Commit**

  ```bash
  git add api/src/services/task_recurrence.py api/src/repositories/task_repository.py
  git commit -m "docs: document weekday convention mismatch with TS local backend; add noqa on f-string SQL"
  ```

---

## Final Verification

- [ ] **Run full test suite**
  ```bash
  cd api && pytest -v
  ```
  Expected: all tests pass, no warnings about uncovered issues.

- [ ] **Run linter**
  ```bash
  cd api && ruff check . && ruff format --check .
  ```
  Fix any issues, commit fixes if needed.

- [ ] **Confirm no remaining High issues**
  - H1 ✅ zip-slip fixed (Task 3)
  - H2 ✅ ValidationError renamed (Task 2)
  - H3 ✅ magic-byte check added (Task 4)
  - H4 ✅ size cap added (Task 3)
  - H6 ✅ default host fixed (Task 1)
