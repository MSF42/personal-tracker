<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import ConfirmDeleteDialog from '@/components/ConfirmDeleteDialog.vue';
import LogWorkoutDialog from '@/components/LogWorkoutDialog.vue';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import type { WorkoutLog } from '@/types/WorkoutLog';
import type { WorkoutRoutine } from '@/types/WorkoutRoutine';
import { formatDate } from '@/utils/format';

const {
    getWorkoutRoutines,
    createWorkoutRoutine,
    deleteWorkoutRoutine,
    getRoutineExercises,
} = useWorkoutRoutineApi();
const { getWorkoutLogs } = useWorkoutLogApi();
const { loading, withLoading } = useLoading();
const toast = useToast();
const router = useRouter();

const routines = ref<WorkoutRoutine[]>([]);
const workoutLogs = ref<WorkoutLog[]>([]);

const todayStr = new Date().toISOString().split('T')[0] as string;
const currentMonthPrefix = todayStr.slice(0, 7);

// --- Stats ---
const stats = computed(() => {
    const recentLogs = workoutLogs.value.filter((l) =>
        l.date.startsWith(currentMonthPrefix),
    ).length;
    const sorted = [...workoutLogs.value].sort((a, b) =>
        b.date.localeCompare(a.date),
    );
    const lastWorkout = sorted.length > 0 ? sorted[0]!.date : null;
    return {
        total: routines.value.length,
        recentLogs,
        lastWorkout,
    };
});

const routineLastPerformed = computed(() => {
    const map: Record<number, string> = {};
    for (const log of workoutLogs.value) {
        const existing = map[log.routine_id];
        if (!existing || log.date > existing) {
            map[log.routine_id] = log.date;
        }
    }
    return map;
});

// --- Add Routine (name only — the rest is edited on the routine's page) ---
const showAddDialog = ref(false);
const newRoutineName = ref('');
const addFormError = ref('');

function openAddDialog() {
    newRoutineName.value = '';
    addFormError.value = '';
    showAddDialog.value = true;
}

async function createAndOpen() {
    if (newRoutineName.value.trim() === '') {
        addFormError.value = 'Name is required';
        return;
    }
    const res = await createWorkoutRoutine({ name: newRoutineName.value });
    if (res.success && res.data) {
        showAddDialog.value = false;
        toast.showSuccess('Routine added');
        await router.push(`/strength/routines/${res.data.id}`);
    } else {
        addFormError.value = res.error?.message ?? 'Something went wrong';
    }
}

function openRoutine(id: number) {
    void router.push(`/strength/routines/${id}`);
}

// --- Delete ---
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);

function confirmDelete(id: number) {
    deletingId.value = id;
    showDeleteConfirm.value = true;
}

async function executeDelete() {
    if (deletingId.value) {
        const res = await deleteWorkoutRoutine(deletingId.value);
        if (res.success) {
            toast.showSuccess('Routine deleted');
        }
    }
    showDeleteConfirm.value = false;
    deletingId.value = null;
    await loadData();
}

// --- Log Workout Dialog ---
const showLogDialog = ref(false);
const loggingRoutine = ref<WorkoutRoutine | null>(null);

function openLogDialog(routine: WorkoutRoutine) {
    loggingRoutine.value = routine;
    showLogDialog.value = true;
}

async function loadLogs() {
    const logsRes = await getWorkoutLogs();
    if (logsRes.success && logsRes.data) workoutLogs.value = logsRes.data;
}

// --- Routine exercise counts (for the list column) ---
const routineExerciseCounts = ref<Record<number, number>>({});

async function loadExerciseCounts() {
    for (const routine of routines.value) {
        const res = await getRoutineExercises(routine.id);
        if (res.success && res.data) {
            routineExerciseCounts.value[routine.id] = res.data.length;
        }
    }
}

async function loadData() {
    const [routinesRes, logsRes] = await Promise.all([
        getWorkoutRoutines(),
        getWorkoutLogs(),
    ]);
    if (routinesRes.success && routinesRes.data)
        routines.value = routinesRes.data;
    else if (!routinesRes.success) toast.showError('Failed to load routines');
    if (logsRes.success && logsRes.data) workoutLogs.value = logsRes.data;
    await loadExerciseCounts();
}

onMounted(() => withLoading(loadData));
</script>

<template>
    <div>
        <h1 class="mb-6 text-2xl font-bold">Workout Routines</h1>

        <!-- Stats Cards -->
        <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <AppCard>
                <template #title>Total Routines</template>
                <template #content>
                    <div class="text-2xl font-bold">{{ stats.total }}</div>
                    <div class="text-surface-500 text-sm">
                        {{ stats.total === 1 ? 'routine' : 'routines' }}
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>Recent Logs</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ stats.recentLogs }}
                    </div>
                    <div class="text-surface-500 text-sm">this month</div>
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
            <h2 class="text-xl font-semibold">Routines</h2>
            <AppButton
                icon="pi pi-plus"
                label="Add Routine"
                @click="openAddDialog"
            />
        </div>

        <!-- Data Table -->
        <AppDataTable
            :loading="loading"
            :row-class="() => 'group'"
            sort-field="name"
            :sort-order="1"
            striped-rows
            :value="routines"
        >
            <template #empty>
                <div class="flex flex-col items-center py-10 text-center">
                    <i
                        class="pi pi-inbox text-surface-300 dark:text-surface-600 mb-3 text-4xl"
                    ></i>
                    <p class="text-surface-500 mb-3">No routines yet</p>
                    <AppButton
                        icon="pi pi-plus"
                        label="Add your first routine"
                        size="small"
                        @click="openAddDialog"
                    />
                </div>
            </template>
            <AppColumn field="name" header="Name" sortable>
                <template #body="{ data }">
                    <button
                        class="text-primary cursor-pointer font-medium hover:underline"
                        @click="openRoutine((data as WorkoutRoutine).id)"
                    >
                        {{ (data as WorkoutRoutine).name }}
                    </button>
                </template>
            </AppColumn>
            <AppColumn field="description" header="Description">
                <template #body="{ data }">
                    <span
                        v-if="(data as WorkoutRoutine).description"
                        class="line-clamp-1"
                    >
                        {{ (data as WorkoutRoutine).description }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn header="Exercises" style="width: 8rem">
                <template #body="{ data }">
                    <AppButton
                        :label="
                            String(
                                routineExerciseCounts[
                                    (data as WorkoutRoutine).id
                                ] ?? '...',
                            )
                        "
                        outlined
                        severity="secondary"
                        size="small"
                        @click="openRoutine((data as WorkoutRoutine).id)"
                    />
                </template>
            </AppColumn>
            <AppColumn header="Last Performed">
                <template #body="{ data }">
                    <span
                        v-if="routineLastPerformed[(data as WorkoutRoutine).id]"
                    >
                        {{
                            formatDate(
                                routineLastPerformed[
                                    (data as WorkoutRoutine).id
                                ]!,
                            )
                        }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn header="Actions" style="width: 10rem">
                <template #body="{ data }">
                    <div
                        class="flex justify-end gap-2 opacity-20 transition-opacity group-hover:opacity-100"
                    >
                        <AppButton
                            aria-label="Log workout"
                            icon="pi pi-play"
                            rounded
                            severity="success"
                            text
                            @click="openLogDialog(data as WorkoutRoutine)"
                        />
                        <AppButton
                            aria-label="Edit routine"
                            icon="pi pi-pencil"
                            rounded
                            severity="info"
                            text
                            @click="openRoutine((data as WorkoutRoutine).id)"
                        />
                        <AppButton
                            aria-label="Delete routine"
                            icon="pi pi-trash"
                            rounded
                            severity="danger"
                            text
                            @click="confirmDelete((data as WorkoutRoutine).id)"
                        />
                    </div>
                </template>
            </AppColumn>
        </AppDataTable>

        <!-- Add Routine Dialog (name only) -->
        <AppDialog
            v-model:visible="showAddDialog"
            header="Add Routine"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Name <span class="text-red-500">*</span>
                    </label>
                    <AppInputText
                        v-model="newRoutineName"
                        autofocus
                        class="w-full"
                        placeholder="e.g. Workout A — Squat focus"
                        @keyup.enter="createAndOpen"
                    />
                    <p v-if="addFormError" class="mt-1 text-sm text-red-500">
                        {{ addFormError }}
                    </p>
                    <p class="text-surface-500 mt-1 text-xs">
                        Add a description and exercises on the next screen.
                    </p>
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showAddDialog = false"
                    />
                    <AppButton label="Create" @click="createAndOpen" />
                </div>
            </div>
        </AppDialog>

        <!-- Log Workout Dialog -->
        <LogWorkoutDialog
            v-model:visible="showLogDialog"
            :routine-id="loggingRoutine?.id ?? null"
            :routine-name="loggingRoutine?.name ?? ''"
            @logged="loadLogs"
        />

        <!-- Delete Confirmation Dialog -->
        <ConfirmDeleteDialog
            v-model:visible="showDeleteConfirm"
            @confirm="executeDelete"
        >
            Are you sure you want to delete this routine?
        </ConfirmDeleteDialog>
    </div>
</template>
