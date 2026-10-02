<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useUnits } from '@/composables/useUnits';
import type { RunningActivity } from '@/types/Running';
import type { PlannedDay } from '@/utils/plan';
import {
    mondayIndex,
    startOfWeek,
    toIsoDate,
    WEEKDAY_LABELS,
} from '@/utils/week';

// A browsable month grid of actual runs alongside the training plan — what
// you ran next to what the plan said, on the same day — with a Mon–Sun total
// at the end of each row (the layout the Steve2026 training sheet used).
const props = defineProps<{
    activities: RunningActivity[];
    plan: Map<string, PlannedDay>;
}>();
// A planned day with nothing logged yet asks the parent to log it, pre-dated.
const emit = defineEmits<{ addRun: [date: string] }>();

const router = useRouter();
const { fmtDistance } = useUnits();

const today = new Date();
const todayIso = toIsoDate(today);

const calendarYear = ref(today.getFullYear());
const calendarMonth = ref(today.getMonth()); // 0-indexed

function prevMonth() {
    if (calendarMonth.value === 0) {
        calendarMonth.value = 11;
        calendarYear.value -= 1;
    } else {
        calendarMonth.value -= 1;
    }
}

function nextMonth() {
    if (calendarMonth.value === 11) {
        calendarMonth.value = 0;
        calendarYear.value += 1;
    } else {
        calendarMonth.value += 1;
    }
}

function goToCurrentMonth() {
    calendarYear.value = today.getFullYear();
    calendarMonth.value = today.getMonth();
}

const isCurrentMonth = computed(
    () =>
        calendarYear.value === today.getFullYear() &&
        calendarMonth.value === today.getMonth(),
);

const monthLabel = computed(() =>
    new Date(calendarYear.value, calendarMonth.value, 1).toLocaleDateString(
        'en-US',
        { month: 'long', year: 'numeric' },
    ),
);

const runsByDate = computed(() => {
    const map = new Map<string, RunningActivity[]>();
    for (const r of props.activities) {
        const bucket = map.get(r.date);
        if (bucket) bucket.push(r);
        else map.set(r.date, [r]);
    }
    return map;
});

/** Planned km still counting toward a week's total: only today-or-later days
 *  with nothing logged yet (a logged run counts with its actual distance; a
 *  past planned day never run is a miss, not volume). */
function remainingPlannedKm(date: string): number {
    if (date < todayIso || runsByDate.value.has(date)) return 0;
    return props.plan.get(date)?.km ?? 0;
}

interface DayInfo {
    date: string;
    actualKm: number;
    runCount: number;
    singleRunId: number | null;
    planned: PlannedDay | null;
}

function dayInfo(day: Date): DayInfo {
    const date = toIsoDate(day);
    const runs = runsByDate.value.get(date) ?? [];
    return {
        date,
        actualKm: runs.reduce((s, r) => s + r.distance_km, 0),
        runCount: runs.length,
        singleRunId: runs.length === 1 ? runs[0]!.id : null,
        planned: props.plan.get(date) ?? null,
    };
}

// A single logged run: go look at it. A planned day with nothing logged yet:
// log it. A day with neither, or several runs (which to open?), does nothing.
function isClickable(info: DayInfo): boolean {
    return !!info.singleRunId || (!!info.planned && info.runCount === 0);
}

function onDayClick(info: DayInfo) {
    if (info.singleRunId) {
        void router.push(`/running/${info.singleRunId}`);
    } else if (info.planned && info.runCount === 0) {
        emit('addRun', info.date);
    }
}

interface Cell {
    day: Date | null;
    info: DayInfo | null;
}

interface CalendarWeek {
    weekStart: string;
    cells: Cell[];
    /** Whole Mon–Sun week, including days in the neighbouring month: actual
     *  km where run, planned km where still to come. */
    totalKm: number;
    actualKm: number;
}

const weeks = computed<CalendarWeek[]>(() => {
    const firstDay = new Date(calendarYear.value, calendarMonth.value, 1);
    const lastDay = new Date(calendarYear.value, calendarMonth.value + 1, 0);
    const cells: Cell[] = [];
    for (let i = 0; i < mondayIndex(firstDay); i++) {
        cells.push({ day: null, info: null });
    }
    for (let d = 1; d <= lastDay.getDate(); d++) {
        const day = new Date(calendarYear.value, calendarMonth.value, d);
        cells.push({ day, info: dayInfo(day) });
    }
    while (cells.length % 7 !== 0) cells.push({ day: null, info: null });

    const result: CalendarWeek[] = [];
    for (let i = 0; i < cells.length; i += 7) {
        const row = cells.slice(i, i + 7);
        const start = startOfWeek(row.find((c) => c.day)!.day!);
        let totalKm = 0;
        let actualKm = 0;
        for (let d = 0; d < 7; d++) {
            const date = new Date(start);
            date.setDate(start.getDate() + d);
            const iso = toIsoDate(date);
            const runKm = (runsByDate.value.get(iso) ?? []).reduce(
                (s, r) => s + r.distance_km,
                0,
            );
            actualKm += runKm;
            totalKm += runKm > 0 ? runKm : remainingPlannedKm(iso);
        }
        result.push({
            weekStart: toIsoDate(start),
            cells: row,
            totalKm,
            actualKm,
        });
    }
    return result;
});
</script>

<template>
    <div>
        <div class="mb-3 flex items-center justify-between">
            <AppButton
                aria-label="Previous month"
                icon="pi pi-chevron-left"
                rounded
                severity="secondary"
                text
                @click="prevMonth"
            />
            <button
                class="text-surface-700 dark:text-surface-300 hover:text-primary-600 dark:hover:text-primary-400 text-sm font-medium"
                :disabled="isCurrentMonth"
                type="button"
                @click="goToCurrentMonth"
            >
                {{ monthLabel }}
            </button>
            <AppButton
                aria-label="Next month"
                icon="pi pi-chevron-right"
                rounded
                severity="secondary"
                text
                @click="nextMonth"
            />
        </div>
        <div
            class="grid grid-cols-[repeat(7,minmax(0,1fr))_minmax(3.5rem,0.8fr)] gap-1"
        >
            <div
                v-for="dayName in WEEKDAY_LABELS"
                :key="dayName"
                class="text-surface-500 py-1 text-center text-xs font-medium"
            >
                {{ dayName }}
            </div>
            <div class="text-surface-500 py-1 text-center text-xs font-medium">
                Week
            </div>
            <template v-for="week in weeks" :key="week.weekStart">
                <div
                    v-for="(cell, idx) in week.cells"
                    :key="`${week.weekStart}-${idx}`"
                    class="border-surface-100 dark:border-surface-800 min-h-[4.5rem] rounded border p-1"
                    :class="{
                        'bg-primary-50 dark:bg-primary-950':
                            cell.info && cell.info.date === todayIso,
                        'cursor-pointer': cell.info && isClickable(cell.info),
                    }"
                    @click="cell.info && onDayClick(cell.info)"
                >
                    <template v-if="cell.day && cell.info">
                        <div class="text-xs font-medium">
                            {{ cell.day.getDate() }}
                        </div>
                        <div class="mt-1 flex flex-col gap-0.5">
                            <div
                                v-if="cell.info.runCount > 0"
                                v-tooltip="
                                    cell.info.runCount > 1
                                        ? `${cell.info.runCount} runs`
                                        : undefined
                                "
                                class="rounded bg-blue-500 px-1 py-0.5 text-center text-[11px] font-medium text-white"
                            >
                                {{ fmtDistance(cell.info.actualKm) }}
                                <span v-if="cell.info.runCount > 1"
                                    >×{{ cell.info.runCount }}</span
                                >
                            </div>
                            <div
                                v-if="cell.info.planned"
                                v-tooltip="cell.info.planned.title"
                                class="rounded border border-dashed px-1 py-0.5 text-center text-[11px]"
                                :class="
                                    cell.info.planned.isRace
                                        ? 'border-orange-500 text-orange-600 dark:text-orange-400'
                                        : 'border-surface-300 text-surface-500 dark:border-surface-600'
                                "
                            >
                                {{
                                    cell.info.planned.km != null
                                        ? fmtDistance(cell.info.planned.km)
                                        : 'Planned'
                                }}
                            </div>
                        </div>
                    </template>
                </div>
                <!-- Mon–Sun total: actual km where run, planned km for days
                     still to come. -->
                <div
                    v-tooltip="
                        week.actualKm > 0 && week.totalKm > week.actualKm
                            ? `${fmtDistance(week.actualKm)} run + ${fmtDistance(week.totalKm - week.actualKm)} planned`
                            : undefined
                    "
                    class="bg-surface-50 dark:bg-surface-900 flex min-h-[4.5rem] flex-col items-center justify-center rounded p-1 text-center"
                >
                    <template v-if="week.totalKm > 0">
                        <span
                            class="text-sm font-semibold"
                            :class="{ 'text-surface-500': week.actualKm === 0 }"
                        >
                            {{ fmtDistance(week.totalKm) }}
                        </span>
                        <span
                            v-if="
                                week.actualKm > 0 &&
                                week.totalKm > week.actualKm
                            "
                            class="text-surface-500 text-[11px]"
                        >
                            {{ fmtDistance(week.actualKm) }} done
                        </span>
                    </template>
                    <span v-else class="text-surface-400 text-xs">—</span>
                </div>
            </template>
        </div>
        <!-- Legend -->
        <div class="text-surface-500 mt-3 flex gap-4 text-xs">
            <div class="flex items-center gap-1.5">
                <span
                    class="inline-block h-2.5 w-2.5 rounded-sm bg-blue-500"
                ></span>
                Actual run
            </div>
            <div class="flex items-center gap-1.5">
                <span
                    class="border-surface-400 inline-block h-2.5 w-2.5 rounded-sm border border-dashed"
                ></span>
                Planned
            </div>
            <div class="flex items-center gap-1.5">
                <span
                    class="inline-block h-2.5 w-2.5 rounded-sm border border-dashed border-orange-500"
                ></span>
                Planned race
            </div>
        </div>
    </div>
</template>
