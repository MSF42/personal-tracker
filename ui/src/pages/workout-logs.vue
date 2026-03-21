<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import ExerciseHistoryDialog from '@/components/ExerciseHistoryDialog.vue';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type {
    ExerciseHistoryEntry,
    SetLog,
    WorkoutLog,
    WorkoutLogDetail,
} from '@/types/WorkoutLog';
import { formatDate } from '@/utils/format';

const {
    getWorkoutLogs,
    getWorkoutLog,
    getExerciseHistory,
    updateWorkoutLog,
    updateSet,
    deleteWorkoutLog,
} = useWorkoutLogApi();
const { loading, withLoading } = useLoading();
const toast = useToast();
const { fmtWeight } = useUnits();

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

// --- Detail Dialog ---
const showDetail = ref(false);
const detail = ref<WorkoutLogDetail | null>(null);

const detailRoutineName = ref('');

async function openDetail(log: WorkoutLog) {
    detailRoutineName.value = log.routine_name;
    const res = await getWorkoutLog(log.id);
    if (res.success && res.data) {
        detail.value = res.data;
        showDetail.value = true;
    }
}

interface SetGroup {
    exerciseName: string;
    sets: WorkoutLogDetail['sets'];
}

const setGroups = computed<SetGroup[]>(() => {
    if (!detail.value) return [];
    const groups: SetGroup[] = [];
    for (const set of detail.value.sets) {
        let group = groups.find((g) => g.exerciseName === set.exercise_name);
        if (!group) {
            group = { exerciseName: set.exercise_name, sets: [] };
            groups.push(group);
        }
        group.sets.push(set);
    }
    return groups;
});

// --- Inline Set Editing ---
const editingSetId = ref<number | null>(null);
const editSetReps = ref(0);
const editSetWeight = ref(0);

function startEditSet(set: SetLog) {
    editingSetId.value = set.id;
    editSetReps.value = set.reps;
    editSetWeight.value = set.weight ?? 0;
}

async function saveSet(set: SetLog) {
    if (!detail.value) return;
    const res = await updateSet(detail.value.id, set.id, {
        reps: editSetReps.value,
        weight: editSetWeight.value,
    });
    if (res.success && res.data) {
        const idx = detail.value.sets.findIndex((s) => s.id === set.id);
        if (idx !== -1) detail.value.sets[idx] = res.data;
    } else if (!res.success) {
        toast.showError('Failed to update set');
    }
    editingSetId.value = null;
}

// --- Exercise History Dialog ---
const showHistory = ref(false);
const historyExerciseName = ref('');
const historyEntries = ref<ExerciseHistoryEntry[]>([]);

async function openExerciseHistory(exerciseId: number, exerciseName: string) {
    historyExerciseName.value = exerciseName;
    const res = await getExerciseHistory(exerciseId);
    if (res.success && res.data) {
        historyEntries.value = res.data;
        showHistory.value = true;
    }
}

// --- Edit Dialog ---
const showEdit = ref(false);
const editingLog = ref<WorkoutLog | null>(null);
const editForm = reactive({
    date: '',
    notes: '',
});

function openEditDialog(log: WorkoutLog) {
    editingLog.value = log;
    editForm.date = log.date;
    editForm.notes = log.notes ?? '';
    showEdit.value = true;
}

async function saveEdit() {
    if (!editingLog.value) return;
    const res = await updateWorkoutLog(editingLog.value.id, {
        date: editForm.date,
        notes: editForm.notes || null,
    });
    if (res.success) {
        toast.showSuccess('Workout log updated');
        showEdit.value = false;
        await loadData();
    }
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
            <AppButton
                :icon="showFilters ? 'pi pi-filter-slash' : 'pi pi-filter'"
                :label="showFilters ? 'Hide Filters' : 'Filters'"
                outlined
                :severity="hasActiveFilters ? 'warn' : 'secondary'"
                @click="showFilters = !showFilters"
            />
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
            <AppColumn header="Actions" style="width: 10rem">
                <template #body="{ data }">
                    <div class="row-actions flex gap-2">
                        <AppButton
                            icon="pi pi-eye"
                            rounded
                            severity="info"
                            text
                            @click="openDetail(data as WorkoutLog)"
                        />
                        <AppButton
                            icon="pi pi-pencil"
                            rounded
                            severity="info"
                            text
                            @click="openEditDialog(data as WorkoutLog)"
                        />
                        <AppButton
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

        <!-- Detail Dialog -->
        <AppDialog
            v-model:visible="showDetail"
            :header="`Workout on ${detail?.date ? formatDate(detail.date) : ''}`"
            modal
            :style="{ width: '36rem', maxWidth: '92vw' }"
        >
            <div v-if="detail" class="flex flex-col gap-4">
                <div class="text-surface-600 dark:text-surface-400 text-sm">
                    <span class="font-medium">Routine:</span>
                    {{ detailRoutineName }}
                </div>
                <div
                    v-if="detail.notes"
                    class="text-surface-600 dark:text-surface-400 text-sm"
                >
                    <span class="font-medium">Notes:</span>
                    {{ detail.notes }}
                </div>

                <div
                    v-if="setGroups.length === 0"
                    class="text-surface-500 text-center text-sm"
                >
                    No sets logged for this workout.
                </div>

                <div
                    v-for="group in setGroups"
                    :key="group.exerciseName"
                    class="border-surface-200 dark:border-surface-700 rounded-lg border p-3"
                >
                    <button
                        class="text-primary mb-2 cursor-pointer font-medium hover:underline"
                        @click="
                            openExerciseHistory(
                                group.sets[0]!.exercise_id,
                                group.exerciseName,
                            )
                        "
                    >
                        {{ group.exerciseName }}
                    </button>
                    <div class="flex flex-col gap-1">
                        <div
                            v-for="set in group.sets"
                            :key="set.id"
                            class="text-surface-600 dark:text-surface-400 flex items-center gap-2 text-sm"
                        >
                            <span class="text-surface-500 w-12 shrink-0">
                                Set {{ set.set_number }}
                            </span>
                            <template v-if="editingSetId !== set.id">
                                <span>{{ set.reps }} reps</span>
                                <span>
                                    {{
                                        set.weight !== null
                                            ? fmtWeight(set.weight)
                                            : '—'
                                    }}
                                </span>
                                <button
                                    class="text-surface-400 hover:text-primary ml-1"
                                    title="Edit set"
                                    @click="startEditSet(set)"
                                >
                                    <i class="pi pi-pencil text-xs" />
                                </button>
                            </template>
                            <template v-else>
                                <AppInputNumber
                                    v-model="editSetReps"
                                    :max="999"
                                    :min="1"
                                    size="small"
                                    style="width: 5rem"
                                />
                                <span class="text-surface-500">reps ×</span>
                                <AppInputNumber
                                    v-model="editSetWeight"
                                    :max="9999"
                                    :max-fraction-digits="2"
                                    :min="0"
                                    size="small"
                                    style="width: 6rem"
                                />
                                <span class="text-surface-500">kg</span>
                                <button
                                    class="hover:text-green-600 text-green-500"
                                    title="Save"
                                    @click="saveSet(set)"
                                >
                                    <i class="pi pi-check text-sm" />
                                </button>
                                <button
                                    class="text-red-400 hover:text-red-600"
                                    title="Cancel"
                                    @click="editingSetId = null"
                                >
                                    <i class="pi pi-times text-sm" />
                                </button>
                            </template>
                        </div>
                    </div>
                </div>

                <div class="flex justify-end">
                    <AppButton label="Close" text @click="showDetail = false" />
                </div>
            </div>
        </AppDialog>
        <!-- Exercise History Dialog -->
        <ExerciseHistoryDialog
            v-model:visible="showHistory"
            :entries="historyEntries"
            :exercise-name="historyExerciseName"
        />

        <!-- Edit Workout Log Dialog -->
        <AppDialog
            v-model:visible="showEdit"
            header="Edit Workout Log"
            modal
            :style="{ width: '28rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium"> Date </label>
                    <AppInputText
                        v-model="editForm.date"
                        class="w-full"
                        type="date"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Notes
                    </label>
                    <AppTextarea
                        v-model="editForm.notes"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton label="Cancel" text @click="showEdit = false" />
                    <AppButton label="Save" @click="saveEdit" />
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
            <p>Are you sure you want to delete this workout log?</p>
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
    </div>
</template>
