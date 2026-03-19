# UI Code Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 9 UI issues — XSS vulnerability, config errors, notes.vue correctness bugs, profile picture bloat, and extraction of two oversized components into composables.

**Architecture:** Five commits on a `cleanup/ui` branch. The first four are independent fixes; the fifth is the structural split of `notes.vue` and `App.vue`. The split in Commit 5 builds on the correctness fixes in Commit 3, so the commits must be done in order.

**Tech Stack:** Vue 3, TypeScript (strict), Vite, Tailwind CSS, PrimeVue. Verification: `npm run verify` (Prettier + ESLint + vue-tsc). No component test framework is configured — correctness is verified via type-check and manual smoke testing after each commit.

---

## File Map

**Modified:**
- `ui/vite.config.ts` — fix proxy port, gate devtools
- `ui/src/utils/markdown.ts` — add DOMPurify sanitization
- `ui/src/pages/notes.vue` — fix `selectedNote`, fix `setFocus`, then reduce to ~150 lines after split
- `ui/src/pages/settings.vue` — profile picture upload → URL instead of base64
- `ui/src/App.vue` — update profile picture rendering; extract backup + profile composables

**Created:**
- `ui/src/composables/useNoteTree.ts` — all note tree state and mutations
- `ui/src/components/NoteRow.vue` — single row rendering component
- `ui/src/composables/useBackup.ts` — backup/restore logic
- `ui/src/composables/useUserProfile.ts` — profile picture + username

---

## Task 1: Vite config fixes

**Issues:** L2, L5
**File:** `ui/vite.config.ts`

- [ ] **Step 1: Fix proxy port**

  In `ui/vite.config.ts`, change both proxy target entries from port `8050` to `8000`:
  ```ts
  target: 'http://localhost:8000',
  ```
  There are two entries under `proxy` — update both.

- [ ] **Step 2: Gate vueDevTools behind non-production mode**

  Change:
  ```ts
  vueDevTools(),
  ```
  to:
  ```ts
  ...(mode !== 'production' ? [vueDevTools()] : []),
  ```
  The `defineConfig` callback receives `{ mode }` — update the signature to use it:
  ```ts
  export default defineConfig(({ mode }) => ({
    plugins: [
      vue(),
      ...(mode !== 'production' ? [vueDevTools()] : []),
      // ...rest of plugins
    ],
    // ...rest of config
  }));
  ```

- [ ] **Step 3: Verify**

  ```bash
  cd ui && npm run type-check
  ```

- [ ] **Step 4: Commit**

  ```bash
  git checkout -b cleanup/ui
  git add ui/vite.config.ts
  git commit -m "fix: proxy API to port 8000; exclude vueDevTools from production build"
  ```

---

## Task 2: XSS fix — DOMPurify sanitization

**Issue:** H5
**Files:** `ui/src/utils/markdown.ts`, `ui/package.json`

User-authored Markdown is rendered via `v-html` without sanitization. An injected `<script>` or `onerror=` attribute executes as JavaScript.

- [ ] **Step 1: Install DOMPurify**

  ```bash
  cd ui && npm install dompurify && npm install --save-dev @types/dompurify
  ```

- [ ] **Step 2: Add sanitization in markdown.ts**

  In `ui/src/utils/markdown.ts`, add the import at the top:
  ```ts
  import DOMPurify from 'dompurify';
  ```

  Wrap the return value of both `marked.parse` and `marked.parseInline` calls:
  ```ts
  // was: return marked.parse(content) as string;
  return DOMPurify.sanitize(marked.parse(content) as string);

  // was: return marked.parseInline(content) as string;
  return DOMPurify.sanitize(marked.parseInline(content) as string);
  ```

- [ ] **Step 3: Verify**

  ```bash
  cd ui && npm run verify
  ```
  Expected: passes format, lint, and type-check.

- [ ] **Step 4: Commit**

  ```bash
  git add ui/src/utils/markdown.ts ui/package.json ui/package-lock.json
  git commit -m "fix: sanitize markdown output with DOMPurify before passing to v-html"
  ```

---

## Task 3: notes.vue correctness fixes

**Issues:** M9, M10
**File:** `ui/src/pages/notes.vue`

Two bugs: `selectedNote` only searches top-level tree nodes; `setFocus` uses fragile double-nextTick + querySelector.

- [ ] **Step 1: Fix selectedNote computed (M9)**

  In `ui/src/pages/notes.vue`, the `selectedNote` computed currently uses `tree.value.find(...)` which only checks root-level nodes. Replace with `findInTree`:

  ```ts
  const selectedNote = computed(
      () =>
          selectedNoteId.value
              ? findInTree(tree.value, selectedNoteId.value)
              : null,
  );
  ```

  `findInTree` is already defined in the file. This change is safe — the sidebar only shows root-level notes today, so behavior is unchanged, but it future-proofs the lookup.

- [ ] **Step 2: Fix setFocus with template ref map (M10)**

  Add a ref map declaration after the existing refs near the top of `<script setup>`:
  ```ts
  const nodeRefs = ref<Record<number, HTMLTextAreaElement>>({});
  ```

  Update `setFocus` to use the map instead of querySelector:
  ```ts
  function setFocus(id: number) {
      focusId.value = id;
      nextTick(() => {
          nodeRefs.value[id]?.focus();
      });
  }
  ```

  In the template, on the `<textarea>` inside the flat node list, add the ref binding:
  ```html
  :ref="(el) => { if (el) nodeRefs.value[node.id] = el as HTMLTextAreaElement }"
  ```
  And on blur, clean up the entry to avoid a stale ref map. Note: `focusId` is a `ref`, use `.value`:
  ```html
  @blur="
      handleBlur(node);
      if (focusId.value === node.id) {
          focusId.value = null;
          delete nodeRefs.value[node.id];
      }
  "
  ```
  Note: this blur cleanup is removed entirely in Task 7 when NoteRow takes over focus management — skip it here if you prefer less churn.

- [ ] **Step 3: Verify**

  ```bash
  cd ui && npm run verify
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add ui/src/pages/notes.vue
  git commit -m "fix: use findInTree for selectedNote; replace double-nextTick focus with template ref map"
  ```

---

## Task 4: Profile picture migration

**Issue:** L7
**Files:** `ui/src/pages/settings.vue`, `ui/src/App.vue`

Profile pictures are currently stored as full base64 data URLs in `user_settings`, inflating the DB and every app load. Migrate to using the existing image upload endpoint.

- [ ] **Step 1: Update settings.vue to upload the file instead of base64-encoding it**

  In `ui/src/pages/settings.vue`, import `useNoteApi` to get `uploadNoteImage`:
  ```ts
  import { useNoteApi } from '@/composables/api/useNoteApi';
  const { uploadNoteImage } = useNoteApi();
  ```

  The existing handler is named `onFileSelected` (line ~45). Replace it entirely with:
  ```ts
  async function onFileSelected(event: Event) {
      const input = event.target as HTMLInputElement;
      const file = input.files?.[0];
      if (!file) return;

      const res = await uploadNoteImage(file);
      if (!res.success || !res.data) return;

      const url = res.data.url;
      const saveRes = await setSetting('profile_picture', url);
      if (saveRes.success) {
          profilePicture.value = url;
      }
  }
  ```

- [ ] **Step 2: Handle legacy base64 values on load**

  In `ui/src/pages/settings.vue`, find `onMounted`. It currently has a conditional like:
  ```ts
  if (profileRes.success && profileRes.data?.value) {
      profilePicture.value = profileRes.data.value;
  }
  ```
  Replace that block with:
  ```ts
  if (profileRes.success && profileRes.data?.value) {
      const raw = profileRes.data.value;
      if (raw.startsWith('data:')) {
          // NOTE: Prior to 2026-03-19, profile pictures were stored as base64 data URLs.
          // On first load after this change, existing base64 values are cleared.
          // Users must re-upload their profile picture once. Acceptable for a personal app.
          await deleteSetting('profile_picture');
          profilePicture.value = null;
      } else {
          profilePicture.value = raw;
      }
  }
  ```

  Add a comment above the guard:
  ```ts
  // NOTE: Prior to 2026-03-19, profile pictures were stored as base64 data URLs.
  // On first load after this change, existing base64 values are cleared.
  // Users must re-upload their profile picture once. Acceptable for a personal app.
  ```

- [ ] **Step 3: Verify App.vue renders URL correctly**

  In `ui/src/App.vue`, confirm the profile picture `<img :src="profilePicture">` already works with a URL path. The existing template uses `:src="profilePicture"` which works for both data URLs and `/uploads/...` paths — no change needed. Verify by running:
  ```bash
  cd ui && npm run type-check
  ```

- [ ] **Step 4: Verify**

  ```bash
  cd ui && npm run verify
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add ui/src/pages/settings.vue ui/src/App.vue
  git commit -m "fix: store profile picture as uploaded file URL instead of base64 data URL"
  ```

---

## Task 5: Extract useNoteTree composable

**Issue:** M8 (part 1 of 3)
**File created:** `ui/src/composables/useNoteTree.ts`

Extract all tree state and mutation logic from `notes.vue` into a composable. This task produces the composable and updates `notes.vue` to consume it — `notes.vue` still renders everything, just sourcing state from the composable.

- [ ] **Step 1: Create ui/src/composables/useNoteTree.ts**

  Move the following from `notes.vue` into the new composable:

  ```ts
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useNoteApi } from '@/composables/api/useNoteApi';
  import type { NoteTreeNode } from '@/types/Note';

  export function useNoteTree() {
      const {
          getNotes, createNote, updateNote, moveNote, deleteNote,
      } = useNoteApi();

      const tree = ref<NoteTreeNode[]>([]);
      const focusId = ref<number | null>(null);
      const selectedNoteId = ref<number | null>(null);
      const focusedNodeId = ref<number | null>(null);
      const nodeRefs = ref<Record<number, HTMLTextAreaElement>>({});
      const dirtyNodes = new Set<number>();

      // --- helpers ---
      function findInTree(nodes: NoteTreeNode[], id: number): NoteTreeNode | null { ... }
      function findPath(nodes: NoteTreeNode[], id: number, path: NoteTreeNode[]): NoteTreeNode[] | null { ... }
      function findParentAndIndex(nodes: NoteTreeNode[], id: number, parent: NoteTreeNode | null = null) { ... }
      function noteTitle(node: NoteTreeNode): string { ... }

      // --- computeds ---
      const selectedNote = computed(...);
      const focusedNode = computed(...);
      const viewRoot = computed(...);
      const focusedPath = computed(...);
      const flatNodes = computed(...);

      // --- data loading ---
      async function loadData() { ... }
      onMounted(loadData);
      watch(selectedNoteId, () => { focusedNodeId.value = null; });

      // --- focus ---
      function setFocus(id: number) { ... }
      function focusTitleArea() { ... }

      // --- mutations ---
      async function toggleCollapse(node: NoteTreeNode) { ... }
      async function addSibling(afterNode: NoteTreeNode) { ... }
      async function addChild(parentNode: NoteTreeNode) { ... }
      async function addRootNote() { ... }
      async function deleteRootNote(node: NoteTreeNode) { ... }
      async function handleDelete(node: NoteTreeNode) { ... }
      async function indent(node: NoteTreeNode) { ... }
      async function outdent(node: NoteTreeNode) { ... }

      // --- content ---
      function handleInput(e: Event, node: NoteTreeNode) { ... }
      async function handleBlur(node: NoteTreeNode) { ... }
      async function flushNode(node: NoteTreeNode) { ... }
      function handleKeydown(e: KeyboardEvent, node: NoteTreeNode) { ... }
      function autoResize(e: Event) { ... }

      return {
          // state
          tree, focusId, selectedNoteId, focusedNodeId, nodeRefs, dirtyNodes,
          // computeds
          selectedNote, focusedNode, viewRoot, focusedPath, flatNodes,
          // helpers
          findInTree, findPath, noteTitle,
          // focus
          setFocus, focusTitleArea,
          // mutations
          toggleCollapse, addSibling, addChild, addRootNote, deleteRootNote,
          handleDelete, indent, outdent,
          // content
          handleInput, handleBlur, flushNode, handleKeydown, autoResize,
      };
  }
  ```

  Copy the actual implementations verbatim from `notes.vue` — no logic changes in this task.

- [ ] **Step 2: Update notes.vue to consume the composable**

  In `notes.vue`, replace all the moved code with:
  ```ts
  import { useNoteTree } from '@/composables/useNoteTree';

  const {
      tree, focusId, selectedNoteId, focusedNodeId, nodeRefs,
      selectedNote, focusedNode, viewRoot, focusedPath, flatNodes,
      noteTitle, setFocus, focusTitleArea,
      toggleCollapse, addSibling, addChild, addRootNote, deleteRootNote,
      handleDelete, indent, outdent,
      handleInput, handleBlur, flushNode, handleKeydown, autoResize,
  } = useNoteTree();
  ```

  Keep in `notes.vue` (not extracted): `hoveredId`, `uploadingImages`, `uploadAndInsertImage`, `handlePaste`, `openFilePicker` — these are UI interaction helpers that will move to `NoteRow` in the next task.

  Keep all `<template>` markup unchanged for now.

- [ ] **Step 3: Verify**

  ```bash
  cd ui && npm run verify
  ```
  Expected: passes. The app should behave identically.

- [ ] **Step 4: Commit**

  ```bash
  git add ui/src/composables/useNoteTree.ts ui/src/pages/notes.vue
  git commit -m "refactor: extract useNoteTree composable from notes.vue"
  ```

---

## Task 6: Create NoteRow component

**Issue:** M8 (part 2 of 3)
**File created:** `ui/src/components/NoteRow.vue`

Extract the per-row rendering into a standalone component. This component owns its own hover state, image upload state, and keyboard handling.

- [ ] **Step 1: Create ui/src/components/NoteRow.vue**

  ```vue
  <script setup lang="ts">
  import { ref } from 'vue';
  import { useNoteApi } from '@/composables/api/useNoteApi';
  import { renderMarkdown } from '@/utils/markdown';
  import type { NoteTreeNode } from '@/types/Note';

  const props = defineProps<{
      node: NoteTreeNode;
      depth: number;
      isFocused: boolean;
      focusedNodeId: number | null;
  }>();

  const emit = defineEmits<{
      'toggle-collapse': [node: NoteTreeNode];
      'set-focus': [node: NoteTreeNode];
      'zoom': [nodeId: number];
      'input': [event: Event, node: NoteTreeNode];
      'blur': [node: NoteTreeNode];
      'keydown': [event: KeyboardEvent, node: NoteTreeNode];
      'paste': [event: ClipboardEvent, node: NoteTreeNode];
      'add-child': [node: NoteTreeNode];
      'delete': [node: NoteTreeNode];
  }>();

  const { uploadNoteImage } = useNoteApi();

  const hovered = ref(false);
  const uploading = ref(false);

  function autoResize(e: Event) {
      const el = e.target as HTMLTextAreaElement;
      el.style.height = 'auto';
      el.style.height = el.scrollHeight + 'px';
  }

  async function uploadAndInsertImage(file: File, textarea: HTMLTextAreaElement | null) {
      uploading.value = true;
      try {
          const res = await uploadNoteImage(file);
          if (!res.success || !res.data) return;
          const markdownImg = `![](${res.data.url})`;
          const cursorPos = textarea?.selectionStart ?? props.node.content.length;
          props.node.content =
              props.node.content.slice(0, cursorPos) +
              markdownImg +
              props.node.content.slice(cursorPos);
          emit('input', { target: { value: props.node.content } } as unknown as Event, props.node);
      } finally {
          uploading.value = false;
      }
  }

  function handlePaste(e: ClipboardEvent) {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
          if (item.type.startsWith('image/')) {
              e.preventDefault();
              const file = item.getAsFile();
              if (!file) return;
              const textarea = document.querySelector(
                  `[data-note-id="${props.node.id}"] textarea`,
              ) as HTMLTextAreaElement | null;
              uploadAndInsertImage(file, textarea);
              return;
          }
      }
      emit('paste', e, props.node);
  }

  function openFilePicker() {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.onchange = () => {
          const file = input.files?.[0];
          if (!file) return;
          uploadAndInsertImage(file, null);
      };
      input.click();
  }
  </script>

  <template>
      <div
          class="group relative flex items-start gap-1 rounded py-0.5 hover:bg-stone-100 dark:hover:bg-stone-800"
          :data-note-id="node.id"
          :style="{ paddingLeft: depth * 1.5 + 'rem' }"
          @mouseenter="hovered = true"
          @mouseleave="hovered = false"
      >
          <!-- Indent guides -->
          <div
              v-for="i in depth"
              :key="'guide-' + i"
              class="pointer-events-none absolute inset-y-0 w-px bg-stone-200 dark:bg-stone-700"
              :style="{ left: (i - 1) * 1.5 + 0.625 + 'rem' }"
          ></div>

          <!-- Bullet — zoom trigger -->
          <button
              class="mt-1.5 flex h-5 w-5 shrink-0 cursor-pointer items-center justify-center rounded"
              :class="focusedNodeId === node.id
                  ? 'text-primary-500'
                  : 'text-surface-400 hover:text-surface-600 dark:hover:text-surface-300'"
              tabindex="-1"
              :title="'Zoom into ' + node.content.split('\n')[0]?.trim() || 'Untitled'"
              @click="emit('zoom', node.id)"
          >
              <span
                  class="inline-block h-1.5 w-1.5 rounded-full"
                  :class="focusedNodeId === node.id
                      ? 'bg-primary-500'
                      : 'bg-surface-400 dark:bg-surface-500'"
              ></span>
          </button>

          <!-- Collapse caret — halfway between parent guide and this bullet -->
          <button
              v-if="node.children.length"
              class="absolute top-2 flex h-3 w-3 cursor-pointer items-center justify-center opacity-0 transition-opacity group-hover:opacity-100 text-surface-400 hover:text-surface-600 dark:hover:text-surface-300"
              :style="{ left: Math.max(0, depth * 1.5 - 0.5) + 'rem' }"
              tabindex="-1"
              @click="emit('toggle-collapse', node)"
          >
              <i
                  class="pi text-[8px]"
                  :class="node.collapsed ? 'pi-caret-right' : 'pi-caret-down'"
              ></i>
          </button>

          <!-- Content: rendered markdown or editable textarea -->
          <div
              v-if="!isFocused"
              class="note-prose prose prose-sm dark:prose-invert text-surface-800 dark:text-surface-200 min-h-[1.75rem] flex-1 cursor-text py-1 text-sm"
              @click="emit('set-focus', node)"
              v-html="renderMarkdown(node.content)"
          ></div>
          <textarea
              v-else
              class="text-surface-800 dark:text-surface-200 min-h-[1.75rem] flex-1 resize-none overflow-hidden border-none bg-transparent py-1 text-sm leading-snug outline-none"
              rows="1"
              :value="node.content"
              @blur="emit('blur', node)"
              @input="emit('input', $event, node)"
              @keydown="emit('keydown', $event, node)"
              @paste="handlePaste"
              @vue:mounted="($event: any) => {
                  const el = $event.el as HTMLTextAreaElement;
                  el.style.height = 'auto';
                  el.style.height = el.scrollHeight + 'px';
                  el.focus();
              }"
          />

          <!-- Hover actions -->
          <div
              class="mt-1 flex shrink-0 gap-0.5 opacity-0 transition-opacity"
              :class="{ 'opacity-100': hovered }"
          >
              <button
                  class="text-surface-400 hover:text-primary-500 rounded p-0.5"
                  title="Add image"
                  @click="openFilePicker"
              >
                  <i class="pi text-xs" :class="uploading ? 'pi-spinner pi-spin' : 'pi-image'"></i>
              </button>
              <button
                  class="text-surface-400 hover:text-primary-500 rounded p-0.5"
                  title="Add child"
                  @click="emit('add-child', node)"
              >
                  <i class="pi pi-plus text-xs"></i>
              </button>
              <button
                  class="text-surface-400 rounded p-0.5 hover:text-red-500"
                  title="Delete"
                  @click="emit('delete', node)"
              >
                  <i class="pi pi-trash text-xs"></i>
              </button>
          </div>
      </div>
  </template>
  ```

  Key design decisions:
  - `hovered` and `uploading` are local state — NoteRow manages its own UI state
  - `@vue:mounted` on the textarea calls `el.focus()` directly — this replaces the template ref map from Task 3. When `isFocused` becomes true, the textarea renders and auto-focuses on mount.
  - Image paste is handled inside NoteRow; other paste events are emitted up
  - The collapse caret, bullet, and indent guides are copied verbatim from `notes.vue`

- [ ] **Step 2: Verify**

  ```bash
  cd ui && npm run type-check
  ```
  Expected: no type errors.

- [ ] **Step 3: Commit (component only — not yet wired into notes.vue)**

  ```bash
  git add ui/src/components/NoteRow.vue
  git commit -m "feat: add NoteRow component (not yet wired)"
  ```

---

## Task 7: Wire NoteRow into notes.vue and reduce

**Issue:** M8 (part 3 of 3)
**File:** `ui/src/pages/notes.vue`

Replace the inline row rendering in `notes.vue` with `<NoteRow>` components, then remove the now-unused local code.

- [ ] **Step 1: Import NoteRow in notes.vue**

  In `<script setup>` of `notes.vue`:
  ```ts
  import NoteRow from '@/components/NoteRow.vue';
  ```

- [ ] **Step 2: Replace the flat node list template**

  Replace the entire `v-for` block that renders `{ node, depth }` with:
  ```html
  <NoteRow
      v-for="{ node, depth } in flatNodes"
      :key="node.id"
      :node="node"
      :depth="depth"
      :is-focused="focusId === node.id"
      :focused-node-id="focusedNodeId"
      @toggle-collapse="toggleCollapse"
      @set-focus="(n) => setFocus(n.id)"
      @zoom="(id) => (focusedNodeId = id)"
      @input="handleInput"
      @blur="(n) => { handleBlur(n); if (focusId === n.id) focusId = null; }"
      @keydown="handleKeydown"
      @add-child="addChild"
      @delete="handleDelete"
  />
  ```

- [ ] **Step 3: Remove dead code from notes.vue**

  Remove from `notes.vue` (now in NoteRow or useNoteTree):
  - `hoveredId` ref
  - `uploadingImages` ref
  - `uploadAndInsertImage` function
  - `handlePaste` function
  - `openFilePicker` function
  - `autoResize` function (still used in title textarea — keep that one usage, remove the function if you inline it)
  - `nodeRefs` ref (NoteRow now handles focus via `@vue:mounted`)

  Also simplify `setFocus` — since NoteRow handles its own focus on mount, `setFocus` only needs to update `focusId`:
  ```ts
  function setFocus(id: number) {
      focusId.value = id;
  }
  ```

- [ ] **Step 4: Verify**

  ```bash
  cd ui && npm run verify
  ```
  Expected: passes. Check line count:
  ```bash
  wc -l ui/src/pages/notes.vue
  ```
  Expected: under 200 lines.

- [ ] **Step 5: Commit**

  ```bash
  git add ui/src/pages/notes.vue ui/src/components/NoteRow.vue
  git commit -m "refactor: replace inline row rendering with NoteRow component; reduce notes.vue to ~150 lines"
  ```

---

## Task 8: Extract App.vue composables

**Issue:** M11
**Files:** `ui/src/composables/useBackup.ts` (new), `ui/src/composables/useUserProfile.ts` (new), `ui/src/App.vue`

- [ ] **Step 1: Create useBackup.ts**

  `App.vue` currently has `backingUp` and `restoring` loading refs that gate button `:loading` props in the template — move them into the composable too.

  ```ts
  import { ref } from 'vue';
  import { useSettingsApi } from '@/composables/api/useSettingsApi';
  import { useToast } from '@/composables/useToast';

  export function useBackup() {
      const { backup, restore } = useSettingsApi();
      const toast = useToast();

      const restoreFileInput = ref<HTMLInputElement | null>(null);
      const restoreFile = ref<File | null>(null);
      const restoreConfirmText = ref('');
      const showRestoreDialog = ref(false);
      const backingUp = ref(false);
      const restoring = ref(false);

      async function downloadBackup() {
          backingUp.value = true;
          try {
              await backup();
          } catch {
              toast.showError('Failed to download backup');
          } finally {
              backingUp.value = false;
          }
      }

      function triggerRestorePicker() {
          restoreFileInput.value?.click();
      }

      function onRestoreFileSelected(file: File) {
          restoreFile.value = file;
          restoreConfirmText.value = '';
          showRestoreDialog.value = true;
      }

      async function confirmRestore() {
          if (restoreConfirmText.value !== 'RESTORE' || !restoreFile.value) return;
          restoring.value = true;
          try {
              const res = await restore(restoreFile.value);
              if (res.success) {
                  toast.showSuccess('Backup restored successfully');
                  showRestoreDialog.value = false;
              } else {
                  toast.showError('Failed to restore backup');
              }
          } finally {
              restoring.value = false;
          }
      }

      return {
          restoreFileInput, restoreFile, restoreConfirmText, showRestoreDialog,
          backingUp, restoring,
          downloadBackup, triggerRestorePicker, onRestoreFileSelected, confirmRestore,
      };
  }
  ```

- [ ] **Step 2: Create useUserProfile.ts**

  ```ts
  import { ref } from 'vue';
  import { useSettingsApi } from '@/composables/api/useSettingsApi';

  export function useUserProfile() {
      const { getSetting } = useSettingsApi();

      const profilePicture = ref<string | null>(null);
      const userName = ref<string | null>(null);

      async function loadProfile() {
          const [profileRes, nameRes] = await Promise.all([
              getSetting('profile_picture'),
              getSetting('user_name'),
          ]);
          if (profileRes.success && profileRes.data?.value) {
              profilePicture.value = profileRes.data.value;
          }
          if (nameRes.success && nameRes.data?.value) {
              userName.value = nameRes.data.value;
          }
      }

      return { profilePicture, userName, loadProfile };
  }
  ```

- [ ] **Step 3: Update App.vue to use the composables**

  In `App.vue`, replace the inline backup/profile/restore logic with:
  ```ts
  import { useBackup } from '@/composables/useBackup';
  import { useUserProfile } from '@/composables/useUserProfile';

  const {
      restoreFileInput, restoreConfirmText, showRestoreDialog,
      backingUp, restoring,
      downloadBackup, triggerRestorePicker, onRestoreFileSelected, confirmRestore,
  } = useBackup();

  const { profilePicture, userName, loadProfile } = useUserProfile();

  onMounted(async () => {
      await loadProfile();
      // theme loading stays in App.vue
  });
  ```

  Remove the now-dead local vars and functions from App.vue. Update template bindings to match the renamed composable exports where needed.

- [ ] **Step 4: Verify**

  ```bash
  cd ui && npm run verify
  ```
  Expected: passes. Check App.vue line count:
  ```bash
  wc -l ui/src/App.vue
  ```
  Expected: under 130 lines.

- [ ] **Step 5: Commit**

  ```bash
  git add ui/src/composables/useBackup.ts ui/src/composables/useUserProfile.ts ui/src/App.vue
  git commit -m "refactor: extract useBackup and useUserProfile composables; reduce App.vue to ~120 lines"
  ```

---

## Final Verification

- [ ] **Full verify pass**
  ```bash
  cd ui && npm run verify
  ```

- [ ] **Smoke test** — start both API and UI dev servers, confirm:
  - Notes page loads and editing works
  - Collapse/expand and zoom work
  - Backup/restore buttons visible in App sidebar
  - Profile picture upload in Settings works

- [ ] **Confirm no remaining High issues**
  - H5 ✅ DOMPurify added (Task 2)
  - L2 ✅ proxy port fixed (Task 1)
  - L5 ✅ devtools gated (Task 1)
  - L7 ✅ profile picture migrated to URL (Task 4)
  - M8 ✅ notes.vue under 200 lines (Tasks 5–7)
  - M9 ✅ selectedNote uses findInTree (Task 3)
  - M10 ✅ focus via @vue:mounted in NoteRow (Task 6)
  - M11 ✅ App.vue under 130 lines (Task 8)
