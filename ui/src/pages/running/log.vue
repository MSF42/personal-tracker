<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import AddEditRunDialog from '@/components/AddEditRunDialog.vue';
import ConfirmDeleteDialog from '@/components/ConfirmDeleteDialog.vue';
import NumberRangeFilter from '@/components/NumberRangeFilter.vue';
import { useRunningApi } from '@/composables/api/useRunningApi';
import { useTaskApi } from '@/composables/api/useTaskApi';
import { useFileDrop } from '@/composables/useFileDrop';
import { useLoading } from '@/composables/useLoading';
import { completeTasksLinkedToRun } from '@/composables/useTaskLinks';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { RunningActivity } from '@/types/Running';
import { formatDate, formatDuration } from '@/utils/format';
import { fromIsoDate, toIsoDate } from '@/utils/week';

const { getActivities, deleteActivity, importGpx, importFit } = useRunningApi();
const { getTasks, updateTask } = useTaskApi();
const { loading, withLoading } = useLoading();
const toast = useToast();
const router = useRouter();
const { distanceUnit, fmtDistance, fmtPace, toKm, fromKm } = useUnits();

const activities = ref<RunningActivity[]>([]);

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

// AppDatePicker binds to a Date; filters.dateFrom/dateTo stay plain ISO
// strings (compared directly against activity dates elsewhere), so these
// are just the conversion layer between the two — same pattern as the
// Add Countdown form.
const dateFromModel = computed<Date | null>({
    get: () => (filters.dateFrom ? fromIsoDate(filters.dateFrom) : null),
    set: (value) => {
        filters.dateFrom = value ? toIsoDate(value) : '';
    },
});
const dateToModel = computed<Date | null>({
    get: () => (filters.dateTo ? fromIsoDate(filters.dateTo) : null),
    set: (value) => {
        filters.dateTo = value ? toIsoDate(value) : '';
    },
});

// Seeded once from the full activity list so opening the filter panel shows
// the actual range of data rather than empty boxes — "clear filters" resets
// back to this full range, not to nothing.
type RunningFilters = typeof filters;
const filterDefaults = ref<RunningFilters | null>(null);

function computeFilterDefaults(): RunningFilters | null {
    if (activities.value.length === 0) return null;
    const paceMultiplier = distanceUnit.value === 'mi' ? 1.60934 : 1;
    const dates = activities.value.map((r) => r.date);
    const distancesKm = activities.value.map((r) => r.distance_km);
    const durationsSec = activities.value.map((r) => r.duration_seconds);
    const paces = activities.value
        .filter((r) => r.pace > 0)
        .map((r) => r.pace * paceMultiplier);

    return {
        dateFrom: dates.reduce((a, b) => (a < b ? a : b)),
        dateTo: dates.reduce((a, b) => (a > b ? a : b)),
        distanceMin: Math.floor(fromKm(Math.min(...distancesKm)) * 10) / 10,
        distanceMax: Math.ceil(fromKm(Math.max(...distancesKm)) * 10) / 10,
        // Duration filters work in whole seconds directly (matching
        // formatDuration/parseDuration's H:MM:SS shape) rather than minutes.
        durationMin: Math.min(...durationsSec),
        durationMax: Math.max(...durationsSec),
        paceMin: paces.length ? Math.floor(Math.min(...paces) * 10) / 10 : null,
        paceMax: paces.length ? Math.ceil(Math.max(...paces) * 10) / 10 : null,
    };
}

const hasActiveFilters = computed(() => {
    const d = filterDefaults.value;
    if (!d) return false;
    return (
        filters.dateFrom !== d.dateFrom ||
        filters.dateTo !== d.dateTo ||
        filters.distanceMin !== d.distanceMin ||
        filters.distanceMax !== d.distanceMax ||
        filters.durationMin !== d.durationMin ||
        filters.durationMax !== d.durationMax ||
        filters.paceMin !== d.paceMin ||
        filters.paceMax !== d.paceMax
    );
});

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
    if (!filterDefaults.value) return;
    Object.assign(filters, filterDefaults.value);
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
        if (
            filters.durationMin !== null &&
            r.duration_seconds < filters.durationMin
        )
            return false;
        if (
            filters.durationMax !== null &&
            r.duration_seconds > filters.durationMax
        )
            return false;
        if (paceMinKm !== null && r.pace < paceMinKm) return false;
        if (paceMaxKm !== null && r.pace > paceMaxKm) return false;
        return true;
    });
});

const showFilters = ref(false);

// --- Dialog state ---
const showDialog = ref(false);
const editingRun = ref<RunningActivity | null>(null);
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);

function openAddDialog() {
    editingRun.value = null;
    showDialog.value = true;
}

function openEditDialog(run: RunningActivity) {
    editingRun.value = run;
    showDialog.value = true;
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

// --- GPX / FIT Import ---
const importFileInput = ref<HTMLInputElement | null>(null);

function triggerImportUpload() {
    importFileInput.value?.click();
}

async function importFiles(files: Iterable<File>) {
    const fileList = [...files];
    if (fileList.length === 0) return;

    let imported = 0;
    let duplicates = 0;
    let lastActivity: RunningActivity | null = null;
    const importedDates: string[] = [];

    for (const file of fileList) {
        const isFit = file.name.toLowerCase().endsWith('.fit');
        const res = isFit ? await importFit(file) : await importGpx(file);
        if (res.success && res.data) {
            imported++;
            lastActivity = res.data.activity;
            importedDates.push(res.data.activity.date);
        } else if (res.error?.code === 'CONFLICT') {
            // The API already holds this activity; skip quietly and summarise.
            duplicates++;
        } else {
            toast.showError(
                `${file.name}: ${res.error?.message ?? 'Import failed'}`,
            );
        }
    }

    if (duplicates > 0) {
        toast.showWarning(
            `Skipped ${duplicates} duplicate${duplicates > 1 ? 's' : ''}`,
            'Already imported — nothing was changed.',
        );
    }
    if (imported > 0) {
        toast.showSuccess(
            `Imported ${imported} file${imported > 1 ? 's' : ''}`,
        );
        // Each imported run completes any "run" task due on its date.
        await Promise.all(
            [...new Set(importedDates)].map((date) =>
                completeTasksLinkedToRun(getTasks, updateTask, date),
            ),
        );
        await loadData();
        if (imported === 1 && lastActivity) {
            await router.push(`/running/${lastActivity.id}`);
        }
    }
}

async function handleImportFiles(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files) await importFiles(input.files);
    input.value = '';
}

// Drag a .gpx/.fit file onto the page (from Finder/Explorer, or straight off
// a watch-sync folder) as a shortcut for the toolbar's file picker — same
// import path, same duplicate/error handling.
const {
    isOver: isFileDragOver,
    onDragEnter,
    onDragOver,
    onDragLeave,
    onFileDrop,
} = useFileDrop((files) => void importFiles(files), ['.gpx', '.fit']);

// --- Data loading ---
async function loadData() {
    const runsRes = await getActivities();
    if (runsRes.success && runsRes.data) {
        activities.value = runsRes.data;
        // Seed the filter range once, from the first load — later reloads
        // (after add/edit/delete/import) leave the user's own filter
        // choices alone rather than resetting them.
        if (!filterDefaults.value) {
            filterDefaults.value = computeFilterDefaults();
            if (filterDefaults.value)
                Object.assign(filters, filterDefaults.value);
        }
    } else if (!runsRes.success) {
        toast.showError('Failed to load running activities');
    }
}

onMounted(() => withLoading(loadData));
</script>

<template>
    <div
        @dragenter="onDragEnter"
        @dragleave="onDragLeave"
        @dragover="onDragOver"
        @drop="onFileDrop"
    >
        <!-- Drag-and-drop overlay: shown while a .gpx/.fit file is dragged
             anywhere over the page, as a shortcut for the picker below. -->
        <div
            v-if="isFileDragOver"
            class="border-primary-400 bg-surface-0/90 dark:bg-surface-900/90 pointer-events-none fixed inset-4 z-50 flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed backdrop-blur-sm"
        >
            <i class="pi pi-upload text-primary-500 text-4xl"></i>
            <p class="text-lg font-medium">Drop to import</p>
            <p class="text-surface-500 text-sm">GPX or FIT files</p>
        </div>

        <!-- Table Header -->
        <div class="mb-4 flex items-center justify-between">
            <h1 class="text-2xl font-bold">Running Log</h1>
            <div class="flex gap-2">
                <AppButton
                    :icon="showFilters ? 'pi pi-filter-slash' : 'pi pi-filter'"
                    :label="showFilters ? 'Hide Filters' : 'Filters'"
                    outlined
                    :severity="hasActiveFilters ? 'warn' : 'secondary'"
                    @click="showFilters = !showFilters"
                />
                <AppButton
                    v-tooltip.bottom="'You can also drag files onto this page'"
                    icon="pi pi-upload"
                    label="Import GPX / FIT"
                    outlined
                    @click="triggerImportUpload"
                />
                <input
                    ref="importFileInput"
                    accept=".gpx,.fit"
                    hidden
                    multiple
                    type="file"
                    @change="handleImportFiles"
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
            <div class="flex flex-wrap gap-x-6 gap-y-4">
                <!-- Date Range -->
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Date From
                    </label>
                    <div class="w-44 shrink-0">
                        <AppDatePicker
                            v-model="dateFromModel"
                            date-format="yy M dd"
                            fluid
                            icon-display="input"
                            show-icon
                        />
                    </div>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Date To
                    </label>
                    <div class="w-44 shrink-0">
                        <AppDatePicker
                            v-model="dateToModel"
                            date-format="yy M dd"
                            fluid
                            icon-display="input"
                            show-icon
                        />
                    </div>
                </div>

                <!-- Distance Range -->
                <NumberRangeFilter
                    v-model:max="filters.distanceMax"
                    v-model:min="filters.distanceMin"
                    label="Distance"
                    :max-fraction-digits="1"
                    :step="0.5"
                    :unit="distanceUnit"
                />

                <!-- Duration Range, as H:MM:SS / M:SS -->
                <DurationRangeFilter
                    v-model:max="filters.durationMax"
                    v-model:min="filters.durationMin"
                />

                <!-- Pace Range, as M:SS -->
                <PaceRangeFilter
                    v-model:max="filters.paceMax"
                    v-model:min="filters.paceMin"
                    :unit="`min/${distanceUnit}`"
                />
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
            :row-class="() => 'group'"
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
                        label="Add your first run"
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
            <AppColumn field="avg_hr" header="Avg HR" sortable>
                <template #body="{ data }">
                    <span v-if="(data as RunningActivity).avg_hr">
                        {{ (data as RunningActivity).avg_hr }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn field="notes" header="Notes" />
            <AppColumn header="Actions" style="width: 8rem">
                <template #body="{ data }">
                    <div
                        class="flex justify-end gap-2 opacity-20 transition-opacity group-hover:opacity-100"
                    >
                        <AppButton
                            v-if="(data as RunningActivity).has_gpx"
                            aria-label="Run details"
                            icon="pi pi-chart-bar"
                            rounded
                            severity="secondary"
                            text
                            title="Run details"
                            @click="
                                router.push(
                                    `/running/${(data as RunningActivity).id}`,
                                )
                            "
                        />
                        <AppButton
                            aria-label="Edit run"
                            icon="pi pi-pencil"
                            rounded
                            severity="info"
                            text
                            @click="openEditDialog(data as RunningActivity)"
                        />
                        <AppButton
                            aria-label="Delete run"
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
        <AddEditRunDialog
            v-model:visible="showDialog"
            :run="editingRun"
            @saved="loadData"
        />

        <!-- Delete Confirmation Dialog -->
        <ConfirmDeleteDialog
            v-model:visible="showDeleteConfirm"
            @confirm="executeDelete"
        >
            Are you sure you want to delete this run?
        </ConfirmDeleteDialog>
    </div>
</template>
