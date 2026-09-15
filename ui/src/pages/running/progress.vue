<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { useRunningApi } from '@/composables/api/useRunningApi';
import { useSettingsApi } from '@/composables/api/useSettingsApi';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { RunningActivity } from '@/types/Running';
import { registerCharts } from '@/utils/chart';
import { detailTableClass } from '@/utils/detailTable';
import { formatDate, formatDuration } from '@/utils/format';
import {
    fromIsoDate,
    startOfWeek,
    toIsoDate,
    weekDays,
    weekRange,
} from '@/utils/week';

registerCharts();

const { getActivities } = useRunningApi();
const { getSetting, setSetting } = useSettingsApi();
const toast = useToast();
const { distanceUnit, fmtDistance, fmtPace, toKm, fromKm } = useUnits();

const activities = ref<RunningActivity[]>([]);

const today = new Date();
const currentYear = today.getFullYear();

// --- Weekly Goal ---
const weeklyGoalKm = ref<number | null>(null);
const showGoalDialog = ref(false);
const goalFormValue = ref<number>(0);

const weeklyGoalProgress = computed(() => {
    if (!weeklyGoalKm.value || weeklyGoalKm.value <= 0) return null;
    const current = weekStats.value.distance;
    const pct = Math.min((current / weeklyGoalKm.value) * 100, 100);
    return {
        percentage: Math.round(pct),
        currentKm: current,
        goalKm: weeklyGoalKm.value,
    };
});

function openGoalDialog() {
    goalFormValue.value = parseFloat(
        fromKm(weeklyGoalKm.value ?? 0).toFixed(1),
    );
    showGoalDialog.value = true;
}

async function saveGoal() {
    const goalKm = goalFormValue.value > 0 ? toKm(goalFormValue.value) : 0;
    const res = await setSetting('running_weekly_goal_km', String(goalKm));
    if (res.success) {
        weeklyGoalKm.value = goalKm > 0 ? goalKm : null;
        toast.showSuccess('Weekly goal updated');
        showGoalDialog.value = false;
    } else {
        toast.showError(res.error?.message ?? 'Failed to save weekly goal');
    }
}

// --- Data loading ---
// This tab always reflects your whole running history — the Log tab's
// filters are for finding specific runs in the list, not for narrowing what
// the trend/summary views below show.
async function loadData() {
    const runsRes = await getActivities();
    if (runsRes.success && runsRes.data) {
        activities.value = runsRes.data;
    } else if (!runsRes.success) {
        toast.showError('Failed to load running activities');
    }
}

async function loadGoal() {
    const res = await getSetting('running_weekly_goal_km');
    if (res.success && res.data?.value) {
        const val = parseFloat(res.data.value);
        if (val > 0) weeklyGoalKm.value = val;
    }
}

onMounted(() => {
    void loadData();
    void loadGoal();
});

// --- Computed stats ---
const weekStats = computed(() => {
    const { start: monStr, end: sunStr } = weekRange();
    const weekRuns = activities.value.filter(
        (r) => r.date >= monStr && r.date <= sunStr,
    );
    return {
        distance: weekRuns.reduce((s, r) => s + r.distance_km, 0),
        count: weekRuns.length,
    };
});

const monthStats = computed(() => {
    const prefix = `${currentYear}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    const monthRuns = activities.value.filter((r) => r.date.startsWith(prefix));
    return {
        distance: monthRuns.reduce((s, r) => s + r.distance_km, 0),
        count: monthRuns.length,
    };
});

const yearStats = computed(() => {
    const yearPrefix = `${currentYear}-`;
    const yearRuns = activities.value.filter((r) =>
        r.date.startsWith(yearPrefix),
    );
    return {
        distance: yearRuns.reduce((s, r) => s + r.distance_km, 0),
        count: yearRuns.length,
    };
});

const allTimeBests = computed(() => {
    const runs = activities.value;
    if (runs.length === 0) {
        return { longest: null, totalDistanceKm: 0 };
    }
    const longest = runs.reduce((best, r) =>
        r.distance_km > best.distance_km ? r : best,
    );
    const totalDistanceKm = runs.reduce((s, r) => s + r.distance_km, 0);
    return { longest, totalDistanceKm };
});

// --- Distance-Bracket Personal Bests ---
const distanceBrackets = [
    { label: '1 km+', min: 1 },
    { label: '3 km+', min: 3 },
    { label: '5 km+', min: 5 },
    { label: '10 km+', min: 10 },
    { label: '15 km+', min: 15 },
    { label: 'Half', min: 21.1 },
];

const bracketPBs = computed(() =>
    distanceBrackets
        .map((bracket) => {
            const qualifying = activities.value.filter(
                (r) => r.distance_km >= bracket.min && r.pace > 0,
            );
            if (!qualifying.length) return null;
            const best = qualifying.reduce((a, c) => (a.pace < c.pace ? a : c));
            return { ...bracket, run: best };
        })
        .filter(
            (
                b,
            ): b is {
                label: string;
                min: number;
                run: RunningActivity;
            } => b !== null,
        ),
);

// --- Pace & Distance Over Time Chart ---
// Points sit on a numeric (real-time) x-axis rather than a category axis of
// formatted date labels — a category axis spaces entries evenly by count,
// which is wrong whenever runs aren't evenly spaced in time.
const chartData = computed(() => {
    const sorted = [...activities.value]
        .filter((r) => r.pace > 0)
        .sort((a, b) => a.date.localeCompare(b.date));
    const paceMultiplier = distanceUnit.value === 'mi' ? 1.60934 : 1;
    return {
        datasets: [
            {
                label: `Pace (min:sec/${distanceUnit.value})`,
                data: sorted.map((r) => ({
                    x: fromIsoDate(r.date).getTime(),
                    y: r.pace * paceMultiplier,
                })),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.3,
                yAxisID: 'y',
            },
            {
                label: `Distance (${distanceUnit.value})`,
                data: sorted.map((r) => ({
                    x: fromIsoDate(r.date).getTime(),
                    y: fromKm(r.distance_km),
                })),
                borderColor: '#f59e0b',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                fill: false,
                tension: 0.3,
                yAxisID: 'y1',
            },
        ],
    };
});

// Pace is stored/plotted as decimal minutes; show it as m:ss on the axis and
// in tooltips (5.75 → "5:45") — a decimal pace reads oddly for runners.
const fmtPaceValue = (minutes: number) => formatDuration(minutes * 60);

const chartOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: true },
        tooltip: {
            callbacks: {
                label: (ctx: {
                    dataset: { label?: string; yAxisID?: string };
                    parsed: { y: number };
                }) => {
                    const label = ctx.dataset.label ?? '';
                    const value =
                        ctx.dataset.yAxisID === 'y'
                            ? fmtPaceValue(ctx.parsed.y)
                            : String(Math.round(ctx.parsed.y * 100) / 100);
                    return `${label}: ${value}`;
                },
            },
        },
    },
    scales: {
        x: {
            type: 'linear' as const,
            ticks: {
                callback: (value: number) =>
                    formatDate(toIsoDate(new Date(value))),
            },
        },
        y: {
            reverse: true,
            position: 'left',
            title: {
                display: true,
                text: `Pace (min:sec/${distanceUnit.value})`,
            },
            ticks: {
                callback: (value: number) => fmtPaceValue(value),
            },
        },
        y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            title: { display: true, text: `Distance (${distanceUnit.value})` },
        },
    },
}));

// --- Pace × Distance (average pace bucketed into 1-unit distance bands) ---
type PaceViewMode = 'time' | 'distance';
const paceViewMode = ref<PaceViewMode>('time');
const paceViewOptions: { label: string; value: PaceViewMode }[] = [
    { label: 'Over Time', value: 'time' },
    { label: 'By Distance', value: 'distance' },
];

const paceChartTitle = computed(() =>
    paceViewMode.value === 'time'
        ? 'Pace & Distance Over Time'
        : 'Average Pace by Distance',
);

interface PaceDistanceBucket {
    label: string;
    bucketStart: number;
    avgPace: number;
    runs: number;
}

// Buckets are 1-unit wide in whatever unit is currently displayed (1-2 km,
// 2-3 km, … or 1-2 mi, 2-3 mi, …), keyed by the floor of each run's display
// distance — so switching units re-buckets rather than relabeling the same
// km-wide bands as miles. Only bands with at least one run are shown.
const paceByDistance = computed<PaceDistanceBucket[]>(() => {
    const buckets = new Map<number, RunningActivity[]>();
    for (const r of activities.value) {
        if (r.pace <= 0) continue;
        const bucketStart = Math.floor(fromKm(r.distance_km));
        const bucket = buckets.get(bucketStart);
        if (bucket) bucket.push(r);
        else buckets.set(bucketStart, [r]);
    }
    return [...buckets.entries()]
        .sort(([a], [b]) => a - b)
        .map(([bucketStart, runs]) => ({
            label: `${bucketStart}-${bucketStart + 1} ${distanceUnit.value}`,
            bucketStart,
            avgPace: runs.reduce((s, r) => s + r.pace, 0) / runs.length,
            runs: runs.length,
        }));
});

const distanceChartData = computed(() => {
    const paceMultiplier = distanceUnit.value === 'mi' ? 1.60934 : 1;
    const buckets = paceByDistance.value;
    return {
        labels: buckets.map((b) => b.label),
        datasets: [
            {
                label: `Avg pace (min:sec/${distanceUnit.value})`,
                data: buckets.map((b) => b.avgPace * paceMultiplier),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6,
            },
        ],
    };
});

const distanceChartOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
            callbacks: {
                label: (ctx: { parsed: { y: number }; dataIndex: number }) => {
                    const bucket = paceByDistance.value[ctx.dataIndex];
                    const runsLabel = bucket
                        ? `${bucket.runs} run${bucket.runs === 1 ? '' : 's'}`
                        : '';
                    return ` ${fmtPaceValue(ctx.parsed.y)} avg · ${runsLabel}`;
                },
            },
        },
    },
    scales: {
        x: {
            grid: { display: false },
            title: {
                display: true,
                text: `Distance (${distanceUnit.value})`,
            },
        },
        y: {
            // Pace never approaches 0 min/km, so starting the axis there
            // would squeeze the whole line into a sliver at the top — zoom
            // to the data's actual range instead (with a little breathing
            // room) so real differences between bands are visible.
            beginAtZero: false,
            grace: '10%',
            title: {
                display: true,
                text: `Avg Pace (min:sec/${distanceUnit.value})`,
            },
            ticks: { callback: (value: number) => fmtPaceValue(value) },
        },
    },
}));

const activeChartData = computed(() =>
    paceViewMode.value === 'time' ? chartData.value : distanceChartData.value,
);
const activeChartOptions = computed(() =>
    paceViewMode.value === 'time'
        ? chartOptions.value
        : distanceChartOptions.value,
);

// --- Weekly Progress -------------------------------------------------------
// Runs bucketed into Mon–Sun weeks. Interior weeks with no runs are kept as
// zero rows (a week off should show as a dip), and the current week is always
// included even before its first run.
interface WeekAgg {
    weekStart: string;
    label: string;
    totalKm: number;
    runs: number;
    longestKm: number;
    durationSec: number;
    cumulativeKm: number;
}

const round1 = (n: number) => Math.round(n * 10) / 10;

function weekLabel(iso: string): string {
    const d = fromIsoDate(iso);
    return `${d.getDate()} ${d.toLocaleDateString('en-US', { month: 'short' })}`;
}

const weeklyAgg = computed<WeekAgg[]>(() => {
    const runs = activities.value;
    if (runs.length === 0) return [];

    const byWeek = new Map<string, RunningActivity[]>();
    for (const r of runs) {
        const ws = toIsoDate(startOfWeek(fromIsoDate(r.date)));
        const bucket = byWeek.get(ws);
        if (bucket) bucket.push(r);
        else byWeek.set(ws, [r]);
    }

    const starts = [...byWeek.keys()].sort();
    const cursor = fromIsoDate(starts[0]!);
    const lastRunWeek = fromIsoDate(starts[starts.length - 1]!);
    const thisWeek = startOfWeek(new Date());
    const end = lastRunWeek > thisWeek ? lastRunWeek : thisWeek;

    const weeks: WeekAgg[] = [];
    let cumulativeKm = 0;
    while (cursor <= end) {
        const iso = toIsoDate(cursor);
        const wr = byWeek.get(iso) ?? [];
        const totalKm = wr.reduce((s, r) => s + r.distance_km, 0);
        cumulativeKm += totalKm;
        weeks.push({
            weekStart: iso,
            label: weekLabel(iso),
            totalKm,
            runs: wr.length,
            longestKm: wr.reduce((m, r) => Math.max(m, r.distance_km), 0),
            durationSec: wr.reduce((s, r) => s + r.duration_seconds, 0),
            cumulativeKm,
        });
        cursor.setDate(cursor.getDate() + 7);
    }
    return weeks;
});

const weeklyRows = computed(() => [...weeklyAgg.value].reverse());

function weekAvgPace(w: WeekAgg): string {
    if (w.totalKm <= 0 || w.durationSec <= 0) return '—';
    return fmtPace(w.durationSec / 60 / w.totalKm);
}

// Toggle between the aggregate list above and a spreadsheet-style grid —
// one row per week, one column per day, total at the end of the row —
// which is the layout the Steve2026 training sheet used.
type WeeklyTableView = 'list' | 'calendar';
const weeklyTableView = ref<WeeklyTableView>('list');
const weeklyTableViewOptions: { label: string; value: WeeklyTableView }[] = [
    { label: 'List', value: 'list' },
    { label: 'Calendar', value: 'calendar' },
];

const WEEKDAY_SHORT_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const todayIso = toIsoDate(today);

interface WeekGridDay {
    date: string;
    distanceKm: number;
    runs: number;
}

interface WeekGridRow {
    weekStart: string;
    label: string;
    days: WeekGridDay[];
    totalKm: number;
}

const weeklyGridRows = computed<WeekGridRow[]>(() => {
    const byDate = new Map<string, RunningActivity[]>();
    for (const r of activities.value) {
        const bucket = byDate.get(r.date);
        if (bucket) bucket.push(r);
        else byDate.set(r.date, [r]);
    }
    return [...weeklyAgg.value].reverse().map((week) => ({
        weekStart: week.weekStart,
        label: week.label,
        totalKm: week.totalKm,
        days: weekDays(fromIsoDate(week.weekStart)).map((date) => {
            const dayRuns = byDate.get(date) ?? [];
            return {
                date,
                distanceKm: dayRuns.reduce((s, r) => s + r.distance_km, 0),
                runs: dayRuns.length,
            };
        }),
    }));
});

type WeeklyView = 'volume' | 'cumulative' | 'longRun';
const weeklyView = ref<WeeklyView>('volume');
const weeklyViewOptions: { label: string; value: WeeklyView }[] = [
    { label: 'Weekly', value: 'volume' },
    { label: 'Cumulative', value: 'cumulative' },
    { label: 'Long run', value: 'longRun' },
];

const weeklyGoalDisplay = computed(() =>
    weeklyGoalKm.value ? round1(fromKm(weeklyGoalKm.value)) : null,
);

const weeklyChartData = computed(() => {
    const weeks = weeklyAgg.value;
    const labels = weeks.map((w) => w.label);

    if (weeklyView.value === 'cumulative') {
        return {
            labels,
            datasets: [
                {
                    type: 'line',
                    label: `Cumulative (${distanceUnit.value})`,
                    data: weeks.map((w) => round1(fromKm(w.cumulativeKm))),
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.12)',
                    fill: true,
                    tension: 0.25,
                },
            ],
        };
    }

    if (weeklyView.value === 'longRun') {
        return {
            labels,
            datasets: [
                {
                    type: 'line',
                    label: `Longest run (${distanceUnit.value})`,
                    data: weeks.map((w) =>
                        w.longestKm > 0 ? round1(fromKm(w.longestKm)) : null,
                    ),
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.12)',
                    fill: true,
                    tension: 0.3,
                    spanGaps: true,
                },
            ],
        };
    }

    const datasets: Record<string, unknown>[] = [
        {
            type: 'bar',
            label: `Distance (${distanceUnit.value})`,
            data: weeks.map((w) => round1(fromKm(w.totalKm))),
            backgroundColor: 'rgba(34, 197, 94, 0.55)',
            borderColor: '#22c55e',
            borderWidth: 1,
            borderRadius: 3,
        },
    ];
    const goal = weeklyGoalDisplay.value;
    if (goal != null) {
        datasets.push({
            type: 'line',
            label: `Goal (${goal} ${distanceUnit.value})`,
            data: labels.map(() => goal),
            borderColor: '#9ca3af',
            borderDash: [5, 4],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
        });
    }
    return { labels, datasets };
});

const weeklyChartOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display:
                weeklyView.value === 'volume' &&
                weeklyGoalDisplay.value != null,
        },
        tooltip: {
            callbacks: {
                label: (ctx: {
                    dataset: { label?: string };
                    parsed: { y: number | null };
                }) =>
                    `${ctx.dataset.label}: ${
                        ctx.parsed.y == null
                            ? '—'
                            : `${ctx.parsed.y} ${distanceUnit.value}`
                    }`,
            },
        },
    },
    scales: {
        x: { grid: { display: false } },
        y: {
            beginAtZero: weeklyView.value !== 'longRun',
            title: { display: true, text: `Distance (${distanceUnit.value})` },
            ticks: {
                callback: (value: number) => `${value} ${distanceUnit.value}`,
            },
        },
    },
}));
</script>

<template>
    <div>
        <h1 class="mb-6 text-2xl font-bold">Running</h1>

        <!-- Stats Cards -->
        <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <AppCard>
                <template #title>
                    <div class="flex items-center justify-between">
                        <span>This Week</span>
                        <AppButton
                            aria-label="Set weekly goal"
                            icon="pi pi-cog"
                            rounded
                            severity="secondary"
                            size="small"
                            text
                            title="Set weekly goal"
                            @click="openGoalDialog"
                        />
                    </div>
                </template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ fmtDistance(weekStats.distance) }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ weekStats.count }}
                        {{ weekStats.count === 1 ? 'run' : 'runs' }}
                    </div>
                    <div v-if="weeklyGoalProgress" class="mt-2">
                        <div class="text-surface-500 mb-1 text-xs">
                            {{ fmtDistance(weeklyGoalProgress.currentKm) }} /
                            {{ fmtDistance(weeklyGoalProgress.goalKm) }}
                        </div>
                        <div
                            class="bg-surface-200 dark:bg-surface-700 h-2 w-full overflow-hidden rounded-full"
                        >
                            <div
                                class="h-full rounded-full transition-all"
                                :class="
                                    weeklyGoalProgress.percentage >= 100
                                        ? 'bg-green-500'
                                        : 'bg-blue-500'
                                "
                                :style="{
                                    width: `${weeklyGoalProgress.percentage}%`,
                                }"
                            ></div>
                        </div>
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>This Month</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ fmtDistance(monthStats.distance) }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ monthStats.count }}
                        {{ monthStats.count === 1 ? 'run' : 'runs' }}
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>This Year</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ fmtDistance(yearStats.distance) }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ yearStats.count }}
                        {{ yearStats.count === 1 ? 'run' : 'runs' }}
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>All Time</template>
                <template #content>
                    <div class="space-y-1">
                        <div>
                            <span class="text-surface-500 text-sm">
                                Longest:
                            </span>
                            <span class="font-semibold">
                                {{
                                    allTimeBests.longest
                                        ? fmtDistance(
                                              allTimeBests.longest.distance_km,
                                          )
                                        : '—'
                                }}
                            </span>
                        </div>
                        <div>
                            <span class="text-surface-500 text-sm">
                                Total:
                            </span>
                            <span class="font-semibold">
                                {{ fmtDistance(allTimeBests.totalDistanceKm) }}
                            </span>
                        </div>
                    </div>
                </template>
            </AppCard>
        </div>

        <!-- Distance-Bracket Personal Bests -->
        <div v-if="bracketPBs.length" class="mb-6">
            <h2 class="mb-3 text-xl font-semibold">Fastest Pace by Distance</h2>
            <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <div
                    v-for="pb in bracketPBs"
                    :key="pb.label"
                    class="border-surface-200 dark:border-surface-700 rounded-lg border p-3 text-center"
                >
                    <div class="text-surface-500 mb-1 text-sm font-medium">
                        {{ pb.label }}
                    </div>
                    <div class="text-xl font-bold">
                        {{ fmtPace(pb.run.pace) }}
                    </div>
                    <div class="text-surface-400 mt-1 text-xs">
                        {{ fmtDistance(pb.run.distance_km) }} &middot;
                        {{ formatDate(pb.run.date) }}
                    </div>
                </div>
            </div>
        </div>

        <!-- Pace & Distance Chart -->
        <div v-if="activities.length > 1" class="mb-6">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h2 class="text-xl font-semibold">{{ paceChartTitle }}</h2>
                <AppSelectButton
                    v-model="paceViewMode"
                    :allow-empty="false"
                    option-label="label"
                    option-value="value"
                    :options="paceViewOptions"
                    size="small"
                />
            </div>
            <div class="h-64">
                <AppChart
                    :data="activeChartData"
                    :options="activeChartOptions"
                    type="line"
                />
            </div>
        </div>

        <!-- Weekly Progress -->
        <div v-if="weeklyAgg.length > 0" class="mb-8">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h2 class="text-xl font-semibold">Weekly Progress</h2>
                <AppSelectButton
                    v-model="weeklyView"
                    :allow-empty="false"
                    option-label="label"
                    option-value="value"
                    :options="weeklyViewOptions"
                    size="small"
                />
            </div>
            <div class="h-64">
                <AppChart
                    :data="weeklyChartData"
                    :options="weeklyChartOptions"
                    type="bar"
                />
            </div>

            <div class="mt-4 mb-2 flex justify-end">
                <AppSelectButton
                    v-model="weeklyTableView"
                    :allow-empty="false"
                    option-label="label"
                    option-value="value"
                    :options="weeklyTableViewOptions"
                    size="small"
                />
            </div>

            <div
                v-if="weeklyTableView === 'list'"
                class="max-h-80 overflow-auto"
            >
                <table :class="detailTableClass">
                    <thead>
                        <tr>
                            <th>Week of</th>
                            <th>Distance</th>
                            <th>Runs</th>
                            <th>Longest</th>
                            <th>Time</th>
                            <th>Avg pace</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="w in weeklyRows" :key="w.weekStart">
                            <td>{{ w.label }}</td>
                            <td>
                                {{ round1(fromKm(w.totalKm)) }}
                                {{ distanceUnit }}
                            </td>
                            <td>{{ w.runs }}</td>
                            <td>
                                {{
                                    w.longestKm > 0
                                        ? `${round1(fromKm(w.longestKm))} ${distanceUnit}`
                                        : '—'
                                }}
                            </td>
                            <td>
                                {{
                                    w.durationSec > 0
                                        ? formatDuration(w.durationSec)
                                        : '—'
                                }}
                            </td>
                            <td>{{ weekAvgPace(w) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Calendar view: one row per week, one column per day, weekly
                 total at the end of the row — the shape of the old training
                 spreadsheet. -->
            <div v-else class="max-h-96 overflow-auto">
                <table :class="detailTableClass">
                    <thead>
                        <tr>
                            <th>Week of</th>
                            <th
                                v-for="d in WEEKDAY_SHORT_LABELS"
                                :key="d"
                                class="text-center"
                            >
                                {{ d }}
                            </th>
                            <th class="text-right">
                                Total ({{ distanceUnit }})
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="week in weeklyGridRows"
                            :key="week.weekStart"
                        >
                            <td>{{ week.label }}</td>
                            <td
                                v-for="day in week.days"
                                :key="day.date"
                                class="text-center"
                                :class="{
                                    'bg-primary-50 dark:bg-primary-950':
                                        day.date === todayIso,
                                }"
                            >
                                <template v-if="day.distanceKm > 0">
                                    {{ round1(fromKm(day.distanceKm)) }}
                                    <span
                                        v-if="day.runs > 1"
                                        class="text-surface-400 text-xs"
                                        >×{{ day.runs }}</span
                                    >
                                </template>
                                <span v-else class="text-surface-400">—</span>
                            </td>
                            <td class="text-right font-semibold">
                                {{
                                    week.totalKm > 0
                                        ? round1(fromKm(week.totalKm))
                                        : '—'
                                }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Weekly Goal Dialog -->
        <AppDialog
            v-model:visible="showGoalDialog"
            header="Weekly Distance Goal"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Goal ({{ distanceUnit }} per week)
                    </label>
                    <AppInputNumber
                        v-model="goalFormValue"
                        class="w-full"
                        :max-fraction-digits="1"
                        :min="0"
                        :step="distanceUnit === 'mi' ? 3 : 5"
                        :suffix="' ' + distanceUnit"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showGoalDialog = false"
                    />
                    <AppButton label="Save" @click="saveGoal" />
                </div>
            </div>
        </AppDialog>
    </div>
</template>
