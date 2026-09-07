<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import ConfirmDeleteDialog from '@/components/ConfirmDeleteDialog.vue';
import LogWorkoutDialog from '@/components/LogWorkoutDialog.vue';
import { useExerciseApi } from '@/composables/api/useExerciseApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
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
    updateWorkoutRoutine,
    createWorkoutRoutine,
    deleteWorkoutRoutine,
    getRoutineExercises,
    addRoutineExercise,
    removeRoutineExercise,
} = useWorkoutRoutineApi();
const { getWorkoutLogs } = useWorkoutLogApi();
const { getExercises } = useExerciseApi();
const { loading, withLoading } = useLoading();
const toast = useToast();
const router = useRouter();

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

const isFormValid = computed(() => form.name.trim() !== '');
const saveTooltip = computed(() =>
    isFormValid.value ? undefined : 'Name is required',
);

const form = reactive({
    name: '',
    description: '',
});

function resetForm() {
    form.name = '';
    form.description = '';
    editingId.value = null;
    formError.value = '';
    routineExercises.value = [];
    addExerciseForm.exerciseId = null;
    addExerciseForm.sets = 3;
    addExerciseForm.reps = 10;
}

function openAddDialog() {
    resetForm();
    showDialog.value = true;
}

async function openEditDialog(routine: WorkoutRoutine) {
    editingId.value = routine.id;
    form.name = routine.name;
    form.description = routine.description ?? '';
    formError.value = '';
    addExerciseForm.exerciseId = null;
    addExerciseForm.sets = 3;
    addExerciseForm.reps = 10;
    showDialog.value = true;
    await loadRoutineExercises(routine.id);
}

async function saveRoutine() {
    formError.value = '';
    if (editingId.value) {
        const payload: WorkoutRoutineUpdate = {
            name: form.name,
            description: form.description || null,
        };
        const res = await updateWorkoutRoutine(editingId.value, payload);
        if (res.success) {
            toast.showSuccess('Routine updated');
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
        if (res.success && res.data) {
            toast.showSuccess('Routine added');
            // Stay open: the exercises section below unlocks now that the
            // routine has an id, so exercises can be added right away.
            editingId.value = res.data.id;
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

// --- Exercises section (part of the same Add/Edit Routine dialog) ---
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

async function loadRoutineExercises(routineId: number) {
    const res = await getRoutineExercises(routineId);
    if (res.success && res.data) {
        routineExercises.value = res.data;
        routineExerciseCounts.value[routineId] = res.data.length;
    }
}

async function handleAddExercise() {
    if (!editingId.value || !addExerciseForm.exerciseId) return;
    const res = await addRoutineExercise(
        editingId.value,
        addExerciseForm.exerciseId,
        addExerciseForm.sets,
        addExerciseForm.reps,
    );
    if (res.success) {
        toast.showSuccess('Exercise added to routine');
        addExerciseForm.exerciseId = null;
        addExerciseForm.sets = 3;
        addExerciseForm.reps = 10;
        await loadRoutineExercises(editingId.value);
    }
}

async function handleRemoveExercise(exerciseId: number) {
    if (!editingId.value) return;
    const res = await removeRoutineExercise(editingId.value, exerciseId);
    if (res.success) {
        toast.showSuccess('Exercise removed from routine');
        await loadRoutineExercises(editingId.value);
    }
}

// --- Log Workout Dialog (shared component) ---
const showLogDialog = ref(false);
const loggingRoutine = ref<WorkoutRoutine | null>(null);

function openLogDialog(routine: WorkoutRoutine) {
    loggingRoutine.value = routine;
    showLogDialog.value = true;
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
    editingId.value ? `Edit ${form.name || 'Routine'}` : 'Add Routine',
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
                        @click="
                            router.push(
                                `/workout-routines/${(data as WorkoutRoutine).id}`,
                            )
                        "
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
                        @click="openEditDialog(data as WorkoutRoutine)"
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
                        class="flex gap-2 opacity-20 transition-opacity group-hover:opacity-100"
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
                            @click="openEditDialog(data as WorkoutRoutine)"
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

        <!-- Add/Edit Routine Dialog (details + exercises together) -->
        <AppDialog
            v-model:visible="showDialog"
            :header="dialogHeader"
            modal
            :style="{ width: '52rem', maxWidth: '94vw' }"
        >
            <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
                <!-- Left: routine details -->
                <div class="flex flex-col gap-4">
                    <div>
                        <label class="mb-1 block text-sm font-medium">
                            Name <span class="text-red-500">*</span>
                        </label>
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
                            rows="4"
                        />
                    </div>
                    <div class="flex justify-end">
                        <span v-tooltip.top="saveTooltip">
                            <AppButton
                                :disabled="!isFormValid"
                                label="Save"
                                @click="saveRoutine"
                            />
                        </span>
                    </div>
                </div>

                <!-- Right: exercises -->
                <div
                    class="border-surface-200 dark:border-surface-700 flex flex-col gap-4 border-t pt-4 md:border-t-0 md:border-l md:pt-0 md:pl-6"
                >
                    <div class="text-sm font-medium">Exercises</div>

                    <p v-if="!editingId" class="text-surface-500 text-sm">
                        Save the routine first to start adding exercises.
                    </p>
                    <template v-else>
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
                                    <span
                                        >{{ re.sets }} sets x
                                        {{ re.reps }} reps</span
                                    >
                                </div>
                            </div>
                            <AppButton
                                aria-label="Remove exercise from routine"
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
                            <div class="mb-2 text-sm font-medium">
                                Add Exercise
                            </div>
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
                                    <div class="min-w-0 flex-1">
                                        <label class="mb-1 block text-xs"
                                            >Sets</label
                                        >
                                        <AppInputNumber
                                            v-model="addExerciseForm.sets"
                                            fluid
                                            :min="1"
                                            show-buttons
                                        />
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <label class="mb-1 block text-xs"
                                            >Reps</label
                                        >
                                        <AppInputNumber
                                            v-model="addExerciseForm.reps"
                                            fluid
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
                    </template>
                </div>

                <div class="flex justify-end md:col-span-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showDialog = false"
                    />
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
