# Code Cleanup Design — Personal Tracker

**Date:** 2026-03-19
**Scope:** Full codebase sweep — API and UI
**Approach:** Option B — domain-grouped branches

---

## Background

A full code review surfaced 23 issues across the FastAPI backend (`api/`) and Vue 3 frontend (`ui/src/`). Issues range from security vulnerabilities (zip slip, XSS, wrong HTTP status codes) to architectural debt (709-line component, duplicate recurrence logic) to minor inconsistencies. All issues will be addressed in two independent branches worked sequentially: API first, then UI.

---

## Branch 1: `cleanup/api`

### Commit 1 — Quick config & dead code
**Issues:** H6, M5, L6

- `api/src/config/settings.py`: Change default `host` from `"0.0.0.0"` to `"127.0.0.1"` to prevent unintentional LAN exposure.
- `api/src/app.py`: Remove the duplicate health router registration. Keep only the bare `/health` prefix; remove the `/api/v1/health` duplicate.
- `api/src/routes/health.py`: Remove `/ping` and `/db-test` debug endpoints entirely.

### Commit 2 — Security patches
**Issues:** H1, H2, H3, H4

- `api/src/errors.py`: Rename `ValidationError` → `AppValidationError`; update all import sites across routes and `app.py`. Eliminates silent shadowing of Pydantic's `ValidationError` which caused 422s to become 500s.
- `api/src/routes/settings.py` — zip-slip fix: The restore endpoint writes two kinds of paths that both require guards:
  1. **`tracker.db`**: The zip entry name must equal exactly `"tracker.db"` (literal string comparison, not path construction) to prevent a crafted entry like `"../tracker.db"` from writing outside the expected location.
  2. **Upload files**: After constructing each upload extraction path as `uploads_path / name`, call `.resolve()` on the result and assert the resolved path starts with `uploads_path.resolve()` before writing. Raise a 400 if either check fails.
  - Add a 100 MB size cap: check `len(content)` after `await file.read()` and raise a 400 if exceeded.
- `api/src/routes/notes.py` — image upload magic-byte validation: Add a second validation layer after the existing `content_type` allowlist check (keep both; defense in depth). Read the first 12 bytes of the uploaded file and verify them against known signatures: JPEG (`FF D8 FF`), PNG (`89 50 4E 47 0D 0A 1A 0A`), GIF (`47 49 46 38`), WebP (`52 49 46 46 ?? ?? ?? ?? 57 45 42 50`). Return a 422 if the bytes do not match the declared content type. After the check, seek back to position 0 before saving.

### Commit 3 — Route correctness & error handling
**Issues:** M2, M6

- `api/src/routes/workout_logs.py`: Move the `GET /routine/{routine_id}` route registration to before `GET /{workout_log_id}`. FastAPI matches routes in registration order; `"routine"` is currently intercepted by `/{workout_log_id}` which fails to parse it as an integer and returns a 422. Note: before moving, verify in tests that a request to `/workout-logs/routine/5` returns the correct response after the reorder — FastAPI does prioritize fixed path segments over parameterized ones in some cases, so if re-ordering alone does not resolve it, add a path prefix to disambiguate.
- `api/src/routes/running.py`: Wrap `parse_gpx(xml_bytes)` in a try/except catching `ValueError` and `xml.etree.ElementTree.ParseError`; re-raise as `AppValidationError` with a descriptive message (e.g. `"GPX file must contain at least 2 trackpoints"` for `ValueError`). Prevents malformed or short GPX files from returning a 500.

### Commit 4 — Model & repository consistency
**Issues:** M3, M4, M7, L3, L4

- `api/src/models/note.py`: Make `NoteTreeNode` extend `NoteResponse` instead of duplicating all seven fields verbatim.
- `api/src/models/settings.py` (new file): Move `UpdateSettingRequest` out of `routes/settings.py` and into `models/` to match the project convention. Update the import in the route file.
- `api/src/models/workout_log.py` + `api/src/routes/workout_logs.py`: Create Pydantic response models for workout log and set log endpoints. Add `response_model=` annotations to all workout log routes.
- `api/src/repositories/workout_log_repository.py`: The `workout_logs` table has no `updated_at` column, making it incompatible with `execute_update` (which unconditionally stamps `updated_at`). Keep the manual parameterized UPDATE for `workout_log_repository.update`, but rewrite it as a proper parameterized query (no f-string column injection) using only the two known-safe columns (`date`, `notes`). Do **not** add `workout_logs` to `_ALLOWED_TABLES` for write operations. Document this explicitly with a comment.
- `api/src/repositories/note_repository.py`: Remove the redundant `PRAGMA foreign_keys = ON` from the `delete` method (already set by `get_db()` on every connection).

### Commit 5 — Recurrence documentation & SQL style
**Issues:** M1 (Python side), L1

- `api/src/services/task_recurrence.py`: Add a docstring documenting the weekday convention (Mon=0, matching Python's `datetime.weekday()`). Add a cross-reference comment pointing to `ui/src/composables/api/backends/local/useTaskApi.ts` lines 35–73, flagging that the TypeScript counterpart uses `Date.getDay()` (Sun=0), producing incorrect next-due dates for weekly tasks on all days except Saturday. Mark as a known issue deferred to a follow-up.
- `api/src/repositories/task_repository.py`: Add a `# noqa: S608` comment with a brief justification on the f-string SQL builder for the count/list queries, consistent with `utils.py`.

---

## Branch 2: `cleanup/ui`

### Commit 1 — Vite config fixes
**Issues:** L2, L5

- `ui/vite.config.ts`: Fix proxy target from port `8050` to `8000` to match CLAUDE.md.
- `ui/vite.config.ts`: Gate `vueDevTools()` behind `mode !== 'production'` to avoid shipping the Vue DevTools hook in production bundles.

### Commit 2 — XSS fix
**Issue:** H5

- Install `dompurify` and `@types/dompurify`.
- `ui/src/utils/markdown.ts`: Pipe `marked` output through `DOMPurify.sanitize()` before returning. Prevents injected `<script>` tags and inline event handlers in note content from executing when rendered via `v-html`.

### Commit 3 — `notes.vue` correctness fixes
**Issues:** M9, M10

- `selectedNote` computed: Replace `tree.value.find(n => n.id === selectedNoteId.value)` with `findInTree(tree.value, selectedNoteId.value)` so non-root notes can be found if the sidebar is ever extended.
- `setFocus`: Replace the double-`nextTick` + `querySelector` pattern with a template ref map. Declare `const nodeRefs = ref<Record<number, HTMLTextAreaElement>>({})` and populate it via `:ref="(el) => { if (el) nodeRefs.value[node.id] = el as HTMLTextAreaElement }"` on each textarea. `setFocus` then calls `nodeRefs.value[id]?.focus()` inside a single `nextTick`.

### Commit 4 — Profile picture migration
**Issue:** L7

Move profile picture storage from base64 data URL in `user_settings` to an uploaded file URL:
- `ui/src/pages/settings.vue`: On image selection, call the existing `/api/v1/notes/upload-image` endpoint instead of reading as base64 via `FileReader`. Store the returned URL string as the `profile_picture` setting value.
- `ui/src/App.vue`: Update profile picture rendering to use `<img :src="profilePicture">` directly (already works for both data URLs and file URLs, but should be confirmed).
- **Data migration**: Existing stored base64 values are silently dropped — on first load after the update, if the stored value starts with `data:`, treat it as invalid, clear the setting, and show no profile picture. This is acceptable for a personal app. Add a comment in the code documenting this decision.

### Commit 5 — Component & composable extraction
**Issues:** M8, M11

#### `notes.vue` split (709 lines → ~150 lines)

**`ui/src/composables/useNoteTree.ts`** (new)
Owns all tree state and mutations:
- `tree`, `selectedNoteId`, `focusedNodeId` refs
- `selectedNote`, `focusedNode`, `viewRoot`, `focusedPath`, `flatNodes` computeds
- `loadData`, `addRootNote`, `addChild`, `addSibling`, `handleDelete`, `indent`, `outdent`, `toggleCollapse`
- `findInTree`, `findPath`, `findParentAndIndex` helpers
- `handleInput`, `handleBlur`, `flushNode`, `dirtyNodes`
- Returns all state and operations; `notes.vue` consumes it via destructuring

**`ui/src/components/NoteRow.vue`** (new)
Single-row rendering component:
- Props: `node: NoteTreeNode`, `depth: number`, `isFocused: boolean`, `focusedNodeId: number | null`
- Emits: `toggle-collapse`, `set-focus`, `zoom`, `keydown`, `paste`, `add-child`, `delete`, `open-file-picker`
- Renders: indent guides, collapse caret, bullet, markdown display or textarea, hover actions
- Owns: `hoveredId` local state, image uploading state, `autoResize`

**`ui/src/pages/notes.vue`** (reduced)
- Imports `useNoteTree` and renders sidebar + title/breadcrumb + `<NoteRow>` list
- No business logic; pure wiring

#### `App.vue` split (282 lines → ~120 lines)

**`ui/src/composables/useBackup.ts`** (new)
- `downloadBackup()`, `restoreBackup(file)`, `showRestoreConfirm` ref, confirmation dialog trigger

**`ui/src/composables/useUserProfile.ts`** (new)
- `profilePicture`, `username` refs; `loadProfile()`, `saveProfile()` operations

**`ui/src/App.vue`** (reduced)
- Imports both composables; owns nav shell and theme toggle only

---

## Out of Scope (Separate Follow-Up)

**M1 — Recurrence weekday convention mismatch** between Python (`datetime.weekday()`, Mon=0) and TypeScript (`Date.getDay()`, Sun=0) in the local backend. Fixing this requires deciding the canonical convention and updating one side's logic with regression tests. Deferred to a dedicated ticket; Commit 5 of `cleanup/api` adds a cross-reference comment flagging the issue.

---

## Success Criteria

1. `pytest` passes with no regressions after `cleanup/api`
2. `npm run verify` passes after `cleanup/ui`
3. No High-severity issues remain
4. `notes.vue` is under 200 lines; `App.vue` is under 130 lines
5. All workout log routes return typed Pydantic responses
6. Profile picture is stored as a URL, not base64; existing base64 values are cleared on first load
