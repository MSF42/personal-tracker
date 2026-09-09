<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import ConfirmDeleteDialog from '@/components/ConfirmDeleteDialog.vue';
import LogWorkoutDialog from '@/components/LogWorkoutDialog.vue';
import WorkoutLogDetailDialog from '@/components/WorkoutLogDetailDialog.vue';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import type { WorkoutLog } from '@/types/WorkoutLog';
import type { WorkoutRoutine } from '@/types/WorkoutRoutine';
import { formatDate } from '@/utils/format';
import { fromIsoDate, toIsoDate } from '@/utils/week';

const { getWorkoutLogs, deleteWorkoutLog } = useWorkoutLogApi();
const { getWorkoutRoutines } = useWorkoutRoutineApi();
const { loading, withLoading } = useLoading();
const toast = useToast();

const logs = ref<WorkoutLog[]>([]);

const todayStr = new Date().toISOString().split('T')[0] as string;
const currentMonthPrefix = todayStr.slice(0, 7);

// --- Stats ---
const stats = computed(() => {
    const thisMonth = logs.value.filter((l) =>
        l.date.startsWith(currentMonthPrefix),
    ).length;
    const sorted = [...logs.value].sort((a, b) => b.date.localeCompare(a.date));
    const lastWorkout = sorted.length > 0 ? sorted[0]!.date : null;
    return {
        total: logs.value.length,
        thisMonth,
        lastWorkout,
    };
});

// --- Filters ---
const showFilters = ref(false);

const filters = reactive({
    routineName: '',
    dateFrom: '',
    dateTo: '',
});

const hasActiveFilters = computed(() =>
    Boolean(filters.routineName || filters.dateFrom || filters.dateTo),
);

// AppDatePicker binds to a Date; filters.dateFrom/dateTo stay plain ISO
// strings (compared directly against log dates elsewhere).
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

function clearFilters() {
    filters.routineName = '';
    filters.dateFrom = '';
    filters.dateTo = '';
}

const uniqueRoutineNames = computed(() => {
    const names = new Set(logs.value.map((l) => l.routine_name));
    return [...names].sort();
});

const routineOptions = computed(() => [
    { label: 'All', value: '' },
    ...uniqueRoutineNames.value.map((name) => ({
        label: name,
        value: name,
    })),
]);

const filteredLogs = computed(() => {
    return logs.value.filter((l) => {
        if (filters.routineName && l.routine_name !== filters.routineName)
            return false;
        if (filters.dateFrom && l.date < filters.dateFrom) return false;
        if (filters.dateTo && l.date > filters.dateTo) return false;
        return true;
    });
});

// --- View/Edit Dialog ---
const showViewDialog = ref(false);
const viewingLogId = ref<number | null>(null);

function openView(log: WorkoutLog) {
    viewingLogId.value = log.id;
    showViewDialog.value = true;
}

// --- Log Workout dialog (resume an in-progress log, or perform a routine
// fresh) — one shared dialog instance driven by whichever action opened it.
const showLogWorkoutDialog = ref(false);
const activeRoutineId = ref<number | null>(null);
const activeRoutineName = ref('');
const activeResumeLogId = ref<number | null>(null);

function openResume(log: WorkoutLog) {
    activeRoutineId.value = log.routine_id;
    activeRoutineName.value = log.routine_name;
    activeResumeLogId.value = log.id;
    showLogWorkoutDialog.value = true;
}

// --- Perform Routine ---
const showChooseRoutine = ref(false);
const routines = ref<WorkoutRoutine[]>([]);
const loadingRoutines = ref(false);

async function openChooseRoutine() {
    showChooseRoutine.value = true;
    if (routines.value.length > 0) return;
    loadingRoutines.value = true;
    const res = await getWorkoutRoutines();
    if (res.success && res.data) routines.value = res.data;
    loadingRoutines.value = false;
}

function performRoutine(routine: WorkoutRoutine) {
    activeRoutineId.value = routine.id;
    activeRoutineName.value = routine.name;
    activeResumeLogId.value = null;
    showChooseRoutine.value = false;
    showLogWorkoutDialog.value = true;
}

// --- Delete Confirmation ---
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);

function confirmDelete(id: number) {
    deletingId.value = id;
    showDeleteConfirm.value = true;
}

async function executeDelete() {
    if (deletingId.value) {
        const res = await deleteWorkoutLog(deletingId.value);
        if (res.success) {
            toast.showSuccess('Workout log deleted');
        }
    }
    showDeleteConfirm.value = false;
    deletingId.value = null;
    await loadData();
}

// --- Data loading ---
async function loadData() {
    const res = await getWorkoutLogs();
    if (res.success && res.data) logs.value = res.data;
    else if (!res.success) toast.showError('Failed to load workout logs');
}

onMounted(() => withLoading(loadData));
</script>

<template>
    <div class="mx-auto max-w-6xl p-6">
        <h1 class="mb-6 text-2xl font-bold">Workout Logs</h1>

        <!-- Stats Cards -->
        <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <AppCard>
                <template #title>Total Workouts</template>
                <template #content>
                    <div class="text-2xl font-bold">{{ stats.total }}</div>
                    <div class="text-surface-500 text-sm">all time</div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>This Month</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ stats.thisMonth }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ stats.thisMonth === 1 ? 'workout' : 'workouts' }}
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>Last Workout</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{
                            stats.lastWorkout
                                ? formatDate(stats.lastWorkout)
                                : '—'
                        }}
                    </div>
                    <div class="text-surface-500 text-sm">most recent</div>
                </template>
            </AppCard>
        </div>

        <!-- Table Header -->
        <div class="mb-4 flex items-center justify-between">
            <h2 class="text-xl font-semibold">Logs</h2>
            <div class="flex items-center gap-2">
                <AppButton
                    :icon="showFilters ? 'pi pi-filter-slash' : 'pi pi-filter'"
                    :label="showFilters ? 'Hide Filters' : 'Filters'"
                    outlined
                    :severity="hasActiveFilters ? 'warn' : 'secondary'"
                    @click="showFilters = !showFilters"
                />
                <AppButton
                    icon="pi pi-play"
                    label="Perform Routine"
                    @click="openChooseRoutine"
                />
            </div>
        </div>

        <!-- Filters Panel -->
        <div
            v-if="showFilters"
            class="border-surface-200 dark:border-surface-700 mb-4 rounded-lg border p-4"
        >
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Routine
                    </label>
                    <AppSelect
                        v-model="filters.routineName"
                        class="w-full"
                        option-label="label"
                        option-value="value"
                        :options="routineOptions"
                    />
                </div>
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
            </div>
            <div class="mt-3 flex items-center justify-between">
                <span class="text-surface-500 text-sm">
                    {{ filteredLogs.length }} of {{ logs.length }} workouts
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
        </div>

        <!-- Data Table -->
        <AppDataTable
            :loading="loading"
            :row-class="() => 'group'"
            sort-field="date"
            :sort-order="-1"
            striped-rows
            :value="filteredLogs"
        >
            <template #empty>
                <div class="flex flex-col items-center py-10 text-center">
                    <i
                        class="pi pi-inbox text-surface-300 dark:text-surface-600 mb-3 text-4xl"
                    ></i>
                    <p class="text-surface-500 mb-3">No workout logs yet</p>
                    <p class="text-surface-400 mb-3 text-sm">
                        Log workouts from the
                        <RouterLink
                            class="text-primary underline"
                            to="/workout-routines"
                            >Routines</RouterLink
                        >
                        page
                    </p>
                </div>
            </template>
            <AppColumn field="date" header="Date" sortable>
                <template #body="{ data }">
                    {{ formatDate((data as WorkoutLog).date) }}
                </template>
            </AppColumn>
            <AppColumn field="routine_name" header="Routine" sortable />
            <AppColumn field="notes" header="Notes">
                <template #body="{ data }">
                    <span
                        v-if="(data as WorkoutLog).notes"
                        class="line-clamp-1"
                    >
                        {{ (data as WorkoutLog).notes }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn header="Status" style="width: 8rem">
                <template #body="{ data }">
                    <AppTag
                        v-if="!(data as WorkoutLog).completed"
                        severity="warn"
                        value="In Progress"
                    />
                    <AppTag v-else severity="success" value="Complete" />
                </template>
            </AppColumn>
            <AppColumn header="Actions" style="width: 11rem">
                <template #body="{ data }">
                    <div
                        class="flex justify-end gap-2 opacity-20 transition-opacity group-hover:opacity-100"
                    >
                        <AppButton
                            v-if="!(data as WorkoutLog).completed"
                            aria-label="Resume workout"
                            icon="pi pi-play"
                            rounded
                            severity="success"
                            text
                            title="Resume workout"
                            @click="openResume(data as WorkoutLog)"
                        />
                        <AppButton
                            aria-label="View workout log"
                            icon="pi pi-eye"
                            rounded
                            severity="secondary"
                            text
                            @click="openView(data as WorkoutLog)"
                        />
                        <AppButton
                            aria-label="Delete workout log"
                            icon="pi pi-trash"
                            rounded
                            severity="danger"
                            text
                            @click="confirmDelete((data as WorkoutLog).id)"
                        />
                    </div>
                </template>
            </AppColumn>
        </AppDataTable>

        <!-- Delete Confirmation Dialog -->
        <ConfirmDeleteDialog
            v-model:visible="showDeleteConfirm"
            @confirm="executeDelete"
        >
            Are you sure you want to delete this workout log?
        </ConfirmDeleteDialog>

        <!-- Choose Routine Dialog (Perform Routine) -->
        <AppDialog
            v-model:visible="showChooseRoutine"
            header="Perform Routine"
            modal
            :style="{ width: '28rem', maxWidth: '92vw' }"
        >
            <div v-if="loadingRoutines" class="py-6 text-center">
                <i class="pi pi-spin pi-spinner text-surface-400 text-2xl"></i>
            </div>
            <div
                v-else-if="routines.length === 0"
                class="text-surface-500 text-sm"
            >
                No routines yet.
                <RouterLink
                    class="text-primary underline"
                    to="/strength?tab=routines"
                >
                    Create one
                </RouterLink>
                first.
            </div>
            <div v-else class="flex max-h-96 flex-col gap-2 overflow-y-auto">
                <button
                    v-for="routine in routines"
                    :key="routine.id"
                    class="border-surface-200 dark:border-surface-700 hover:border-primary-400 dark:hover:border-primary-500 cursor-pointer rounded-lg border p-3 text-left transition-colors"
                    type="button"
                    @click="performRoutine(routine)"
                >
                    <div class="font-medium">{{ routine.name }}</div>
                    <div
                        v-if="routine.description"
                        class="text-surface-500 mt-0.5 truncate text-xs"
                    >
                        {{ routine.description }}
                    </div>
                </button>
            </div>
        </AppDialog>

        <!-- Log Workout Dialog (resume or perform-routine, shared) -->
        <LogWorkoutDialog
            v-model:visible="showLogWorkoutDialog"
            :resume-log-id="activeResumeLogId"
            :routine-id="activeRoutineId"
            :routine-name="activeRoutineName"
            @logged="loadData"
        />

        <!-- View/Edit Workout Log Dialog -->
        <WorkoutLogDetailDialog
            v-model:visible="showViewDialog"
            :log-id="viewingLogId"
            @updated="loadData"
        />
    </div>
</template>
