# postFormData Upload Refactor Design

**Date:** 2026-02-21
**Status:** Approved

## Problem

`importGpx` in `useRunningApi.ts` and `uploadNoteImage` in `useNoteApi.ts` each
contain ~38-line manual `fetch()` implementations that bypass the centralized
`useApi` composable. Both construct their own try/catch, response-status checks,
and error-parsing logic. Any change to how file uploads work (error format, auth
headers, base URL) must be made in two places.

Additionally, neither implementation calls `handleHttpError()`, so upload failures
produce no toast notification — inconsistent with every other API error in the app.

## Chosen Approach: Add `postFormData<T>` to `useApi`

Add a single new method to `useApi` that mirrors `request()` for FormData payloads:

```ts
const postFormData = async <T>(
    endpoint: string,
    formData: FormData,
): Promise<ApiResponse<T>> => { ... }
```

- Uses `buildUrl` (same as `request`)
- Omits `Content-Type` header so the browser sets the multipart boundary
- Uses `handleHttpError` and the toast path on error — consistent with all other methods
- Returns `ApiResponse<T>` — same shape callers already handle

## Changes

### `ui/src/composables/api/backends/http/useApi.ts`

Add `postFormData<T>` as a module-level private function (parallel to `request()`),
and expose it from the `useApi()` return object.

### `ui/src/composables/api/backends/http/useRunningApi.ts`

Replace `importGpx` body (~38 lines) with:

```ts
const formData = new FormData();
formData.append('file', file);
return postFormData<RunningActivity>('running/import-gpx', formData);
```

### `ui/src/composables/api/backends/http/useNoteApi.ts`

Replace `uploadNoteImage` body (~37 lines) with:

```ts
const formData = new FormData();
formData.append('file', file);
return postFormData<{ url: string }>('notes/upload-image', formData);
```

## Behavior Change

Upload errors now show toast notifications — consistent with the rest of the app.
Return type (`ApiResponse<T>`) and calling signatures are unchanged.

## Alternatives Considered

**Standalone utility module** — inconsistent with the pattern; every other composable
uses `useApi`. Rejected.

**Extract error-parsing only** — leaves two separate `fetch()` calls with the same
structure; real duplication remains. Rejected.
