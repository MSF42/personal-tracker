# Notes Page Styling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the Notes page with a slate sidebar panel and warm paper content area.

**Architecture:** All changes are class string edits in the `<template>` block of a single file — no logic, script, or composable changes. The sidebar gets a slate-100 background with structured header; the content area gets a stone-50 warm background with a title accent bar.

**Tech Stack:** Vue 3, Tailwind CSS v4, PrimeVue 4, `pi` icon font

**Spec:** `docs/superpowers/specs/2026-03-19-notes-page-styling-design.md`

---

### Task 1: Sidebar shell — background and border

**Files:**
- Modify: `ui/src/pages/notes.vue:399-401`

- [ ] **Step 1: Add slate background to the outer sidebar div**

At line 400, replace:
```html
class="border-surface-200 dark:border-surface-700 flex w-64 shrink-0 flex-col border-r"
```
With:
```html
class="bg-slate-100 dark:bg-slate-800 border-surface-200 dark:border-surface-700 flex w-64 shrink-0 flex-col border-r"
```

- [ ] **Step 2: Verify visually**

Run `npm run dev` from `ui/` if not already running. Open `/notes` and confirm the sidebar has a light slate background in light mode. Toggle dark mode and confirm it goes dark slate.

- [ ] **Step 3: Commit**

```bash
git add ui/src/pages/notes.vue
git commit -m "style: add slate background to notes sidebar"
```

---

### Task 2: Sidebar header — NOTES label and replace AppButton

**Files:**
- Modify: `ui/src/pages/notes.vue:402-412`

- [ ] **Step 1: Add the NOTES label and replace AppButton**

Replace lines 402–412:
```html
<div
    class="border-surface-200 dark:border-surface-700 border-b p-3"
>
    <AppButton
        class="w-full"
        icon="pi pi-plus"
        label="Add Note"
        size="small"
        @click="addRootNote"
    />
</div>
```
With:
```html
<div
    class="border-surface-200 dark:border-surface-700 border-b p-3"
>
    <div class="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">Notes</div>
    <button
        class="w-full rounded-md bg-blue-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700"
        @click="addRootNote"
    >
        <i class="pi pi-plus mr-1.5 text-xs"></i>New Note
    </button>
</div>
```

- [ ] **Step 2: Verify visually**

Confirm the "NOTES" label appears above a solid blue full-width button. Click the button to confirm it still creates a note (`addRootNote` fires correctly).

- [ ] **Step 3: Commit**

```bash
git add ui/src/pages/notes.vue
git commit -m "style: add NOTES label and solid blue New Note button to sidebar"
```

---

### Task 3: Note list items — hover lift and padding

**Files:**
- Modify: `ui/src/pages/notes.vue:418,422`

- [ ] **Step 1: Update item padding and hover style**

On line 418, change `px-2 py-1.5` to `px-3 py-1.5`:
```html
class="group relative flex cursor-pointer items-center gap-1 rounded px-3 py-1.5 text-sm"
```

On line 422, replace the unselected branch:

Before:
```
: 'text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800'
```
After:
```
: 'text-surface-700 dark:text-surface-300 hover:bg-surface-0 hover:shadow-sm dark:hover:bg-slate-700'
```

- [ ] **Step 2: Verify visually**

Hover over unselected note items. Confirm they show a white card lift with subtle shadow in light mode, and a slate-700 fill in dark mode. Confirm selected item still shows primary blue highlight.

- [ ] **Step 3: Commit**

```bash
git add ui/src/pages/notes.vue
git commit -m "style: add card lift hover to sidebar note items"
```

---

### Task 4: Content area — warm background and title treatment

**Files:**
- Modify: `ui/src/pages/notes.vue:472,474-475`

- [ ] **Step 1: Add warm background to content wrapper**

On line 472, replace:
```html
<div v-else class="flex flex-1 flex-col overflow-y-auto p-6">
```
With:
```html
<div v-else class="bg-stone-50 dark:bg-stone-900 flex flex-1 flex-col overflow-y-auto px-7 pt-6 pb-4">
```

Note: `p-6` is replaced by `px-7 pt-6 pb-4` (more breathing room top, tighter bottom to flow into outline).

- [ ] **Step 2: Update title textarea classes**

On line 475, apply two changes: `mb-4` → `mb-2` and add `tracking-tight`.

Before:
```html
class="text-surface-900 dark:text-surface-100 mb-4 w-full resize-none border-none bg-transparent text-2xl leading-snug font-bold outline-none"
```
After:
```html
class="text-surface-900 dark:text-surface-100 mb-2 w-full resize-none border-none bg-transparent text-2xl leading-snug font-bold tracking-tight outline-none"
```

- [ ] **Step 3: Insert the blue accent bar after the title textarea**

After the closing `/>` of the textarea (after line 489), insert:
```html
<div class="mb-4 mt-1.5 h-0.5 w-9 rounded bg-blue-500"></div>
```

- [ ] **Step 4: Verify visually**

Confirm the content area has a warm off-white background, the title text is tighter, and a small blue bar appears beneath it. Check dark mode shows stone-900 background.

- [ ] **Step 5: Commit**

```bash
git add ui/src/pages/notes.vue
git commit -m "style: warm paper content area with title accent bar"
```

---

### Task 5: Outline rows — warm hover and guide line colors

**Files:**
- Modify: `ui/src/pages/notes.vue:496,506`

Note: title and outline are both direct children of the `px-7` wrapper changed in Task 4 — no separate container padding needed; they align automatically.

- [ ] **Step 1: Update outline row hover to warm tint**

On line 496, replace `hover:bg-surface-50 dark:hover:bg-surface-800` with `hover:bg-stone-100 dark:hover:bg-stone-800`:
```html
class="hover:bg-stone-100 dark:hover:bg-stone-800 group relative flex items-start gap-1 rounded py-0.5"
```

- [ ] **Step 2: Update indent guide colors to warm family**

On line 506, replace `bg-surface-200 dark:bg-surface-700` with `bg-stone-200 dark:bg-stone-700`:
```html
class="pointer-events-none absolute inset-y-0 w-px bg-stone-200 dark:bg-stone-700"
```

- [ ] **Step 3: Verify visually**

Hover over outline rows and confirm a warm stone tint appears. Confirm indent guide lines are still visible but feel warm rather than cool-gray.

- [ ] **Step 4: Run verify**

From `ui/`:
```bash
npm run verify
```
Expected: no errors (Prettier, ESLint, vue-tsc all pass).

- [ ] **Step 5: Commit**

```bash
git add ui/src/pages/notes.vue
git commit -m "style: warm stone tint for outline row hover and indent guides"
```

---

## Final Checklist

- [ ] Light mode: slate-100 sidebar, stone-50 content, blue accent bar under title, white card lift on hovered note items
- [ ] Dark mode: slate-800 sidebar, stone-900 content, all text readable, slate-700 lift on hovered items
- [ ] Selected note item still clearly highlighted with primary colors
- [ ] New Note button is solid blue, full-width, and functional
- [ ] Outline hover rows show warm stone tint
- [ ] Indent guides use stone-200 (light) / stone-700 (dark)
- [ ] `npm run verify` passes clean
