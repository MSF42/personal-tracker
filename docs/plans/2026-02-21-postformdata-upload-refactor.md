# postFormData Upload Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate the duplicate manual `fetch()` implementations in `importGpx` and `uploadNoteImage` by adding a `postFormData<T>` method to `useApi`.

**Architecture:** Add a private `requestFormData<T>()` function to `useApi.ts` (parallel to the existing `request<T>()`) and expose it as `postFormData` on the return object. Both composables then delegate to it instead of owning their own fetch logic. No callers outside `useRunningApi` and `useNoteApi` need to change.

**Tech Stack:** TypeScript, Vue 3, native `fetch` API

**Linter/type-checker:** `npm run verify` (Prettier + ESLint + vue-tsc), run from `ui/` directory
**Repo root:** `/Users/stevefurches/Documents/Steve/personal-tracker`
**UI root:** `/Users/stevefurches/Documents/Steve/personal-tracker/ui`

> **Note:** The UI has no automated test suite. Verification is via TypeScript type-checking (`npm run type-check`) and linting (`npm run lint`). The final `npm run verify` covers all three checks.

---

### Task 1: Add `postFormData` to `useApi.ts`

**Files:**
- Modify: `ui/src/composables/api/backends/http/useApi.ts`

---

**Step 1: Add `requestFormData<T>` private function**

In `ui/src/composables/api/backends/http/useApi.ts`, add the following immediately after the closing brace of the existing `request<T>` function (currently ending at line 124). The new function mirrors `request()` exactly except it takes `FormData` instead of a JSON body, and it does not set a `Content-Type` header (the browser sets the multipart boundary automatically).

```ts
async function requestFormData<T>(
    endpoint: string,
    formData: FormData,
): Promise<ApiResponse<T>> {
    const url = buildUrl(endpoint);
    try {
        const response = await fetch(url, { method: 'POST', body: formData });

        if (!isSuccessStatus(response.status)) {
            let backendError: BackendError | undefined;
            try {
                backendError = await response.json();
            } catch {
                // Response body isn't JSON
            }
            return {
                data: null,
                error: handleHttpError(response.status, backendError, endpoint),
                success: false,
            };
        }

        if (isNoContent(response.status)) {
            return { data: null, error: null, success: true };
        }

        const data = (await response.json()) as T;
        return { data, error: null, success: true };
    } catch (err) {
        const apiError: ApiError = {
            message:
                err instanceof Error
                    ? err.message
                    : 'An unexpected error occurred',
            endpoint,
        };

        const toast = getToast();
        if (toast) {
            toast.showApiError(apiError);
        }

        return { data: null, error: apiError, success: false };
    }
}
```

**Step 2: Expose `postFormData` from `useApi()`**

Inside the `useApi()` function body (currently lines 126–192), add the new method alongside the others:

```ts
const postFormData = async <T>(
    endpoint: string,
    formData: FormData,
): Promise<ApiResponse<T>> => {
    return requestFormData<T>(endpoint, formData);
};
```

Then add `postFormData` to the return object:

```ts
return {
    getData,
    getDataArray,
    getPaginated,
    post,
    postWithParams,
    put,
    remove,
    postFormData,
};
```

**Step 3: Type-check**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker/ui && npm run type-check
```

Expected: No errors.

**Step 4: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add ui/src/composables/api/backends/http/useApi.ts && \
git commit -m "feat: add postFormData to useApi for multipart uploads"
```

---

### Task 2: Update `importGpx` in `useRunningApi.ts`

**Files:**
- Modify: `ui/src/composables/api/backends/http/useRunningApi.ts`

---

**Step 1: Replace `importGpx` body**

Current `importGpx` (lines 39–77) is a 38-line manual fetch implementation. Replace the entire function body with a 3-line call to `api.postFormData`:

Current:
```ts
    const importGpx = async (
        file: File,
    ): Promise<ApiResponse<GpxImportResponse>> => {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch(
                `${window.location.origin}/api/v1/runs/import-gpx`,
                { method: 'POST', body: formData },
            );
            if (!response.ok) {
                let errorMsg = 'Import failed';
                try {
                    const err = await response.json();
                    errorMsg = err.error || err.detail || errorMsg;
                } catch {
                    // ignore parse error
                }
                return {
                    data: null,
                    error: { message: errorMsg, statusCode: response.status },
                    success: false,
                };
            }
            const data = (await response.json()) as GpxImportResponse;
            return { data, error: null, success: true };
        } catch (err) {
            return {
                data: null,
                error: {
                    message:
                        err instanceof Error
                            ? err.message
                            : 'An unexpected error occurred',
                },
                success: false,
            };
        }
    };
```

Replace with:
```ts
    const importGpx = async (
        file: File,
    ): Promise<ApiResponse<GpxImportResponse>> => {
        const formData = new FormData();
        formData.append('file', file);
        return api.postFormData<GpxImportResponse>('runs/import-gpx', formData);
    };
```

**Step 2: Type-check**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker/ui && npm run type-check
```

Expected: No errors.

**Step 3: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add ui/src/composables/api/backends/http/useRunningApi.ts && \
git commit -m "refactor: use postFormData in importGpx"
```

---

### Task 3: Update `uploadNoteImage` in `useNoteApi.ts`

**Files:**
- Modify: `ui/src/composables/api/backends/http/useNoteApi.ts`

---

**Step 1: Replace `uploadNoteImage` body**

Current `uploadNoteImage` (lines 29–65) is a 37-line manual fetch implementation. Replace the entire function body:

Current:
```ts
    const uploadNoteImage = async (
        file: File,
    ): Promise<ApiResponse<NoteImageUpload>> => {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch(
                `${window.location.origin}/api/v1/notes/images`,
                { method: 'POST', body: formData },
            );
            if (!response.ok) {
                let errorMsg = 'Upload failed';
                try {
                    const err = await response.json();
                    if (err.error) errorMsg = err.error;
                } catch {
                    /* ignore parse error */
                }
                return {
                    data: null,
                    error: { message: errorMsg },
                    success: false,
                };
            }
            const data = (await response.json()) as NoteImageUpload;
            return { data, error: null, success: true };
        } catch (err) {
            return {
                data: null,
                error: {
                    message:
                        err instanceof Error ? err.message : 'Upload failed',
                },
                success: false,
            };
        }
    };
```

Replace with:
```ts
    const uploadNoteImage = async (
        file: File,
    ): Promise<ApiResponse<NoteImageUpload>> => {
        const formData = new FormData();
        formData.append('file', file);
        return api.postFormData<NoteImageUpload>('notes/images', formData);
    };
```

**Step 2: Run full verify**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker/ui && npm run verify
```

Expected: No errors (Prettier formatting, ESLint, vue-tsc all pass).

**Step 3: Verify no stray manual fetch references remain for these endpoints**

```bash
grep -r "import-gpx\|notes/images" \
  /Users/stevefurches/Documents/Steve/personal-tracker/ui/src/composables/
```

Expected: Only the two new 3-line functions appear — no hardcoded `window.location.origin` references.

**Step 4: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add ui/src/composables/api/backends/http/useNoteApi.ts && \
git commit -m "refactor: use postFormData in uploadNoteImage"
```

---

## Done

After all 3 tasks: `postFormData` is the single place where multipart upload logic lives. `importGpx` and `uploadNoteImage` are each 4 lines. Upload errors now show toast notifications consistent with the rest of the app.
