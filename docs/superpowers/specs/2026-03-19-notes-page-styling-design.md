# Notes Page Styling

**Date:** 2026-03-19
**Status:** Approved
**Scope:** `ui/src/pages/notes.vue` — template changes only, no script/logic changes

---

## Goal

Visually polish the Notes page. The left sidebar should feel like a structured app panel; the content area should feel like a warm writing canvas.

---

## Dark Mode Note

The project uses class-based dark mode (`@custom-variant dark (&:where(.dark, .dark *))` in `style.css`). All `dark:` prefixes rely on a `.dark` class on an ancestor element — they work identically to existing dark variants throughout the template.

---

## Left Sidebar Changes

The sidebar is the outer `<div>` at line 399:
```html
<div class="border-surface-200 dark:border-surface-700 flex w-64 shrink-0 flex-col border-r">
```

**1. Add background color** (new addition — no existing background class to replace):
```html
<div class="bg-slate-100 dark:bg-slate-800 border-surface-200 dark:border-surface-700 flex w-64 shrink-0 flex-col border-r">
```

**2. Add "NOTES" section label** — insert a new `<div>` as the first child inside the header `<div>` at line 402, before the `<AppButton>`:
```html
<div class="border-surface-200 dark:border-surface-700 border-b p-3">
    <div class="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">Notes</div>
    <AppButton ... />
</div>
```

**3. Replace AppButton with a styled native button** — the current `<AppButton>` renders as a PrimeVue component that doesn't easily accept arbitrary Tailwind background overrides. Replace it with:
```html
<button
    class="w-full rounded-md bg-blue-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700"
    @click="addRootNote"
>
    <i class="pi pi-plus mr-1.5 text-xs"></i>New Note
</button>
```

**4. Update hovered note item** — in the `:class` ternary at line 422, replace the unselected branch:

Before:
```
'text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800'
```

After:
```
'text-surface-700 dark:text-surface-300 hover:bg-surface-0 hover:shadow-sm dark:hover:bg-slate-700'
```

- `hover:bg-surface-0` uses the existing semantic token (resolves to white in light mode) for the card-lift effect — consistent with the project's `surface-*` convention
- `hover:shadow-sm` adds the subtle card elevation
- `dark:hover:bg-slate-700` uses a literal slate value because `surface-800` is too dark against the `slate-800` sidebar background; this intentional mixing is documented here

**5. Increase note item horizontal padding** — on the note item `<div>` at line 418:

Before: `px-2 py-1.5`
After: `px-3 py-1.5`

---

## Right Content Area Changes

**6. Add warm background to the outer content wrapper** (the `<div class="flex-1 ...">` that wraps the title + outline when a note is selected):

Add `bg-stone-50 dark:bg-stone-900` to that container.

**7. Title treatment** — find the title `<div>` (currently `text-2xl font-bold leading-snug`):

- Add `tracking-tight` to the title itself
- Add a blue accent bar immediately after the title text:
```html
<div class="mt-1.5 h-0.5 w-9 rounded bg-blue-500"></div>
```

**8. Adjust title section padding** — change the title section wrapper from `p-6` to `px-7 pt-6 pb-4` so the title has more vertical breathing room and aligns with the outline content.

**9. Align outline container padding** — change the outline container's left padding to `px-7` to align with the title.

**10. Warm outline row hover** — update the outline row hover class from `hover:bg-surface-50` to `hover:bg-stone-100 dark:hover:bg-stone-800`.

**11. Indent guide lines** — update guide line colors from `bg-surface-200 dark:bg-surface-700` to `bg-stone-200 dark:bg-stone-700` to stay in the warm family.

---

## What Is Not Changing

- Selected note item state (`bg-primary-100`, `text-primary-700`, etc.)
- Delete button visibility/hover behavior
- All script, composable, and API logic
- Sidebar width (`w-64`)
- Outline structure, collapse toggles, and indent logic

---

## Files Affected

- `ui/src/pages/notes.vue` — template only

---

## Verification

1. `npm run verify` passes (no lint/type/format errors)
2. **Light mode:** slate-100 sidebar, warm stone-50 content, blue accent bar under title, white card lift on hovered note items
3. **Dark mode:** slate-800 sidebar, stone-900 content, all text readable, hovered note item shows slate-700 lift
4. Selected note item still clearly highlighted with primary colors
5. New Note button is solid blue and full-width
6. Outline hover rows show warm stone tint
7. Indent guide lines use stone-200 (light) / stone-700 (dark)
