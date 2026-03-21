<script setup lang="ts">
import {
    CategoryScale,
    Chart,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    Title,
    Tooltip,
} from 'chart.js';
import { computed, onMounted, reactive, ref } from 'vue';

import { useRunningApi } from '@/composables/api/useRunningApi';
import { useSettingsApi } from '@/composables/api/useSettingsApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { GpxSegment, RunningActivity } from '@/types/Running';
import { formatDate } from '@/utils/format';

Chart.register(
    CategoryScale,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    Title,
    Tooltip,
);

const {
    getActivities,
    createActivity,
    updateActivity,
    deleteActivity,
    importGpx,
    getSegments,
} = useRunningApi();
const { getSetting, setSetting } = useSettingsApi();
const { loading, withLoading } = useLoading();
const toast = useToast();
const { distanceUnit, fmtDistance, fmtPace, toKm, fromKm } = useUnits();

const activities = ref<RunningActivity[]>([]);

const today = new Date();
const currentYear = today.getFullYear();

// --- Filters ---
const filters = reactive({
    dateFrom: '',
    dateTo: '',
    distanceMin: null as number | null,
    distanceMax: null as number | null,
    durationMin: null as number | null,
    durationMax: null as number | null,
    paceMin: null as number | null,
    paceMax: null as number | null,
});

const hasActiveFilters = computed(() =>
    Boolean(
        filters.dateFrom ||
        filters.dateTo ||
        filters.distanceMin !== null ||
        filters.distanceMax !== null ||
        filters.durationMin !== null ||
        filters.durationMax !== null ||
        filters.paceMin !== null ||
        filters.paceMax !== null,
    ),
);

const filterWarning = computed(() => {
    if (
        filters.distanceMin !== null &&
        filters.distanceMax !== null &&
        filters.distanceMin > filters.distanceMax
    ) {
        return 'Min distance is greater than max — no results will match.';
    }
    if (
        filters.durationMin !== null &&
        filters.durationMax !== null &&
        filters.durationMin > filters.durationMax
    ) {
        return 'Min duration is greater than max — no results will match.';
    }
    return null;
});

function clearFilters() {
    filters.dateFrom = '';
    filters.dateTo = '';
    filters.distanceMin = null;
    filters.distanceMax = null;
    filters.durationMin = null;
    filters.durationMax = null;
    filters.paceMin = null;
    filters.paceMax = null;
}

const filteredActivities = computed(() => {
    // Convert filter inputs from display unit to stored units for comparison
    const distMinKm =
        filters.distanceMin !== null ? toKm(filters.distanceMin) : null;
    const distMaxKm =
        filters.distanceMax !== null ? toKm(filters.distanceMax) : null;
    const paceMinKm =
        filters.paceMin !== null
            ? distanceUnit.value === 'mi'
                ? filters.paceMin / 1.60934
                : filters.paceMin
            : null;
    const paceMaxKm =
        filters.paceMax !== null
            ? distanceUnit.value === 'mi'
                ? filters.paceMax / 1.60934
                : filters.paceMax
            : null;
    return activities.value.filter((r) => {
        if (filters.dateFrom && r.date < filters.dateFrom) return false;
        if (filters.dateTo && r.date > filters.dateTo) return false;
        if (distMinKm !== null && r.distance_km < distMinKm) return false;
        if (distMaxKm !== null && r.distance_km > distMaxKm) return false;
        const durationMin = filters.durationMin
            ? filters.durationMin * 60
            : null;
        const durationMax = filters.durationMax
            ? filters.durationMax * 60
            : null;
        if (durationMin !== null && r.duration_seconds < durationMin)
            return false;
        if (durationMax !== null && r.duration_seconds > durationMax)
            return false;
        if (paceMinKm !== null && r.pace < paceMinKm) return false;
        if (paceMaxKm !== null && r.pace > paceMaxKm) return false;
        return true;
    });
});

const showFilters = ref(false);

// --- Dialog state ---
const showDialog = ref(false);
const editingId = ref<number | null>(null);
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);
const formError = ref('');

const form = reactive({
    date: today.toISOString().split('T')[0] as string,
    title: '',
    minutes: 0,
    seconds: 0,
    distance_km: 0,
    notes: '',
});

function resetForm() {
    form.date = today.toISOString().split('T')[0] as string;
    form.title = '';
    form.minutes = 0;
    form.seconds = 0;
    form.distance_km = 0;
    form.notes = '';
    editingId.value = null;
    formError.value = '';
}

function openAddDialog() {
    resetForm();
    showDialog.value = true;
}

function openEditDialog(run: RunningActivity) {
    editingId.value = run.id;
    form.date = run.date;
    form.title = run.title ?? '';
    form.minutes = Math.floor(run.duration_seconds / 60);
    form.seconds = run.duration_seconds % 60;
    form.distance_km = parseFloat(fromKm(run.distance_km).toFixed(2));
    form.notes = run.notes ?? '';
    formError.value = '';
    showDialog.value = true;
}

async function saveRun() {
    formError.value = '';
    if (!form.date.trim()) {
        formError.value = 'Date is required';
        return;
    }
    const durationSeconds = form.minutes * 60 + form.seconds;
    const distance_km = toKm(form.distance_km);
    if (editingId.value) {
        const res = await updateActivity(editingId.value, {
            date: form.date,
            duration_seconds: durationSeconds,
            distance_km,
            notes: form.notes || null,
            title: form.title || null,
        });
        if (res.success) {
            toast.showSuccess('Run updated');
            showDialog.value = false;
            await loadData();
        } else {
            formError.value = res.error?.message ?? 'Failed to save run';
        }
    } else {
        const res = await createActivity({
            date: form.date,
            duration_seconds: durationSeconds,
            distance_km,
            notes: form.notes || null,
            title: form.title || null,
        });
        if (res.success) {
            toast.showSuccess('Run added');
            showDialog.value = false;
            await loadData();
        } else {
            formError.value = res.error?.message ?? 'Failed to save run';
        }
    }
}

function confirmDelete(id: number) {
    deletingId.value = id;
    showDeleteConfirm.value = true;
}

async function executeDelete() {
    if (deletingId.value) {
        const res = await deleteActivity(deletingId.value);
        if (res.success) {
            toast.showSuccess('Run deleted');
        }
    }
    showDeleteConfirm.value = false;
    deletingId.value = null;
    await loadData();
}

// --- GPX Import ---
const gpxFileInput = ref<HTMLInputElement | null>(null);
const showSegmentsDialog = ref(false);
const selectedSegments = ref<GpxSegment[]>([]);

function triggerGpxUpload() {
    gpxFileInput.value?.click();
}

async function handleGpxFiles(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files || files.length === 0) return;

    let imported = 0;
    let lastSegments: GpxSegment[] = [];

    for (const file of files) {
        const res = await importGpx(file);
        if (res.success && res.data) {
            imported++;
            lastSegments = res.data.segments;
        } else {
            toast.showError(
                `${file.name}: ${res.error?.message ?? 'Import failed'}`,
            );
        }
    }

    if (imported > 0) {
        toast.showSuccess(
            `Imported ${imported} file${imported > 1 ? 's' : ''}`,
        );
        if (imported === 1 && lastSegments.length > 0) {
            selectedSegments.value = lastSegments;
            showSegmentsDialog.value = true;
        }
        await loadData();
    }
    input.value = '';
}

async function viewSegments(runId: number) {
    const res = await getSegments(runId);
    if (res.success && res.data) {
        selectedSegments.value = res.data;
        showSegmentsDialog.value = true;
    }
}

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
    if (goalFormValue.value > 0) {
        const goalKm = toKm(goalFormValue.value);
        await setSetting('running_weekly_goal_km', String(goalKm));
        weeklyGoalKm.value = goalKm;
    } else {
        await setSetting('running_weekly_goal_km', '0');
        weeklyGoalKm.value = null;
    }
    showGoalDialog.value = false;
}

// --- Data loading ---
async function loadData() {
    const runsRes = await getActivities();
    if (runsRes.success && runsRes.data) activities.value = runsRes.data;
    else if (!runsRes.success) toast.showError('Failed to load running activities');
}

async function loadGoal() {
    const res = await getSetting('running_weekly_goal_km');
    if (res.success && res.data?.value) {
        const val = parseFloat(res.data.value);
        if (val > 0) weeklyGoalKm.value = val;
    }
}

onMounted(() => {
    withLoading(loadData);
    loadGoal();
});

// --- Computed stats ---
function getMonday(d: Date): Date {
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.getFullYear(), d.getMonth(), diff);
}

const weekStats = computed(() => {
    const monday = getMonday(new Date());
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    const monStr = monday.toISOString().split('T')[0] as string;
    const sunStr = sunday.toISOString().split('T')[0] as string;
    const weekRuns = filteredActivities.value.filter(
        (r) => r.date >= monStr && r.date <= sunStr,
    );
    return {
        distance: weekRuns.reduce((s, r) => s + r.distance_km, 0),
        count: weekRuns.length,
    };
});

const monthStats = computed(() => {
    const prefix = `${currentYear}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    const monthRuns = filteredActivities.value.filter((r) =>
        r.date.startsWith(prefix),
    );
    return {
        distance: monthRuns.reduce((s, r) => s + r.distance_km, 0),
        count: monthRuns.length,
    };
});

const yearStats = computed(() => {
    const yearPrefix = `${currentYear}-`;
    const yearRuns = filteredActivities.value.filter((r) =>
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

// --- Pace Over Time Chart ---
const chartData = computed(() => {
    const sorted = [...filteredActivities.value]
        .filter((r) => r.pace > 0)
        .sort((a, b) => a.date.localeCompare(b.date));
    const paceMultiplier = distanceUnit.value === 'mi' ? 1.60934 : 1;
    return {
        labels: sorted.map((r) => formatDate(r.date)),
        datasets: [
            {
                label: `Pace (min/${distanceUnit.value})`,
                data: sorted.map((r) => r.pace * paceMultiplier),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.3,
            },
        ],
    };
});

const chartOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
        y: {
            reverse: true,
            title: { display: true, text: `Pace (min/${distanceUnit.value})` },
        },
    },
}));

// --- Formatting helpers ---
function formatDuration(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) {
        return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    return `${m}:${String(s).padStart(2, '0')}`;
}

const dialogHeader = computed(() => (editingId.value ? 'Edit Run' : 'Add Run'));
</script>

<template>
    <div class="mx-auto max-w-6xl p-6">
        <h1 class="mb-6 text-2xl font-bold">Running</h1>

        <!-- Stats Cards -->
        <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <AppCard>
                <template #title>
                    <div class="flex items-center justify-between">
                        <span>This Week</span>
                        <AppButton
                            icon="pi pi-cog"
                            rounded
                            severity="secondary"
                            size="small"
                            text
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

        <!-- Pace Over Time Chart -->
        <div v-if="filteredActivities.length > 1" class="mb-6">
            <h2 class="mb-3 text-xl font-semibold">Pace Over Time</h2>
            <div class="h-64">
                <AppChart
                    :data="chartData"
                    :options="chartOptions"
                    type="line"
                />
            </div>
        </div>

        <!-- Table Header -->
        <div class="mb-4 flex items-center justify-between">
            <h2 class="text-xl font-semibold">Running Log</h2>
            <div class="flex gap-2">
                <AppButton
                    :icon="showFilters ? 'pi pi-filter-slash' : 'pi pi-filter'"
                    :label="showFilters ? 'Hide Filters' : 'Filters'"
                    outlined
                    :severity="hasActiveFilters ? 'warn' : 'secondary'"
                    @click="showFilters = !showFilters"
                />
                <AppButton
                    icon="pi pi-upload"
                    label="Import GPX"
                    outlined
                    @click="triggerGpxUpload"
                />
                <input
                    ref="gpxFileInput"
                    accept=".gpx"
                    hidden
                    multiple
                    type="file"
                    @change="handleGpxFiles"
                />
                <AppButton
                    icon="pi pi-plus"
                    label="Add Run"
                    @click="openAddDialog"
                />
            </div>
        </div>

        <!-- Filters Panel -->
        <div
            v-if="showFilters"
            class="border-surface-200 dark:border-surface-700 mb-4 rounded-lg border p-4"
        >
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <!-- Date Range -->
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Date From
                    </label>
                    <AppInputText
                        v-model="filters.dateFrom"
                        class="w-full"
                        type="date"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Date To
                    </label>
                    <AppInputText
                        v-model="filters.dateTo"
                        class="w-full"
                        type="date"
                    />
                </div>

                <!-- Distance Range -->
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Min Distance ({{ distanceUnit }})
                    </label>
                    <AppInputNumber
                        v-model="filters.distanceMin"
                        class="w-full"
                        :max-fraction-digits="1"
                        :min="0"
                        placeholder="Min"
                        show-buttons
                        :step="0.5"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Max Distance ({{ distanceUnit }})
                    </label>
                    <AppInputNumber
                        v-model="filters.distanceMax"
                        class="w-full"
                        :max-fraction-digits="1"
                        :min="0"
                        placeholder="Max"
                        show-buttons
                        :step="0.5"
                    />
                </div>

                <!-- Duration Range (in minutes) -->
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Min Duration (min)
                    </label>
                    <AppInputNumber
                        v-model="filters.durationMin"
                        class="w-full"
                        :min="0"
                        placeholder="Min"
                        show-buttons
                        :step="5"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Max Duration (min)
                    </label>
                    <AppInputNumber
                        v-model="filters.durationMax"
                        class="w-full"
                        :min="0"
                        placeholder="Max"
                        show-buttons
                        :step="5"
                    />
                </div>

                <!-- Pace Range -->
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Min Pace (min/{{ distanceUnit }})
                    </label>
                    <AppInputNumber
                        v-model="filters.paceMin"
                        class="w-full"
                        :max-fraction-digits="1"
                        :min="0"
                        placeholder="Min"
                        show-buttons
                        :step="0.5"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Max Pace (min/{{ distanceUnit }})
                    </label>
                    <AppInputNumber
                        v-model="filters.paceMax"
                        class="w-full"
                        :max-fraction-digits="1"
                        :min="0"
                        placeholder="Max"
                        show-buttons
                        :step="0.5"
                    />
                </div>
            </div>
            <div class="mt-3 flex items-center justify-between">
                <span class="text-surface-500 text-sm">
                    {{ filteredActivities.length }} of
                    {{ activities.length }} runs
                </span>
                <AppButton
                    v-if="hasActiveFilters"
                    icon="pi pi-times"
                    label="Clear Filters"
                    severity="secondary"
                    size="small"
                    text
                    @click="clearFilters"
                />
            </div>
            <p
                v-if="filterWarning"
                class="mt-2 text-sm text-amber-600 dark:text-amber-400"
            >
                <i class="pi pi-exclamation-triangle mr-1"></i
                >{{ filterWarning }}
            </p>
        </div>

        <!-- Data Table -->
        <AppDataTable
            :loading="loading"
            sort-field="date"
            :sort-order="-1"
            striped-rows
            :value="filteredActivities"
        >
            <template #empty>
                <div class="flex flex-col items-center py-10 text-center">
                    <i
                        class="pi pi-inbox text-surface-300 dark:text-surface-600 mb-3 text-4xl"
                    ></i>
                    <p class="text-surface-500 mb-3">No runs logged yet</p>
                    <AppButton
                        icon="pi pi-plus"
                        label="Log your first run"
                        size="small"
                        @click="openAddDialog"
                    />
                </div>
            </template>
            <AppColumn field="date" header="Date" sortable>
                <template #body="{ data }">
                    {{ formatDate((data as RunningActivity).date) }}
                </template>
            </AppColumn>
            <AppColumn field="title" header="Title">
                <template #body="{ data }">
                    <span v-if="(data as RunningActivity).title">
                        {{ (data as RunningActivity).title }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn field="distance_km" header="Distance" sortable>
                <template #body="{ data }">
                    {{ fmtDistance((data as RunningActivity).distance_km) }}
                </template>
            </AppColumn>
            <AppColumn field="duration_seconds" header="Duration" sortable>
                <template #body="{ data }">
                    {{
                        formatDuration(
                            (data as RunningActivity).duration_seconds,
                        )
                    }}
                </template>
            </AppColumn>
            <AppColumn field="pace_formatted" header="Pace">
                <template #body="{ data }">
                    {{ fmtPace((data as RunningActivity).pace) }}
                </template>
            </AppColumn>
            <AppColumn field="notes" header="Notes" />
            <AppColumn header="Actions" style="width: 8rem">
                <template #body="{ data }">
                    <div class="row-actions flex gap-2">
                        <AppButton
                            v-if="(data as RunningActivity).has_gpx"
                            icon="pi pi-chart-bar"
                            rounded
                            severity="secondary"
                            text
                            @click="viewSegments((data as RunningActivity).id)"
                        />
                        <AppButton
                            icon="pi pi-pencil"
                            rounded
                            severity="info"
                            text
                            @click="openEditDialog(data as RunningActivity)"
                        />
                        <AppButton
                            icon="pi pi-trash"
                            rounded
                            severity="danger"
                            text
                            @click="confirmDelete((data as RunningActivity).id)"
                        />
                    </div>
                </template>
            </AppColumn>
        </AppDataTable>

        <!-- Add/Edit Dialog -->
        <AppDialog
            v-model:visible="showDialog"
            :header="dialogHeader"
            modal
            :style="{ width: '28rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium"> Date </label>
                    <AppInputText
                        v-model="form.date"
                        class="w-full"
                        type="date"
                    />
                    <p v-if="formError" class="mt-1 text-sm text-red-500">
                        {{ formError }}
                    </p>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Title
                    </label>
                    <AppInputText
                        v-model="form.title"
                        class="w-full"
                        placeholder="e.g. Morning Run"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Distance ({{ distanceUnit }})
                    </label>
                    <AppInputNumber
                        v-model="form.distance_km"
                        class="w-full"
                        :max-fraction-digits="2"
                        :min-fraction-digits="1"
                        :step="0.1"
                        :suffix="' ' + distanceUnit"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Duration
                    </label>
                    <div class="flex items-center gap-2">
                        <AppInputNumber
                            v-model="form.minutes"
                            class="w-full"
                            :min="0"
                            suffix=" min"
                        />
                        <AppInputNumber
                            v-model="form.seconds"
                            class="w-full"
                            :max="59"
                            :min="0"
                            suffix=" sec"
                        />
                    </div>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Notes
                    </label>
                    <AppTextarea v-model="form.notes" class="w-full" rows="2" />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showDialog = false"
                    />
                    <AppButton label="Save" @click="saveRun" />
                </div>
            </div>
        </AppDialog>

        <!-- Delete Confirmation Dialog -->
        <AppDialog
            v-model:visible="showDeleteConfirm"
            header="Confirm Delete"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <p>Are you sure you want to delete this run?</p>
            <div class="mt-4 flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    text
                    @click="showDeleteConfirm = false"
                />
                <AppButton
                    label="Delete"
                    severity="danger"
                    @click="executeDelete"
                />
            </div>
        </AppDialog>

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

        <!-- GPX Segments Dialog -->
        <AppDialog
            v-model:visible="showSegmentsDialog"
            header="GPX Segments"
            modal
            :style="{ width: '40rem', maxWidth: '92vw' }"
        >
            <AppDataTable :value="selectedSegments">
                <AppColumn field="segment_name" header="Segment" />
                <AppColumn header="Distance">
                    <template #body="{ data }">
                        {{ fmtDistance((data as GpxSegment).distance_km) }}
                    </template>
                </AppColumn>
                <AppColumn header="Duration">
                    <template #body="{ data }">
                        {{
                            formatDuration(
                                (data as GpxSegment).duration_seconds,
                            )
                        }}
                    </template>
                </AppColumn>
                <AppColumn header="Pace">
                    <template #body="{ data }">
                        {{ fmtPace((data as GpxSegment).pace) }}
                    </template>
                </AppColumn>
            </AppDataTable>
        </AppDialog>
    </div>
</template>
