// Shared styling for the plain data tables on detail pages (running laps/best
// efforts, routine exercises/session history). Centralized so both pages stay
// in sync and so this is expressed as Tailwind utilities (matching the app's
// `border-surface-200 dark:border-surface-700` convention) instead of a
// hand-rolled <style> block duplicated per page.
export const detailTableClass =
    'w-full border-collapse text-sm ' +
    '[&_th]:border-b [&_th]:border-surface-200 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:font-semibold dark:[&_th]:border-surface-700 ' +
    '[&_td]:border-b [&_td]:border-surface-100 [&_td]:px-3 [&_td]:py-2 [&_td]:whitespace-nowrap dark:[&_td]:border-surface-800';

// Additional row-hover affordance for tables whose rows highlight something
// elsewhere on the page (running's laps/best-efforts hover the map/charts).
export const detailTableHoverRowClass =
    '[&_tbody_tr]:cursor-default [&_tbody_tr]:transition-colors [&_tbody_tr:hover]:bg-amber-500/10';
