<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { useExerciseApi } from '@/composables/api/useExerciseApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { Exercise } from '@/types/Exercise';
import type { WorkoutLog } from '@/types/WorkoutLog';
import type {
    RoutineExercise,
    WorkoutRoutine,
    WorkoutRoutineCreate,
    WorkoutRoutineUpdate,
} from '@/types/WorkoutRoutine';
import { formatDate } from '@/utils/format';

const {
    getWorkoutRoutines,
    createWorkoutRoutine,
    updateWorkoutRoutine,
    deleteWorkoutRoutine,
    getRoutineExercises,
    addRoutineExercise,
    removeRoutineExercise,
} = useWorkoutRoutineApi();
const { getWorkoutLogs, createWorkoutLog, logSet } = useWorkoutLogApi();
const { getExercises } = useExerciseApi();
const { loading, withLoading } = useLoading();
const toast = useToast();
const { weightUnit, toKg } = useUnits();

const routines = ref<WorkoutRoutine[]>([]);
const workoutLogs = ref<WorkoutLog[]>([]);
const allExercises = ref<Exercise[]>([]);

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

// --- Routine Dialog state ---
const showDialog = ref(false);
const editingId = ref<number | null>(null);
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);
const formError = ref('');

const form = reactive({
    name: '',
    description: '',
});

function resetForm() {
    form.name = '';
    form.description = '';
    editingId.value = null;
    formError.value = '';
}

function openAddDialog() {
    resetForm();
    showDialog.value = true;
}

function openEditDialog(routine: WorkoutRoutine) {
    editingId.value = routine.id;
    form.name = routine.name;
    form.description = routine.description ?? '';
    formError.value = '';
    showDialog.value = true;
}

async function saveRoutine() {
    formError.value = '';
    if (!form.name.trim()) {
        formError.value = 'Name is required';
        return;
    }
    if (editingId.value) {
        const payload: WorkoutRoutineUpdate = {
            name: form.name,
            description: form.description || null,
        };
        const res = await updateWorkoutRoutine(editingId.value, payload);
        if (res.success) {
            toast.showSuccess('Routine updated');
            showDialog.value = false;
            await loadData();
        } else {
            formError.value = res.error?.message ?? 'Something went wrong';
        }
    } else {
        const payload: WorkoutRoutineCreate = {
            name: form.name,
            description: form.description || null,
        };
        const res = await createWorkoutRoutine(payload);
        if (res.success) {
            toast.showSuccess('Routine added');
            showDialog.value = false;
            await loadData();
        } else {
            formError.value = res.error?.message ?? 'Something went wrong';
        }
    }
}

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

// --- Manage Exercises Dialog ---
const showExercisesDialog = ref(false);
const managingRoutine = ref<WorkoutRoutine | null>(null);
const routineExercises = ref<RoutineExercise[]>([]);
const addExerciseForm = reactive({
    exerciseId: null as number | null,
    sets: 3,
    reps: 10,
});

const availableExercises = computed(() => {
    const usedIds = new Set(routineExercises.value.map((re) => re.id));
    return allExercises.value.filter((e) => !usedIds.has(e.id));
});

async function openExercisesDialog(routine: WorkoutRoutine) {
    managingRoutine.value = routine;
    addExerciseForm.exerciseId = null;
    addExerciseForm.sets = 3;
    addExerciseForm.reps = 10;
    showExercisesDialog.value = true;
    await loadRoutineExercises(routine.id);
}

async function loadRoutineExercises(routineId: number) {
    const res = await getRoutineExercises(routineId);
    if (res.success && res.data) {
        routineExercises.value = res.data;
        routineExerciseCounts.value[routineId] = res.data.length;
    }
}

async function handleAddExercise() {
    if (!managingRoutine.value || !addExerciseForm.exerciseId) return;
    const res = await addRoutineExercise(
        managingRoutine.value.id,
        addExerciseForm.exerciseId,
        addExerciseForm.sets,
        addExerciseForm.reps,
    );
    if (res.success) {
        toast.showSuccess('Exercise added to routine');
        addExerciseForm.exerciseId = null;
        addExerciseForm.sets = 3;
        addExerciseForm.reps = 10;
        await loadRoutineExercises(managingRoutine.value.id);
    }
}

async function handleRemoveExercise(exerciseId: number) {
    if (!managingRoutine.value) return;
    const res = await removeRoutineExercise(
        managingRoutine.value.id,
        exerciseId,
    );
    if (res.success) {
        toast.showSuccess('Exercise removed from routine');
        await loadRoutineExercises(managingRoutine.value.id);
    }
}

// --- Log Workout Dialog ---
const showLogDialog = ref(false);
const loggingRoutine = ref<WorkoutRoutine | null>(null);
const logExercises = ref<RoutineExercise[]>([]);
const logStep = ref<1 | 2>(1);
const workoutLogId = ref<number | null>(null);
const logForm = reactive({
    date: todayStr,
    notes: '',
});

interface SetEntry {
    exerciseId: number;
    exerciseName: string;
    setNumber: number;
    reps: number;
    weight: null | number;
    saved: boolean;
}

const setEntries = ref<SetEntry[]>([]);

async function openLogDialog(routine: WorkoutRoutine) {
    loggingRoutine.value = routine;
    logStep.value = 1;
    workoutLogId.value = null;
    logForm.date = todayStr;
    logForm.notes = '';
    setEntries.value = [];
    showLogDialog.value = true;

    const res = await getRoutineExercises(routine.id);
    if (res.success && res.data) {
        logExercises.value = res.data;
    }
}

async function createLog() {
    if (!loggingRoutine.value) return;
    const res = await createWorkoutLog(
        loggingRoutine.value.id,
        logForm.date,
        logForm.notes || null,
    );
    if (res.success && res.data) {
        workoutLogId.value = res.data.id;
        // Build set entries from routine exercises
        const entries: SetEntry[] = [];
        for (const ex of logExercises.value) {
            for (let s = 1; s <= ex.sets; s++) {
                entries.push({
                    exerciseId: ex.id,
                    exerciseName: ex.name,
                    setNumber: s,
                    reps: ex.reps,
                    weight: null,
                    saved: false,
                });
            }
        }
        setEntries.value = entries;
        logStep.value = 2;
        toast.showSuccess('Workout log created');
        await loadLogs();
    }
}

async function saveSet(entry: SetEntry) {
    if (!workoutLogId.value) return;
    const res = await logSet(
        workoutLogId.value,
        entry.exerciseId,
        entry.setNumber,
        entry.reps,
        entry.weight != null ? toKg(entry.weight) : null,
    );
    if (res.success) {
        entry.saved = true;
    }
}

async function saveAllAndClose() {
    const unsaved = setEntries.value.filter((e) => !e.saved);
    await Promise.all(unsaved.map((e) => saveSet(e)));
    showLogDialog.value = false;
}

function getExerciseGroups() {
    const groups: { exerciseId: number; name: string; sets: SetEntry[] }[] = [];
    for (const entry of setEntries.value) {
        let group = groups.find((g) => g.exerciseId === entry.exerciseId);
        if (!group) {
            group = {
                exerciseId: entry.exerciseId,
                name: entry.exerciseName,
                sets: [],
            };
            groups.push(group);
        }
        group.sets.push(entry);
    }
    return groups;
}

// --- Data loading ---
async function loadLogs() {
    const logsRes = await getWorkoutLogs();
    if (logsRes.success && logsRes.data) workoutLogs.value = logsRes.data;
}

// --- Routine exercise count helper ---
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
    const [routinesRes, logsRes, exercisesRes] = await Promise.all([
        getWorkoutRoutines(),
        getWorkoutLogs(),
        getExercises(),
    ]);
    if (routinesRes.success && routinesRes.data)
        routines.value = routinesRes.data;
    else if (!routinesRes.success) toast.showError('Failed to load routines');
    if (logsRes.success && logsRes.data) workoutLogs.value = logsRes.data;
    if (exercisesRes.success && exercisesRes.data)
        allExercises.value = exercisesRes.data;
    await loadExerciseCounts();
}

onMounted(() => withLoading(loadData));

const dialogHeader = computed(() =>
    editingId.value ? 'Edit Routine' : 'Add Routine',
);
</script>

<template>
    <div class="mx-auto max-w-6xl p-6">
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
            <AppColumn field="name" header="Name" sortable />
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
                        @click="openExercisesDialog(data as WorkoutRoutine)"
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
                    <div class="row-actions flex gap-2">
                        <AppButton
                            icon="pi pi-play"
                            rounded
                            severity="success"
                            text
                            @click="openLogDialog(data as WorkoutRoutine)"
                        />
                        <AppButton
                            icon="pi pi-pencil"
                            rounded
                            severity="info"
                            text
                            @click="openEditDialog(data as WorkoutRoutine)"
                        />
                        <AppButton
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

        <!-- Add/Edit Routine Dialog -->
        <AppDialog
            v-model:visible="showDialog"
            :header="dialogHeader"
            modal
            :style="{ width: '28rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">Name</label>
                    <AppInputText v-model="form.name" class="w-full" />
                    <p v-if="formError" class="mt-1 text-sm text-red-500">
                        {{ formError }}
                    </p>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Description
                    </label>
                    <AppTextarea
                        v-model="form.description"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showDialog = false"
                    />
                    <AppButton label="Save" @click="saveRoutine" />
                </div>
            </div>
        </AppDialog>

        <!-- Manage Exercises Dialog -->
        <AppDialog
            v-model:visible="showExercisesDialog"
            :header="`Exercises in ${managingRoutine?.name ?? ''}`"
            modal
            :style="{ width: '36rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <!-- Current exercises list -->
                <div
                    v-if="routineExercises.length === 0"
                    class="text-surface-500 text-center text-sm"
                >
                    No exercises in this routine yet.
                </div>
                <div
                    v-for="re in routineExercises"
                    :key="re.id"
                    class="border-surface-200 dark:border-surface-700 flex items-center justify-between rounded-lg border p-3"
                >
                    <div class="flex-1">
                        <div class="font-medium">{{ re.name }}</div>
                        <div
                            class="text-surface-500 flex items-center gap-2 text-sm"
                        >
                            <AppTag :value="re.muscle_group" />
                            <span>{{ re.sets }} sets x {{ re.reps }} reps</span>
                        </div>
                    </div>
                    <AppButton
                        icon="pi pi-trash"
                        rounded
                        severity="danger"
                        text
                        @click="handleRemoveExercise(re.id)"
                    />
                </div>

                <!-- Add exercise section -->
                <div
                    class="border-surface-200 dark:border-surface-700 rounded-lg border p-3"
                >
                    <div class="mb-2 text-sm font-medium">Add Exercise</div>
                    <div class="flex flex-col gap-2">
                        <AppSelect
                            v-model="addExerciseForm.exerciseId"
                            class="w-full"
                            option-label="name"
                            option-value="id"
                            :options="availableExercises"
                            placeholder="Select exercise..."
                        />
                        <div class="flex gap-2">
                            <div class="flex-1">
                                <label class="mb-1 block text-xs">Sets</label>
                                <AppInputNumber
                                    v-model="addExerciseForm.sets"
                                    class="w-full"
                                    :min="1"
                                    show-buttons
                                />
                            </div>
                            <div class="flex-1">
                                <label class="mb-1 block text-xs">Reps</label>
                                <AppInputNumber
                                    v-model="addExerciseForm.reps"
                                    class="w-full"
                                    :min="1"
                                    show-buttons
                                />
                            </div>
                        </div>
                        <AppButton
                            :disabled="!addExerciseForm.exerciseId"
                            icon="pi pi-plus"
                            label="Add"
                            size="small"
                            @click="handleAddExercise"
                        />
                    </div>
                </div>
            </div>
        </AppDialog>

        <!-- Log Workout Dialog -->
        <AppDialog
            v-model:visible="showLogDialog"
            :header="`Log Workout: ${loggingRoutine?.name ?? ''}`"
            modal
            :style="{ width: '40rem', maxWidth: '92vw' }"
        >
            <!-- Step 1: Date + Notes -->
            <div v-if="logStep === 1" class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">Date</label>
                    <AppInputText
                        v-model="logForm.date"
                        class="w-full"
                        type="date"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Notes
                    </label>
                    <AppTextarea
                        v-model="logForm.notes"
                        class="w-full"
                        placeholder="Optional notes..."
                        rows="2"
                    />
                </div>
                <div
                    v-if="logExercises.length === 0"
                    class="text-surface-500 text-sm"
                >
                    This routine has no exercises. Add exercises first.
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showLogDialog = false"
                    />
                    <AppButton
                        :disabled="logExercises.length === 0"
                        label="Start Workout"
                        @click="createLog"
                    />
                </div>
            </div>

            <!-- Step 2: Log Sets -->
            <div v-if="logStep === 2" class="flex flex-col gap-4">
                <div
                    v-for="group in getExerciseGroups()"
                    :key="group.exerciseId"
                    class="border-surface-200 dark:border-surface-700 rounded-lg border p-3"
                >
                    <div class="mb-2 font-medium">{{ group.name }}</div>
                    <div class="flex flex-col gap-2">
                        <div
                            v-for="entry in group.sets"
                            :key="entry.setNumber"
                            class="flex items-center gap-2"
                        >
                            <span class="text-surface-500 w-16 text-sm">
                                Set {{ entry.setNumber }}
                            </span>
                            <AppInputNumber
                                v-model="entry.reps"
                                class="w-24"
                                :disabled="entry.saved"
                                :min="0"
                                placeholder="Reps"
                            />
                            <span class="text-surface-500 text-xs">reps</span>
                            <AppInputNumber
                                v-model="entry.weight"
                                class="w-24"
                                :disabled="entry.saved"
                                :max-fraction-digits="1"
                                :min="0"
                                placeholder="Weight"
                            />
                            <span class="text-surface-500 text-xs">{{
                                weightUnit
                            }}</span>
                            <AppButton
                                v-if="!entry.saved"
                                icon="pi pi-check"
                                severity="success"
                                size="small"
                                text
                                @click="saveSet(entry)"
                            />
                            <i
                                v-else
                                class="pi pi-check-circle text-green-500"
                            />
                        </div>
                    </div>
                </div>
                <div class="flex justify-end">
                    <AppButton label="Done" @click="saveAllAndClose" />
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
            <p>Are you sure you want to delete this routine?</p>
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
