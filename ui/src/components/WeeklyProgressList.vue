<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import { useUnits } from '@/composables/useUnits';
import type { RunningActivity } from '@/types/Running';
import { detailTableClass } from '@/utils/detailTable';
import { formatDuration } from '@/utils/format';
import type { WeekPlan } from '@/utils/plan';
import { fromIsoDate, startOfWeek, toIsoDate } from '@/utils/week';

// Week-by-week running, planned vs actual: every Mon–Sun week from the first
// run to the end of the training plan, newest first. Interior weeks with no
// runs stay as rows (a week off still shows), and weeks still ahead show what
// the plan asks for.
const props = defineProps<{
    activities: RunningActivity[];
    weekPlan: Map<string, WeekPlan>;
}>();

const { distanceUnit, fmtPace, fromKm } = useUnits();

interface WeekRow {
    weekStart: string;
    totalKm: number;
    runs: number;
    longestKm: number;
    durationSec: number;
    plannedKm: number;
    plannedRuns: number;
    isCurrent: boolean;
    started: boolean;
}

const today = new Date();
const currentWeekStart = toIsoDate(startOfWeek(today));

const rows = computed<WeekRow[]>(() => {
    const byWeek = new Map<string, RunningActivity[]>();
    for (const r of props.activities) {
        const ws = toIsoDate(startOfWeek(fromIsoDate(r.date)));
        const bucket = byWeek.get(ws);
        if (bucket) bucket.push(r);
        else byWeek.set(ws, [r]);
    }
    const starts = [...byWeek.keys(), ...props.weekPlan.keys()].sort();
    if (starts.length === 0) return [];
    const first = starts[0]!;
    const last = [starts[starts.length - 1]!, currentWeekStart].sort()[1]!;

    const result: WeekRow[] = [];
    const cursor = fromIsoDate(first);
    while (toIsoDate(cursor) <= last) {
        const iso = toIsoDate(cursor);
        const wr = byWeek.get(iso) ?? [];
        const plan = props.weekPlan.get(iso);
        result.push({
            weekStart: iso,
            totalKm: wr.reduce((s, r) => s + r.distance_km, 0),
            runs: wr.length,
            longestKm: wr.reduce((m, r) => Math.max(m, r.distance_km), 0),
            durationSec: wr.reduce((s, r) => s + r.duration_seconds, 0),
            plannedKm: plan?.km ?? 0,
            plannedRuns: plan?.runs ?? 0,
            isCurrent: iso === currentWeekStart,
            started: iso <= currentWeekStart,
        });
        cursor.setDate(cursor.getDate() + 7);
    }
    return result.reverse();
});

const round1 = (n: number) => Math.round(n * 10) / 10;
const km = (n: number) => `${round1(fromKm(n))} ${distanceUnit.value}`;

// "5 Oct", plus the year outside the current one ("27 Sep 2027") since the
// plan runs into next year.
function weekLabel(iso: string): string {
    const d = fromIsoDate(iso);
    const label = `${d.getDate()} ${d.toLocaleDateString('en-US', { month: 'short' })}`;
    return d.getFullYear() === today.getFullYear()
        ? label
        : `${label} ${d.getFullYear()}`;
}

function avgPace(w: WeekRow): string {
    if (w.totalKm <= 0 || w.durationSec <= 0) return '—';
    return fmtPace(w.durationSec / 60 / w.totalKm);
}

/** Share of the week's planned distance actually run, once the week has begun. */
function planPercent(w: WeekRow): number | null {
    if (!w.started || w.plannedKm <= 0) return null;
    return Math.round((w.totalKm / w.plannedKm) * 100);
}

// Newest-first puts the whole remaining plan above today, so bring the
// current week into view whenever the rows change.
const listEl = ref<HTMLElement | null>(null);
watch(
    () => rows.value.length,
    () =>
        void nextTick(() => {
            const row = listEl.value?.querySelector<HTMLElement>(
                '[data-current-week]',
            );
            if (listEl.value && row) {
                listEl.value.scrollTop = Math.max(0, row.offsetTop - 40);
            }
        }),
    { immediate: true },
);
</script>

<template>
    <div ref="listEl" class="relative max-h-80 overflow-auto">
        <!-- Header stays put while the weeks scroll. With collapsed borders a
             sticky cell's border scrolls away, so the divider is redrawn as
             an inset shadow. -->
        <table
            :class="[
                detailTableClass,
                '[&_th]:bg-surface-0 dark:[&_th]:bg-surface-900 [&_th]:sticky [&_th]:top-0 [&_th]:z-10 [&_th]:shadow-[inset_0_-1px_0_var(--p-surface-200)] dark:[&_th]:shadow-[inset_0_-1px_0_var(--p-surface-700)]',
            ]"
        >
            <thead>
                <tr>
                    <th>Week of</th>
                    <th>Distance</th>
                    <th>Plan</th>
                    <th>Runs</th>
                    <th>Longest</th>
                    <th>Time</th>
                    <th>Avg pace</th>
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="w in rows"
                    :key="w.weekStart"
                    :class="{
                        'bg-primary-50 dark:bg-primary-950': w.isCurrent,
                        'text-surface-500': !w.started,
                    }"
                    :data-current-week="w.isCurrent || undefined"
                >
                    <td>
                        {{ weekLabel(w.weekStart) }}
                        <span
                            v-if="!w.started && w.plannedRuns > 0"
                            class="border-surface-300 dark:border-surface-600 ml-1 rounded border border-dashed px-1 text-[11px]"
                            >Planned</span
                        >
                    </td>
                    <td>{{ w.started ? km(w.totalKm) : '—' }}</td>
                    <td>
                        <template v-if="w.plannedKm > 0">
                            {{ km(w.plannedKm) }}
                            <span
                                v-if="planPercent(w) != null"
                                class="ml-1 text-xs"
                                :class="
                                    planPercent(w)! >= 100
                                        ? 'font-medium text-green-600 dark:text-green-400'
                                        : 'text-surface-500'
                                "
                            >
                                {{ planPercent(w) }}%
                            </span>
                        </template>
                        <span v-else class="text-surface-400">—</span>
                    </td>
                    <td>
                        {{ w.started ? w.runs : 0 }}
                        <span
                            v-if="w.plannedRuns > 0"
                            class="text-surface-500 text-xs"
                        >
                            / {{ w.plannedRuns }}
                        </span>
                    </td>
                    <td>{{ w.longestKm > 0 ? km(w.longestKm) : '—' }}</td>
                    <td>
                        {{
                            w.durationSec > 0
                                ? formatDuration(w.durationSec)
                                : '—'
                        }}
                    </td>
                    <td>{{ avgPace(w) }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>
